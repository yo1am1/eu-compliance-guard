"""Obligation packs (2.0 bolt 020): reviewed obligations, reused across projects.

A pack is one versioned JSON file: obligations with their conditions, exceptions and exact
article pins, the source targets those pins name, and the article digests the reviewer read.
`pack build` drafts one from a project's declarations; `pack sign` signs the file with the
reviewer's SSH key (namespace `eucg-pack`) beside it as `<pack>.sig`; `pack verify` checks
that signature; `pack import` adds the pack's targets and obligations to a project.

Import only adds candidate obligations. It never maps a requirement and never records an
applicability decision: whether an obligation applies stays a named reviewer's decision.
A signature says who reviewed which pack version against which text, not that it is right.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import grounding, lawlock, models as m, revalidation as r, signing
from .notice import LEGAL_NOTICE

NAMESPACE = "eucg-pack"
STARTERS = Path(__file__).resolve().parent / "starter_packs"
SIG_FORMAT = "eucg-pack-signature-v1"


class PackError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def to_bytes(pack: m.ObligationPack) -> bytes:
    return (json.dumps(pack.model_dump(mode="json"), indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def _read(path: str | os.PathLike, limit: int = m.MAX_REQUEST_BYTES) -> bytes:
    with r._parent(path) as (fd, name):
        raw = r._read_file(fd, name, limit=limit, retain=True)
    if raw.content is None:
        raise PackError("io-failed")
    return raw.content


def load(path: str | os.PathLike) -> tuple[m.ObligationPack, bytes]:
    content = _read(path)
    return m.parse_record(m.ObligationPack, content), content


def build(declarations: str | os.PathLike, pack_id: str, title: str, obligation_ids: list[str] | None = None,
          revision: int = 0, lock_path: str | None = None, status: str = "draft") -> m.ObligationPack:
    path = Path(declarations)
    declared = r.load_input(path)
    chosen = [item for item in declared.obligations if not obligation_ids or item.id in obligation_ids]
    if obligation_ids and {item.id for item in chosen} != set(obligation_ids):
        raise PackError("unknown-id")
    if not chosen:
        raise PackError("invalid-input")
    cited = {pin.source_target_id for item in chosen for pin in item.source_provisions}
    articles: dict[str, set[str]] = {}
    from .articles import article_key
    for item in chosen:
        for pin in item.source_provisions:
            key = article_key(pin.locator)
            if key:
                articles.setdefault(pin.source_target_id, set()).add(key)
    lock_file = Path(lock_path) if lock_path else path.parent / lawlock.LOCK_NAME
    law = []
    if lock_file.exists():
        for entry in lawlock.read(lock_file).entries:
            if entry.target_id in cited:
                law.append(m.LawLockEntry(target_id=entry.target_id, version=entry.version, source_digest=entry.source_digest,
                                          articles=[a for a in entry.articles if a.key in articles.get(entry.target_id, set())]))
    return m.ObligationPack(
        schema_version=1, pack_version=1, id=pack_id, revision=revision, title=title, status=status,
        synthetic=declared.synthetic, source_targets=sorted((t for t in declared.source_targets if t.id in cited),
                                                            key=lambda t: t.id),
        obligations=sorted((_portable(item) for item in chosen), key=lambda item: item.id), law=law,
        limitations=["Candidate obligations only: whether each applies is a named reviewer's decision.",
                     "Pins name a target and an article, not one project's reviewed source copy; controls and "
                     "overlays stay with the project.", LEGAL_NOTICE])


def _portable(item: m.Obligation) -> m.Obligation:
    """The obligation without what belongs to one project: its selected source copies, controls and overlays."""
    return item.model_copy(update={
        "source_provisions": [pin.model_copy(update={"source_id": None, "revision": None}) for pin in item.source_provisions],
        "control_ids": [], "overlay_ids": []})


def write(pack: m.ObligationPack, path: str | os.PathLike) -> Path:
    return lawlock.write_bytes(path, to_bytes(pack))


def _sig_path(path: str | os.PathLike) -> Path:
    return Path(str(path) + ".sig")


def sign(path: str | os.PathLike, key: str, principal: str) -> Path:
    signing.check_principal(principal)
    pack, content = load(path)
    stored = {"format": SIG_FORMAT, "pack": pack.id, "revision": pack.revision, "principal": principal,
              "digest": m.content_digest(content), "signature": signing.ssh_sign(content, key, NAMESPACE)}
    return lawlock.write_bytes(_sig_path(path), (json.dumps(stored, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def verify(path: str | os.PathLike, allowed_signers: str, loaded: tuple[m.ObligationPack, bytes] | None = None) -> dict:
    """Check the pack's signature over exactly these bytes (read once, or passed in by the caller)."""
    pack, content = loaded or load(path)
    result = {"pack": pack.id, "revision": pack.revision, "status": pack.status, "digest": m.content_digest(content),
              "principal": None, "signature": "missing"}
    try:
        stored = json.loads(_read(_sig_path(path), 64 * 1024).decode("utf-8"))
        principal, armored = stored["principal"], stored["signature"]
    except PackError:
        return result
    except (UnicodeDecodeError, ValueError, KeyError, TypeError):
        return result | {"signature": "invalid"}
    valid = isinstance(principal, str) and isinstance(armored, str) and \
        signing.ssh_verify(content, armored, allowed_signers, principal, NAMESPACE)
    return result | {"principal": principal if isinstance(principal, str) else None,
                     "signature": "valid" if valid else "invalid"}


