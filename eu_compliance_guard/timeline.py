"""Application-date timeline (2.3): the dates an act gives, quoted from its retained text.

Each clause of a retained act that names a calendar date and says that something applies, is
applicable, comes into force, or must be adopted (transposition) becomes one entry: the act, the
article, the ISO date, the kind, and the clause word for word. Dates are compared with the
declarations' assessment date, never with today, so the same inputs give the same timeline.
A date that is only described ("the twentieth day following publication") is not computed.
The timeline shows what the text says; whether and how it applies to a project is a reviewer's
decision.
"""
from __future__ import annotations

from datetime import date

MONTHS = {name: number for number, name in enumerate(
    ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
     "december"), 1)}
# Phrases that make a dated clause an application date, in order of precedence.
KINDS = (("adopt and publish", "transposition"), ("shall apply", "applies"), ("shall be applicable", "applies"),
         ("apply from", "applies"), ("applies from", "applies"), ("apply those measures", "applies"),
         ("apply the measures", "applies"), ("come into force", "in force"), ("comes into force", "in force"),
         ("enter into force", "in force"), ("enters into force", "in force"))
MAX_QUOTE = 400


def _clauses(text: str) -> list[str]:
    """Sentences, and the items of a list ("(a) …; (b) …"), as separate clauses."""
    clauses, current = [], []
    for index, char in enumerate(text):
        current.append(char)
        following = text[index + 1:index + 2]
        if (char == ";" or (char == "." and following in (" ", ""))) and not text[max(0, index - 3):index].endswith("Art"):
            clause = "".join(current).strip()
            if clause:
                clauses.append(clause)
            current = []
    tail = "".join(current).strip()
    if tail:
        clauses.append(tail)
    return clauses


def _dates(clause: str) -> list[str]:
    """ISO dates written as '2 August 2026' or 'August 2, 2026' in a clause."""
    words = [word.strip(",.;:()") for word in clause.split()]
    found = []
    for index in range(len(words) - 2):
        a, b, c = words[index], words[index + 1], words[index + 2]
        day, month, year = None, None, None
        if a.isdigit() and b.lower() in MONTHS and c.isdigit():
            day, month, year = a, b, c
        elif a.lower() in MONTHS and b.isdigit() and c.isdigit():
            month, day, year = a, b, c
        if day is None or len(year) != 4 or not 1 <= int(day) <= 31:
            continue
        try:
            found.append(date(int(year), MONTHS[month.lower()], int(day)).isoformat())
        except ValueError:
            continue
    return found


def _kind(clause: str) -> str | None:
    lowered = " ".join(clause.lower().split())
    return next((kind for phrase, kind in KINDS if phrase in lowered), None)


def timeline(catalogue: dict[str, dict[str, dict]], assessment_date: str | None = None) -> list[dict]:
    entries = []
    for act in sorted(catalogue):
        for key, item in catalogue[act].items():
            for clause in _clauses(item["text"]):
                kind = _kind(clause)
                if kind is None:
                    continue
                for iso in _dates(clause):
                    quote = " ".join(clause.split())
                    entries.append({"date": iso, "act": act, "article": key, "kind": kind,
                                    "quote": quote if len(quote) <= MAX_QUOTE else quote[:MAX_QUOTE - 1] + "…",
                                    "status": (None if assessment_date is None else
                                               "reached" if iso <= assessment_date else "upcoming")})
    unique = {(entry["date"], entry["act"], entry["article"], entry["quote"]): entry for entry in entries}
    return sorted(unique.values(), key=lambda entry: (entry["date"], entry["act"], entry["article"], entry["quote"]))


def format_timeline(entries: list[dict], assessment_date: str | None = None, acts: list[str] | None = None) -> str:
    if not entries:
        return ("No dated application, entry-into-force or transposition clause in the retained text"
                + (f" of {', '.join(acts)}" if acts else "") + ".")
    lines = [f"Dates quoted from the retained text" + (f", against the assessment date {assessment_date}" if assessment_date else "")
             + ":"]
    for entry in entries:
        status = {"reached": " (reached)", "upcoming": " (upcoming)"}.get(entry["status"], "")
        lines.append(f"- {entry['date']}{status} · {entry['act']} {entry['article']} · {entry['kind']}")
        lines.append(f"    \"{entry['quote']}\"")
    lines.append("What the text says, not whether or how it applies to this project; a reviewer decides.")
    return "\n".join(lines)
