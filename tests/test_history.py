"""Synthetic predecessor integrity, dependency comparison and effective-review checks."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from eu_compliance_guard import history as h, models as m, revalidation as r, view

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/revalidation-synthetic.json"


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="eucg-history-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root.chmod(0o700)
        (self.root / "revalidation-synthetic").mkdir()
        for name in ("source.txt", "evidence.txt"):
            (self.root / "revalidation-synthetic" / name).write_bytes((FIXTURE.parent / "revalidation-synthetic" / name).read_bytes())
        self.payload = json.loads(FIXTURE.read_bytes())
        self.input = self.root / "declarations.json"
        self.save()
        self.prior_path = self.root / "prior"
        self.prior = r.run(self.input, self.prior_path)
        self.snapshot = {str(path.relative_to(self.prior_path)): path.read_bytes()
                         for path in self.prior_path.rglob("*") if path.is_file()}

    def save(self):
        self.input.write_text(json.dumps(self.payload))

    def successor(self, name="next", **options):
        self.save()
        return r.run(self.input, self.root / name, previous=self.prior_path, **options)

    def overlay(self, bundle, obligation="obligation-example"):
        disposition = next(item for item in self.prior.obligation_dispositions if item.obligation_id == obligation)
        return next(item for item in bundle.current_assessments if item.obligation_disposition_id == disposition.id)

    def rewrite_marker(self):
        marker_path = self.prior_path / "complete.json"
        marker = json.loads(marker_path.read_bytes())
        for item in marker["files"]:
            item["digest"] = m.content_digest((self.prior_path / item["path"]).read_bytes())
        marker_path.write_text(json.dumps(marker))

    def test_offline_chain_retains_proof_unknown_freshness_and_byte_identical_history(self):
        successor = self.successor()
        self.assertEqual(successor.run.parent_run_id, self.prior.run.id)
        self.assertEqual(successor.comparison.changes, [])
        self.assertEqual(self.overlay(successor).freshness, "unknown")
        self.assertIn("offline", " ".join(self.overlay(successor).reasons))
        proof = next(item for item in successor.evidence if item.kind == "dependency_comparison")
        self.assertEqual(proof.digest, m.content_digest((self.root / "next/comparison.json").read_bytes()))
        self.assertEqual(h.load_run(self.root / "next")[0], successor)
        third = r.run(self.input, self.root / "third", previous=self.root / "next")
        self.assertEqual(third.run.parent_run_id, successor.run.id)
        for path, content in self.snapshot.items():
            self.assertEqual((self.prior_path / path).read_bytes(), content)
        self.assertIn("Historical claim freshness", (self.root / "next/report.md").read_text())

    def test_changed_requirement_invalidates_its_mapping_and_keeps_declared_claim(self):
        self.payload["requirements"][0].update(revision=1, statement="FICTIONAL changed requirement")
        successor = self.successor()
        overlay = self.overlay(successor)
        self.assertEqual(overlay.freshness, "stale")
        self.assertIn("requirement:requirement-example", overlay.changed_dependencies)
        self.assertEqual(successor.declarations.applicability_decisions[0].applicability, "applicable")
        self.assertEqual(successor.effective_applicability_decisions[0].applicability, "unresolved")
        self.assertEqual(successor.requirement_assessments[0].state, "unresolved")
        self.assertTrue(successor.requirement_assessments[0].next_actions)
        self.assertEqual(self.prior.requirement_assessments[0].state, "supported")
        html = view.render_html(successor)
        self.assertIn("Predecessor comparison", html)
        self.assertIn('<td><code>obligation-example</code></td><td><span class="tag ">stale</span>', html)
        self.assertIn("stale", html)
        self.assertIn('scope="col"', html)
        self.assertIn('tabindex="0" role="region"', html)
        self.assertNotIn("<script", html)

    def test_withdrawn_support_never_keeps_a_supporting_rationale(self):
        self.payload["requirements"][0].update(revision=1, statement="FICTIONAL changed requirement")
        successor = self.successor()
        assessment = successor.requirement_assessments[0]
        self.assertEqual(assessment.state, "unresolved")
        self.assertEqual(assessment.rationale, h.WITHDRAWN_MAPPING_RATIONALE)
        decision = successor.effective_applicability_decisions[0]
        self.assertEqual((decision.applicability, decision.rationale), ("unresolved", h.WITHDRAWN_DECISION_RATIONALE))
        self.assertEqual(successor.declarations.applicability_decisions[0].rationale,
                         self.payload["applicability_decisions"][0]["rationale"])
        disposition = next(item for item in successor.obligation_dispositions if item.obligation_id == "obligation-example")
        self.assertEqual(disposition.rationale, decision.rationale)
        report = (self.root / "next/report.md").read_text()
        self.assertNotIn("Recorded mapping supports this declared requirement only", report)
        self.assertNotIn("- Applicability reasoning: Fictional declared role", report)
        self.assertIn("- Applicability reasoning: Support withdrawn after the predecessor comparison", report)
        self.assertIn("- Rationale: Fictional declared role meets fictional condition", report)  # Supplied claim kept.
        self.assertNotIn("Recorded mapping supports", view.render_html(successor))

    def test_withdrawn_support_persists_until_reviews_are_renewed_after_the_predecessor(self):
        from datetime import datetime, timedelta, timezone
        self.payload["requirements"][0].update(revision=1, statement="FICTIONAL changed requirement")
        changed = self.successor("changed")
        self.assertEqual(changed.requirement_assessments[0].state, "unresolved")
        rerun = r.run(self.input, self.root / "rerun", previous=self.root / "changed")
        self.assertEqual(rerun.comparison.changes, [])
        self.assertEqual(rerun.requirement_assessments[0].state, "unresolved")
        self.assertEqual(rerun.effective_applicability_decisions[0].applicability, "unresolved")
        self.assertIn("stays withdrawn", " ".join(self.overlay(rerun).reasons))
        again = r.run(self.input, self.root / "again", previous=self.root / "rerun")
        self.assertEqual(again.requirement_assessments[0].state, "unresolved")
        import time
        time.sleep(0.01)  # The renewal happens after the stale run and before the next run.
        renewed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self.assertGreater(datetime.fromisoformat(renewed_at), datetime.fromisoformat(again.run.ended_at))
        for key in ("applicability_decisions", "evidence_reviews"):
            for item in self.payload[key]:
                if item["obligation"]["id"] == "obligation-example":
                    item.update(revision=item["revision"] + 1, reviewed_at=renewed_at)
        self.save()
        renewed = r.run(self.input, self.root / "renewed", previous=self.root / "again")
        self.assertEqual(renewed.requirement_assessments[0].state, "supported")
        self.assertEqual(renewed.effective_applicability_decisions[0].applicability, "applicable")
        self.payload["requirements"][0].update(revision=2, statement="FICTIONAL changed again")
        self.save()
        both = r.run(self.input, self.root / "both", previous=self.root / "again")
        self.assertEqual(both.requirement_assessments[0].state, "unresolved")
        self.assertIn("requirement:requirement-example", self.overlay(both).changed_dependencies)
        self.assertNotIn("decision:decision-example", self.overlay(both).changed_dependencies)

    def test_a_first_decision_after_the_predecessor_is_not_withdrawn(self):
        import copy
        from datetime import datetime, timezone
        import time
        decisions = self.payload["applicability_decisions"]
        reviews = self.payload["evidence_reviews"]
        first, review = copy.deepcopy(decisions[0]), copy.deepcopy(reviews[0])
        self.payload["applicability_decisions"] = [item for item in decisions if item["obligation"]["id"] != "obligation-unmapped"]
        self.save()
        before = r.run(self.input, self.root / "undecided")
        time.sleep(0.01)
        decided_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        first.update(id="decision-unmapped", reviewed_at=decided_at, evidence_ids=[])
        first["obligation"]["id"] = "obligation-unmapped"
        review.update(id="review-unmapped", reviewed_at=decided_at, method="organizational")
        review["obligation"]["id"] = "obligation-unmapped"
        self.payload["applicability_decisions"].append(first)
        self.payload["evidence_reviews"].append(review)
        requirement = self.payload["requirements"][1]
        requirement.update(revision=requirement["revision"] + 1,
                           obligation_refs=[{"id": "obligation-unmapped", "revision": 0}])
        self.save()
        after = r.run(self.input, self.root / "decided", previous=self.root / "undecided")
        states = {item.requirement.id: item.state for item in after.requirement_assessments}
        self.assertEqual(states[requirement["id"]], "supported")
        rerun = r.run(self.input, self.root / "decided-again", previous=self.root / "decided")
        self.assertEqual({item.requirement.id: item.state for item in rerun.requirement_assessments}[requirement["id"]], "supported")
        self.assertEqual(before.run.parent_run_id, None)

    def test_future_dated_reviews_never_establish_or_restore_support(self):
        for key in ("applicability_decisions", "evidence_reviews"):
            for item in self.payload[key]:
                item["reviewed_at"] = "2099-01-01T00:00:00Z"
        self.save()
        first = r.run(self.input, self.root / "future-1")
        self.assertEqual(first.requirement_assessments[0].state, "unresolved")
        self.assertIn("Obligation obligation-example: applicability review dated after this run", first.gaps)
        self.payload["requirements"][0].update(revision=1, statement="FICTIONAL changed requirement")
        self.save()
        r.run(self.input, self.root / "future-2", previous=self.root / "future-1")
        rerun = r.run(self.input, self.root / "future-3", previous=self.root / "future-2")
        self.assertEqual(rerun.requirement_assessments[0].state, "unresolved")

    def test_withdrawn_family_screening_persists_until_renewed(self):
        import time
        from datetime import datetime, timezone
        decision = self.payload["applicability_decisions"][0]
        self.payload["family_screenings"] = [{
            "family": "gdpr", "synthetic": True, "scope": decision["scope"], "assessment_date": decision["assessment_date"],
            "applicability": "applicable", "rationale": "Fictional screening.", "fact_refs": decision["fact_refs"],
            "source_refs": [{"id": "source-example", "revision": 0}], "reviewer": "Fictional reviewer",
            "reviewed_at": decision["reviewed_at"], "gaps": []}]
        self.save()
        family = lambda bundle: next(item for item in bundle.family_screenings if item.family == "gdpr").applicability
        first = r.run(self.input, self.root / "fam-1")
        self.assertEqual(family(first), "applicable")
        self.payload["requirements"][0].update(revision=1, statement="FICTIONAL changed requirement")
        self.save()
        self.assertEqual(family(r.run(self.input, self.root / "fam-2", previous=self.root / "fam-1")), "unresolved")
        rerun = r.run(self.input, self.root / "fam-3", previous=self.root / "fam-2")
        self.assertEqual(rerun.comparison.changes, [])
        self.assertEqual(family(rerun), "unresolved")
        self.assertIn(h.FAMILY_WITHDRAWN_GAP, next(item for item in rerun.family_screenings if item.family == "gdpr").gaps)
        time.sleep(0.01)
        self.payload["family_screenings"][0].update(rationale="Fictional screening, renewed.",
                                                    reviewed_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
        self.save()
        self.assertEqual(family(r.run(self.input, self.root / "fam-4", previous=self.root / "fam-3")), "applicable")

    def test_family_withdrawal_is_carried_while_the_screening_is_unresolved_for_another_reason(self):
        from datetime import datetime, timedelta, timezone

        class Later(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime.now(tz) + timedelta(hours=1)

        decision = self.payload["applicability_decisions"][0]
        self.payload["family_screenings"] = [{
            "family": "gdpr", "synthetic": True, "scope": decision["scope"], "assessment_date": decision["assessment_date"],
            "applicability": "applicable", "rationale": "Fictional screening.", "fact_refs": decision["fact_refs"],
            "source_refs": [{"id": "source-example", "revision": 0}], "reviewer": "Fictional reviewer",
            "reviewed_at": decision["reviewed_at"], "gaps": []}]
        self.save()
        screening = lambda bundle: next(item for item in bundle.family_screenings if item.family == "gdpr")
        self.assertEqual(screening(r.run(self.input, self.root / "fam-1")).applicability, "applicable")
        self.payload["requirements"][0].update(revision=1, statement="FICTIONAL changed requirement")
        self.save()
        self.assertEqual(screening(r.run(self.input, self.root / "fam-2", previous=self.root / "fam-1")).applicability,
                         "unresolved")
        # A renewal dated after the run that reads it is a gap and leaves the screening unresolved anyway.
        future = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
        self.payload["family_screenings"][0].update(rationale="Fictional screening, renewed.", reviewed_at=future)
        self.save()
        dated = screening(r.run(self.input, self.root / "fam-3", previous=self.root / "fam-2"))
        self.assertIn("Family screening dated after this run.", dated.gaps)
        self.assertIn(h.FAMILY_WITHDRAWN_GAP, dated.gaps)
        with patch.object(r, "datetime", Later):  # The date has passed; the record itself is unchanged.
            plain = r.run(self.input, self.root / "fam-4", previous=self.root / "fam-3")
        self.assertEqual(plain.comparison.changes, [])
        self.assertEqual(screening(plain).applicability, "unresolved")
        self.assertIn(h.FAMILY_WITHDRAWN_GAP, screening(plain).gaps)
        # Declared support the predecessor could not confirm is withdrawn by a change all the same.
        self.payload["family_screenings"][0].update(rationale="Fictional screening.", reviewed_at=decision["reviewed_at"])
        self.payload["requirements"][0].update(revision=0, statement="FICTIONAL: record the declared review.")
        self.save()
        r.run(self.input, self.root / "fam-5")
        source = self.root / "revalidation-synthetic/source.txt"
        kept = source.read_bytes()
        source.unlink()
        self.payload["requirements"][0].update(revision=1, statement="FICTIONAL changed requirement")
        self.save()
        unread = screening(r.run(self.input, self.root / "fam-6", previous=self.root / "fam-5"))
        self.assertIn(h.FAMILY_WITHDRAWN_GAP, unread.gaps)
        source.write_bytes(kept)
        self.assertEqual(screening(r.run(self.input, self.root / "fam-7", previous=self.root / "fam-6")).applicability,
                         "unresolved")

    def now(self):
        import time
        from datetime import datetime, timezone
        time.sleep(0.01)
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def withdraw(self):
        self.payload["requirements"][0].update(revision=1, statement="FICTIONAL changed requirement")
        self.save()
        return r.run(self.input, self.root / "w-2", previous=self.prior_path)

    def test_obligation_and_family_renewed_together_are_restored_and_stay_restored(self):
        decision = self.payload["applicability_decisions"][0]
        self.payload["family_screenings"] = [{
            "family": "gdpr", "synthetic": True, "scope": decision["scope"], "assessment_date": decision["assessment_date"],
            "applicability": "applicable", "rationale": "Fictional screening.", "fact_refs": decision["fact_refs"],
            "source_refs": [{"id": "source-example", "revision": 0}], "reviewer": "Fictional reviewer",
            "reviewed_at": decision["reviewed_at"], "gaps": []}]
        self.save()
        self.prior = r.run(self.input, self.root / "w-1")
        self.prior_path = self.root / "w-1"
        family = lambda bundle: next(item for item in bundle.family_screenings if item.family == "gdpr").applicability
        withdrawn = self.withdraw()
        self.assertEqual((withdrawn.requirement_assessments[0].state, family(withdrawn)), ("unresolved", "unresolved"))
        stamp = self.now()
        for key in ("applicability_decisions", "evidence_reviews"):
            for item in self.payload[key]:
                if item["obligation"]["id"] == "obligation-example":
                    item.update(revision=item["revision"] + 1, reviewed_at=stamp)
        self.payload["family_screenings"][0].update(rationale="Fictional screening, renewed.", reviewed_at=stamp)
        self.save()
        renewed = r.run(self.input, self.root / "w-3", previous=self.root / "w-2")
        self.assertEqual((renewed.requirement_assessments[0].state, family(renewed)), ("supported", "applicable"))
        quiet = r.run(self.input, self.root / "w-4", previous=self.root / "w-3")
        self.assertEqual((quiet.requirement_assessments[0].state, family(quiet)), ("supported", "applicable"))

    def test_renamed_obligation_cannot_reuse_old_reviews(self):
        self.withdraw()
        self.payload = json.loads(json.dumps(self.payload).replace("obligation-example", "obligation-renamed"))
        for key in ("applicability_decisions", "evidence_reviews"):
            for item in self.payload[key]:
                if item["obligation"]["id"] == "obligation-renamed":
                    item["revision"] += 1
        self.payload["requirements"][0]["revision"] = 2
        self.save()
        renamed = r.run(self.input, self.root / "w-3", previous=self.root / "w-2")
        self.assertEqual(renamed.requirement_assessments[0].state, "unresolved")
        self.assertIn("Obligation obligation-renamed: A new or changed review record", " ".join(renamed.gaps))

    def test_removed_and_readded_obligation_cannot_reuse_old_reviews(self):
        original = deepcopy(self.payload)
        self.withdraw()
        removed = deepcopy(self.payload)
        removed["obligations"] = [item for item in removed["obligations"] if item["id"] != "obligation-example"]
        removed["controls"] = [item for item in removed["controls"] if "obligation-example" not in item["obligation_ids"]]
        for key in ("applicability_decisions", "evidence_reviews"):
            removed[key] = [item for item in removed[key] if item["obligation"]["id"] != "obligation-example"]
        removed["requirements"][0].update(revision=2, obligation_refs=[])
        self.payload = removed
        self.save()
        r.run(self.input, self.root / "w-3", previous=self.root / "w-2")
        self.payload = original
        self.payload["requirements"][0].update(revision=3, statement="FICTIONAL changed requirement")
        self.save()
        readded = r.run(self.input, self.root / "w-4", previous=self.root / "w-3")
        self.assertEqual(readded.requirement_assessments[0].state, "unresolved")

    def test_documented_maximum_registers_publish_and_revalidate(self):
        base_obligation = next(item for item in self.payload["obligations"] if item["id"] == "obligation-unmapped")
        base_requirement = self.payload["requirements"][0]
        while len(self.payload["obligations"]) < 200:
            index = len(self.payload["obligations"])
            obligation = deepcopy(base_obligation)
            obligation["id"] = f"obligation-{index}"
            requirement = deepcopy(base_requirement)
            requirement.update(id=f"requirement-{index}", obligation_refs=[{"id": obligation["id"], "revision": 0}])
            self.payload["obligations"].append(obligation)
            self.payload["requirements"].append(requirement)
        self.payload["requirements"] = self.payload["requirements"][:200]
        self.save()
        first = r.run(self.input, self.root / "max-1")
        for requirement in self.payload["requirements"][2:]:
            requirement.update(revision=1, statement=requirement["statement"] + " changed")
        self.save()
        second = r.run(self.input, self.root / "max-2", previous=self.root / "max-1")
        self.assertEqual((len(first.obligation_dispositions), len(second.current_assessments)), (200, 200))
        self.assertTrue(all(len(item.changed_dependencies) <= h.MAX_LISTED_CHANGES for item in second.current_assessments))
        third = r.run(self.input, self.root / "max-3", previous=self.root / "max-2")
        self.assertEqual(third.comparison.changes, [])
        self.assertEqual(sum(item.state == "unresolved" for item in third.requirement_assessments), 199)

    def test_unrelated_requirement_does_not_invalidate_supported_mapping(self):
        self.payload["requirements"][1].update(revision=1, statement="FICTIONAL unrelated change")
        successor = self.successor()
        self.assertEqual(self.overlay(successor).changed_dependencies, [])
        self.assertEqual(successor.requirement_assessments[0].state, "supported")

    def test_same_revision_semantic_edit_and_revision_rollback_rejected_before_network(self):
        for revision in (0,):
            self.payload["requirements"][0].update(revision=revision, statement="FICTIONAL changed")
            with patch("eu_compliance_guard.sources.retrieve") as retrieve:
                with self.assertRaises(r.RevalidationError) as caught:
                    self.successor(fetch_official=True)
            self.assertEqual(caught.exception.code, "invalid-revision")
            retrieve.assert_not_called()
        self.assertFalse((self.root / "next").exists())

    def test_assessment_date_invalidates_every_historical_review(self):
        self.payload["scope"].update(assessment_date="2026-10-19", revision=1)
        for item in self.payload["applicability_decisions"]:
            item["scope"]["revision"] = 1
            item["revision"] += 1
        successor = self.successor()
        self.assertTrue(all(item.freshness == "stale" for item in successor.current_assessments))
        self.assertTrue(all(item.applicability == "unresolved" for item in successor.effective_applicability_decisions))

    def test_missing_evidence_unknown_and_changed_bytes_stale_with_uncertainty_retained(self):
        path = self.root / "revalidation-synthetic/evidence.txt"
        path.unlink()
        missing = self.successor("missing-evidence")
        self.assertEqual(self.overlay(missing).freshness, "unknown")
        self.assertTrue(any(change.kind == "evidence_availability" for change in missing.comparison.changes))
        path.write_text("FICTIONAL changed evidence")
        changed = self.successor("changed-evidence")
        self.assertEqual(self.overlay(changed).freshness, "stale")
        self.assertIn("unavailable", " ".join(self.overlay(changed).reasons))

    def test_unobserved_file_in_predecessor_cannot_launder_a_later_change(self):
        """Declared support is withdrawn by a change even after a run that could not read a file."""
        evidence = self.root / "revalidation-synthetic/evidence.txt"
        source = self.root / "revalidation-synthetic/source.txt"
        kept = {path: path.read_bytes() for path in (evidence, source)}
        evidence.unlink()
        self.assertEqual(self.successor("ev-missing").requirement_assessments[0].state, "unresolved")
        evidence.write_text("FICTIONAL changed evidence")
        self.payload["evidence"][0]["evidence"]["digest"] = m.content_digest(evidence.read_bytes())
        self.save()
        changed = r.run(self.input, self.root / "ev-changed", previous=self.root / "ev-missing")
        self.assertEqual(changed.requirement_assessments[0].state, "unresolved")
        self.assertIn(h.INVALIDATED_GAP, changed.effective_applicability_decisions[0].gaps)
        self.assertEqual(r.run(self.input, self.root / "ev-rerun", previous=self.root / "ev-changed")
                         .requirement_assessments[0].state, "unresolved")
        self.payload = json.loads(FIXTURE.read_bytes())
        evidence.write_bytes(kept[evidence])
        source.unlink()
        self.assertEqual(self.successor("src-missing").requirement_assessments[0].state, "unresolved")
        source.write_bytes(kept[source])
        self.payload["source_reviews"][0]["review_notes"]["case_law"] = "Changed fictional review note"
        self.save()
        reviewed = r.run(self.input, self.root / "src-changed", previous=self.root / "src-missing")
        self.assertEqual(reviewed.requirement_assessments[0].state, "unresolved")
        self.assertIn("source_review:source-example", self.overlay(reviewed).changed_dependencies)

    def test_regaining_the_declared_bytes_after_an_unobserved_run_is_no_change(self):
        evidence = self.root / "revalidation-synthetic/evidence.txt"
        kept = evidence.read_bytes()
        evidence.unlink()
        self.successor("ev-missing")
        evidence.write_bytes(kept)
        restored = r.run(self.input, self.root / "ev-restored", previous=self.root / "ev-missing")
        self.assertTrue(any(change.kind == "file" and change.before is None for change in restored.comparison.changes))
        self.assertEqual(self.overlay(restored).changed_dependencies, [])
        self.assertEqual(restored.requirement_assessments[0].state, "supported")

    def test_source_retrieval_timestamp_is_observational_and_source_digest_edit_is_not(self):
        self.payload["sources"][0]["source"]["retrieved_at"] = "2026-10-19T10:00:00Z"
        successor = self.successor()
        self.assertEqual(successor.comparison.changes, [])
        (self.root / "revalidation-synthetic/source.txt").write_text("FICTIONAL changed source")
        changed = self.successor("source-changed")
        self.assertEqual(self.overlay(changed).freshness, "stale")

    def test_same_bytes_failed_refresh_and_changed_downloads_keep_distinct_freshness(self):
        from test_retrieval_workflow import result
        source = self.payload["sources"][0]
        target = self.payload["source_targets"][0]
        content = (self.root / source["file"]["path"]).read_bytes()
        same = result(target_id=target["id"], url=target["intended_url"], content=content, media_type="text/plain")
        with patch("eu_compliance_guard.sources.retrieve", return_value=[same]):
            online_prior = self.successor("online-prior", fetch_official=True)
            current = r.run(self.input, self.root / "online-next", previous=self.root / "online-prior", fetch_official=True)
        target_id = next(item.id for item in online_prior.obligation_dispositions if item.obligation_id == "obligation-example")
        overlay = next(item for item in current.current_assessments if item.obligation_disposition_id == target_id)
        self.assertEqual(overlay.freshness, "current_for_recorded_inputs")
        self.assertEqual(current.comparison.changes, [])
        self.assertIn("neither", " ".join(overlay.reasons))
        failed = result(target_id=target["id"], url=target["intended_url"], content=None, failure="timeout")
        with patch("eu_compliance_guard.sources.retrieve", return_value=[failed]):
            unavailable = r.run(self.input, self.root / "failed-next", previous=self.root / "online-next", fetch_official=True)
        overlay = next(item for item in unavailable.current_assessments if item.obligation_disposition_id == target_id)
        self.assertEqual(overlay.freshness, "unknown")
        self.assertTrue(unavailable.declarations.sources)
        changed = result(target_id=target["id"], url=target["intended_url"], content=content + b"\nFICTIONAL change", media_type="text/plain")
        with patch("eu_compliance_guard.sources.retrieve", return_value=[changed]):
            newer = r.run(self.input, self.root / "new-bytes", previous=self.root / "online-prior", fetch_official=True)
        self.assertTrue(any(change.kind == "source_bytes" for change in newer.comparison.changes))
        self.assertTrue(all(item.freshness == "stale" for item in newer.current_assessments))

    def test_backwards_revision_is_invalid_even_for_identical_semantics(self):
        self.payload["requirements"][0]["revision"] = 1
        self.successor("revision-one")
        self.payload["requirements"][0]["revision"] = 0
        self.save()
        with self.assertRaises(r.RevalidationError) as caught:
            r.run(self.input, self.root / "rollback", previous=self.root / "revision-one")
        self.assertEqual(caught.exception.code, "invalid-revision")

    def test_new_removed_and_changed_entity_kinds_are_retained(self):
        self.payload["requirements"].pop()
        extra = deepcopy(self.payload["requirements"][0])
        extra["id"] = "new-requirement"
        self.payload["requirements"].append(extra)
        self.payload["evidence_reviews"][0].update(revision=1, reviewer="Other fictional reviewer")
        self.payload["source_reviews"][0]["review_notes"]["identity"] = "Changed fictional review note"
        successor = self.successor()
        changes = {(item.kind, item.identity): item for item in successor.comparison.changes}
        self.assertIsNone(changes["requirement", "new-requirement"].before)
        self.assertIsNone(changes["requirement", "requirement-unmapped"].after)
        self.assertIn(("evidence_review", "review-example"), changes)
        self.assertIn(("source_review", "source-example"), changes)

    def test_incomplete_corrupt_symlink_cross_project_predecessors_fail_without_output_or_fetch(self):
        for name, mutate, code in (
            ("incomplete", lambda: (self.prior_path / "complete.json").unlink(), "incomplete-run"),
            ("corrupt", lambda: (self.prior_path / "report.md").write_text("tampered"), "corrupt-run"),
            ("source", lambda: next((self.prior_path / "sources").iterdir()).write_text("tampered"), "corrupt-run"),
        ):
            with self.subTest(name=name):
                mutate()
                with patch("eu_compliance_guard.sources.retrieve") as retrieve, self.assertRaises(r.RevalidationError) as caught:
                    self.successor(name, fetch_official=True)
                self.assertEqual(caught.exception.code, code)
                retrieve.assert_not_called()
                self.assertFalse((self.root / name).exists())
                for path, content in self.snapshot.items():
                    (self.prior_path / path).write_bytes(content)
        symlink = self.root / "linked-prior"
        symlink.symlink_to(self.prior_path, target_is_directory=True)
        with self.assertRaises(r.RevalidationError) as caught:
            r.run(self.input, self.root / "linked-output", previous=symlink)
        self.assertEqual(caught.exception.code, "unsafe-path")
        self.payload["project_id"] = "other-project"
        self.payload["scope"]["project_id"] = "other-project"
        for kind in ("requirements", "applicability_decisions", "evidence_reviews"):
            for item in self.payload[kind]:
                item["project_id"] = "other-project"
        self.payload["evidence"][0]["evidence"]["project_id"] = "other-project"
        with self.assertRaises(r.RevalidationError) as caught:
            self.successor("wrong-project")
        self.assertEqual(caught.exception.code, "wrong-project")

    def test_marker_digest_rewrites_do_not_hide_semantically_mismatched_artifacts(self):
        payload = json.loads((self.prior_path / "input.json").read_bytes())
        payload["requirements"][0]["statement"] = "FICTIONAL inconsistent artifact"
        (self.prior_path / "input.json").write_text(json.dumps(payload))
        self.rewrite_marker()
        with self.assertRaises(r.RevalidationError) as caught:
            self.successor()
        self.assertEqual(caught.exception.code, "corrupt-run")

    def test_omitting_supported_source_from_marker_and_duplicate_json_are_corrupt(self):
        marker_path = self.prior_path / "complete.json"
        marker = json.loads(marker_path.read_bytes())
        marker["files"] = [item for item in marker["files"] if not item["path"].startswith("sources/")]
        marker_path.write_text(json.dumps(marker))
        with self.assertRaises(r.RevalidationError) as caught:
            self.successor()
        self.assertEqual(caught.exception.code, "corrupt-run")
        raw = self.snapshot["complete.json"]
        marker_path.write_bytes(b'{"schema_version":1,' + raw[1:])
        with self.assertRaises(r.RevalidationError) as caught:
            self.successor()
        self.assertEqual(caught.exception.code, "corrupt-run")

    def test_predecessor_bundle_byte_bound_and_safe_view_adapter(self):
        bundle_file = self.prior_path / "bundle.json"
        bundle_file.write_bytes(bundle_file.read_bytes() + b" " * m.MAX_BUNDLE_BYTES)
        with self.assertRaises(r.RevalidationError) as caught:
            self.successor()
        self.assertEqual(caught.exception.code, "capacity-exceeded")
        with self.assertRaises(view.ViewError) as caught:
            view.verify_run(self.prior_path)
        self.assertEqual(caught.exception.code, "capacity-exceeded")

    def test_generated_comparison_membership_and_proof_cannot_be_forged(self):
        bundle = self.successor()
        data = bundle.model_dump(mode="json")
        for mutate in (
            lambda item: item["run"].update(parent_run_id="other-run"),
            lambda item: item["current_assessments"].pop(),
            lambda item: item["evidence"][-1].update(digest="sha256:" + "0" * 64),
            lambda item: item["current_assessments"][0].update(freshness="stale", changed_dependencies=[]),
        ):
            changed = deepcopy(data)
            mutate(changed)
            with self.assertRaises(ValueError):
                m.RevalidationBundle.model_validate(changed)


if __name__ == "__main__":
    unittest.main()