def import_pack(declarations: str | os.PathLike, path: str | os.PathLike, allowed_signers: str | None,
                unsigned: bool = False, write: bool = True) -> dict:
    loaded = load(path)
    pack = loaded[0]
    # The bytes verified are the bytes imported: the file is read once.
    checked = verify(path, allowed_signers, loaded) if allowed_signers else None
    if checked and checked["signature"] != "valid":
        raise PackError("bad-signature")
    if checked is None and not unsigned:
        raise PackError("unsigned-pack")  # an unverified pack is imported only when asked for explicitly
    target = Path(declarations)
    declared = r.load_input(target)
    data = json.loads(m.canonical_json(declared))
    added = {"source_targets": [], "obligations": []}
    # An obligation already in the project is the same one when it differs only in what belongs to
    # the project (its own source copies, controls and overlays), as in the project a pack came from.
    own = {item.id: _portable(item).model_dump(mode="json") for item in declared.obligations}
    for kind, records in (("source_targets", pack.source_targets), ("obligations", pack.obligations)):
        present = {item["id"]: own.get(item["id"], item) if kind == "obligations" else item for item in data[kind]}
        for record in records:
            value = record.model_dump(mode="json")
            if record.id not in present:
                data[kind].append(value)
                added[kind].append(record.id)
            elif present[record.id] != value:
                raise PackError("pack-conflict")  # a different record with the same id is never overwritten
    mismatches = []
    lock_file = target.parent / lawlock.LOCK_NAME
    if pack.law and lock_file.exists():
        locked = {(entry.target_id, item.key): item.digest for entry in lawlock.read(lock_file).entries for item in entry.articles}
        for entry in pack.law:
            for item in entry.articles:
                digest = locked.get((entry.target_id, item.key))
                if digest is not None and digest != item.digest:
                    mismatches.append(f"{entry.target_id} {item.key}")
    content = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    m.parse_record(m.RevalidationInput, content)  # never write what does not validate
    if write and (added["source_targets"] or added["obligations"]):
        with r._parent(target) as (parent_fd, name):
            grounding._replace(parent_fd, name, content)
    return {"pack": pack.id, "revision": pack.revision, "status": pack.status,
            "signed_by": checked["principal"] if checked else None, "added": added, "law_mismatches": mismatches}


def starters() -> list[dict]:
    """The draft starter packs shipped with the tool: unreviewed, unsigned, imported with --unsigned."""
    found = []
    for path in sorted(STARTERS.glob("*.pack.json")):
        pack, _ = load(path)
        found.append({"path": str(path), "id": pack.id, "title": pack.title, "status": pack.status,
                      "obligations": len(pack.obligations), "targets": [item.id for item in pack.source_targets]})
    return found


def format_starters(found: list[dict]) -> str:
    lines = [f"- {item['id']} ({item['status']}, {item['obligations']} obligations): {item['title']}\n    {item['path']}"
             for item in found]
    lines.append("Drafts written with AI assistance, reviewed by no one, with no guarantee. Import one with "
                 "`pack import <path> --unsigned`; it adds candidate obligations only.")
    return "\n".join(lines)


def format_verify(result: dict) -> str:
    head = f"Pack {result['pack']} revision {result['revision']} ({result['status']}, {result['digest']})"
    if result["signature"] == "valid":
        return f"{head}: signed by {result['principal']}."
    if result["signature"] == "missing":
        return f"{head}: not signed."
    return f"{head}: signature INVALID for this allowed-signers file."


def format_import(result: dict) -> str:
    added = result["added"]
    lines = [f"Pack {result['pack']} revision {result['revision']} ("
             + (f"signed by {result['signed_by']}" if result["signed_by"] else "UNSIGNED, imported on request") + ")",
             f"- added {len(added['obligations'])} obligation(s): {', '.join(added['obligations']) or 'none'}",
             f"- added {len(added['source_targets'])} source target(s): {', '.join(added['source_targets']) or 'none'}"]
    if result["law_mismatches"]:
        lines.append("- the pack was reviewed against different text of: " + ", ".join(result["law_mismatches"])
                     + "; read those articles again before relying on it")
    lines.append("No requirement was mapped and no applicability was decided. Map requirements with accept, "
                 "then record decisions as a named reviewer.")
    return "\n".join(lines)
