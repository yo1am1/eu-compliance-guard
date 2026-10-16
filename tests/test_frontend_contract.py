"""Synthetic wire regressions for frontend recovery and safe detail delivery."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from pydantic import ValidationError

from eu_compliance_guard import models as m


FIXTURE = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures/contract-synthetic.json").read_text()
)


def recovery_snapshot():
    payload = deepcopy(FIXTURE["snapshot"])
    payload["findings"] = [{
        "id": "finding-ui", "project_id": "project-fixture",
        "control_id": "control-ui", "subject_id": "subject-ui",
    }]
    payload["finding_assessments"] = [{
        "id": "assessment-ui", "project_id": "project-fixture",
        "run_id": "run-fixture", "finding_id": "finding-ui", "revision": 1,
        "manifest_id": "manifest-fixture", "control_revision": 0,
        "obligation_disposition_ids": ["disposition-fixture"],
        "attempt_ids": ["attempt-fixture"], "evidence_ids": [],
        "validation_ids": [], "technical_outcome": "not_tested",
        "impact": "Synthetic check pending", "affected_parties": [],
        "owner": "Synthetic reviewer", "action_ids": [],
    }]
    payload["current_assessments"][0].pop("obligation_disposition_id")
    payload["current_assessments"][0]["finding_assessment_id"] = "assessment-ui"
    return payload


def patch_preview():
    diff = "--- before\n+++ after\n-old\n+synthetic café\n"
    digest = m.content_digest(diff.encode("utf-8"))
    return {
        "project_id": "project-fixture", "run_id": "run-fixture",
        "proposal_id": "patch-ui", "revision": 0, "diff_digest": digest,
        "preview_digest": digest, "redaction": "safe", "diff": diff,
    }


class FrontendContractTests(unittest.TestCase):
    def test_snapshot_rejects_ambiguous_revisions_and_dangling_assessment_links(self):
        original = recovery_snapshot()
        m.parse_record(m.Snapshot, json.dumps(original))
        for collection in ("findings", "finding_assessments", "current_assessments"):
            payload = deepcopy(original)
            duplicate = deepcopy(payload[collection][0])
            if "revision" in duplicate:
                duplicate["revision"] += 1
            payload[collection].append(duplicate)
            with self.subTest(duplicate=collection), self.assertRaises(ValidationError):
                m.parse_record(m.Snapshot, json.dumps(payload))
        for field, missing in (
            ("finding_id", "missing-finding"),
            ("attempt_ids", ["missing-attempt"]),
            ("obligation_disposition_ids", ["missing-disposition"]),
        ):
            payload = deepcopy(original)
            payload["finding_assessments"][0][field] = missing
            with self.subTest(reference=field), self.assertRaises(ValidationError):
                m.parse_record(m.Snapshot, json.dumps(payload))

    def test_snapshot_rejects_misbound_finding_overlays(self):
        for field, wrong in (
            ("project_id", "other-project"),
            ("historical_run_id", "other-run"),
            ("finding_assessment_id", "missing-assessment"),
            ("expected_manifest_id", "other-historical-manifest"),
        ):
            payload = recovery_snapshot()
            payload["current_assessments"][0][field] = wrong
            with self.subTest(field=field), self.assertRaises(ValidationError):
                m.parse_record(m.Snapshot, json.dumps(payload))

    def test_graph_only_freshness_roundtrips_without_rewriting_history(self):
        historical = m.parse_record(m.Snapshot, json.dumps(recovery_snapshot()))
        payload = recovery_snapshot()
        payload["current_assessments"][0].update(
            revision=1, freshness="current_for_recorded_inputs",
            observed_manifest_id="manifest-graph-only-change",
            comparison_evidence_ids=["comparison-browser-dependencies"],
            reasons=["Only graph inputs changed; browser dependencies unchanged"],
        )
        current = m.parse_record(m.Snapshot, json.dumps(payload))
        self.assertEqual(current.finding_assessments, historical.finding_assessments)
        self.assertEqual(historical.current_assessments[0].freshness, "unknown")
        self.assertEqual(current.current_assessments[0].comparison_evidence_ids,
                         ["comparison-browser-dependencies"])
        self.assertEqual(m.parse_record(m.Snapshot, m.canonical_json(current)), current)
        for changes in (
            {"comparison_evidence_ids": []},
            {"observed_manifest_id": None},
            {"changed_dependencies": ["deployed-browser-fixture"]},
        ):
            invalid = deepcopy(payload)
            invalid["current_assessments"][0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                m.parse_record(m.Snapshot, json.dumps(invalid))

    def test_safe_evidence_never_delivers_unavailable_or_unredacted_text(self):
        text = "Synthetic café\n"
        evidence = {
            "id": "evidence-ui", "project_id": "project-fixture",
            "run_id": "run-fixture", "kind": "text", "provenance": "observed",
            "digest": m.content_digest(text.encode("utf-8")),
            "captured_at": "2026-10-15T07:00:00Z", "manifest_id": "manifest-fixture",
            "media_type": "text/plain", "redaction": "safe",
            "availability": "available", "source_refs": [],
        }
        accepted = m.parse_record(m.SafeEvidence, json.dumps({
            "evidence": evidence, "content_text": text,
        }))
        self.assertEqual(accepted.content_text, text)
        for changes in (
            {"redaction": "blocked"}, {"redaction": "unknown"},
            {"availability": "purged"}, {"availability": "missing"},
            {"availability": "corrupt"}, {"availability": "blocked"},
        ):
            metadata = {**evidence, **changes}
            with self.subTest(changes=changes):
                with self.assertRaises(ValidationError):
                    m.parse_record(m.SafeEvidence, json.dumps({
                        "evidence": metadata, "content_text": text,
                        "blocked_reason": "Synthetic unavailable preview",
                    }))
                blocked = m.parse_record(m.SafeEvidence, json.dumps({
                    "evidence": metadata, "blocked_reason": "Synthetic unavailable preview",
                }))
                self.assertIsNone(blocked.content_text)
                self.assertNotIn(text, m.canonical_json(blocked).decode("utf-8"))

    def test_patch_preview_checks_preview_bytes_and_preserves_separate_diff_digest(self):
        payload = patch_preview()
        payload["diff_digest"] = m.content_digest(b"Original diff before redaction")
        accepted = m.parse_record(m.PatchPreview, json.dumps(payload))
        self.assertNotEqual(accepted.diff_digest, accepted.preview_digest)
        self.assertEqual(accepted.diff, payload["diff"])
        for changes in (
            {"diff": payload["diff"] + "tampered"}, {"preview_digest": None},
            {"redaction": "blocked"}, {"redaction": "unknown"},
            {"blocked_reason": "Preview withheld"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                m.parse_record(m.PatchPreview, json.dumps({**payload, **changes}))
        blocked = m.parse_record(m.PatchPreview, json.dumps({
            **payload, "redaction": "blocked", "diff": None,
            "blocked_reason": "Synthetic redaction failure",
        }))
        self.assertIsNone(blocked.diff)

    def test_detail_pages_enforce_section_scope_and_page_bound(self):
        page = {
            "schema_version": 1, "project_id": "project-fixture",
            "origin_run_id": "run-fixture", "section": "patches",
            "projection_revision": 2, "records": [patch_preview()],
            "next_cursor": "page-two",
        }
        accepted = m.parse_record(m.DetailPage, json.dumps(page))
        self.assertEqual(accepted.next_cursor, "page-two")
        self.assertEqual(m.parse_record(m.DetailPage, m.canonical_json(accepted)), accepted)
        for section in ("sources", "controls", "conversations", "graph"):
            with self.subTest(section=section), self.assertRaises(ValidationError):
                m.parse_record(m.DetailPage, json.dumps({**page, "section": section}))
        for field, wrong in (("project_id", "other-project"), ("run_id", "other-run")):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                m.parse_record(m.DetailPage, json.dumps({
                    **page, "records": [{**patch_preview(), field: wrong}],
                }))
        m.parse_record(m.DetailPage, json.dumps({**page, "records": [patch_preview()] * 100}))
        with self.assertRaises(ValidationError):
            m.parse_record(m.DetailPage, json.dumps({**page, "records": [patch_preview()] * 101}))

    def test_conversation_detail_retains_distinct_origin_and_execution_runs(self):
        conversation = {
            "id": "conversation-ui", "project_id": "project-fixture",
            "finding_id": "finding-ui", "finding_assessment_id": "assessment-ui",
            "origin_run_id": "run-fixture", "execution_run_id": "successor-run",
            "context_manifest_id": "historical-context", "revision": 1,
            "message_ids": ["message-ui"],
        }
        page = {
            "schema_version": 1, "project_id": "project-fixture",
            "origin_run_id": "run-fixture", "section": "conversations",
            "projection_revision": 1, "records": [conversation],
        }
        accepted = m.parse_record(m.DetailPage, json.dumps(page))
        retained = accepted.records[0]
        self.assertEqual(retained.origin_run_id, "run-fixture")
        self.assertEqual(retained.execution_run_id, "successor-run")
        with self.assertRaises(ValidationError):
            m.parse_record(m.DetailPage, json.dumps({**page, "origin_run_id": "successor-run"}))


if __name__ == "__main__":
    unittest.main()
