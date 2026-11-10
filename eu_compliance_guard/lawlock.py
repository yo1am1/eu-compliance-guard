"""Law lockfile and change impact (2.0 bolt 017).

`lock` records, from a verified run's retained official text, each act's version, source digest
and a digest per article, in `.eu-compliance-guard/eu-law.lock`. `impact` rebuilds that record
from a newer run and lists the articles that changed, then the obligations, decisions and
requirements that cite them: exactly those need review again. Nothing is reopened or decided
here; the lock is evidence of what text a review saw. Offline, deterministic.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import articles, jurisdictions, models as m, revalidation as r

LOCK_NAME = "eu-law.lock"


def build(run_dir: str | os.PathLike) -> m.LawLock:
    from .view import catalogue, verify_run
    contents: dict[str, bytes] = {}
    bundle = verify_run(run_dir, contents)
    acts = catalogue(bundle, contents)
    targets = {item.id: item for item in bundle.declarations.source_targets}
    digests = {}
    for attempt in bundle.source_attempts:
        if attempt.retrieved_source and attempt.retrieval.artifact_path in contents:
            digests[attempt.source_target_id] = m.content_digest(contents[attempt.retrieval.artifact_path])
    for selected in bundle.declarations.sources:
        digests.setdefault(selected.target_id, selected.source.content_digest)
    entries = []
    for target_id in sorted(acts):
        target = targets.get(target_id)
        version = jurisdictions.version(target.intended_identifier, target.intended_url) if target else None
        entries.append(m.LawLockEntry(
            target_id=target_id, version=(version["id"] + ("@" + version["date"] if version["jurisdiction"] == "UK" and version["date"] else ""))
            if version else None, source_digest=digests[target_id],
            articles=[m.LawLockArticle(key=key, digest=m.content_digest(f"{item['title']}\n{item['text']}".encode("utf-8")))
                      for key, item in sorted(acts[target_id].items())]))
    return m.LawLock(schema_version=1, lock_version=1, project_id=bundle.project_id, run_id=bundle.run.id, entries=entries)


def to_bytes(lock: m.LawLock) -> bytes:
    return (json.dumps(lock.model_dump(mode="json"), indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def write(lock: m.LawLock, path: str | os.PathLike) -> Path:
    """Atomically create or replace the lockfile, never through a link."""
    return write_bytes(path, to_bytes(lock))


def write_bytes(path: str | os.PathLike, content: bytes, mode: int = 0o644) -> Path:
    """Atomically create or replace a project file, never through a link or over a folder."""
    path = Path(path)
    with r._parent(path) as (parent_fd, name):
        temporary = "." + name + ".tmp"
        try:
            os.unlink(temporary, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode, dir_fd=parent_fd)
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(fd)
        try:
            info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if not (info.st_mode & 0o170000 == 0o100000):  # an existing link or folder is never replaced
                os.unlink(temporary, dir_fd=parent_fd)
                raise r.RevalidationError("unsafe-path")
        except FileNotFoundError:
            pass
        os.replace(temporary, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        os.fsync(parent_fd)
    return path


def read(path: str | os.PathLike) -> m.LawLock:
    with r._parent(path) as (fd, name):
        raw = r._read_file(fd, name, limit=m.MAX_REQUEST_BYTES, retain=True)
    if raw.content is None:
        raise r.RevalidationError("io-failed")
    return m.parse_record(m.LawLock, raw.content)


def impact(old: m.LawLock, new: m.LawLock, declared: m.RevalidationInput) -> dict:
    """Articles that changed between two locks, and the declared records that cite them."""
    if old.project_id != new.project_id:
        raise r.RevalidationError("wrong-project")
    before = {item.target_id: item for item in old.entries}
    after = {item.target_id: item for item in new.entries}
    changes = []
    touched: dict[str, set[str]] = {}
    # A locked act whose text the newer run did not retain cannot be compared: that is no law change.
    unchecked = sorted(set(before) - set(after))
    for target_id in sorted(set(after)):
        a = {x.key: x.digest for x in before[target_id].articles} if target_id in before else {}
        b = {x.key: x.digest for x in after[target_id].articles} if target_id in after else {}
        changed = sorted(key for key in set(a) & set(b) if a[key] != b[key])
        added, removed = sorted(set(b) - set(a)), sorted(set(a) - set(b))
        version = (before[target_id].version if target_id in before else None,
                   after[target_id].version if target_id in after else None)
        if changed or added or removed or version[0] != version[1]:
            changes.append({"target": target_id, "version_before": version[0], "version_after": version[1],
                            "changed": changed, "added": added, "removed": removed})
        touched[target_id] = set(changed) | set(removed)
    obligations = []
    for obligation in declared.obligations:
        cited = sorted({f"{pin.source_target_id} {articles.article_key(pin.locator)}" for pin in obligation.source_provisions
                        if articles.article_key(pin.locator) in touched.get(pin.source_target_id, set())})
        if cited:
            obligations.append({"obligation": obligation.id, "cites": cited})
    not_compared = sorted(obligation.id for obligation in declared.obligations
                          if any(pin.source_target_id in unchecked for pin in obligation.source_provisions))
    affected = {item["obligation"] for item in obligations}
    decisions = sorted(item.id for item in declared.applicability_decisions if item.obligation.id in affected)
    requirements = sorted(item.id for item in declared.requirements if any(ref.id in affected for ref in item.obligation_refs))
    return {"lock_run": old.run_id, "new_run": new.run_id, "changes": changes, "obligations": obligations,
            "decisions_to_review": decisions, "requirements_to_review": requirements,
            "not_retained": unchecked, "obligations_not_compared": not_compared}


def format_impact(report: dict) -> str:
    unchecked = []
    if report["not_retained"]:
        unchecked.append(f"Not compared: the newer run did not retain the text of {', '.join(report['not_retained'])}"
                         + (f"; obligations citing it ({', '.join(report['obligations_not_compared'])}) were not checked."
                            if report["obligations_not_compared"] else "."))
    if not report["changes"]:
        return "\n".join([f"No locked article changed between {report['lock_run']} and {report['new_run']}.", *unchecked])
    lines = [f"Law changes since the lock ({report['lock_run']} → {report['new_run']}):"]
    for item in report["changes"]:
        version = (f" (version {item['version_before'] or 'not recorded'} → {item['version_after'] or 'not recorded'})"
                   if item["version_before"] != item["version_after"] else "")
        parts = [f"changed {', '.join(item['changed'])}" if item["changed"] else "",
                 f"added {', '.join(item['added'])}" if item["added"] else "",
                 f"removed {', '.join(item['removed'])}" if item["removed"] else ""]
        lines.append(f"- {item['target']}{version}: " + ("; ".join(part for part in parts if part) or "same articles"))
    if report["obligations"]:
        lines.append("Review again (they cite a changed or removed article):")
        lines += [f"- obligation {item['obligation']} ({', '.join(item['cites'])})" for item in report["obligations"]]
        if report["decisions_to_review"]:
            lines.append(f"- applicability decisions: {', '.join(report['decisions_to_review'])}")
        if report["requirements_to_review"]:
            lines.append(f"- requirements: {', '.join(report['requirements_to_review'])}")
    else:
        lines.append("No declared obligation cites a changed or removed article.")
    lines += unchecked
    lines.append("Nothing was reopened or decided; a reviewer re-reads the changed text and records the outcome.")
    return "\n".join(lines)
