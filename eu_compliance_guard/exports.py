"""Exports (2.3): drafts for tools and people who keep compliance records, from the declarations.

`export ropa` drafts a record of processing activities in the shape of GDPR Article 30(1), one
entry per declared activity. `export dpia` drafts DPIA screening inputs: the three cases of
Article 35(3) (law) and the nine criteria of the WP29 guidelines endorsed by the EDPB (WP248
rev.01, guidance), each with the signals the declarations show. Every value keeps its basis
(observed, declared, assumed, unknown); a missing or uncertain field is listed as a gap, never
filled in. Nothing is decided: whether a DPIA is required, or a record is complete, is a
reviewer's call. JSON, Markdown, and CSV for the record; deterministic, from the files alone.
"""
from __future__ import annotations

import csv
import io
import json

from . import models as m
from .grounding import CONCEPTS, tokens
from .notice import LEGAL_NOTICE

DRAFT = "DRAFT for review: generated from declarations, not verified, not legal advice."


def _value(value) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _fact(fact: m.Fact) -> dict:
    return {"id": fact.id, "key": fact.key, "value": fact.value, "basis": fact.basis}


def _fact_text(fact: dict) -> str:
    return f"{fact['key']}: {_value(fact['value'])} [{fact['basis']}]"


def ropa(declared: m.RevalidationInput) -> dict:
    scope = declared.scope
    activities, gaps = [], []
    for activity in scope.activities:
        entry = {"id": activity.id, "purpose": activity.purpose, "data_subjects": list(activity.subjects),
                 "data_categories": list(activity.data_categories), "lawful_basis": _fact(activity.lawful_basis),
                 "roles": [_fact(item) for item in activity.roles], "recipients": [_fact(item) for item in activity.recipients],
                 "locations_and_transfers": [_fact(item) for item in activity.locations],
                 "storage": [_fact(item) for item in activity.stores], "retention": [_fact(item) for item in activity.retention],
                 "security_measures": None, "evidence_owner": activity.evidence_owner}
        activities.append(entry)
        for field, label in (("data_subjects", "categories of data subjects (Art. 30(1)(c))"),
                             ("data_categories", "categories of personal data (Art. 30(1)(c))"),
                             ("recipients", "recipients (Art. 30(1)(d))"),
                             ("retention", "time limits for erasure (Art. 30(1)(f))")):
            if not entry[field]:
                gaps.append(f"{activity.id}: {label} not declared")
        gaps.append(f"{activity.id}: security measures (Art. 30(1)(g)) are not part of the declarations; describe them")
        for fact in [entry["lawful_basis"], *entry["roles"], *entry["recipients"], *entry["locations_and_transfers"],
                     *entry["storage"], *entry["retention"]]:
            if fact["basis"] in ("assumed", "unknown"):
                gaps.append(f"{activity.id}: '{fact['key']}' is {fact['basis']}")
    if not scope.activities:
        gaps.append("no processing activity is declared")
    return {"kind": "ropa", "title": "Record of processing activities (GDPR Article 30(1))", "status": DRAFT,
            "project_id": declared.project_id, "assessment_date": scope.assessment_date,
            "controller": {"establishment": list(scope.establishment), "roles": [_fact(item) for item in scope.roles]},
            "activities": activities, "gaps": gaps}


# Signals are words in an activity's purpose, data subjects and data categories. They suggest a
# criterion; they never answer it.
CRITERIA = (
    ("art35-3-a", "Article 35(3)(a)", "law",
     "Systematic and extensive evaluation of personal aspects, including profiling, with legal or similarly significant effects",
     {"profiling", "profile", "scoring", "score", "evaluation", "credit", "eligibility", "recommendation"}),
    ("art35-3-b", "Article 35(3)(b)", "law",
     "Large-scale processing of special categories (Article 9(1)) or criminal-offence data (Article 10)",
     CONCEPTS["special_category"][1] | {"criminal", "offence", "conviction"}),
    ("art35-3-c", "Article 35(3)(c)", "law", "Systematic monitoring of a publicly accessible area on a large scale",
     {"cctv", "camera", "surveillance", "video", "public"}),
    ("wp248-1", "WP248 rev.01 criterion 1", "guidance", "Evaluation or scoring",
     {"profiling", "profile", "scoring", "score", "evaluation", "recommendation", "personalisation", "personalization"}),
    ("wp248-2", "WP248 rev.01 criterion 2", "guidance", "Automated decision-making with legal or similar significant effect",
     {"automated", "decision", "eligibility", "approval", "rejection", "credit"}),
    ("wp248-3", "WP248 rev.01 criterion 3", "guidance", "Systematic monitoring",
     CONCEPTS["tracking"][1] | {"monitoring", "location", "geolocation"}),
    ("wp248-4", "WP248 rev.01 criterion 4", "guidance", "Sensitive data or data of a highly personal nature",
     CONCEPTS["special_category"][1] | {"criminal", "financial", "location"}),
    ("wp248-5", "WP248 rev.01 criterion 5", "guidance", "Data processed on a large scale", set()),
    ("wp248-6", "WP248 rev.01 criterion 6", "guidance", "Matching or combining datasets",
     {"matching", "combining", "combine", "enrichment", "merge"}),
    ("wp248-7", "WP248 rev.01 criterion 7", "guidance", "Data concerning vulnerable data subjects",
     CONCEPTS["children"][1] | {"employee", "employees", "patient", "patients", "elderly"}),
    ("wp248-8", "WP248 rev.01 criterion 8", "guidance", "Innovative use or applying new technological solutions",
     CONCEPTS["ai"][1] | {"biometric", "iot"}),
    ("wp248-9", "WP248 rev.01 criterion 9", "guidance",
     "Processing that prevents data subjects from exercising a right or using a service or contract",
     {"eligibility", "denial", "refuse", "blocking"}),
)


