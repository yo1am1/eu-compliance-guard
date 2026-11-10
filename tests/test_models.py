"""Synthetic trust-boundary cases for the shared records."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from pydantic import ValidationError
from eu_compliance_guard import models as m
from eu_compliance_guard.schema import contract_schema, schema_bytes, SCHEMA_PATH

FIXTURE = json.loads((Path(__file__).resolve().parents[1] / "fixtures/contract-synthetic.json").read_text())


class ContractTests(unittest.TestCase):
    def test_synthetic_records_roundtrip_without_losing_unknowns(self):
        records = {"scope": m.Scope, "run": m.AuditRun, "source": m.LegalSource, "source_attempt": m.SourceAttempt,
                   "disposition": m.ObligationDisposition, "current": m.CurrentAssessment}
        for key, model in records.items():
            with self.subTest(record=key):
                record = m.parse_record(model, json.dumps(FIXTURE[key]))
                self.assertEqual(m.parse_record(model, m.canonical_json(record)), record)
        self.assertEqual(FIXTURE["disposition"]["manual_review"], "pending")

    def test_schema_version_and_revisions_are_not_coerced(self):
        lock = dict(schema_version=1, lock_version=1, project_id="project-fixture", run_id="run-fixture", entries=[])
        m.LawLock.model_validate(lock)
        for bad in (True, 1.0, "1", 2):
            with self.subTest(field="schema_version", value=bad), self.assertRaises(ValidationError):
                m.LawLock.model_validate({**lock, "schema_version": bad})
        for bad in (True, -1, "0", 2**53):
            with self.subTest(field="revision", value=bad), self.assertRaises(ValidationError):
                m.SourceRef.model_validate({"id": "source", "revision": bad})

    def test_source_failures_do_not_require_or_invent_legal_source_bytes(self):
        attempt = m.SourceAttempt.model_validate(FIXTURE["source_attempt"])
        self.assertIsNone(attempt.retrieved_source)
        self.assertIsNone(attempt.last_successful_source)
        with self.assertRaises(ValidationError):
            m.SourceAttempt.model_validate({**FIXTURE["source_attempt"], "retrieved_source": {"id": "invented", "revision": 0}})
        with self.assertRaises(ValidationError):
            m.SourceAttempt.model_validate({**FIXTURE["source_attempt"], "state": "retrieved", "failure": None})
        for synthetic, source_type in ((False, "synthetic_fixture"), (True, "eu_act")):
            with self.subTest(type=source_type), self.assertRaises(ValidationError):
                m.LegalSource.model_validate({**FIXTURE["source"], "synthetic": synthetic, "type": source_type})

    def test_paths_digests_and_external_links_reject_unsafe_inputs(self):
        for path in ("../private", "/private", "a/../private", "a//file", "C:/file", "a\\file", "a/./file", "a/", "a\x00file"):
            with self.subTest(path=path), self.assertRaises(ValidationError):
                m.SourceFile(path=path, digest=m.content_digest(b"test"))
        for url in ("javascript:alert(1)", "file:///private", "https://u:password@example.invalid", "https://example.invalid:bad", "https://example.invalid/\npath"):
            with self.subTest(url=url), self.assertRaises(ValidationError):
                m.LegalSource.model_validate({**FIXTURE["source"], "url": url})
        with self.assertRaises(ValidationError):
            m.SourceFile(path="safe/file.py", digest="unversioned")

    def test_current_overlay_requires_one_target_and_observed_matching_inputs(self):
        original = m.CurrentAssessment.model_validate(FIXTURE["current"])
        with self.assertRaises(ValidationError):
            m.CurrentAssessment.model_validate({**FIXTURE["current"], "freshness": "current_for_recorded_inputs"})
        with self.assertRaises(ValidationError):
            m.CurrentAssessment.model_validate({**FIXTURE["current"], "finding_assessment_id": "second-target"})
        new = m.CurrentAssessment.model_validate({**FIXTURE["current"], "revision": 1,
            "freshness": "current_for_recorded_inputs", "observed_manifest_id": "manifest-fixture", "reasons": []})
        self.assertEqual(original.freshness, "unknown")
        self.assertEqual(new.revision, 1)

    def test_time_json_and_size_limits(self):
        for changes in ({"assessment_date": "2026-02-30"}, {"assessment_date": "20261015"}):
            with self.assertRaises(ValidationError):
                m.Scope.model_validate({**FIXTURE["scope"], **changes})
        with self.assertRaises(ValidationError):
            m.LegalSource.model_validate({**FIXTURE["source"], "retrieved_at": "2026-10-15T07:00:00"})
        with self.assertRaises(ValueError):
            m.parse_record(m.Scope, b" " * (m.MAX_REQUEST_BYTES + 1))
        nested = None
        for _ in range(14): nested = [nested]
        payload = dict(id="fact", revision=0, key="unknown", value=nested, basis="unknown", evidence_ids=[], owner="synthetic", observed_at="2026-10-15T07:00:00Z", conflicts=[])
        with self.assertRaises(ValidationError):
            m.Fact.model_validate(payload)

    def test_bundle_bounds_hold_every_gap_a_run_record_declares(self):
        class Holder(m.Record):
            run: m.AuditRun

        run = m.AuditRun.model_validate(FIXTURE["run"]).model_copy(update={"gaps": [f"Synthetic gap {index}" for index in range(5000)]})
        holder = Holder(run=run)
        # Declarations keep the per-record limit; a bundle's records are bounded per list and in total.
        with self.assertRaisesRegex(ValueError, "nested collection limit"):
            m._collection_bounds(holder)
        m._collection_bounds(holder, list_limit=5000, aggregate=50000, record_limit=None)
        oversized = holder.model_copy(update={"run": run.model_copy(update={"gaps": [*run.gaps, "One more"]})})
        with self.assertRaisesRegex(ValueError, "aggregate collection limit"):
            m._collection_bounds(oversized, list_limit=5000, aggregate=50000, record_limit=None)
        with self.assertRaisesRegex(ValueError, "aggregate collection limit"):
            m._collection_bounds(holder, list_limit=5000, aggregate=5000, record_limit=None)

    def test_missing_review_evidence_and_duplicate_methods_cannot_pass(self):
        disposition = deepcopy(FIXTURE["disposition"])
        disposition["required_method_dispositions"][0]["outcome"] = "passed"
        with self.assertRaises(ValidationError):
            m.ObligationDisposition.model_validate(disposition)
        disposition["required_method_dispositions"][0]["missing_evidence"] = []
        self.assertEqual(m.ObligationDisposition.model_validate(disposition).manual_review, "pending")
        disposition["required_method_dispositions"] *= 2
        with self.assertRaises(ValidationError):
            m.ObligationDisposition.model_validate(disposition)

    def test_unrelated_input_change_needs_retained_dependency_comparison(self):
        payload = {**FIXTURE["current"], "freshness": "current_for_recorded_inputs",
                   "observed_manifest_id": "new-graph-only-manifest", "reasons": ["Independent browser inputs unchanged"]}
        with self.assertRaises(ValidationError):
            m.CurrentAssessment.model_validate(payload)
        payload["comparison_evidence_ids"] = ["comparison-fixture"]
        m.CurrentAssessment.model_validate(payload)
        with self.assertRaises(ValidationError):
            m.CurrentAssessment.model_validate({**payload, "changed_dependencies": ["browser-fixture"]})

    def test_review_claims_require_accountability_and_pinned_source_references(self):
        with self.assertRaises(ValidationError):
            m.ProvisionRef(source_target_id="target", source_id="source", locator="fictional-section")
        review = dict(source_id="source", source_revision=0, assessment_date="2026-10-15", state="reviewed_for_assessment", act_chain=[], case_law_refs=[], national_overlay_ids=[], application_dates=[], transition_dates=[], gaps=[])
        with self.assertRaises(ValidationError):
            m.SourceReview.model_validate(review)
        m.SourceReview.model_validate({**review, "reviewer": "Synthetic reviewer", "last_successful_verification": "2026-10-15T07:00:00Z"})

    def test_schema_exports_all_records_and_has_no_drift(self):
        schema = contract_schema()
        self.assertIn("SourceAttempt", schema["$defs"])
        self.assertIn("CurrentAssessment", schema["$defs"])
        self.assertNotIn("oneOf", schema)  # records only: the unused command union was removed in 2.6
        self.assertEqual(SCHEMA_PATH.read_bytes(), schema_bytes())


if __name__ == "__main__":
    unittest.main()
