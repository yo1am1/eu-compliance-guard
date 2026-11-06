"""Signed decisions (2.0 bolt 018): a reviewer signs what they decided, against what text.

`sign` builds a canonical record of one applicability decision: the decision, its obligation,
the locked digests of the articles it cites, the digests of the evidence it relies on, and the
project's commit. It signs that record with the reviewer's own SSH key (`ssh-keygen -Y sign`,
Git's signing format) and stores it in `.eu-compliance-guard/signatures/`. `verify` checks each
signature against an allowed-signers file and says whether the signed record still matches the
current decision, law and evidence. Signing records accountability; it never makes a decision.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile

from . import articles, lawlock, models as m, revalidation as r

NAMESPACE = "eucg-decision"
FORMAT = "eucg-decision-v1"
TIMEOUT = 60
MAX_SIGNATURE_BYTES = 4 * 1024 * 1024


class SigningError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _commit(root: Path) -> str | None:
    try:
        done = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None
    value = done.stdout.strip()
    return value if done.returncode == 0 and len(value) in (40, 64) and value.isalnum() else None


def record(declarations: str | os.PathLike, decision_id: str, lock: m.LawLock | None) -> dict:
    """The canonical record a signature covers, built from the current files."""
    path = Path(declarations)
    declared = r.load_input(path)
    decision = next((item for item in declared.applicability_decisions if item.id == decision_id), None)
    if decision is None:
        raise SigningError("unknown-id")
    obligation = next((item for item in declared.obligations if item.id == decision.obligation.id), None)
    entries = {item.target_id: item for item in (lock.entries if lock else [])}
    law = []
    for pin in obligation.source_provisions if obligation else []:
        entry, key = entries.get(pin.source_target_id), articles.article_key(pin.locator)
        digest = next((item.digest for item in entry.articles if item.key == key), None) if entry else None
        law.append({"target": pin.source_target_id, "version": entry.version if entry else None,
                    "article": key, "digest": digest})
    evidence = {item.evidence.id: item.evidence.digest for item in declared.evidence}
    return {"format": FORMAT, "project_id": declared.project_id,
            "decision": decision.model_dump(mode="json"),
            "obligation": obligation.model_dump(mode="json") if obligation else None,
            "law": sorted(law, key=lambda item: (item["target"], item["article"] or "")),
            "evidence": [{"id": identity, "digest": evidence.get(identity)} for identity in sorted(decision.evidence_ids)],
            "commit": _commit(path.parent)}


def _signatures(declarations: Path) -> Path:
    return declarations.parent / "signatures"


def check_principal(principal: str) -> None:
    if not principal or any(char.isspace() for char in principal) or len(principal) > 256:
        raise SigningError("bad-principal")


def ssh_sign(data: bytes, key: str, namespace: str) -> str:
    """An armored `ssh-keygen -Y sign` signature over the bytes, with the signer's own key."""
    with tempfile.TemporaryDirectory(prefix="eucg-sign-") as folder:
        message = Path(folder) / "message"
        message.write_bytes(data)
        try:
            done = subprocess.run(["ssh-keygen", "-Y", "sign", "-f", key, "-n", namespace, str(message)],
                                  capture_output=True, timeout=TIMEOUT, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError):
            raise SigningError("signing-failed") from None
        signature = Path(str(message) + ".sig")
        if done.returncode != 0 or not signature.is_file():
            raise SigningError("signing-failed")
        return signature.read_text(encoding="ascii")


def ssh_verify(data: bytes, armored: str, allowed_signers: str, principal: str, namespace: str) -> bool:
    with tempfile.TemporaryDirectory(prefix="eucg-verify-") as scratch:
        sig = Path(scratch) / "message.sig"
        try:
            sig.write_text(armored, encoding="ascii")
            done = subprocess.run(["ssh-keygen", "-Y", "verify", "-f", allowed_signers, "-I", principal, "-n", namespace,
                                   "-s", str(sig)], input=data, capture_output=True, timeout=TIMEOUT)
        except (OSError, ValueError, subprocess.SubprocessError):
            return False
        return done.returncode == 0