def dpia(declared: m.RevalidationInput) -> dict:
    criteria = []
    for identity, source, kind, text, words in CRITERIA:
        signals = []
        for activity in declared.scope.activities:
            fields = " ".join([activity.purpose, *activity.subjects, *activity.data_categories])
            found = sorted(set(tokens(fields)) & words)
            if found:
                signals.append({"activity": activity.id, "words": found})
        criteria.append({"id": identity, "source": source, "kind": kind, "criterion": text, "signals": signals,
                         "answer": None})
    suggested = sum(1 for item in criteria if item["kind"] == "guidance" and item["signals"])
    return {"kind": "dpia", "title": "DPIA screening inputs (GDPR Article 35)", "status": DRAFT,
            "project_id": declared.project_id, "assessment_date": declared.scope.assessment_date,
            "criteria": criteria, "guidance_criteria_with_signals": suggested,
            "note": ("Under WP248 rev.01, processing meeting two or more criteria will in most cases need a DPIA. "
                     "Signals are words in the declarations that suggest a criterion; each answer is a reviewer's.")}


def to_markdown(export: dict) -> str:
    lines = [f"# {export['title']}", "", f"**{export['status']}**", "",
             f"Project `{export['project_id']}`, assessment date {export['assessment_date']}.", ""]
    if export["kind"] == "ropa":
        controller = export["controller"]
        lines += ["## Controller", "", f"- Establishment: {', '.join(controller['establishment']) or 'not declared'}"]
        lines += [f"- {_fact_text(fact)}" for fact in controller["roles"]]
        for activity in export["activities"]:
            lines += ["", f"## {activity['id']}: {activity['purpose']}", "",
                      f"- Data subjects: {', '.join(activity['data_subjects']) or 'not declared'}",
                      f"- Personal data: {', '.join(activity['data_categories']) or 'not declared'}",
                      f"- Lawful basis: {_fact_text(activity['lawful_basis'])}"]
            for field, label in (("roles", "Role"), ("recipients", "Recipient"), ("locations_and_transfers", "Location or transfer"),
                                 ("storage", "Storage"), ("retention", "Retention")):
                lines += [f"- {label}: {_fact_text(fact)}" for fact in activity[field]] or [f"- {label}: not declared"]
            lines.append("- Security measures: not declared")
        lines += ["", "## Gaps", ""] + [f"- {gap}" for gap in export["gaps"]]
    else:
        lines += ["| Criterion | Source | Signals in the declarations | Answer |", "|---|---|---|---|"]
        for item in export["criteria"]:
            signals = "; ".join(f"{s['activity']}: {', '.join(s['words'])}" for s in item["signals"]) or "none found"
            lines.append(f"| {item['criterion']} | {item['source']} ({item['kind']}) | {signals} | reviewer to answer |")
        lines += ["", export["note"]]
    lines += ["", LEGAL_NOTICE]
    return "\n".join(_cell(line) for line in lines) + "\n"


def _cell(line: str) -> str:
    """Declared text never breaks the Markdown: no line breaks inside a line, no raw HTML."""
    return " ".join(line.splitlines()).replace("<", "&lt;").replace(">", "&gt;")


def to_csv(export: dict) -> str:
    """The record as one row per activity (Markdown and JSON carry the gaps)."""
    if export["kind"] != "ropa":
        raise ValueError("csv is available for the record of processing only")
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["status", "activity", "purpose", "data_subjects", "data_categories", "lawful_basis", "roles",
                     "recipients", "locations_and_transfers", "storage", "retention", "security_measures"])
    for activity in export["activities"]:
        join = lambda facts: "; ".join(_fact_text(fact) for fact in facts)
        row = [DRAFT, activity["id"], activity["purpose"], "; ".join(activity["data_subjects"]),
               "; ".join(activity["data_categories"]), _fact_text(activity["lawful_basis"]), join(activity["roles"]),
               join(activity["recipients"]), join(activity["locations_and_transfers"]), join(activity["storage"]),
               join(activity["retention"]), "not declared"]
        # A cell starting with =, +, - or @ is a formula in spreadsheets; it is kept as text.
        writer.writerow(["'" + cell if cell[:1] in ("=", "+", "-", "@") else cell for cell in row])
    return out.getvalue()
