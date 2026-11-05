"""Deterministic legal-touchpoint check of a unified diff, for pull requests and CI.

Reads only the diff text and, when present, the declarations file. It names added lines that
touch EU legal concepts, whether the declarations already mention each concept, code evidence
pinned to a changed file (which then needs grounding again), and requirements declared in a
changed file. It never decides what the law requires; "no touchpoints" is not a clean bill.
"""
from __future__ import annotations


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
GIT_PREFIXES = ("a/", "b/", "c/", "i/", "w/", "o/", "1/", "2/")  # git's default, mnemonic and --no-index prefixes


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


def _quoted_end(text: str, start: int) -> int:
    """Index just past the closing quote of the C-style quoted name opening at text[start], or -1."""
    index = start + 1
    while index < len(text):
        if text[index] == "\\":
            index += 2
        elif text[index] == '"':
            return index + 1
        else:
            index += 1
    return -1


def _name(value: str) -> str | None:
    """The name on a ---/+++ line as written: unquoted, without a trailing tab or timestamp; None for /dev/null."""
    value = value.strip()
    if value.startswith('"') and (end := _quoted_end(value, 0)) > 0:
        value = _unquote(value[:end])
    else:
        value = value.split("\t", 1)[0].strip()
    return None if value == "/dev/null" else value


def _unprefix(first: str | None, second: str | None) -> tuple[str | None, str | None]:
    """The old and new name of a file pair without their diff prefixes.

    git writes a/ b/ by default, i/ w/, c/ w/, c/ i/ or o/ w/ with diff.mnemonicPrefix (swapped by
    -R), 1/ 2/ for --no-index, custom ones with --src-prefix/--dst-prefix and none with --no-prefix.
    The same name twice has no prefix, names that agree after their first component carry one
    each, and other pairs (renames) drop only prefixes git itself writes.
    """
    if first is not None and second is not None:
        if first == second:
            return first, second
        _, slash, tail = first.partition("/")
        _, other_slash, other_tail = second.partition("/")
        if slash and other_slash and tail == other_tail:
            return tail, other_tail
        if first[:2] != second[:2] and first[:2] in GIT_PREFIXES and second[:2] in GIT_PREFIXES:
            return first[2:], second[2:]
    return tuple(name[2:] if name is not None and name[:2] in ("a/", "b/") else name for name in (first, second))


def _header_names(rest: str) -> tuple[str, str] | None:
    """The two names of a `diff --git` header as written, or None when spaces leave the split ambiguous."""
    if rest.startswith('"'):
        end = _quoted_end(rest, 0)
        return (_unquote(rest[:end]), _unquote(rest[end + 1:])) if end > 0 and rest[end:end + 1] == " " else None
    if rest.endswith('"') and (split := rest.rfind(' "')) > 0:  # git quotes each name on its own
        return rest[:split], _unquote(rest[split + 1:])
    if rest.count(" ") == 1:
        first, _, second = rest.partition(" ")
        return first, second
    half = (len(rest) - 1) // 2  # one path behind prefixes of equal length puts the separator in the middle
    first, second = rest[:half], rest[half + 1:]
    old, new = _unprefix(first, second)
    return (first, second) if rest[half:half + 1] == " " and old == new else None


class _File:
    """One changed file of the diff: its old and new path, as far as the diff names them."""

    def __init__(self, key: str, old: str | None = None, new: str | None = None, settled: bool = False):
        self.key, self.old, self.new = key, old, new
        self.settled = settled  # one path in the header, or rename/copy lines: ---/+++ only mark /dev/null
        self.open = True  # before its ---/+++ pair and first hunk, where extended header lines belong

    @classmethod
    def header(cls, line: str) -> "_File":
        if line.startswith("diff --git "):
            names = _header_names(line[len("diff --git "):])
            if names is None:  # renames name both sides on their own lines; never guess a split
                return cls(line)
            old, new = _unprefix(*names)
            return cls(line, old, new, settled=old == new)
        path = _unquote(line.split(" ", 2)[2])  # diff --cc / --combined: the merge result, unprefixed
        return cls(line, path, path, settled=True)

    def pair(self, old_line: str, new_line: str) -> None:
        old, new = _name(old_line[4:]), _name(new_line[4:])
        if not self.settled:
            self.old, self.new = _unprefix(old, new)
        else:  # the header already named the file; a /dev/null side means it was added or deleted
            self.old = None if old is None else self.old
            self.new = None if new is None else self.new
        self.open = False


