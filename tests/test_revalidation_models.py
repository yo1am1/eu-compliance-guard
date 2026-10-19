"""Offline synthetic contract checks; no source authority or legal truth is verified."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from pydantic import ValidationError

from eu_compliance_guard import models as m


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures/revalidation-synthetic.json"
FIXTURE = json.loads(FIXTURE_PATH.read_text())
STAMP = "2026-10-18T10:00:00Z"


def bundle_payload():
    declared = deepcopy(FIXTURE)
    decisions = deepcopy(declared["applicability_decisions"])
    decisions[0].update(applicability="unresolved", gaps=["Fictional review pending"])
    second = deepcopy(decisions[0])
    second.update(id="decision-unmapped", obligation={"id": "obligation-unmapped", "revision": 0})
    decisions.append(second)
    dispositions = []
    for obligation, decision in zip(declared["obligations"], decisions):
        dispositions.append({
            "id": "disposition-" + obligation["id"], "project_id": declared["project_id"],
            "run_id": "run-output", "obligation_id": obligation["id"], "obligation_revision": 0,
            "applicability": "unresolved", "applicability_decision_id": decision["id"],
            "rationale": "Fictional pending review", "manual_review": "pending",
            "required_method_dispositions": [{
                "method": obligation["required_methods"][0], "outcome": "unresolved_review",
                "attempt_ids": [], "review_ids": [], "missing_evidence": ["Fictional review pending"],
            }],
        })
    manifest = {
        "id": "manifest-output", "digest": m.content_digest(b"synthetic manifest"),
        "source_files": [], "exclusions": declared["scope"]["exclusions"],
        "scope_revision": 0, "fact_digest": m.content_digest(b"synthetic facts"),
        "registry_digest": m.content_digest(b"synthetic registry"), "source_versions": [],
        "fixture_digest": m.content_digest(FIXTURE_PATH.read_bytes()), "tool_versions": ["synthetic-test"],
        "config_digest": m.content_digest(b"offline"), "environment_identity": "synthetic-test",
    }
    evidence = deepcopy(declared["evidence"][0]["evidence"])
    evidence.update(run_id="run-output", manifest_id="manifest-output")
    return {
        "schema_version": 1, "project_id": declared["project_id"], "synthetic": True,
        "input_digest": m.content_digest(FIXTURE_PATH.read_bytes()),
        "declarations": declared, "manifest": manifest,
        "run": {
            "id": "run-output", "project_id": declared["project_id"], "revision": 0,
            "state": "partial", "manifest_id": "manifest-output",
            "permission_id": declared["scope"]["permission_id"], "coverage_plan": list(m.LEGAL_FAMILIES),
            "started_at": STAMP, "ended_at": STAMP, "terminal_sequence": 0,
            "gaps": ["Fictional review pending"], "budgets": {"run_seconds": 300, "check_seconds": 300},
        },
        "evidence": [evidence], "obligation_dispositions": dispositions,
        "requirement_assessments": [{
            "requirement": {"id": req["id"], "revision": 0},
            "obligation_disposition_ids": ["disposition-" + pin["id"] for pin in req["obligation_refs"]],
            "evidence_ids": req["evidence_ids"], "review_ids": [], "state": "unresolved",
            "rationale": "Fictional incomplete mapping", "gaps": ["Review pending"],
            "next_actions": ["Request fictional review"],
        } for req in declared["requirements"]],
        "effective_applicability_decisions": decisions,
        "family_screenings": [{
            "family": family, "synthetic": True, "scope": {"id": declared["scope"]["id"], "revision": 0},
            "assessment_date": declared["scope"]["assessment_date"], "rationale": "Fictional unassessed family",
            "fact_refs": [], "source_refs": [], "gaps": ["Research required"],
        } for family in m.LEGAL_FAMILIES],
        "gaps": ["Fictional example only"], "next_actions": ["Review declared coverage"],
    }


def supported_payload():
    """A recorded fictional mapping with observed files and accountable reviews."""
    payload = bundle_payload()
    declared = payload["declarations"]
    payload["manifest"]["source_files"] = [
        deepcopy(declared["sources"][0]["file"]),
        {"path": declared["evidence"][0]["path"], "digest": declared["evidence"][0]["evidence"]["digest"]},
    ]
    payload["effective_applicability_decisions"][0] = deepcopy(declared["applicability_decisions"][0])
    disposition = payload["obligation_dispositions"][0]
    disposition.update(applicability="applicable", manual_review="supported")
    disposition["required_method_dispositions"][0].update(
        outcome="passed", missing_evidence=[], review_ids=["review-example"])
    payload["requirement_assessments"][0].update(state="supported", gaps=[], review_ids=["review-example"])
    return payload


class RevalidationModelTests(unittest.TestCase):
    def test_fixture_roundtrips_with_actual_selected_digests_and_fact_bases(self):
        record = m.parse_record(m.RevalidationInput, FIXTURE_PATH.read_bytes())
        self.assertEqual(m.parse_record(m.RevalidationInput, m.canonical_json(record)), record)
        source = record.sources[0]
        self.assertEqual(source.source.content_digest,
                         m.content_digest((FIXTURE_PATH.parent / source.file.path).read_bytes()))
        selected = record.evidence[0]
        self.assertEqual(selected.evidence.digest,
                         m.content_digest((FIXTURE_PATH.parent / selected.path).read_bytes()))
        self.assertEqual({fact.basis for fact in m.scope_facts(record.scope)}, {"declared", "assumed", "unknown"})

    def test_empty_and_incomplete_review_declarations_remain_representable(self):
        payload = {key: FIXTURE[key] for key in (
            "schema_version", "project_id", "synthetic", "declaration_run_id", "declaration_manifest_id", "scope")}
        record = m.RevalidationInput.model_validate(payload)
        self.assertEqual(record.requirements, [])
        pending = deepcopy(FIXTURE)
        pending["applicability_decisions"][0].update(reviewer=None, reviewed_at=None, rationale="")
        pending["source_reviews"][0].pop("review_notes")
        parsed = m.RevalidationInput.model_validate(pending)
        self.assertIsNone(parsed.applicability_decisions[0].reviewer)
        self.assertEqual(parsed.source_reviews[0].review_notes, {})

    def test_legacy_source_review_defaults_preserve_existing_validation(self):
        payload = deepcopy(FIXTURE["source_reviews"][0])
        payload.pop("synthetic")
        payload.pop("review_notes")
        record = m.SourceReview.model_validate(payload)
        self.assertFalse(record.synthetic)
        self.assertEqual(record.review_notes, {})
        with self.assertRaises(ValidationError):
            m.SourceReview.model_validate({**payload, "reviewer": None})

    def test_duplicate_identity_and_typed_reference_failures(self):
        changes = [
            lambda p: p["requirements"].append(deepcopy(p["requirements"][0])),
            lambda p: p["requirements"][0]["obligation_refs"][0].update(revision=1),
            lambda p: p["requirements"][0]["fact_refs"][0].update(id="obligation-example"),
            lambda p: p["requirements"][0].update(project_id="other"),
            lambda p: p["evidence"][0]["evidence"].update(run_id="other"),
            lambda p: p["evidence"][0]["evidence"].update(manifest_id="other"),
            lambda p: p["scope"].update(project_id="other"),
            lambda p: p["obligations"][0]["source_provisions"][0].update(source_target_id="missing"),
            lambda p: p["obligations"][0]["source_provisions"][0].update(revision=1),
            lambda p: p["source_reviews"][0].update(case_law_refs=["missing"]),
            lambda p: p["evidence_reviews"][0].update(method="undeclared-method"),
        ]
        for change in changes:
            payload = deepcopy(FIXTURE)
            change(payload)
            with self.subTest(change=changes.index(change)), self.assertRaises(ValidationError):
                m.RevalidationInput.model_validate(payload)

    def test_repeated_facts_require_identical_content_and_resolved_conflicts(self):
        payload = deepcopy(FIXTURE)
        payload["scope"]["size_and_sector"] = [deepcopy(payload["scope"]["roles"][0])]
        m.RevalidationInput.model_validate(payload)
        payload["scope"]["size_and_sector"][0]["basis"] = "assumed"
        with self.assertRaises(ValidationError):
            m.RevalidationInput.model_validate(payload)
        payload = deepcopy(FIXTURE)
        payload["scope"]["roles"][0]["conflicts"] = ["missing-fact"]
        with self.assertRaises(ValidationError):
            m.RevalidationInput.model_validate(payload)

    def test_synthetic_requirements_and_each_review_kind_cannot_enter_real_envelope(self):
        base = deepcopy(FIXTURE)
        base["synthetic"] = False
        base["sources"][0]["source"].update(type="eu_act", synthetic=False)
        base["source_targets"][0]["intended_type"] = "eu_act"
        for name in ("requirements", "source_reviews", "applicability_decisions", "evidence_reviews"):
            for item in base[name]:
                item["synthetic"] = False
        m.RevalidationInput.model_validate(base)
        for name in ("requirements", "source_reviews", "applicability_decisions", "evidence_reviews"):
            mixed = deepcopy(base)
            mixed[name][0]["synthetic"] = True
            with self.subTest(record=name), self.assertRaises(ValidationError):
                m.RevalidationInput.model_validate(mixed)
            mixed["synthetic"] = True
            m.RevalidationInput.model_validate(mixed)

    def test_selected_media_is_declared_essence_with_separate_charset(self):
        source = deepcopy(FIXTURE["sources"][0])
        source.update(media_type="TEXT/HTML", charset="ISO-8859-1")
        # Unsupported encodings are representable so admission can explain the gap.
        self.assertEqual(m.SelectedSource.model_validate(source).charset, "ISO-8859-1")
        for change in ({"media_type": "text/html; charset=utf-8"},
                       {"file": {"path": "source.txt", "digest": m.content_digest(b"wrong")}}):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                m.SelectedSource.model_validate({**source, **change})

    def test_collection_limits_selected_paths_and_nested_scope_bounds(self):
        payload = deepcopy(FIXTURE)
        template = payload["requirements"][1]
        payload["requirements"] = [{**template, "id": f"requirement-{i}"} for i in range(200)]
        m.RevalidationInput.model_validate(payload)
        payload["requirements"].append({**template, "id": "requirement-201"})
        with self.assertRaises(ValidationError):
            m.RevalidationInput.model_validate(payload)
        payload = deepcopy(FIXTURE)
        fact = payload["scope"]["roles"][0]
        payload["scope"]["roles"] = [fact] * 500
        m.RevalidationInput.model_validate(payload)
        payload["scope"]["roles"].append(fact)
        with self.assertRaises(ValidationError):
            m.RevalidationInput.model_validate(payload)
        payload = deepcopy(FIXTURE)
        payload["evidence"] = [{"evidence": {**payload["evidence"][0]["evidence"], "id": f"evidence-{i}"},
                                "path": f"selected/{i}.txt"} for i in range(31)]
        payload["evidence"][0]["evidence"]["id"] = "evidence-example"
        m.RevalidationInput.model_validate(payload)  # 31 evidence files plus one source.
        payload["evidence"].append({"evidence": {**payload["evidence"][0]["evidence"], "id": "evidence-over"},
                                    "path": "selected/over.txt"})
        with self.assertRaises(ValidationError):
            m.RevalidationInput.model_validate(payload)
        payload = deepcopy(FIXTURE)
        payload["scope"]["roles"][0]["evidence_ids"] = ["evidence-example"] * 1001
        with self.assertRaises(ValidationError):
            m.RevalidationInput.model_validate(payload)

    def test_partial_bundle_roundtrip_and_complete_requirement_obligation_coverage(self):
        record = m.RevalidationBundle.model_validate(bundle_payload())
        self.assertEqual(m.parse_record(m.RevalidationBundle, m.canonical_json(record)), record)
        self.assertEqual(len(record.obligation_dispositions), 2)
        self.assertEqual(len(record.family_screenings), 11)
        for name in ("obligation_dispositions", "requirement_assessments", "family_screenings", "evidence"):
            payload = bundle_payload()
            payload[name].pop()
            with self.subTest(collection=name), self.assertRaises(ValidationError):
                m.RevalidationBundle.model_validate(payload)

    def test_output_membership_and_effective_review_cannot_be_forged(self):
        changes = [
            lambda p: p.update(synthetic=False),
            lambda p: p["evidence"][0].update(run_id="declaration-example"),
            lambda p: p["run"].update(manifest_id="wrong"),
            lambda p: p["manifest"].update(fixture_digest=m.content_digest(b"wrong declared input")),
            lambda p: p["obligation_dispositions"][0].update(applicability_decision_id="missing"),
            lambda p: p["effective_applicability_decisions"][0].update(synthetic=False),
            lambda p: p["effective_applicability_decisions"][0].update(applicability="applicable", reviewer=None),
            lambda p: p["requirement_assessments"][0].update(obligation_disposition_ids=[]),
            lambda p: p["run"].update(state="completed"),
        ]
        for index, change in enumerate(changes):
            payload = bundle_payload()
            change(payload)
            with self.subTest(case=index), self.assertRaises(ValidationError):
                m.RevalidationBundle.model_validate(payload)

    def test_documentary_pass_needs_matching_available_reviewed_evidence(self):
        payload = supported_payload()
        m.RevalidationBundle.model_validate(payload)
        for change in (
            lambda p: p["evidence"][0].update(availability="missing"),
            lambda p: p["declarations"]["evidence_reviews"][0].update(reviewer=None),
            lambda p: p["declarations"]["evidence_reviews"][0].update(contrary_evidence=["Fictional conflicting document"]),
        ):
            invalid = deepcopy(payload)
            change(invalid)
            with self.assertRaises(ValidationError):
                m.RevalidationBundle.model_validate(invalid)

    def test_support_requires_source_observation_notes_authority_and_applicability(self):
        changes = [
            lambda p: p["manifest"].update(source_files=[]),
            lambda p: p["declarations"]["sources"][0].update(file=None),
            lambda p: p["declarations"]["sources"][0].update(media_type="application/pdf"),
            lambda p: p["declarations"]["sources"][0].update(charset="latin-1"),
            lambda p: p["declarations"]["source_reviews"][0].update(review_notes={}),
            lambda p: p["declarations"]["source_reviews"][0]["review_notes"].update(case_law=" "),
            lambda p: p["declarations"]["source_reviews"][0].update(reviewer=" "),
            lambda p: p["declarations"]["source_reviews"][0].update(assessment_date="2026-10-17"),
            lambda p: p["declarations"]["source_targets"][0].update(publisher="Different candidate"),
            lambda p: p["effective_applicability_decisions"][0].update(reviewer=" "),
            lambda p: p["effective_applicability_decisions"][0].update(fact_refs=[]),
            lambda p: p["effective_applicability_decisions"][0].update(provisions=[]),
            lambda p: p["effective_applicability_decisions"][0].update(condition_answers=[" "]),
            lambda p: p["effective_applicability_decisions"][0].update(exception_answers=[" "]),
            lambda p: p["declarations"]["scope"]["roles"][0].update(basis="assumed"),
            lambda p: p["declarations"]["scope"]["roles"][0].update(basis="unknown"),
            lambda p: p["declarations"]["scope"]["roles"][0].update(conflicts=["fact-unknown"]),
            lambda p: p["declarations"]["evidence"][0].update(path=None),
            lambda p: p["declarations"]["evidence_reviews"][0].update(period=" "),
            lambda p: p["declarations"]["evidence_reviews"][0].update(owner=" "),
        ]
        for index, change in enumerate(changes):
            payload = supported_payload()
            change(payload)
            # Incomplete owner claims are retained; effective support is rejected.
            m.RevalidationInput.model_validate(payload["declarations"])
            with self.subTest(case=index), self.assertRaises(ValidationError):
                m.RevalidationBundle.model_validate(payload)
        payload = supported_payload()
        payload["declarations"]["sources"][0]["source"].update(type="final_guidance", synthetic=False)
        payload["declarations"]["source_targets"][0]["intended_type"] = "final_guidance"
        with self.assertRaises(ValidationError):
            m.RevalidationBundle.model_validate(payload)

    def test_unsupported_requirement_and_evidence_upgrades_are_rejected(self):
        payload = bundle_payload()
        payload["requirement_assessments"][0].update(state="supported", gaps=[])
        with self.assertRaises(ValidationError):
            m.RevalidationBundle.model_validate(payload)
        for change in (
            lambda p: p["evidence"][0].update(digest=m.content_digest(b"different bytes")),
            lambda p: p["evidence"][0].update(provenance="independently_verified"),
            lambda p: p["declarations"]["evidence"][0]["evidence"].update(availability="blocked"),
            lambda p: p["declarations"]["evidence"][0]["evidence"].update(redaction="blocked"),
        ):
            payload = supported_payload()
            change(payload)
            with self.assertRaises(ValidationError):
                m.RevalidationBundle.model_validate(payload)
        payload = bundle_payload()
        payload["evidence"][0].update(digest=m.content_digest(b"changed observed bytes"), availability="corrupt")
        m.RevalidationBundle.model_validate(payload)

    def test_resolved_screenings_need_date_accountability_and_dependency_pins(self):
        payload = supported_payload()
        screening = payload["family_screenings"][0]
        screening.update(applicability="applicable", gaps=[], reviewer="Fictional reviewer", reviewed_at=STAMP,
                         fact_refs=[{"id": "fact-declared", "revision": 0}],
                         source_refs=[{"id": "source-example", "revision": 0}])
        payload["declarations"]["family_screenings"] = [deepcopy(screening)]
        m.RevalidationBundle.model_validate(payload)
        for changes in ({"assessment_date": "2026-10-17"}, {"reviewer": " "}, {"reviewed_at": None},
                        {"fact_refs": []}, {"source_refs": []}, {"synthetic": False},
                        {"source_refs": [{"id": "missing", "revision": 0}]}):
            invalid = deepcopy(payload)
            invalid["family_screenings"][0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                m.RevalidationBundle.model_validate(invalid)

    def test_effective_decision_inherits_each_synthetic_dependency(self):
        for kind in ("sources", "source_reviews", "evidence_reviews", "requirements"):
            payload = bundle_payload()
            declared = payload["declarations"]
            for name in ("requirements", "source_reviews", "applicability_decisions", "evidence_reviews"):
                for record in declared[name]:
                    record["synthetic"] = False
            declared["sources"][0]["source"].update(type="eu_act", synthetic=False)
            declared["source_targets"][0]["intended_type"] = "eu_act"
            if kind == "sources":
                declared["sources"][0]["source"].update(type="synthetic_fixture", synthetic=True)
                declared["source_targets"][0]["intended_type"] = "synthetic_fixture"
            else:
                declared[kind][0]["synthetic"] = True
            decision = payload["effective_applicability_decisions"][0]
            decision.update(synthetic=False, provisions=[])
            with self.subTest(kind=kind), self.assertRaises(ValidationError):
                m.RevalidationBundle.model_validate(payload)

    def test_completed_cannot_hide_unresolved_unmapped_obligation(self):
        payload = supported_payload()
        payload["run"].update(state="completed", gaps=[])
        payload["gaps"] = []
        payload["requirement_assessments"][1].update(state="outside_declared_assessment", gaps=[])
        for screening in payload["family_screenings"]:
            screening.update(applicability="not_applicable", gaps=[], reviewer="Fictional reviewer", reviewed_at=STAMP,
                             fact_refs=[{"id": "fact-declared", "revision": 0}],
                             source_refs=[{"id": "source-example", "revision": 0}])
        with self.assertRaises(ValidationError):
            m.RevalidationBundle.model_validate(payload)
        decision = payload["effective_applicability_decisions"][1]
        decision.update(applicability="applicable", gaps=[])
        payload["declarations"]["applicability_decisions"].append(deepcopy(decision))
        payload["declarations"]["family_screenings"] = deepcopy(payload["family_screenings"])
        disposition = payload["obligation_dispositions"][1]
        disposition.update(applicability="applicable", manual_review="supported")
        # The remaining organizational method is still unresolved.
        with self.assertRaises(ValidationError):
            m.RevalidationBundle.model_validate(payload)

    def test_resolved_output_cannot_invent_or_rewrite_attestations(self):
        for change in (
            lambda p: p["declarations"].update(applicability_decisions=[]),
            lambda p: p["effective_applicability_decisions"][0].update(revision=1),
            lambda p: p["effective_applicability_decisions"][0].update(rationale="Invented different reasoning"),
            lambda p: p["effective_applicability_decisions"][0].update(reviewer="Invented reviewer"),
        ):
            payload = supported_payload()
            change(payload)
            with self.assertRaises(ValidationError):
                m.RevalidationBundle.model_validate(payload)

    def test_manual_review_is_independent_of_other_pending_methods(self):
        payload = supported_payload()
        payload["declarations"]["obligations"][0]["required_methods"].append("technical")
        payload["obligation_dispositions"][0]["required_method_dispositions"].append({
            "method": "technical", "outcome": "not_tested", "attempt_ids": [], "review_ids": [],
            "missing_evidence": ["No technical test performed"],
        })
        payload["requirement_assessments"][0].update(state="unresolved", gaps=["Technical method not tested"])
        record = m.RevalidationBundle.model_validate(payload)
        self.assertEqual(record.obligation_dispositions[0].manual_review, "supported")
        self.assertEqual(record.obligation_dispositions[0].required_method_dispositions[0].outcome, "passed")

    def test_independent_verification_needs_separately_retained_proof(self):
        payload = supported_payload()
        original = payload["declarations"]["evidence"][0]["evidence"]
        observed = payload["evidence"][0]
        original["provenance"] = observed["provenance"] = "independently_verified"
        with self.assertRaises(ValidationError):
            m.RevalidationBundle.model_validate(payload)
        proof = deepcopy(payload["declarations"]["evidence"][0])
        proof["evidence"].update(id="verification-proof", provenance="documented", source_refs=[])
        payload["declarations"]["evidence"].append(proof)
        rebound = deepcopy(proof["evidence"])
        rebound.update(run_id="run-output", manifest_id="manifest-output")
        payload["evidence"].append(rebound)
        original["source_refs"] = observed["source_refs"] = ["verification-proof"]
        m.RevalidationBundle.model_validate(payload)
        payload["evidence"][1]["availability"] = "missing"
        with self.assertRaises(ValidationError):
            m.RevalidationBundle.model_validate(payload)

    def test_aggregate_collection_bound_and_source_target_bound(self):
        payload = deepcopy(FIXTURE)
        target = payload["source_targets"][0]
        payload["source_targets"] += [{**target, "id": f"target-{i}"} for i in range(15)]
        m.RevalidationInput.model_validate(payload)
        payload["source_targets"].append({**target, "id": "target-over"})
        with self.assertRaises(ValidationError):
            m.RevalidationInput.model_validate(payload)
        payload = deepcopy(FIXTURE)
        obligation = payload["obligations"][1]
        payload["obligations"] += [{**obligation, "id": f"obligation-{i}", "conditions": ["Fictional condition"] * 900}
                                   for i in range(5)]
        m.RevalidationInput.model_validate(payload)
        payload["obligations"].append({**obligation, "id": "obligation-over", "conditions": ["Fictional condition"] * 900})
        with self.assertRaises(ValidationError):
            m.RevalidationInput.model_validate(payload)

    def test_relied_on_facts_cannot_hide_unavailable_evidence(self):
        payload = supported_payload()
        payload["declarations"]["scope"]["roles"][0]["evidence_ids"] = ["evidence-example"]
        payload["declarations"]["applicability_decisions"][0]["evidence_ids"] = []
        payload["effective_applicability_decisions"][0]["evidence_ids"] = []
        payload["evidence"][0]["availability"] = "missing"
        payload["obligation_dispositions"][0]["required_method_dispositions"][0].update(
            outcome="unresolved_review", missing_evidence=["Missing fact proof"])
        payload["requirement_assessments"][0].update(state="unresolved", gaps=["Missing fact proof"])
        m.RevalidationInput.model_validate(payload["declarations"])
        with self.assertRaises(ValidationError):
            m.RevalidationBundle.model_validate(payload)
        payload["effective_applicability_decisions"][0].update(applicability="unresolved", gaps=["Missing fact proof"])
        payload["obligation_dispositions"][0]["applicability"] = "unresolved"
        screening = payload["family_screenings"][0]
        screening.update(applicability="applicable", gaps=[], reviewer="Fictional reviewer", reviewed_at=STAMP,
                         fact_refs=[{"id": "fact-declared", "revision": 0}],
                         source_refs=[{"id": "source-example", "revision": 0}])
        payload["declarations"]["family_screenings"] = [deepcopy(screening)]
        with self.assertRaises(ValidationError):
            m.RevalidationBundle.model_validate(payload)

    def test_explicit_source_dependencies_need_admitted_material_and_allow_cycles(self):
        payload = supported_payload()
        dependency = deepcopy(payload["declarations"]["sources"][0])
        dependency["source"]["id"] = "source-dependency"
        payload["declarations"]["sources"].append(dependency)
        review = deepcopy(payload["declarations"]["source_reviews"][0])
        review["source_id"] = "source-dependency"
        payload["declarations"]["source_reviews"].append(review)
        for relation in ("related_source_ids", "act_chain", "case_law_refs", "national_overlay_ids", "overlay_ids"):
            variant = deepcopy(payload)
            declared = variant["declarations"]
            parent = (declared["sources"][0]["source"] if relation == "related_source_ids"
                      else declared["obligations"][0] if relation == "overlay_ids"
                      else declared["source_reviews"][0])
            parent[relation] = ["source-dependency"]
            declared["sources"][1]["source"]["related_source_ids"] = ["source-example"]
            with self.subTest(relation=relation):
                m.RevalidationBundle.model_validate(variant)
                declared["sources"][1]["file"] = None
                with self.assertRaises(ValidationError):
                    m.RevalidationBundle.model_validate(variant)

    def test_requirement_support_needs_its_own_dependencies(self):
        payload = json.loads(json.dumps(supported_payload()))
        selected = deepcopy(payload["declarations"]["evidence"][0])
        selected["evidence"].update(id="requirement-only", availability="missing")
        payload["declarations"]["evidence"].append(selected)
        output = deepcopy(selected["evidence"])
        output.update(run_id=payload["run"]["id"], manifest_id=payload["manifest"]["id"])
        payload["evidence"].append(output)
        payload["declarations"]["requirements"][0]["evidence_ids"].append("requirement-only")
        payload["requirement_assessments"][0]["evidence_ids"].append("requirement-only")
        with self.assertRaises(ValidationError):
            m.RevalidationBundle.model_validate(payload)
        payload["requirement_assessments"][0]["evidence_ids"].remove("requirement-only")
        with self.assertRaises(ValidationError):
            m.RevalidationBundle.model_validate(payload)
        for dependency in ("fact", "origin", "fact-evidence"):
            payload = json.loads(json.dumps(supported_payload()))
            requirement = payload["declarations"]["requirements"][0]
            if dependency == "fact":
                requirement["fact_refs"] = [{"id": "fact-unknown", "revision": 0}]
            elif dependency == "origin":
                requirement.update(origin={"path": "missing-origin.txt", "digest": m.content_digest(b"origin")},
                                   locator="section 1")
            else:
                payload["declarations"]["evidence"].append(deepcopy(selected))
                payload["evidence"].append(deepcopy(output))
                fact = payload["declarations"]["scope"]["roles"][1]
                fact.update(basis="declared", evidence_ids=["requirement-only"])
                requirement["fact_refs"] = [{"id": fact["id"], "revision": fact["revision"]}]
            with self.subTest(dependency=dependency), self.assertRaises(ValidationError):
                m.RevalidationBundle.model_validate(payload)

    def test_generated_contracts_export_the_offline_records(self):
        from eu_compliance_guard.schema import contract_schema
        schema = contract_schema()
        typescript = (FIXTURE_PATH.parent.parent / "frontend/src/lib/contract.ts").read_text()
        for record in (m.DeclaredRequirement, m.SourceTarget, m.SelectedSource, m.SelectedEvidence,
                       m.FamilyScreening, m.ApplicabilityDecision, m.EvidenceReview,
                       m.RequirementAssessment, m.RevalidationInput, m.RevalidationBundle, m.RunCompletion):
            with self.subTest(record=record.__name__):
                self.assertIn(record.__name__, schema["$defs"])
                self.assertRegex(typescript, rf"export (?:type|interface) {record.__name__}\b")

    def test_completion_marker_has_only_generated_artifacts_and_no_self_hash(self):
        files = [{"path": name, "digest": m.content_digest(name.encode())}
                 for name in ("input.json", "manifest.json", "bundle.json", "report.md")]
        marker = {"schema_version": 1, "run_id": "run-output", "files": files}
        record = m.RunCompletion.model_validate(marker)
        self.assertEqual(m.parse_record(m.RunCompletion, m.canonical_json(record)), record)
        for path in ("complete.json", "private.txt", "sources/not-the-digest.bin"):
            with self.subTest(path=path), self.assertRaises(ValidationError):
                m.RunCompletion.model_validate({**marker, "files": [*files, {"path": path, "digest": m.content_digest(b"x")}]})
