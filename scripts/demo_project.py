"""The fictional FitBox project that the end-to-end test and the README images are built on.

Synthetic code (fixtures/eval/project) with the real GDPR and ePrivacy texts (fixtures/official)
as its declared sources. Nothing here is a real project or a reviewed legal position.
"""
import gzip
import hashlib
import json
from pathlib import Path
import shutil

REPO = Path(__file__).resolve().parents[1]
PUBLISHER = "Publications Office of the European Union"
ACTS = (("gdpr", "gdpr-32016R0679", "32016R0679", "gdpr"),
        ("eprivacy", "eprivacy-02002L0058-20091219", "02002L0058-20091219", "eprivacy"))


def _fact(identity, key, basis, value):
    return {"id": identity, "revision": 0, "key": key, "value": value, "basis": basis, "evidence_ids": [],
            "owner": "Fictional owner", "observed_at": "2026-11-01T10:00:00Z", "conflicts": []}


def _requirement(identity, statement, fact_id):
    return {"id": identity, "revision": 0, "project_id": "fitbox", "synthetic": True, "statement": statement, "origin": None,
            "locator": None, "activity_ids": [], "fact_refs": [{"id": fact_id, "revision": 0}], "obligation_refs": [],
            "evidence_ids": []}


def copy_project(target: Path) -> Path:
    """The project's code, and the two acts under law/."""
    shutil.copytree(REPO / "fixtures/eval/project", target)
    (target / "law").mkdir()
    for name, stem, _, _ in ACTS:
        (target / f"law/{name}.html").write_bytes(gzip.decompress((REPO / f"fixtures/official/{stem}.html.gz").read_bytes()))
    return target


def seed(declarations: Path) -> None:
    """Add requirements, facts and the two acts to a file `init --project-id fitbox --synthetic` wrote."""
    data = json.loads(declarations.read_text())
    data["files_root"] = "project"
    # Technical facts go under roles: size_and_sector facts are organisational by design and never searched in code.
    data["scope"]["roles"] = [_fact("fact-controller", "Acts as controller for user accounts", "declared", "yes"),
                              _fact("fact-health", "Processes users' body weight (health data) for meal coaching", "assumed", "yes"),
                              _fact("fact-cookies", "Sets analytics cookies on the landing page", "unknown", None)]
    data["requirements"] = [
        _requirement("req-delete", "Users can delete their account and all their personal data.", "fact-controller"),
        _requirement("req-cookies", "Ask for consent before storing analytics cookies.", "fact-cookies"),
        _requirement("req-health", "Body weight is special category health data and needs explicit consent.", "fact-health")]
    for name, _, celex, family in ACTS:
        digest = "sha256:" + hashlib.sha256((declarations.parent.parent / f"law/{name}.html").read_bytes()).hexdigest()
        url = f"https://publications.europa.eu/resource/celex/{celex}"
        data["source_targets"].append({"id": f"target-eu-{name}", "revision": 0, "family": family, "intended_url": url,
                                       "intended_identifier": celex, "publisher": PUBLISHER, "intended_type": "eu_act",
                                       "language": "en", "jurisdiction": "EU", "redirect_hosts": []})
        data["sources"].append({"target_id": f"target-eu-{name}", "media_type": "text/html", "charset": "utf-8",
                                "file": {"path": f"law/{name}.html", "digest": digest},
                                "source": {"id": f"source-{name}", "revision": 0, "type": "eu_act", "publisher": PUBLISHER,
                                           "identifier": celex, "url": url, "language": "en", "jurisdiction": "EU",
                                           "document_date": None, "retrieved_at": "2026-11-06T10:00:00Z",
                                           "content_digest": digest, "provisions": [], "related_source_ids": [],
                                           "synthetic": False}})
    declarations.write_text(json.dumps(data, indent=2))


def reviewed_decision(declarations: Path) -> None:
    """Record one fictional reviewed decision: the erasure obligation applies."""
    data = json.loads(declarations.read_text())
    obligation = next(item for item in data["obligations"] if item["id"] == "obligation-gdpr-erasure")
    data["applicability_decisions"] = [{
        "applicability": "applicable", "assessment_date": data["scope"]["assessment_date"],
        "condition_answers": ["Fictional: users have accounts with personal data."], "evidence_ids": [],
        "exception_answers": ["None asserted (fictional)."], "fact_refs": [{"id": "fact-controller", "revision": 0}], "gaps": [],
        "id": "decision-erasure", "jurisdictions": ["EU"], "obligation": {"id": obligation["id"], "revision": obligation["revision"]},
        "project_id": "fitbox", "provisions": [{"locator": "Article 17", "revision": 0, "source_id": "source-gdpr",
                                               "source_target_id": "target-eu-gdpr"}],
        "rationale": "Fictional reviewer decision.", "reviewed_at": "2026-11-07T12:00:00Z", "reviewer": "Fictional reviewer",
        "revision": 0, "scope": {"id": data["scope"]["id"], "revision": data["scope"]["revision"]}, "synthetic": True}]
    declarations.write_text(json.dumps(data, indent=2))
