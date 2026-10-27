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
        self.assertIn(overlay.obligation_disposition_id, html)
        self.assertIn("stale", html)
        self.assertIn('scope="col"', html)
        self.assertIn('tabindex="0" role="region"', html)
        self.assertNotIn("<script", html)

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
        bundle_file.write_bytes(bundle_file.read_bytes() + b" " * m.MAX_REQUEST_BYTES)
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
