"""Deterministic legal-touchpoint check of a unified diff, for pull requests and CI.

Reads only the diff text and, when present, the declarations file. It names added lines that
touch EU legal concepts, whether the declarations already mention each concept, code evidence
pinned to a changed file (which then needs grounding again), and requirements declared in a
changed file. It never decides what the law requires; "no touchpoints" is not a clean bill.
"""
from __future__ import annotations

import re

from . import models as m
from .grounding import CONCEPTS, SKIP_DIRS, TEXT_NAMES, TEXT_SUFFIXES, tokens

MAX_DIFF_BYTES = 16 * 1024 * 1024
MAX_EXAMPLES = 5
SNIPPET = 120
FAMILIES = {
    "personal_data": ["gdpr"], "special_category": ["gdpr"], "children": ["gdpr", "service_disclosures"],
    "tracking": ["eprivacy", "gdpr"], "consent": ["gdpr", "eprivacy"], "marketing": ["eprivacy", "gdpr"],
    "ai": ["ai", "gdpr"], "third_party": ["gdpr", "data_products"], "retention": ["gdpr"],
    "subscription": ["consumer", "service_disclosures"], "security": ["gdpr", "cybersecurity"],
    "accessibility": ["accessibility"],
}
# Terms specific enough to flag a line on their own; other concept terms need a second one.
STRONG = {"health", "medical", "diagnosis", "biometric", "pregnancy", "religion", "ethnicity", "sexual", "disability",
          "bmi", "minor", "parental", "child", "children", "consent", "cookie", "cookies", "llm", "openai", "anthropic",
          "gpt", "newsletter", "unsubscribe", "subscription", "cancellation", "refund", "withdrawal", "retention",
          "geolocation", "fingerprint", "analytics", "tracking", "gtag", "mixpanel", "hotjar", "aria", "a11y", "dob"}
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


class PRCheckError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _path(header: str) -> str | None:
    value = header[4:].split("\t", 1)[0].strip()
    if value == "/dev/null":
        return None
    return value[2:] if value[:2] in ("a/", "b/") else value


def _text_file(path: str) -> bool:
    parts = path.split("/")
    name = parts[-1]
    return (not any(part in SKIP_DIRS for part in parts[:-1])
            and (name in TEXT_NAMES or any(name.endswith(suffix) for suffix in TEXT_SUFFIXES)))


def parse_diff(text: str) -> tuple[dict[str, list[tuple[int, str]]], set[str]]:
    """Added lines per new path, and every path the diff touches (old or new side)."""
    added: dict[str, list[tuple[int, str]]] = {}
    touched: set[str] = set()
    current, number, old = None, 0, None
    for line in text.splitlines():
        if line.startswith("--- "):
            old = _path(line)
            if old:
                touched.add(old)
        elif line.startswith("+++ "):
            current = _path(line)
            if current:
                touched.add(current)
        elif (match := HUNK.match(line)):
            number = int(match.group(1))
        elif current is not None and line.startswith("+"):
            added.setdefault(current, []).append((number, line[1:]))
            number += 1
        elif current is not None and line.startswith(" "):
            number += 1
    return added, touched


def concepts_in(line: str) -> list[str]:
    terms = set(tokens(line))
    return [key for key, (_, vocabulary) in CONCEPTS.items()
            if (hits := vocabulary & terms) and (len(hits) >= 2 or hits & STRONG)]


def _snippet(text: str) -> str:
    text = re.sub(r"\s+", " ", text.replace("`", "'")).strip()
    return text if len(text) <= SNIPPET else text[:SNIPPET - 1] + "…"


