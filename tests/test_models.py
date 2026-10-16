"""Synthetic trust-boundary cases for the shared engine/frontend/host contracts."""

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
        records = {"scope": m.Scope, "run": m.AuditRun, "attempt": m.CheckAttempt,
                   "source": m.LegalSource, "source_attempt": m.SourceAttempt,
                   "disposition": m.ObligationDisposition, "current": m.CurrentAssessment,
                   "snapshot": m.Snapshot}
        for key, model in records.items():
            with self.subTest(record=key):
                record = m.parse_record(model, json.dumps(FIXTURE[key]))
                self.assertEqual(m.parse_record(model, m.canonical_json(record)), record)
        self.assertEqual(m.parse_command(json.dumps(FIXTURE["command"])).operation, "audit.cancel")
        self.assertEqual(FIXTURE["disposition"]["manual_review"], "pending")

    def test_commands_reject_forged_identity_unknown_operations_and_extra_arguments(self):
        for changes in ({"caller": "owner"}, {"operation": "shell.exec"},
                        {"arguments": {"reason": "test", "owner": True}},
                        {"arguments": {"reason": "test", "command": "anything"}}):
            payload = {**FIXTURE["command"], **changes}
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                m.parse_command(json.dumps(payload))

    def test_schema_version_and_revisions_are_not_coerced(self):
        for field, bad in (("schema_version", True), ("schema_version", 1.0),
                           ("schema_version", "1"), ("schema_version", 2),
                           ("expected_revision", True), ("expected_revision", -1),
                           ("expected_revision", "0"), ("expected_revision", 2**53)):
            with self.subTest(field=field, value=bad), self.assertRaises(ValidationError):
                m.parse_command(json.dumps({**FIXTURE["command"], field: bad}))

    def test_unfinished_cancelled_and_interrupted_checks_cannot_pass(self):
        for state in ("pending", "running", "cancelled", "interrupted"):
            with self.subTest(state=state), self.assertRaises(ValidationError):
                m.CheckAttempt.model_validate({**FIXTURE["attempt"], "state": state, "outcome": "passed"})
        with self.assertRaises(ValidationError):
            m.CheckAttempt.model_validate({**FIXTURE["attempt"], "state": "completed"})
        m.CheckAttempt.model_validate({**FIXTURE["attempt"], "state": "interrupted", "outcome": "blocked"})

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

    def test_snapshot_rejects_wrong_projects_runs_manifests_and_cursors(self):
        for field, value in (("project_id", "other"), ("run_id", "other"), ("manifest_id", "other")):
            payload = deepcopy(FIXTURE["snapshot"])
            payload["attempts"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValidationError):
                m.Snapshot.model_validate(payload)
        for cursor in ("other:0", "run-fixture:01", "run-fixture:-1", "run-fixture:9007199254740992"):
            with self.subTest(cursor=cursor), self.assertRaises(ValidationError):
                m.Snapshot.model_validate({**FIXTURE["snapshot"], "cursor": cursor})
        with self.assertRaises(ValidationError):
            m.Snapshot.model_validate({**FIXTURE["snapshot"], "terminal": True})

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
            m.parse_command(b" " * (m.MAX_REQUEST_BYTES + 1))
        nested = None
        for _ in range(14): nested = [nested]
        payload = dict(id="fact", revision=0, key="unknown", value=nested, basis="unknown", evidence_ids=[], owner="synthetic", observed_at="2026-10-15T07:00:00Z", conflicts=[])
        with self.assertRaises(ValidationError):
            m.Fact.model_validate(payload)

    def test_proposals_need_contained_paths_retests_and_verification_references(self):
        envelope = dict(schema_version=1, conversation_id="conversation", context_manifest_id="context", finding_assessment_id="assessment", message="Synthetic proposal", proposal=dict(kind="one_file_text_patch", relative_path="safe.py", preimage_digest=m.content_digest(b"before"), proposed_postimage="after", retest_ids=["check"]))
        m.AgentReplyEnvelope.model_validate(envelope)
        for changes in ({"relative_path": "../other"}, {"retest_ids": []}, {"proposed_postimage": "x" * 524289}):
            payload = {**envelope, "proposal": {**envelope["proposal"], **changes}}
            with self.assertRaises(ValidationError):
                m.AgentReplyEnvelope.model_validate(payload)
        patch = dict(id="patch", project_id="project-fixture", run_id="run-fixture", finding_ids=["finding"], revision=0, diff_digest=m.content_digest(b"diff"), relative_paths=["safe.py"], preimages=[m.content_digest(b"before")], expected_postimages=[m.content_digest(b"after")], permission_id="permission", retest_ids=["check"], state="verified", before_attempt_ids=[], after_attempt_ids=[])
        with self.assertRaises(ValidationError):
            m.PatchProposal.model_validate(patch)

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

    def test_snapshot_rejects_duplicate_and_dangling_references(self):
        payload = deepcopy(FIXTURE["snapshot"])
        payload["attempts"] *= 2
        with self.assertRaises(ValidationError):
            m.Snapshot.model_validate(payload)
        payload = deepcopy(FIXTURE["snapshot"])
        payload["current_assessments"][0]["obligation_disposition_id"] = "missing"
        with self.assertRaises(ValidationError):
            m.Snapshot.model_validate(payload)

    def test_unrelated_input_change_needs_retained_dependency_comparison(self):
        payload = {**FIXTURE["current"], "freshness": "current_for_recorded_inputs",
                   "observed_manifest_id": "new-graph-only-manifest", "reasons": ["Independent browser inputs unchanged"]}
        with self.assertRaises(ValidationError):
            m.CurrentAssessment.model_validate(payload)
        payload["comparison_evidence_ids"] = ["comparison-fixture"]
        m.CurrentAssessment.model_validate(payload)
        with self.assertRaises(ValidationError):
            m.CurrentAssessment.model_validate({**payload, "changed_dependencies": ["browser-fixture"]})

    def test_safe_previews_reject_unknown_redaction_wrong_digests_and_sections(self):
        digest = m.content_digest(b"safe synthetic text")
        evidence = dict(id="evidence", project_id="project-fixture", run_id="run-fixture", kind="text", provenance="observed", digest=digest, captured_at="2026-10-15T07:00:00Z", manifest_id="manifest-fixture", media_type="text/plain", redaction="unknown", availability="available", source_refs=[])
        with self.assertRaises(ValidationError):
            m.SafeEvidence(evidence=evidence, content_text="safe synthetic text")
        m.SafeEvidence(evidence=evidence, blocked_reason="Redaction unverified")
        evidence["redaction"] = "safe"
        m.SafeEvidence(evidence=evidence, content_text="safe synthetic text")
        with self.assertRaises(ValidationError):
            m.SafeEvidence(evidence=evidence, content_text="different bytes")
        page = dict(schema_version=1, project_id="project-fixture", origin_run_id="run-fixture", section="sources", projection_revision=0, records=[FIXTURE["source"]])
        m.DetailPage.model_validate(page)
        with self.assertRaises(ValidationError):
            m.DetailPage.model_validate({**page, "section": "patches"})
        preview = dict(project_id="project-fixture", run_id="run-fixture", proposal_id="patch", revision=0, diff_digest=digest, preview_digest=digest, redaction="unknown", diff="safe synthetic text")
        with self.assertRaises(ValidationError):
            m.PatchPreview.model_validate(preview)
        m.PatchPreview.model_validate({**preview, "redaction": "safe"})

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
        self.assertEqual(len(schema["oneOf"]), 16)
        self.assertEqual(SCHEMA_PATH.read_bytes(), schema_bytes())
        from fastapi.sse import EventSourceResponse
        self.assertIsNotNone(EventSourceResponse)


if __name__ == "__main__":
    unittest.main()
