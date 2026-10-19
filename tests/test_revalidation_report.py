"""Synthetic metadata rendering and hostile-text checks; no legal truth asserted."""

import html
import re
import unittest
from unittest.mock import patch

from eu_compliance_guard import models as m
from eu_compliance_guard.report import render_report
from test_revalidation_models import bundle_payload, supported_payload


class RevalidationReportTests(unittest.TestCase):
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
