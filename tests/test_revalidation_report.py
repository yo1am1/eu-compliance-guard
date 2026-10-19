"""Synthetic metadata rendering and hostile-text checks; no legal truth asserted."""

from copy import deepcopy
import html
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from eu_compliance_guard import models as m
from eu_compliance_guard.report import render_report
from test_revalidation_models import FIXTURE, FIXTURE_PATH, bundle_payload, supported_payload


class RevalidationReportTests(unittest.TestCase):
    @staticmethod
    def insufficient_payload():
        payload = supported_payload()
        declared = payload["declarations"]
        locator = "Fictional Article 7(2)(a)"
        declared["sources"][0]["source"]["identifier"] = "FICTIONAL-EU-EXAMPLE"
        declared["source_targets"][0]["intended_identifier"] = "FICTIONAL-EU-EXAMPLE"
        declared["sources"][0]["source"]["provisions"] = [locator]
        for obligation in declared["obligations"]:
            obligation["source_provisions"][0]["locator"] = locator
        for decision in declared["applicability_decisions"] + payload["effective_applicability_decisions"]:
            decision["provisions"][0]["locator"] = locator
        declared["requirements"][0].update(
            statement="FICTIONAL: retain an accountable ownership record.",
            origin={"path": "requirements.md", "digest": m.content_digest(b"fictional requirement")},
            locator="Requirement R-7")
        declared["evidence_reviews"][0].update(
            state="insufficient", rationale="Fictional ownership record omits the approval owner.",
            missing_evidence=["Fictional signed owner approval"],
            contrary_evidence=["Fictional register lists no accountable owner."])
        disposition = payload["obligation_dispositions"][0]
        disposition["manual_review"] = "unsupported"
        disposition["required_method_dispositions"][0].update(
            outcome="observed_failure", missing_evidence=["Fictional signed owner approval"])
        payload["requirement_assessments"][0].update(
            state="conflicting", rationale="Fictional review records an evidence deficiency.",
            gaps=["Fictional ownership evidence insufficient."], next_actions=["Request the missing fictional owner approval."])
        return payload

    def test_attention_issue_connects_deficiency_project_and_exact_declared_provision(self):
        report = html.unescape(render_report(m.RevalidationBundle.model_validate(self.insufficient_payload())))
        attention = report.split("## Run and retained artifacts", 1)[0]
        issue = attention.split("### FICTIONAL / SYNTHETIC — Reviewed evidence deficiency", 1)[1].split("### ", 1)[0]
        for value in (
            "requirement-example@0: FICTIONAL: retain an accountable ownership record.",
            "requirements.md — Requirement R-7", "obligation-example@0: duty",
            "FICTIONAL-EU-EXAMPLE — Fictional Article 7(2)(a)",
            "type synthetic_fixture", "source source-example@0", "https://example.invalid/synthetic-authority",
            "Effective applicability: applicable", "decision-example@0", "Fictional reviewer",
            "Fictional ownership record omits the approval owner.", "Fictional signed owner approval",
            "Fictional register lists no accountable owner.", "review-example@0", "evidence-example",
            "Next review action", "not an established legal breach",
        ):
            with self.subTest(value=value):
                self.assertIn(value, issue)
        self.assertIn("Unmapped requirement; no candidate obligation or exact legal provision", attention)
        self.assertIn("Unmapped obligation; no project requirement", attention)

    def test_unknown_and_not_applicable_issues_are_not_reported_as_legal_violations(self):
        for applicability in ("unresolved", "not_applicable"):
            payload = self.insufficient_payload()
            payload["declarations"]["applicability_decisions"][0]["applicability"] = applicability
            payload["effective_applicability_decisions"][0]["applicability"] = applicability
            payload["obligation_dispositions"][0]["applicability"] = applicability
            report = html.unescape(render_report(m.RevalidationBundle.model_validate(payload)))
            attention = report.split("## Run and retained artifacts", 1)[0]
            with self.subTest(applicability=applicability):
                self.assertIn("Effective applicability: " + applicability, attention)
                self.assertIn("not an established legal breach", attention)
                self.assertIn("a not-applicable decision is not a violation", attention)
                self.assertNotIn("Legal violation:", attention)

    def test_supported_and_metadata_missing_cases_remain_explicit_in_attention(self):
        text = html.unescape(render_report(m.RevalidationBundle.model_validate(supported_payload())))
        attention = text.split("## Run and retained artifacts", 1)[0]
        self.assertIn("Recorded mapping support", attention)
        self.assertIn("Requirement assessment: supported", attention)
        self.assertIn("Fictional section 1", attention)
        payload = bundle_payload()
        payload["declarations"]["obligations"][0]["source_provisions"] = []
        payload["declarations"]["requirements"][0]["origin"] = None
        text = html.unescape(render_report(m.RevalidationBundle.model_validate(payload)))
        attention = text.split("## Run and retained artifacts", 1)[0]
        self.assertIn("No provision locator declared", attention)
        self.assertIn("Review gap", attention)
        self.assertNotIn("Reviewed evidence deficiency", attention)

    def test_offline_insufficiency_run_places_fictional_article_next_to_issue(self):
        from eu_compliance_guard.revalidation import run
        payload = deepcopy(FIXTURE)
        source_bytes = b"FICTIONAL ONLY. Fictional Article 7(2)(a): retain an accountable ownership record."
        locator = "Fictional Article 7(2)(a)"
        source = payload["sources"][0]
        source["file"]["digest"] = source["source"]["content_digest"] = m.content_digest(source_bytes)
        source["source"].update(identifier="FICTIONAL-EU-EXAMPLE", provisions=[locator])
        payload["source_targets"][0]["intended_identifier"] = "FICTIONAL-EU-EXAMPLE"
        for obligation in payload["obligations"]:
            obligation["source_provisions"][0]["locator"] = locator
        payload["applicability_decisions"][0]["provisions"][0]["locator"] = locator
        requirement_bytes = b"FICTIONAL: retain an accountable ownership record."
        payload["requirements"][0].update(statement=requirement_bytes.decode(),
            origin={"path": "requirements.md", "digest": m.content_digest(requirement_bytes)}, locator="Requirement R-7",
            activity_ids=["activity-example"])
        payload["scope"]["activities"] = [{"id": "activity-example", "purpose": "Fictional onboarding",
            "subjects": [], "data_categories": [], "roles": [], "lawful_basis": deepcopy(payload["scope"]["roles"][0]),
            "recipients": [], "locations": [], "stores": [], "retention": [], "evidence_owner": "Fictional owner"}]
        payload["evidence_reviews"][0].update(state="insufficient",
            rationale="Fictional ownership record omits the approval owner.",
            missing_evidence=["Fictional signed owner approval"], contrary_evidence=["Fictional record lacks an owner."])
        with tempfile.TemporaryDirectory(prefix="eucg-report-issue-") as parent:
            parent = Path(parent)
            (parent / "revalidation-synthetic").mkdir()
            (parent / source["file"]["path"]).write_bytes(source_bytes)
            (parent / payload["evidence"][0]["path"]).write_bytes(
                (FIXTURE_PATH.parent / FIXTURE["evidence"][0]["path"]).read_bytes())
            (parent / "requirements.md").write_bytes(requirement_bytes)
            declaration = parent / "input.json"
            declaration.write_text(json.dumps(payload), encoding="utf-8")
            bundle = run(declaration, parent / "run")
            self.assertEqual(bundle.obligation_dispositions[0].required_method_dispositions[0].outcome, "observed_failure")
            report = html.unescape((parent / "run/report.md").read_text())
            issue = report.split("### FICTIONAL / SYNTHETIC — Reviewed evidence deficiency", 1)[1].split("### ", 1)[0]
            for value in (locator, "FICTIONAL-EU-EXAMPLE", "approval owner", "requirements.md — Requirement R-7",
                          "activity-example: Fictional onboarding", "Fictional signed owner approval"):
                self.assertIn(value, issue)
            self.assertNotIn("established violation", issue)
            self.assertTrue((parent / "run/complete.json").is_file())

    def test_all_declared_records_mapping_chains_and_uncertainty_are_visible(self):
        bundle = m.RevalidationBundle.model_validate(supported_payload())
        text = html.unescape(render_report(bundle))
        for value in (
            "FICTIONAL / SYNTHETIC", "Processing state: partial", "No compliance verdict",
            "requirement-example@0 → obligation-example@0", "unmapped obligation",
            "requirement-unmapped", "obligation-unmapped", "unresolved", "supported",
            "declared", "assumed", "unknown", "SYNTHETIC", "Exclusions",
            "Fictional reviewer", "Fictional 2026-10-18", "Source review",
            "amendments_repeal", "case_law", "national_overlays", "translation",
            "application_transition_dates", "Fictional section 1", "documented",
            bundle.evidence[0].digest, "Missing evidence", "Contrary evidence", "Next actions",
        ):
            with self.subTest(value=value):
                self.assertIn(value, text)
        for family in m.LEGAL_FAMILIES:
            self.assertIn("Family: " + family, text)
        # Every derived record carries the envelope label, including mixed input.
        self.assertTrue(all(line.startswith("### FICTIONAL / SYNTHETIC")
                            for line in text.splitlines() if line.startswith("### ")))

    def test_hostile_markup_urls_paths_and_controls_are_inert(self):
        payload = bundle_payload()
        hostile = '<script>alert(1)</script> ![image](https://evil.invalid/pixel) [run](javascript:alert(2)) `code` | cell\n# injected\r\x00\x1b\u202e **bold** <https://evil.invalid/?secret=x> user@evil.invalid'
        payload["declarations"]["requirements"][0]["statement"] = hostile
        payload["declarations"]["scope"]["exclusions"].append(hostile)
        payload["declarations"]["source_reviews"][0]["review_notes"]["identity"] = hostile
        payload["declarations"]["evidence_reviews"][0]["contrary_evidence"] = [hostile]
        text = render_report(m.RevalidationBundle.model_validate(payload))
        for raw in ("<script>", "![image]", "javascript:", "https://", "user@evil", "`code`", "| cell", "\n# injected", "\x00", "\x1b", "\u202e"):
            with self.subTest(raw=raw):
                self.assertNotIn(raw, text)
        links = re.findall(r"\]\(([^)]+)\)", text)
        self.assertEqual(links, ["input.json", "manifest.json", "bundle.json", "complete.json"])
        self.assertIn("<script>", html.unescape(text))  # Visible literal text after Markdown entity decoding.
        self.assertIn("\\u000a", html.unescape(text))
        self.assertIn("\\u202e", html.unescape(text))

    def test_renderer_has_no_evidence_body_io_and_preserves_mixed_labels(self):
        payload = bundle_payload()
        payload["declarations"]["requirements"][0]["synthetic"] = False
        payload["declarations"]["sources"][0]["source"].update(type="eu_act", synthetic=False)
        payload["declarations"]["source_targets"][0]["intended_type"] = "eu_act"
        bundle = m.RevalidationBundle.model_validate(payload)
        with patch("builtins.open", side_effect=AssertionError("renderer must not read files")), \
                patch("pathlib.Path.read_bytes", side_effect=AssertionError("no evidence bodies")):
            report = render_report(bundle)
        self.assertIn("MIXED DECLARATIONS", report)
        self.assertNotIn("RAW-EVIDENCE-SECRET-SENTINEL", report)
        self.assertIn("body excluded", report)

    def test_output_byte_bound_at_boundary_and_one_over_without_truncation(self):
        bundle = m.RevalidationBundle.model_validate(bundle_payload())
        report = render_report(bundle)
        exact = len(report.encode("utf-8"))
        with patch("eu_compliance_guard.report.MAX_REPORT_BYTES", exact):
            self.assertEqual(render_report(bundle), report)
        with patch("eu_compliance_guard.report.MAX_REPORT_BYTES", exact - 1):
            with self.assertRaisesRegex(ValueError, "^report-too-large$"):
                render_report(bundle)

    def test_empty_register_and_requirements_are_explicit_gaps(self):
        payload = bundle_payload()
        for key in ("requirements", "obligations", "applicability_decisions", "evidence_reviews"):
            payload["declarations"][key] = []
        payload["requirement_assessments"] = []
        payload["obligation_dispositions"] = []
        payload["effective_applicability_decisions"] = []
        report = render_report(m.RevalidationBundle.model_validate(payload))
        self.assertIn("No requirements supplied", report)
        self.assertIn("No obligation register supplied", report)


if __name__ == "__main__":
    unittest.main()
