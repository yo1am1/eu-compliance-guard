"""Imports (2.0 bolt 019): results of other tools, kept as untrusted evidence.

`import-evidence --kind wec|sarif FILE` reads an EDPS Website Evidence Collector inspection
(`inspection.json`) or a SARIF 2.1 log. It keeps a copy and a digest-named summary, grouped
by the concepts the review uses (tracking, third parties, security and others), under
`.eu-compliance-guard/imports/`. It never changes the declarations. A reviewer reads the
summary, and may then declare the copy as evidence by hand. Everything inside an import is
untrusted tool output: it is quoted, cut short and never followed. An empty import shows only
that the tool reported nothing, never that the project complies.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import lawlock, models as m, prcheck, revalidation as r

FORMAT = "eucg-import-v1"
KINDS = ("wec", "sarif")
MAX_BYTES = 32 * 1024 * 1024
MAX_EXAMPLES = 5
MAX_TEXT = 160


class ImportFailure(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _plain(value) -> str:
    """Untrusted text, shown as one short line without control characters."""
    text = "".join(char if char.isprintable() else " " for char in str(value))
    text = " ".join(text.split())
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT - 1] + "…"


def _add(found: dict, concept: str, example: str) -> None:
    entry = found.setdefault(concept, {"count": 0, "examples": set()})
    entry["count"] += 1
    entry["examples"].add(_plain(example))


def _list(value) -> list:
    return value if isinstance(value, list) else []


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _wec(data: dict) -> tuple[str, dict, list[str]]:
    found: dict = {}
    for cookie in _list(data.get("cookies")):
        cookie = _dict(cookie)
        party = "first-party" if cookie.get("firstPartyStorage") else "third-party"
        _add(found, "tracking", f"cookie {cookie.get('name', '?')} ({party}, {cookie.get('domain', '?')})")
    for origin, items in sorted(_dict(data.get("localStorage")).items()):
        for key in sorted(_dict(items)):
            _add(found, "tracking", f"localStorage {key} ({origin})")
    for beacon in _list(data.get("beacons")):
        beacon = _dict(beacon)
        _add(found, "tracking", f"beacon {beacon.get('url', '?')}" + (f" ({beacon['listName']})" if beacon.get("listName") else ""))
    hosts = _dict(_dict(data.get("hosts")).get("requests"))
    for host in _list(hosts.get("thirdParty")):
        _add(found, "third_party", f"request to third-party host {host}")
    connection = _dict(data.get("secure_connection"))
    notes = []
    if connection.get("https_support") is False or connection.get("https_redirect") is False:
        _add(found, "security", "HTTPS not supported or not enforced by redirect")
    for form in _list(data.get("unsafeForms")):
        form = _dict(form)
        _add(found, "security", f"form submitted without TLS: {form.get('action', form.get('id', '?'))}")
    if not any(key in data for key in ("cookies", "beacons", "hosts", "localStorage")):
        notes.append("No cookies, beacons, hosts or storage keys in this file: is it a WEC inspection.json?")
    subject = _plain(data.get("uri_ins") or data.get("uri_dest") or "unknown site")
    return f"EDPS Website Evidence Collector inspection of {subject}", found, notes


def _sarif(data: dict) -> tuple[str, dict, list[str]]:
    found: dict = {}
    tools, notes = [], []
    for run in _list(data.get("runs")):
        run = _dict(run)
        driver = _dict(_dict(run.get("tool")).get("driver"))
        tools.append(_plain(driver.get("name", "unknown tool")))
        rules = {_dict(rule).get("id"): _dict(rule) for rule in _list(driver.get("rules"))}
        for result in _list(run.get("results")):
            result = _dict(result)
            rule_id = result.get("ruleId") if isinstance(result.get("ruleId"), str) else ""
            rule = rules.get(rule_id, {})
            message = _dict(result.get("message")).get("text", "")
            tags = _list(_dict(rule.get("properties")).get("tags")) + _list(_dict(result.get("properties")).get("tags"))
            text = " ".join(str(part) for part in [rule_id, rule.get("name", ""), message, *tags])
            where = ""
            for location in _list(result.get("locations"))[:1]:
                physical = _dict(_dict(location).get("physicalLocation"))
                uri = _dict(physical.get("artifactLocation")).get("uri", "")
                line = _dict(physical.get("region")).get("startLine")
                where = f" at {uri}" + (f":{line}" if isinstance(line, int) and not isinstance(line, bool) else "")
            example = f"{result.get('level', 'warning')} {rule_id or 'unnamed rule'}{where}: {message}"
            concepts = prcheck.concepts_in(text) or ["unclassified"]
            for concept in concepts:
                _add(found, concept, example)
    if not tools:
        notes.append("No SARIF runs in this file.")
    return f"SARIF results from {', '.join(sorted(set(tools))) or 'no tool'}", found, notes


def summarise(content: bytes, kind: str) -> dict:
    if kind not in KINDS:
        raise ImportFailure("invalid-input")
    try:
        data = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise ImportFailure("invalid-input") from None
    if not isinstance(data, dict):
        raise ImportFailure("invalid-input")
    title, found, notes = (_wec if kind == "wec" else _sarif)(data)
    concepts = {key: {"label": prcheck.CONCEPTS[key][0] if key in prcheck.CONCEPTS else "Not matched to a concept",
                      "count": value["count"], "examples": sorted(value["examples"])[:MAX_EXAMPLES]}
                for key, value in sorted(found.items())}
    return {"format": FORMAT, "kind": kind, "title": title, "digest": m.content_digest(content), "untrusted": True,
            "concepts": concepts, "notes": notes}


def import_file(declarations: str | os.PathLike, path: str | os.PathLike, kind: str) -> tuple[Path, dict]:
    with r._parent(path) as (fd, name):
        raw = r._read_file(fd, name, limit=MAX_BYTES, retain=True)
    if raw.content is None:
        raise ImportFailure("io-failed")  # missing, not a regular file, or changed while read
    summary = summarise(raw.content, kind)
    folder = Path(declarations).parent / "imports"
    if folder.is_symlink():
        raise ImportFailure("unsafe-path")
    folder.mkdir(mode=0o755, exist_ok=True)
    stem = f"{kind}-{summary['digest'].removeprefix('sha256:')[:16]}"
    lawlock.write_bytes(folder / f"{stem}.json", raw.content)
    summary["copy"] = f"imports/{stem}.json"
    target = lawlock.write_bytes(folder / f"{stem}.summary.json",
                                 (json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
    return target, summary


def format_summary(summary: dict) -> str:
    lines = [f"{summary['title']} (untrusted tool output, {summary['digest']})"]
    for key, value in summary["concepts"].items():
        lines.append(f"- {value['label']}: {value['count']} item(s)")
        lines.extend(f"    {example}" for example in value["examples"])
    lines.extend(f"- {note}" for note in summary["notes"])
    if not summary["concepts"]:
        lines.append("- The tool reported nothing here. That is not a compliance conclusion.")
    lines.append(f"Kept as {summary.get('copy', 'a copy')}. The declarations were not changed: read the summary, then "
                 "declare the copy as evidence by hand if a reviewer relies on it.")
    return "\n".join(lines)