def pr_check(diff: str, declared: m.RevalidationInput | None = None) -> dict:
    if len(diff.encode("utf-8", "replace")) > MAX_DIFF_BYTES:
        raise PRCheckError("capacity-exceeded")
    added, touched = parse_diff(diff)
    found: dict[str, list[str]] = {}
    for path, lines in sorted(added.items()):
        if not _text_file(path) or path.startswith(".eu-compliance-guard/"):
            continue
        for number, text in lines:
            for concept in concepts_in(text):
                found.setdefault(concept, []).append(f"{path}:{number}  {_snippet(text)}")
    vocabulary_declared: set[str] = set()
    pinned, requirements = [], []
    if declared is not None:
        base = "" if declared.files_root == "project" else ".eu-compliance-guard/"
        touched_declared = {path.removeprefix(base) for path in touched if path.startswith(base)}
        texts = [item.statement for item in declared.requirements]
        texts += [f"{fact.key} {fact.value}" for fact in m.scope_facts(declared.scope)]
        texts += [f"{item.purpose} {' '.join(item.data_categories)}" for item in declared.scope.activities]
        vocabulary_declared = set(tokens(" ".join(texts)))
        facts_by_evidence: dict[str, list[str]] = {}
        for fact in m.scope_facts(declared.scope):
            for evidence in fact.evidence_ids:
                facts_by_evidence.setdefault(evidence, []).append(fact.id)
        for item in declared.evidence:
            if item.path in touched_declared:
                pinned.append({"evidence": item.evidence.id, "path": base + item.path,
                               "facts": sorted(set(facts_by_evidence.get(item.evidence.id, []))),
                               "refs": list(item.evidence.source_refs)})
        requirements = [{"requirement": item.id, "path": base + item.origin.path}
                        for item in declared.requirements if item.origin and item.origin.path in touched_declared]
    touchpoints = []
    for concept in CONCEPTS:
        if concept in found:
            label, vocabulary = CONCEPTS[concept]
            touchpoints.append({"concept": concept, "label": label, "families": FAMILIES[concept],
                                "count": len(found[concept]), "examples": found[concept][:MAX_EXAMPLES],
                                "declared": bool(vocabulary & vocabulary_declared)})
    attention = sum(not item["declared"] for item in touchpoints) + len(pinned) + len(requirements)
    return {"files": len(touched), "declarations": declared is not None, "touchpoints": touchpoints,
            "pinned_evidence": pinned, "requirements_in_changed_files": requirements, "attention": attention}


def format_markdown(report: dict) -> str:
    lines = ["### EU Compliance Guard: legal touchpoints in this diff", ""]
    if not report["touchpoints"] and not report["pinned_evidence"] and not report["requirements_in_changed_files"]:
        lines.append(f"No legal touchpoints matched in {report['files']} changed file(s). "
                     "A keyword check, not a clean bill: review data flows the words miss.")
    if report["touchpoints"]:
        lines += ["| Concept | Candidate families | Added lines | Declared |", "| --- | --- | --- | --- |"]
        for item in report["touchpoints"]:
            declared = "yes" if item["declared"] else ("**no**" if report["declarations"] else "no declarations")
            lines.append(f"| {item['label']} | {', '.join(item['families'])} | {item['count']} | {declared} |")
        lines.append("")
        for item in report["touchpoints"]:
            lines.append(f"<details><summary>{item['label']}</summary>\n")
            lines += [f"- `{example}`" for example in item["examples"]]
            lines.append("\n</details>")
    if report["pinned_evidence"]:
        lines += ["", "**Code evidence pinned to a changed file** (ground these facts again: `eu-compliance-guard ground`):"]
        lines += [f"- `{item['path']}` backs {', '.join(item['facts']) or item['evidence']}" for item in report["pinned_evidence"]]
    if report["requirements_in_changed_files"]:
        lines += ["", "**Requirements declared in a changed file** (re-read their statements):"]
        lines += [f"- {item['requirement']} (`{item['path']}`)" for item in report["requirements_in_changed_files"]]
    if not report["declarations"]:
        lines += ["", "No `.eu-compliance-guard/declarations.json` found, so nothing is compared with declarations."]
    lines += ["", f"{report['attention']} item(s) need attention. Candidate families are screening hints, "
              "not a legal conclusion or a compliance verdict."]
    return "\n".join(lines)


def format_text(report: dict) -> str:
    lines = [f"{report['files']} changed file(s); {report['attention']} item(s) need attention."]
    for item in report["touchpoints"]:
        state = "declared" if item["declared"] else "not declared"
        lines.append(f"- {item['label']} ({', '.join(item['families'])}): {item['count']} added line(s), {state}")
        lines += [f"    {example}" for example in item["examples"][:3]]
    for item in report["pinned_evidence"]:
        lines.append(f"- pinned evidence in changed {item['path']}: ground {', '.join(item['facts']) or item['evidence']} again")
    for item in report["requirements_in_changed_files"]:
        lines.append(f"- requirement {item['requirement']} is declared in changed {item['path']}")
    lines.append("Keyword screening only; not a compliance verdict.")
    return "\n".join(lines)
