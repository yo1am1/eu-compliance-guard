"""Build the draft starter packs in eu_compliance_guard/starter_packs/ from the official texts in
fixtures/official/.

The packs are drafts written with AI assistance from the article text and reviewed by no one
(Owner decision, 2026-11-06: no lawyer, no guarantees). Each obligation pins exact articles;
each pack records the digest of every pinned article as read here, so `pack import` can say
when a project's own text differs. Run `python scripts/build_starter_packs.py` after changing a
pack below; a test fails when the shipped packs and this script disagree.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eu_compliance_guard import articles, models as m, packs  # noqa: E402
from eu_compliance_guard.notice import LEGAL_NOTICE  # noqa: E402

DRAFT = "Draft written with AI assistance from the article text; reviewed by no one; no guarantee."
PUBLISHER = "Publications Office of the European Union"
TEXTS = {  # target id: (official fixture, CELEX, family)
    "target-eu-gdpr": ("gdpr-32016R0679", "32016R0679", "gdpr"),
    "target-eu-eprivacy": ("eprivacy-02002L0058-20091219", "02002L0058-20091219", "eprivacy"),
    "target-eu-eaa": ("eaa-32019L0882", "32019L0882", "accessibility"),
    "target-eu-cra": ("cra-32024R2847", "32024R2847", "cybersecurity"),
}


def duty(identity, target, family, locators, conditions, exceptions=()):
    return {"id": identity, "revision": 0, "family": family, "classification": "duty",
            "source_provisions": [{"source_target_id": target, "source_id": None, "revision": None, "locator": locator}
                                  for locator in locators],
            "conditions": list(conditions), "exceptions": list(exceptions), "overlay_ids": [], "control_ids": [],
            "required_methods": [], "limitations": [DRAFT]}


G, E, A, C = "target-eu-gdpr", "target-eu-eprivacy", "target-eu-eaa", "target-eu-cra"
PACKS = {
    "gdpr-core": ("GDPR core obligations for an online service", G, [
        duty("obligation-gdpr-lawful-basis", G, "gdpr", ["Article 6(1)", "Article 7"],
             ["Personal data are processed.", "Where the basis is consent, the controller can demonstrate it (Article 7)."]),
        duty("obligation-gdpr-child-consent", G, "gdpr", ["Article 8(1)"],
             ["An information society service is offered directly to a child and processing relies on consent."],
             ["A child of at least 16 can consent; Member States may set a lower age, not below 13."]),
        duty("obligation-gdpr-information", G, "gdpr", ["Article 12", "Article 13", "Article 14"],
             ["Personal data are collected from the data subject (Article 13) or obtained otherwise (Article 14)."]),
        duty("obligation-gdpr-access", G, "gdpr", ["Article 15"], ["A data subject asks for access to their personal data."]),
        duty("obligation-gdpr-erasure", G, "gdpr", ["Article 17"],
             ["A data subject asks for erasure and one of the grounds in Article 17(1) applies."],
             ["The exceptions in Article 17(3), such as a legal obligation to keep the data."]),
        duty("obligation-gdpr-portability", G, "gdpr", ["Article 20"],
             ["Processing is based on consent or a contract and carried out by automated means."]),
        duty("obligation-gdpr-objection", G, "gdpr", ["Article 21"],
             ["Processing is based on Article 6(1)(e) or (f), or is for direct marketing."]),
        duty("obligation-gdpr-processor-contract", G, "gdpr", ["Article 28"],
             ["A processor processes personal data on the controller's behalf."]),
        duty("obligation-gdpr-records", G, "gdpr", ["Article 30"], ["The controller or processor processes personal data."],
             ["Fewer than 250 employees, unless the processing is likely to result in a risk, is not occasional, or "
              "includes special categories or criminal-offence data (Article 30(5))."]),
        duty("obligation-gdpr-security", G, "gdpr", ["Article 32"], ["Personal data are processed."]),
        duty("obligation-gdpr-breach-notification", G, "gdpr", ["Article 33", "Article 34"],
             ["A personal data breach occurs: notify the supervisory authority within 72 hours where feasible, unless "
              "it is unlikely to result in a risk; tell data subjects when it is likely to result in a high risk."]),
        duty("obligation-gdpr-dpia", G, "gdpr", ["Article 35"],
             ["A type of processing is likely to result in a high risk to the rights and freedoms of natural persons."]),
        duty("obligation-gdpr-transfers", G, "gdpr", ["Article 44", "Article 45", "Article 46"],
             ["Personal data are transferred to a third country or an international organisation."]),
    ]),
    "eprivacy-cookies": ("ePrivacy: cookies and electronic marketing", E, [
        duty("obligation-eprivacy-terminal-storage", E, "eprivacy", ["Article 5(3)"],
             ["Information is stored on, or read from, a user's device (cookies, local storage, similar technologies)."],
             ["Storage or access for the sole purpose of carrying out a transmission, or strictly necessary for a "
              "service the user explicitly requested (Article 5(3)).",
              "Member States implement the Directive in national law; check the national rules."]),
        duty("obligation-eprivacy-direct-marketing", E, "eprivacy", ["Article 13(1)", "Article 13(2)"],
             ["Electronic mail, automated calls or fax are used for direct marketing."],
             ["Existing customers, for the sender's own similar products, with a free and easy opt-out at collection "
              "and in every message (Article 13(2))."]),
    ]),
    "eaa-services": ("European Accessibility Act: services to consumers", A, [
        duty("obligation-eaa-service-accessibility", A, "accessibility", ["Article 2(2)", "Article 4(3)"],
             ["A service listed in Article 2(2) (for example e-commerce, consumer banking, e-books, electronic "
              "communications) is provided to consumers after 28 June 2025."],
             ["Microenterprises providing services are exempt (Article 4(5)).",
              "A fundamental alteration or a disproportionate burden, assessed and documented (Article 14).",
              "Member States implement the Directive in national law; check the national rules."]),
        duty("obligation-eaa-service-information", A, "accessibility", ["Article 13"],
             ["The service is subject to the accessibility requirements: prepare the information in Annex V, make "
              "it public and keep it while the service is provided."]),
    ]),
    "cra-products": ("Cyber Resilience Act: manufacturers of products with digital elements", C, [
        duty("obligation-cra-essential-requirements", C, "cybersecurity", ["Article 6", "Article 13"],
             ["A product with digital elements is made available on the Union market (Article 2(1)); applies from "
              "11 December 2027 (Article 71)."],
             ["Products covered by the rules listed in Article 2(2) to (4), such as medical devices and vehicles."]),
        duty("obligation-cra-reporting", C, "cybersecurity", ["Article 14"],
             ["The manufacturer becomes aware of an actively exploited vulnerability or a severe incident: early "
              "warning within 24 hours and notification within 72 hours; applies from 11 September 2026 (Article 71)."]),
        duty("obligation-cra-conformity", C, "cybersecurity", ["Article 28", "Article 30", "Article 32"],
             ["The product is placed on the market: conformity assessment, EU declaration of conformity and CE marking."]),
    ]),
}


def law_entry(target: str) -> tuple[m.SourceTarget, dict[str, dict], bytes]:
    stem, celex, family = TEXTS[target]
    raw = gzip.decompress((ROOT / "fixtures/official" / f"{stem}.html.gz").read_bytes())
    source = m.SourceTarget(id=target, revision=0, family=family,
                            intended_url=f"https://publications.europa.eu/resource/celex/{celex}",
                            intended_identifier=celex, publisher=PUBLISHER, intended_type="eu_act", language="en",
                            jurisdiction="EU", redirect_hosts=[])
    return source, articles.parse(raw, "application/xhtml+xml"), raw


def build(name: str) -> m.ObligationPack:
    title, target, obligations = PACKS[name]
    source, parsed, raw = law_entry(target)
    keys = sorted({articles.article_key(pin["locator"]) for item in obligations for pin in item["source_provisions"]})
    missing = [key for key in keys if key not in parsed]
    if missing:
        raise SystemExit(f"{name}: pinned provisions not in the official text: {missing}")
    law = m.LawLockEntry(target_id=target, version=TEXTS[target][1], source_digest=m.content_digest(raw),
                         articles=[m.LawLockArticle(key=key, digest=m.content_digest(
                             f"{parsed[key]['title']}\n{parsed[key]['text']}".encode("utf-8"))) for key in keys])
    return m.ObligationPack(
        schema_version=1, pack_version=1, id=f"pack-eu-{name}", revision=0, title=title, status="draft",
        synthetic=False, source_targets=[source],
        obligations=[m.Obligation.model_validate(item) for item in sorted(obligations, key=lambda item: item["id"])],
        law=[law],
        limitations=["Starter pack: candidate obligations only; whether each applies is a named reviewer's decision.",
                     DRAFT, "Directives bind Member States; national transposition is not covered.", LEGAL_NOTICE])


def main() -> None:
    folder = ROOT / "eu_compliance_guard" / "starter_packs"
    folder.mkdir(exist_ok=True)
    for name in PACKS:
        (folder / f"eu-{name}.pack.json").write_bytes(packs.to_bytes(build(name)))
        print(f"eu_compliance_guard/starter_packs/eu-{name}.pack.json")


if __name__ == "__main__":
    main()