def _plain(text: str) -> str:
    """The text without the ANSI colour codes (ESC [ digits and semicolons m) of `git diff --color`."""
    parts, index = [], 0
    while (start := text.find("\x1b[", index)) >= 0:
        end = start + 2
        while end < len(text) and text[end] in "0123456789;":
            end += 1
        if text[end:end + 1] == "m":
            parts.append(text[index:start])
            index = end + 1
        else:  # not a colour code: keep it as data
            parts.append(text[index:end])
            index = end
    parts.append(text[index:])
    return "".join(parts)


def _lines(text: str) -> list[str]:
    """Split on newlines only, like git and editors; form feeds and other separators stay in the line."""
    return [line[:-1] if line.endswith("\r") else line for line in _plain(text).split("\n")]


def _text_file(path: str) -> bool:
    parts = path.split("/")
    name = parts[-1]
    return (not any(part in SKIP_DIRS for part in parts[:-1])
            and (name in TEXT_NAMES or any(name.endswith(suffix) for suffix in TEXT_SUFFIXES)))


def _number(text: str) -> int | None:
    """An ASCII decimal hunk number of at most 12 digits, or None."""
    return int(text) if 0 < len(text) <= 12 and text.isascii() and text.isdigit() else None


def _range(text: str, sign: str) -> tuple[int, int] | None:
    """(start, count) of a hunk range such as `-10,2` or `+11`; a missing count means one line."""
    if not text.startswith(sign):
        return None
    start, comma, count = text[1:].partition(",")
    first, size = _number(start), _number(count) if comma else 1
    return None if first is None or size is None else (first, size)


def _hunk(line: str) -> tuple[list[int], int, int] | None:
    """Old line counts (one per parent), new start and new count of a hunk header.

    `@@ -a,b +c,d @@` has one parent; a merge's combined `@@@ -a,b -c,d +e,f @@@` has one `@`
    more than it has parents. None when the line is not a well-formed hunk header.
    """
    marks = len(line) - len(line.lstrip("@"))
    end = line.find(" " + "@" * marks, marks)
    if marks < 2 or line[marks:marks + 1] != " " or end < 0:
        return None
    ranges = line[marks + 1:end].split(" ")
    if len(ranges) != marks:  # marks - 1 old ranges and the new one
        return None
    olds = [_range(item, "-") for item in ranges[:-1]]
    new = _range(ranges[-1], "+")
    if new is None or None in olds:
        return None
    return [size for _, size in olds], new[0], new[1]