def sign(declarations: str | os.PathLike, decision_id: str, key: str, principal: str, lock_path: str | None = None) -> Path:
    path = Path(declarations)
    lock = lawlock.read(lock_path or path.parent / lawlock.LOCK_NAME) if (lock_path or (path.parent / lawlock.LOCK_NAME).exists()) else None
    payload = record(path, decision_id, lock)
    decision = payload["decision"]
    if decision["applicability"] == "unresolved" or not decision["reviewer"]:
        raise SigningError("unreviewed-decision")  # only a decision a named reviewer recorded is signed
    check_principal(principal)
    armored = ssh_sign(_canonical(payload), key, NAMESPACE)
    folder = _signatures(path)
    folder.mkdir(mode=0o755, exist_ok=True)
    if folder.is_symlink():
        raise SigningError("unsafe-path")
    stored = {"format": FORMAT, "principal": principal, "payload": payload, "signature": armored}
    return lawlock.write_bytes(folder / f"{decision_id}.json",
                               (json.dumps(stored, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))


def verify(declarations: str | os.PathLike, allowed_signers: str, lock_path: str | None = None) -> list[dict]:
    path = Path(declarations)
    lock_file = Path(lock_path) if lock_path else path.parent / lawlock.LOCK_NAME
    lock = lawlock.read(lock_file) if lock_file.exists() else None
    results = []
    folder = _signatures(path)
    for file in sorted(folder.glob("*.json")) if folder.is_dir() and not folder.is_symlink() else []:
        try:
            with r._parent(file) as (fd, name):
                raw = r._read_file(fd, name, limit=MAX_SIGNATURE_BYTES, retain=True)
            if raw.content is None:
                raise OSError("not a regular file")
            stored = json.loads(raw.content.decode("utf-8"))
            payload, principal, armored = stored["payload"], stored["principal"], stored["signature"]
            decision_id = payload["decision"]["id"]
        except (OSError, ValueError, KeyError, TypeError, r.RevalidationError):
            results.append({"decision": file.stem, "signature": "invalid", "changed": ["unreadable signature file"]})
            continue
        if decision_id != file.stem:
            # A valid signature copied over another decision's file must not stand in for it.
            results.append({"decision": file.stem, "signature": "invalid", "changed": [f"file holds decision {decision_id}"]})
            continue
        valid = isinstance(principal, str) and isinstance(armored, str) and \
            ssh_verify(_canonical(payload), armored, allowed_signers, principal, NAMESPACE)
        try:
            current = record(path, decision_id, lock)
            changed = [part for part in ("decision", "obligation", "law", "evidence") if current[part] != payload[part]]
        except SigningError:
            changed = ["decision removed"]
        results.append({"decision": decision_id, "principal": principal, "signature": "valid" if valid else "invalid",
                        "commit": payload.get("commit"), "changed": changed})
    # A reviewed decision with no signature file is listed, so a missing signature is never silent.
    signed = {item["decision"] for item in results}
    for decision in r.load_input(path).applicability_decisions:
        if decision.reviewer and decision.applicability != "unresolved" and decision.id not in signed:
            results.append({"decision": decision.id, "signature": "missing", "changed": []})
    return sorted(results, key=lambda item: item["decision"])


def format_verify(results: list[dict]) -> str:
    if not results:
        return "No signed decisions."
    lines = []
    for item in results:
        if item["signature"] == "missing":
            lines.append(f"- {item['decision']}: reviewed but not signed")
        elif item["signature"] != "valid":
            lines.append(f"- {item['decision']}: signature INVALID for this allowed-signers file" +
                         (f" ({', '.join(item['changed'])})" if item.get("changed") else ""))
        elif item["changed"]:
            lines.append(f"- {item['decision']}: signed by {item['principal']}, but since then changed: {', '.join(item['changed'])}"
                         " — review and sign again")
        else:
            lines.append(f"- {item['decision']}: signed by {item['principal']}; decision, law and evidence unchanged")
    lines.append("A signature shows who recorded a decision against which text; it is not a compliance verdict.")
    return "\n".join(lines)
