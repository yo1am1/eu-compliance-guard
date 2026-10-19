"""Synthetic acceptance boundaries; selected data is created in private temp dirs."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from eu_compliance_guard import models as m, revalidation as r


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/revalidation-synthetic.json"


class RevalidationAcceptanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="eucg-acceptance-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.input = self.root / "input.json"
        self.payload = json.loads(FIXTURE.read_bytes())
        self.payload["sources"][0]["file"] = None

    def save(self):
        self.input.write_text(json.dumps(self.payload), encoding="utf-8")

    def select_zero_files(self, count, size):
        digest = hashlib.sha256()
        chunk = bytes(65536)
        remaining = size
        while remaining:
            part = chunk[:min(remaining, len(chunk))]
            digest.update(part)
            remaining -= len(part)
        template = deepcopy(self.payload["evidence"][0])
        self.payload["evidence"] = []
        for index in range(count):
            selected = deepcopy(template)
            selected["path"] = f"selected-{index}.bin"
            selected["evidence"].update(
                id="evidence-example" if index == 0 else f"evidence-{index}",
                digest="sha256:" + digest.hexdigest())
            with (self.root / selected["path"]).open("wb") as file:
                file.truncate(size)
            self.payload["evidence"].append(selected)
        self.save()

    def test_actual_64_mib_budget_and_one_byte_over(self):
        self.select_zero_files(8, 8 * 1024 * 1024)
        bundle = r.run(self.input, self.root / "exact")
        self.assertEqual(len(bundle.manifest.source_files), 8)
        self.assertTrue(all(item.availability == "available" for item in bundle.evidence))
        self.assertTrue((self.root / "exact/complete.json").is_file())
        selected = deepcopy(self.payload["evidence"][0])
        selected["path"] = "one-byte-over.bin"
        selected["evidence"].update(id="evidence-over", digest=m.content_digest(b"\0"))
        (self.root / selected["path"]).write_bytes(b"\0")
        self.payload["evidence"].append(selected)
        self.save()
        with self.assertRaises(r.RevalidationError) as caught:
            r.run(self.input, self.root / "over")
        self.assertEqual(caught.exception.code, "capacity-exceeded")
        self.assertFalse((self.root / "over").exists())

    def test_32_selected_files_and_one_over_rejected_before_observation(self):
        self.select_zero_files(32, 0)
        bundle = r.run(self.input, self.root / "exact")
        self.assertEqual(len(bundle.manifest.source_files), 32)
        selected = deepcopy(self.payload["evidence"][0])
        selected["path"] = "not-read.bin"
        selected["evidence"]["id"] = "evidence-over"
        self.payload["evidence"].append(selected)
        self.save()
        with patch.object(r, "_observe", side_effect=AssertionError("must validate first")):
            with self.assertRaises(r.RevalidationError) as caught:
                r.run(self.input, self.root / "over")
        self.assertEqual(caught.exception.code, "invalid-input")
        self.assertFalse((self.root / "over").exists())

    def test_remaining_collection_boundaries(self):
        original = json.loads(FIXTURE.read_bytes())
        obligation = original["obligations"][0]
        many_obligations = [deepcopy(obligation) for _ in range(200)]
        for index, item in enumerate(many_obligations):
            item["id"] = "obligation-example" if index == 0 else f"obligation-{index}"
        cases = {}
        cases["obligations"] = {**deepcopy(original), "obligations": deepcopy(many_obligations)}
        cases["evidence"] = deepcopy(original)
        cases["evidence"]["evidence"] = []
        for index in range(200):
            selected = deepcopy(original["evidence"][0])
            selected["path"] = None
            selected["evidence"]["id"] = "evidence-example" if index == 0 else f"evidence-{index}"
            cases["evidence"]["evidence"].append(selected)
        for key, template in (("applicability_decisions", original["applicability_decisions"][0]),
                              ("evidence_reviews", original["evidence_reviews"][0])):
            payload = {**deepcopy(original), "obligations": deepcopy(many_obligations)}
            payload[key] = []
            for index, item in enumerate(many_obligations):
                review = deepcopy(template)
                review.update(id=f"review-{index}", obligation={"id": item["id"], "revision": item["revision"]})
                payload[key].append(review)
            cases[key] = payload
        cases["controls"] = deepcopy(original)
        cases["controls"]["controls"] = [{
            "id": f"control-{index}", "revision": 0, "obligation_ids": [],
            "assertion_or_question": "Fictional control", "required_facts": [], "check_ids": [],
            "required_evidence": [], "owner": "Fictional owner", "provenance": [], "limitations": [],
        } for index in range(200)]
        material = deepcopy(original)
        material["sources"] = []
        material["source_reviews"] = []
        for index in range(16):
            selected = deepcopy(original["sources"][0])
            identity = "source-example" if index == 0 else f"source-{index}"
            selected["source"]["id"] = identity
            material["sources"].append(selected)
            review = deepcopy(original["source_reviews"][0])
            review["source_id"] = identity
            material["source_reviews"].append(review)
        cases["sources"] = deepcopy(material)
        cases["source_reviews"] = deepcopy(material)
        cases["family_screenings"] = deepcopy(original)
        cases["family_screenings"]["family_screenings"] = [{
            "family": family, "synthetic": True, "scope": {"id": original["scope"]["id"], "revision": 0},
            "assessment_date": original["scope"]["assessment_date"], "rationale": "Fictional unreviewed domain",
            "fact_refs": [], "source_refs": [], "gaps": ["Review pending"],
        } for family in m.LEGAL_FAMILIES]
        for name, payload in cases.items():
            with self.subTest(collection=name):
                m.RevalidationInput.model_validate(payload)
                payload[name].append(deepcopy(payload[name][-1]))
                with self.assertRaises(ValidationError) as caught:
                    m.RevalidationInput.model_validate(payload)
                self.assertTrue(any(error["loc"] == (name,) and error["type"] == "too_long"
                                    for error in caught.exception.errors(include_input=False)))

    def test_exact_nested_and_aggregate_collection_guard_boundaries(self):
        scope = deepcopy(self.payload["scope"])
        for name in ("activities", "establishment", "markets", "customer_types", "size_and_sector",
                     "jurisdictions", "included_scenarios", "exclusions"):
            scope[name] = []
        fact = deepcopy(scope["roles"][0])
        fact["evidence_ids"] = ["synthetic-evidence"] * 999
        # Five fact entries plus five 999-item evidence lists total exactly 5,000.
        scope["roles"] = [deepcopy(fact) for _ in range(5)]
        m._collection_bounds(m.Scope.model_validate(scope))
        scope["roles"][-1]["evidence_ids"].append("synthetic-extra")
        with self.assertRaisesRegex(ValueError, "aggregate collection limit"):
            m._collection_bounds(m.Scope.model_validate(scope))
        scope["roles"] = [deepcopy(fact)]
        scope["roles"][0]["evidence_ids"].append("synthetic-extra")
        m._collection_bounds(m.Scope.model_validate(scope))
        scope["roles"][0]["conflicts"] = ["synthetic-conflict"]
        with self.assertRaisesRegex(ValueError, "nested collection limit"):
            m._collection_bounds(m.Scope.model_validate(scope))

    def test_activity_and_fact_occurrence_boundaries(self):
        payload = json.loads(FIXTURE.read_bytes())
        fact = payload["scope"]["roles"][0]
        payload["scope"]["activities"] = [{
            "id": f"activity-{index}", "purpose": "Fictional processing", "subjects": [],
            "data_categories": [], "roles": [], "lawful_basis": deepcopy(fact),
            "recipients": [], "locations": [], "stores": [], "retention": [],
            "evidence_owner": "Fictional owner",
        } for index in range(100)]
        m.RevalidationInput.model_validate(payload)
        payload["scope"]["activities"].append({**deepcopy(payload["scope"]["activities"][0]), "id": "activity-over"})
        with self.assertRaises(ValidationError):
            m.RevalidationInput.model_validate(payload)
        payload["scope"]["activities"] = []
        payload["scope"]["roles"] = [deepcopy(fact) for _ in range(500)]
        m.RevalidationInput.model_validate(payload)
        payload["scope"]["roles"].append(deepcopy(fact))
        with self.assertRaises(ValidationError):
            m.RevalidationInput.model_validate(payload)
