"""Accept an article suggestion in one step (1.5 bolt 007): `accept REQ=TARGET:Article N`.

The requirement gains a candidate obligation that pins the article: an existing obligation
pinning the same target and article is reused, otherwise one is created. Revisions rise and
every pin follows. Applicability is never decided here: with no applicability decision the
obligation stays unresolved until a named reviewer records one. The declarations file is
rewritten only if the result validates, atomically and never through a link.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import articles, grounding, models as m, revalidation as r


class MappingError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def parse(value: str) -> tuple[str, str, str]:
    """'req-1=target-gdpr:Article 17' -> ('req-1', 'target-gdpr', 'Article 17'). Target ids may hold ':'."""
    requirement, separator, rest = value.partition("=")
    target, colon, locator = rest.rpartition(":")
    if not separator or not colon or not requirement or not target or articles.article_key(locator) is None:
        raise MappingError("bad-mapping")
    return requirement, target, articles.article_key(locator)


def _slug(text: str) -> str:
    return "".join(char if char.isascii() and char.isalnum() else "-" for char in text.lower()).strip("-")


def known_articles(path: str | os.PathLike, declared: m.RevalidationInput, target_id: str) -> set[str] | None:
    """The article keys of a target's text, from the law lock and the declared source copies.

    None when there is no text to check against (no lock entry and no readable source)."""
    from . import lawlock
    path = Path(path)
    keys, checked = set(), False
    lock = path.parent / lawlock.LOCK_NAME
    if lock.is_file():
        for entry in lawlock.read(lock).entries:
            if entry.target_id == target_id:
                keys.update(article.key for article in entry.articles)
                checked = True
    selected = [item for item in declared.sources if item.target_id == target_id and item.file]
    if selected:
        with r._parent(path) as (parent_fd, _), r.files_root(declared, parent_fd) as root_fd:
            for item in selected:
                observation = r._read_file(root_fd, item.file.path, limit=r.MAX_FILE_BYTES, retain=True)
                if observation.content is None or observation.digest != item.source.content_digest:
                    continue
                parsed = articles.parse(observation.content, item.media_type)
                if parsed:
                    keys.update(parsed)
                    checked = True
    return keys if checked else None


def accept(path: str | os.PathLike, value: str, *, write: bool = True) -> dict:
    requirement_id, target_id, locator = parse(value)
    path = Path(path)
    declared = r.load_input(path)
    requirement = next((item for item in declared.requirements if item.id == requirement_id), None)
    target = next((item for item in declared.source_targets if item.id == target_id), None)
    if requirement is None or target is None:
        raise MappingError("unknown-id")
    known = known_articles(path, declared, target_id)
    if known is not None and locator not in known:
        raise MappingError("unknown-article")
    data = json.loads(m.canonical_json(declared))
    existing = next((item for item in data["obligations"]
                     if any(pin["source_target_id"] == target_id and articles.article_key(pin["locator"]) == locator
                            for pin in item["source_provisions"])), None)
    created = existing is None
    if created:
        identity = f"obligation-{_slug(target_id)}-{_slug(locator)}"[:128]
        taken = {item["id"] for item in data["obligations"]}
        suffix = 2
        while identity in taken:
            identity = f"obligation-{_slug(target_id)}-{_slug(locator)}-{suffix}"[:128]
            suffix += 1
        existing = {"id": identity, "revision": 0, "family": target.family,
                    "classification": "duty" if target.intended_type in r.BINDING_SOURCE_TYPES else "recommendation",
                    "source_provisions": [{"source_target_id": target_id, "source_id": None, "revision": None, "locator": locator}],
                    "conditions": [], "exceptions": [], "overlay_ids": [], "control_ids": [], "required_methods": [],
                    "limitations": []}
        data["obligations"].append(existing)
    record = next(item for item in data["requirements"] if item["id"] == requirement_id)
    linked = any(ref["id"] == existing["id"] for ref in record["obligation_refs"])
    if not linked:
        record["obligation_refs"].append({"id": existing["id"], "revision": existing["revision"]})
        record["revision"] += 1
        grounding._bump_pins(data, {requirement_id: (record["revision"] - 1, record["revision"])})
    content = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    m.parse_record(m.RevalidationInput, content)  # never write what does not validate
    if write and not linked:
        with r._parent(path) as (parent_fd, name):
            grounding._replace(parent_fd, name, content)
    return {"requirement": requirement_id, "obligation": existing["id"], "target": target_id, "locator": locator,
            "created": created, "already_linked": linked, "checked_against_text": known is not None}


def format_result(result: dict) -> str:
    if result["already_linked"]:
        return f"{result['requirement']} already maps to {result['obligation']}; nothing changed."
    how = "new candidate obligation" if result["created"] else "existing candidate obligation"
    unchecked = ("" if result.get("checked_against_text", True) else
                 f"{result['locator']} was not checked against the act: {result['target']} has no retained text or lock entry yet.\n")
    return (f"{result['requirement']} now maps to {result['obligation']} ({how}, {result['target']} {result['locator']}).\n"
            + unchecked +
            "Applicability stays unresolved until a named reviewer records a decision; add its review methods, then run check.")
