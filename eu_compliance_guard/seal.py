"""Tamper-evident run log (2.6): `.eu-compliance-guard/runs.log`.

A run's own checksums only detect accidental change: whoever can write the run folder can rewrite
a report and its checksums. `seal` appends one line per run to a log kept with the project: the
run's id, the digest of its completion marker (which lists every artifact's digest), and the
digest of the previous line. Changing a sealed run, or any earlier line, breaks the chain.

The log is evidence only against someone who cannot also rewrite the log. Commit it to Git, so a
rewrite needs a visible history change, or sign entries with an SSH key (`--key`), so it needs
the key. `seal --check` verifies the chain, each sealed run still on this machine, and signatures.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import files, models as m, revalidation as r, signing
from .errors import CodedError

LOG_NAME = "runs.log"
NAMESPACE = "eucg-run"
MAX_LOG_BYTES = 4 * 1024 * 1024
MARKER_BYTES = 64 * 1024


class SealError(CodedError):
    pass


def _marker(run_dir: Path) -> tuple[str, str] | None:
    """(run id, digest of the completion marker) of a run folder, or None when it has no readable marker."""
    try:
        with r._parent(run_dir / "complete.json") as (fd, name):
            observed = r._read_file(fd, name, limit=MARKER_BYTES, retain=True)
        if observed.content is None:
            return None
        return m.parse_record(m.RunCompletion, observed.content).run_id, observed.digest
    except (OSError, ValueError, r.RevalidationError):
        return None


def _read(path: Path) -> list[tuple[m.SealEntry, str]]:
    """Each entry with its exact line. A line that does not parse makes the whole log invalid."""
    try:
        with r._parent(path) as (fd, name):
            observed = r._read_file(fd, name, limit=MAX_LOG_BYTES, retain=True)
    except r.RevalidationError:
        raise SealError("unsafe-path") from None
    if observed.availability == "missing":
        return []
    if observed.content is None:
        raise SealError("unsafe-path")
    try:
        lines = observed.content.decode("utf-8").splitlines()
        return [(m.parse_record(m.SealEntry, line.encode("utf-8")), line) for line in lines]
    except ValueError:
        raise SealError("invalid-seal-log") from None


def _digest(line: str) -> str:
    return m.content_digest(line.encode("utf-8"))


def _signed_part(entry: dict) -> bytes:
    return signing._canonical({key: value for key, value in entry.items() if key != "signature"})


def seal(declarations: str | os.PathLike, run_dir: str | os.PathLike, key: str | None = None,
         principal: str | None = None) -> dict:
    """Append the run to the log. Sealing the same run again changes nothing."""
    from .view import verify_run
    declarations = Path(declarations)
    bundle = verify_run(run_dir)  # only an intact run is sealed
    if bundle.project_id != r.load_input(declarations).project_id:
        raise SealError("wrong-project")
    run_id, marker = _marker(Path(run_dir)) or (None, None)
    if run_id is None:
        raise SealError("incomplete-run")
    path = declarations.parent / LOG_NAME
    entries = _read(path)
    for entry, _ in entries:
        if entry.run_id == run_id:
            if entry.marker != marker:
                raise SealError("seal-conflict")  # this run id is already sealed with other contents
            return {"path": str(path), "run_id": run_id, "seq": entry.seq, "already": True, "signed": entry.signature is not None}
    record = {"schema_version": 1, "seq": len(entries) + 1, "project_id": bundle.project_id, "run_id": run_id,
              "marker": marker, "previous": _digest(entries[-1][1]) if entries else None,
              "principal": None, "signature": None}
    if key is not None:
        signing.check_principal(principal or "")
        record["principal"] = principal
        record["signature"] = signing.ssh_sign(_signed_part(record), key, NAMESPACE)
    line = json.dumps(m.SealEntry.model_validate(record).model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
    content = "".join(text + "\n" for _, text in entries) + line + "\n"
    files.write_bytes(path, content.encode("utf-8"))
    return {"path": str(path), "run_id": run_id, "seq": record["seq"], "already": False, "signed": key is not None}


def check(declarations: str | os.PathLike, state: str | os.PathLike | None, allowed_signers: str | None = None) -> dict:
    """The chain, each sealed run still in `state`, and signatures. `ok` is False on any break."""
    from .view import ViewError, verify_run
    entries = _read(Path(declarations).parent / LOG_NAME)
    local: dict[str, list[tuple[Path, str]]] = {}  # a run id can be in several folders: a copy must not hide a change
    for folder in sorted(Path(state).iterdir()) if state and Path(state).is_dir() else []:
        found = _marker(folder) if folder.name.startswith("run-") and folder.is_dir() and not folder.is_symlink() else None
        if found:
            local.setdefault(found[0], []).append((folder, found[1]))
    results, previous = [], None
    for number, (entry, line) in enumerate(entries, 1):
        chain = entry.seq == number and entry.previous == previous
        previous = _digest(line)
        copies = local.get(entry.run_id, [])
        if not copies:
            run = "not on this machine"
        elif any(marker != entry.marker for _, marker in copies):
            run = "changed"
        else:
            try:
                for folder, _ in copies:
                    verify_run(folder)
                run = "intact"
            except ViewError:
                run = "changed"
        signature = "none"
        if entry.signature is not None:
            signature = "unverified" if allowed_signers is None else "valid" if signing.ssh_verify(
                _signed_part(entry.model_dump(mode="json")), entry.signature, allowed_signers, entry.principal or "",
                NAMESPACE) else "invalid"
        results.append({"seq": entry.seq, "run_id": entry.run_id, "chain": chain, "run": run, "signature": signature,
                        "principal": entry.principal})
    sealed = {entry.run_id for entry, _ in entries}
    return {"entries": results, "unsealed": sorted(set(local) - sealed), "signatures_checked": allowed_signers is not None,
            "ok": all(item["chain"] and item["run"] != "changed" and item["signature"] != "invalid" for item in results)}


def format_check(report: dict) -> str:
    if not report["entries"]:
        lines = ["No sealed runs: runs.log is empty or missing. `seal` adds the latest run."]
    else:
        lines = []
        for item in report["entries"]:
            # An unverified signer name is only a claim in the log, so it is not printed. With an allowed-signers
            # file an entry without a signature is named: removing signatures must not look like a clean log.
            signed = {"none": "; NOT signed" if report.get("signatures_checked") else "",
                      "unverified": "; signed (not verified: give --allowed-signers)",
                      "valid": f"; signature of {item['principal']} valid", "invalid": "; signature INVALID"}[item["signature"]]
            state = {"intact": "run intact", "changed": "run CHANGED since it was sealed",
                     "not on this machine": "run not on this machine (not compared)"}[item["run"]]
            lines.append(f"- {item['seq']}. {item['run_id']}: " + ("" if item["chain"] else "CHAIN BROKEN here; ") + state + signed)
    if report["unsealed"]:
        lines.append(f"Not sealed: {', '.join(report['unsealed'])}.")
    lines.append("The log proves nothing against someone who can rewrite it too: commit runs.log to Git, or sign entries.")
    return "\n".join(lines)