def parse_diff(text: str) -> tuple[dict[str, list[tuple[int, str]]], set[str], int]:
    """Added lines per new path, every path the diff touches (old or new side), and how many files changed.

    A file is one `diff --git` (or merge `diff --cc`) section, or a `---`/`+++` pair in a plain
    unified diff; a rename or copy is one changed file, named by its rename/copy lines, and a file
    changed in several commits (`git log -p`) counts once.
    Text that is not blank but names no file (prose, a stat summary, a bare hunk) is refused, and
    so is a hunk line that is not a unified diff line (word-diff output, a broken header):
    reporting such input as screened would pass a strict gate on lines that were never read.
    A merge's combined diff (`git show <merge>`) has one prefix column per parent; a line with
    "+" in any column and no "-" is in the result but missing from a parent, so it counts as added.
    """
    added: dict[str, list[tuple[int, str]]] = {}
    files: list[_File] = []
    file: _File | None = None
    number = 0
    # Lines still owed to the current hunk, per parent and on the new side: inside it, "--- x" is a removed line.
    old_left: list[int] = []
    new_left = 0
    lines = _lines(text)
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if line.startswith(("diff --git ", "diff --cc ", "diff --combined ")):
            old_left, new_left = [], 0  # a new file always ends the hunk, even one whose counts were short
            file = _File.header(line)
            files.append(file)
            continue
        if new_left > 0 or max(old_left, default=0) > 0:
            if line.startswith("\\"):  # "\ No newline at end of file"
                continue
            parents = len(old_left)
            columns, content = line[:parents].ljust(parents), line[parents:]
            if columns.strip(" +-") or ("+" in columns and "-" in columns):
                raise PRCheckError("invalid-input")
            if "-" in columns:  # gone from the result; only the parents marked "-" had it
                old_left = [left - (mark == "-") for left, mark in zip(old_left, columns)]
                continue
            if "+" in columns and file.new:
                added.setdefault(file.new, []).append((number, content))
            if " " in columns:  # the parents marked " " have the line too
                old_left = [left - (mark == " ") for left, mark in zip(old_left, columns)]
            number += 1
            new_left -= 1
            continue
        if line.startswith("@@"):
            hunk = _hunk(line)
            if hunk is None and file is None:  # prose before any file (a commit message line): not a hunk
                continue
            if hunk is None or file is None:  # a hunk with no file to attribute its lines to cannot be screened
                raise PRCheckError("invalid-input")
            old_left, number, new_left = hunk
            file.open = False
        elif line.startswith("--- ") and index < len(lines) and lines[index].startswith("+++ "):
            if file is None or not file.open:  # a plain unified diff names each file only here
                file = _File(line)
                files.append(file)
            file.pair(line, lines[index])
            index += 1
        elif file is not None and file.open and line.startswith(("rename from ", "copy from ", "rename to ", "copy to ")):
            value = _unquote(line.split(" ", 2)[2])
            if line.startswith(("rename from ", "copy from ")):
                file.old = value
            else:
                file.new = value
            file.settled = True
    if not files and text.strip():
        raise PRCheckError("invalid-input")
    touched = {path for item in files for path in (item.old, item.new) if path}
    return added, touched, len({item.new or item.old or item.key for item in files})


def concepts_in(line: str) -> list[str]:
    terms = set(tokens(line))
    return [key for key, (_, vocabulary) in CONCEPTS.items()
            if (hits := vocabulary & terms) and (len(hits) >= 2 or hits & STRONG)]


def _code(text: str) -> str:
    """Text safe inside a markdown code span: no backticks or line breaks to break out with."""
    parts, broken = [], False
    for char in text.replace("`", "'"):
        if char in "\r\n":
            if not broken:
                parts.append(" ")
            broken = True
        else:
            parts.append(char)
            broken = False
    return "".join(parts)


def _mentioned(concept: str, declared_terms: set[str]) -> bool:
    """A strong term counts alone; otherwise two of the concept's terms must appear in the declarations."""
    vocabulary = CONCEPTS[concept][1]
    return bool(vocabulary & STRONG & declared_terms) or len(vocabulary & declared_terms) >= 2


def _snippet(text: str) -> str:
    text = " ".join(text.replace("`", "'").split())
    return text if len(text) <= SNIPPET else text[:SNIPPET - 1] + "…"


def pr_check(diff: str, declared: m.RevalidationInput | None = None) -> dict:
    if len(diff.encode("utf-8", "replace")) > MAX_DIFF_BYTES:
        raise PRCheckError("capacity-exceeded")
    added, touched, files = parse_diff(diff)
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
    return {"files": files, "declarations": declared is not None, "touchpoints": touchpoints,
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
        if not report["declarations"]:
            state = "no declarations to compare"
        else:
            state = "mentioned in declarations" if item["declared"] else "not mentioned in declarations"
        lines.append(f"- {item['label']} ({', '.join(item['families'])}): {item['count']} added line(s), {state}")
        lines += [f"    {example}" for example in item["examples"][:3]]
    for item in report["pinned_evidence"]:
        lines.append(f"- pinned evidence in changed {item['path']}: ground {', '.join(item['facts']) or item['evidence']} again")
    for item in report["requirements_in_changed_files"]:
        lines.append(f"- requirement {item['requirement']} is declared in changed {item['path']}")
    if not report["declarations"]:
        lines.append("No declarations file found, so nothing is compared with declarations.")
    lines.append("Keyword screening only; not a compliance verdict.")
    return "\n".join(lines)
