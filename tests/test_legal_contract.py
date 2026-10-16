"""Fictional legal-source and obligation regressions; no legal authority is verified."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from pydantic import ValidationError

from eu_compliance_guard import models as m


FIXTURE = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures/contract-synthetic.json").read_text()
)
REVIEW = {
    "source_id": FIXTURE["source"]["id"],
    "source_revision": FIXTURE["source"]["revision"],
    "assessment_date": "2026-10-15",
    "state": "reviewed_for_assessment",
    "act_chain": [],
    "case_law_refs": [],
    "national_overlay_ids": [],
    "application_dates": [],
    "transition_dates": [],
    "last_successful_verification": "2026-10-15T07:00:00Z",
    "reviewer": "Fictional fixture reviewer",
    "gaps": [],
}


def shared_control_snapshot():
    payload = deepcopy(FIXTURE["snapshot"])
    attempt = payload["attempts"][0]
    attempt.update(state="completed", outcome="passed", expected=False, actual=False)
    applicable = deepcopy(FIXTURE["disposition"])
    applicable.update(
        id="disposition-applicable", obligation_id="fictional-obligation-applicable",
        applicability_decision_id="fictional-decision-applicable",
        applicability="applicable", rationale="Fictional fixture condition established",
        manual_review="supported",
        required_method_dispositions=[{
            "method": "technical", "outcome": "passed",
            "attempt_ids": [attempt["id"]], "review_ids": [], "missing_evidence": [],
        }],
    )
    payload["obligation_dispositions"].append(applicable)
    payload["findings"] = [{
        "id": "finding-shared", "project_id": payload["project_id"],
        "control_id": "fictional-shared-control", "subject_id": "synthetic-subject",
    }]
    payload["finding_assessments"] = [{
        "id": "assessment-shared", "project_id": payload["project_id"],
        "run_id": payload["run"]["id"], "finding_id": "finding-shared", "revision": 0,
        "manifest_id": payload["run"]["manifest_id"], "control_revision": 0,
        "obligation_disposition_ids": [item["id"] for item in payload["obligation_dispositions"]],
        "attempt_ids": [attempt["id"]], "evidence_ids": [], "validation_ids": [],
        "technical_outcome": "passed", "impact": "Fictional assertion only",
        "affected_parties": [], "owner": "Synthetic owner", "action_ids": [],
    }]
    return payload


class LegalContractTests(unittest.TestCase):
    def test_refresh_failure_keeps_previous_source_and_exposes_review_gap(self):
        source = m.LegalSource.model_validate(FIXTURE["source"])
        original = source.model_dump()
        previous = {"id": source.id, "revision": source.revision}
        failure = m.SourceAttempt.model_validate({
            **FIXTURE["source_attempt"], "last_successful_source": previous,
            "attempted_at": "2026-10-15T08:00:00Z",
        })
        stale = m.SourceReview.model_validate({
            **REVIEW, "state": "stale", "gaps": ["Fictional refresh unavailable"],
        })
        self.assertEqual(failure.last_successful_source.model_dump(), previous)
        self.assertIsNone(failure.retrieved_source)
        self.assertEqual(source.model_dump(), original)
        self.assertEqual(stale.last_successful_verification, REVIEW["last_successful_verification"])
        with self.assertRaises(ValidationError):
            m.SourceReview.model_validate({**stale.model_dump(), "state": "reviewed_for_assessment"})

    def test_first_failure_needs_no_previous_or_fabricated_source(self):
        failed = m.SourceAttempt.model_validate(FIXTURE["source_attempt"])
        self.assertIsNone(failed.last_successful_source)
        self.assertIsNone(failed.retrieved_source)
        for change in (
            {"retrieved_source": {"id": "invented", "revision": 0}},
            {"failure": None},
            {"state": "retrieved", "failure": None},
        ):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                m.SourceAttempt.model_validate({**FIXTURE["source_attempt"], **change})

    def test_unverified_translation_retains_bytes_without_verified_review(self):
        source_ref = {"id": FIXTURE["source"]["id"], "revision": 0}
        attempt = m.SourceAttempt.model_validate({
            **FIXTURE["source_attempt"], "state": "translation_unverified",
            "retrieved_source": source_ref,
            "failure": {"code": "translation-unverified", "safe_message": "Fictional translation pending"},
        })
        self.assertEqual(attempt.retrieved_source.model_dump(), source_ref)
        with self.assertRaises(ValidationError):
            m.SourceReview.model_validate({**REVIEW, "gaps": ["Translation not verified"]})

    def test_provision_pin_is_paired_but_unknown_source_remains_representable(self):
        target = {"source_target_id": "fictional-target", "locator": "fictional section"}
        self.assertIsNone(m.ProvisionRef.model_validate(target).source_id)
        pinned = m.ProvisionRef.model_validate({**target, "source_id": "fictional-source", "revision": 0})
        self.assertEqual(pinned.revision, 0)
        for pin in ({"source_id": "fictional-source"}, {"revision": 0}):
            with self.subTest(pin=pin), self.assertRaises(ValidationError):
                m.ProvisionRef.model_validate({**target, **pin})

    def test_review_requires_each_accountability_component(self):
        self.assertEqual(m.SourceReview.model_validate(REVIEW).state, "reviewed_for_assessment")
        for change in (
            {"reviewer": None}, {"last_successful_verification": None},
            {"gaps": ["Fictional amendment chain unchecked"]},
        ):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                m.SourceReview.model_validate({**REVIEW, **change})

    def test_fictional_authority_cannot_be_relabelled_as_real_law(self):
        source = m.LegalSource.model_validate(FIXTURE["source"])
        self.assertTrue(source.synthetic)
        for change in ({"type": "eu_act"}, {"synthetic": False}):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                m.LegalSource.model_validate({**FIXTURE["source"], **change})

    def test_passed_method_cannot_hide_missing_required_evidence(self):
        method = deepcopy(FIXTURE["disposition"]["required_method_dispositions"][0])
        self.assertEqual(m.MethodDisposition.model_validate(method).outcome, "unresolved_review")
        with self.assertRaises(ValidationError):
            m.MethodDisposition.model_validate({**method, "outcome": "passed"})
        complete = m.MethodDisposition.model_validate({**method, "outcome": "passed", "missing_evidence": []})
        self.assertEqual(complete.outcome, "passed")

    def test_conflicting_duplicate_methods_cannot_replace_review_gap(self):
        payload = deepcopy(FIXTURE["disposition"])
        pending = payload["required_method_dispositions"][0]
        payload["required_method_dispositions"].append({
            **pending, "outcome": "passed", "missing_evidence": [],
        })
        with self.assertRaises(ValidationError):
            m.ObligationDisposition.model_validate(payload)

    def test_shared_technical_pass_preserves_distinct_legal_manual_dispositions(self):
        snapshot = m.Snapshot.model_validate(shared_control_snapshot())
        dispositions = {item.applicability: item for item in snapshot.obligation_dispositions}
        self.assertEqual(snapshot.finding_assessments[0].technical_outcome, "passed")
        self.assertEqual(dispositions["applicable"].manual_review, "supported")
        self.assertEqual(dispositions["unresolved"].manual_review, "pending")
        pending_method = dispositions["unresolved"].required_method_dispositions[0]
        self.assertEqual(pending_method.outcome, "unresolved_review")
        self.assertEqual(pending_method.missing_evidence, ["Owner evidence"])
        self.assertEqual(set(snapshot.finding_assessments[0].obligation_disposition_ids),
                         {item.id for item in snapshot.obligation_dispositions})

    def test_obligation_without_technical_finding_keeps_its_disposition(self):
        snapshot = m.Snapshot.model_validate(FIXTURE["snapshot"])
        self.assertEqual(snapshot.findings, [])
        self.assertEqual(snapshot.finding_assessments, [])
        self.assertEqual(len(snapshot.obligation_dispositions), 1)
        self.assertEqual(snapshot.obligation_dispositions[0].applicability, "unresolved")

    def test_snapshot_rejects_duplicate_disposition_and_assessment_identities(self):
        for collection in ("obligation_dispositions", "finding_assessments", "findings"):
            payload = shared_control_snapshot()
            payload[collection].append(deepcopy(payload[collection][0]))
            with self.subTest(collection=collection), self.assertRaises(ValidationError):
                m.Snapshot.model_validate(payload)

    def test_snapshot_rejects_dangling_legal_assessment_joins(self):
        for field, value in (
            ("finding_id", "missing-finding"),
            ("obligation_disposition_ids", ["missing-disposition"]),
            ("attempt_ids", ["missing-attempt"]),
        ):
            payload = shared_control_snapshot()
            payload["finding_assessments"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValidationError):
                m.Snapshot.model_validate(payload)
        for target in ("obligation_disposition_id", "finding_assessment_id"):
            payload = shared_control_snapshot()
            overlay = payload["current_assessments"][0]
            overlay.pop("obligation_disposition_id")
            overlay[target] = "missing-assessment"
            with self.subTest(target=target), self.assertRaises(ValidationError):
                m.Snapshot.model_validate(payload)
