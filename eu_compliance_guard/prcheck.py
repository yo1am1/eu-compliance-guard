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

# Lets a workflow find and update its own comment, never another bot's.
MARKER = "<!-- eu-compliance-guard-pr-check -->"
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
HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class PRCheckError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _unquote(value: str) -> str:
    """git's C-style quoted path ("src/gr\\303\\266e.py") as text; octal escapes are UTF-8 bytes."""
    if len(value) < 2 or value[0] != '"' or value[-1] != '"':
        return value
    raw, body, index = bytearray(), value[1:-1], 0
    simple = {"n": 10, "t": 9, "r": 13, '"': 34, "\\": 92, "a": 7, "b": 8, "f": 12, "v": 11}
    while index < len(body):
        char = body[index]
        if char == "\\" and index + 1 < len(body):
            following = body[index + 1]
            octal = body[index + 1:index + 4]
            if len(octal) == 3 and all(digit in "01234567" for digit in octal):
                raw.append(int(octal, 8) & 0xFF)
                index += 4
                continue
            raw.append(simple.get(following, ord(following)))
            index += 2
            continue
        raw.extend(char.encode("utf-8"))
        index += 1
    return raw.decode("utf-8", "replace")


def _path(header: str) -> str | None:
    value = header[4:].strip()
    value = _unquote(value) if value.startswith('"') else value.split("\t", 1)[0].strip()
    if value == "/dev/null":
        return None
    return value[2:] if value[:2] in ("a/", "b/") else value


def _lines(text: str) -> list[str]:
    """Split on newlines only, like git and editors; form feeds and other separators stay in the line."""
    return [line[:-1] if line.endswith("\r") else line for line in text.split("\n")]


def _text_file(path: str) -> bool:
    parts = path.split("/")
    name = parts[-1]
    return (not any(part in SKIP_DIRS for part in parts[:-1])
            and (name in TEXT_NAMES or any(name.endswith(suffix) for suffix in TEXT_SUFFIXES)))


def parse_diff(text: str) -> tuple[dict[str, list[tuple[int, str]]], set[str]]:
    """Added lines per new path, and every path the diff touches (old or new side)."""
    added: dict[str, list[tuple[int, str]]] = {}
    touched: set[str] = set()
    current, number = None, 0
    old_left = new_left = 0  # lines still owed to the current hunk: inside it, "--- x" is a removed line
    for line in _lines(text):
        if line.startswith("diff --git "):
            old_left = new_left = 0  # a new file always ends the hunk, even one whose counts were short
            continue
        if old_left > 0 or new_left > 0:
            if line.startswith("+"):
                if current is not None:
                    added.setdefault(current, []).append((number, line[1:]))
                number += 1
                new_left -= 1
            elif line.startswith("-"):
                old_left -= 1
            elif line.startswith(" ") or line == "":
                number += 1
                old_left -= 1
                new_left -= 1
            continue  # "\\ No newline at end of file" and the like
        if line.startswith("--- "):
            old = _path(line)
            if old:
                touched.add(old)
        elif line.startswith("+++ "):
            current = _path(line)
            if current:
                touched.add(current)
        elif (match := HUNK.match(line)):
            number = int(match.group(2))
            old_left = int(match.group(1)) if match.group(1) is not None else 1
            new_left = int(match.group(3)) if match.group(3) is not None else 1
    return added, touched


def concepts_in(line: str) -> list[str]:
    terms = set(tokens(line))
    return [key for key, (_, vocabulary) in CONCEPTS.items()
            if (hits := vocabulary & terms) and (len(hits) >= 2 or hits & STRONG)]


def _code(text: str) -> str:
    """Text safe inside a markdown code span: no backticks or line breaks to break out with."""
    return re.sub(r"[\r\n]+", " ", text.replace("`", "'"))


def _mentioned(concept: str, declared_terms: set[str]) -> bool:
    """A strong term counts alone; otherwise two of the concept's terms must appear in the declarations."""
    vocabulary = CONCEPTS[concept][1]
    return bool(vocabulary & STRONG & declared_terms) or len(vocabulary & declared_terms) >= 2


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
            label = CONCEPTS[concept][0]
            touchpoints.append({"concept": concept, "label": label, "families": FAMILIES[concept],
                                "count": len(found[concept]), "examples": found[concept][:MAX_EXAMPLES],
                                "declared": _mentioned(concept, vocabulary_declared)})
    attention = sum(not item["declared"] for item in touchpoints) + len(pinned) + len(requirements)
    return {"files": len(touched), "declarations": declared is not None, "touchpoints": touchpoints,
            "pinned_evidence": pinned, "requirements_in_changed_files": requirements, "attention": attention}


def format_markdown(report: dict) -> str:
    lines = [MARKER, "### EU Compliance Guard: legal touchpoints in this diff", ""]
    if not report["touchpoints"] and not report["pinned_evidence"] and not report["requirements_in_changed_files"]:
        lines.append(f"No legal touchpoints matched in {report['files']} changed file(s). "
                     "A keyword check, not a clean bill: review data flows the words miss.")
    if report["touchpoints"]:
        lines += ["| Concept | Candidate families | Added lines | Mentioned in declarations |", "| --- | --- | --- | --- |"]
        for item in report["touchpoints"]:
            declared = "yes" if item["declared"] else ("**no**" if report["declarations"] else "no declarations")
            lines.append(f"| {item['label']} | {', '.join(item['families'])} | {item['count']} | {declared} |")
        lines.append("")
        for item in report["touchpoints"]:
            lines.append(f"<details><summary>{item['label']}</summary>\n")
            lines += [f"- `{_code(example)}`" for example in item["examples"]]
            lines.append("\n</details>")
    if report["pinned_evidence"]:
        lines += ["", "**Code evidence pinned to a changed file** (ground these facts again: `eu-compliance-guard ground`):"]
        lines += [f"- `{_code(item['path'])}` backs {', '.join(item['facts']) or item['evidence']}" for item in report["pinned_evidence"]]
    if report["requirements_in_changed_files"]:
        lines += ["", "**Requirements declared in a changed file** (re-read their statements):"]
        lines += [f"- {item['requirement']} (`{_code(item['path'])}`)" for item in report["requirements_in_changed_files"]]
    if not report["declarations"]:
        lines += ["", "No `.eu-compliance-guard/declarations.json` found, so nothing is compared with declarations."]
    lines += ["", f"{report['attention']} item(s) need attention. Candidate families are screening hints, "
              "not a legal conclusion or a compliance verdict."]
    return "\n".join(lines)


def format_text(report: dict) -> str:
    lines = [f"{report['files']} changed file(s); {report['attention']} item(s) need attention."]
    for item in report["touchpoints"]:
        state = "mentioned in declarations" if item["declared"] else "not mentioned in declarations"
        lines.append(f"- {item['label']} ({', '.join(item['families'])}): {item['count']} added line(s), {state}")
        lines += [f"    {example}" for example in item["examples"][:3]]
    for item in report["pinned_evidence"]:
        lines.append(f"- pinned evidence in changed {item['path']}: ground {', '.join(item['facts']) or item['evidence']} again")
    for item in report["requirements_in_changed_files"]:
        lines.append(f"- requirement {item['requirement']} is declared in changed {item['path']}")
    lines.append("Keyword screening only; not a compliance verdict.")
    return "\n".join(lines)
