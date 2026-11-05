"""Next-step ranking on synthetic runs."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
from typing import get_args
import unittest
from unittest.mock import patch

from eu_compliance_guard import models as m, nextstep as n, revalidation as r, view as v
from eu_compliance_guard.__main__ import main

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/revalidation-synthetic.json"


class NextStepTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="eucg-next-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)
        (self.root / "revalidation-synthetic").mkdir()
        for name in ("source.txt", "evidence.txt"):
            (self.root / "revalidation-synthetic" / name).write_bytes((FIXTURE.parent / "revalidation-synthetic" / name).read_bytes())
        self.payload = json.loads(FIXTURE.read_bytes())

    def run_bundle(self, name="run-20261025T000000Z"):
        path = self.root / "input.json"
        path.write_text(json.dumps(self.payload))
        runs = self.root / "state"
        runs.mkdir(mode=0o700, exist_ok=True)
        r.run(path, runs / name)
        return runs / name

    def test_steps_rank_by_unblocked_requirements_and_name_no_verdict(self):
        steps = n.next_steps(v.verify_run(self.run_bundle()), top=10)
        self.assertTrue(steps)
        counts = [step["unblocks"] for step in steps]
        self.assertEqual(counts, sorted(counts, reverse=True))
        kinds = {step["kind"] for step in steps}
        self.assertLessEqual(kinds, set(n.KINDS))
        self.assertIn("mapping", kinds)  # requirement-unmapped has no obligation
        self.assertIn("fact", kinds)
        for step in steps:
            self.assertEqual(step["unblocks"], len(step["requirements"]))
        self.assertIn("not a compliance verdict", n.format_steps(steps))
        self.assertIn("not a compliance conclusion", n.format_steps([]))

    def test_facts_relied_on_by_more_requirements_come_first(self):
        fact = next(item for item in self.payload["scope"]["roles"] if item["basis"] == "unknown")
        for requirement in self.payload["requirements"]:
            requirement["fact_refs"] = [{"id": fact["id"], "revision": fact["revision"]}]
        steps = n.next_steps(v.verify_run(self.run_bundle()), top=10)
        facts = [step for step in steps if step["kind"] == "fact"]
        self.assertEqual(facts[0]["subject"], fact["id"])
        self.assertEqual(facts[0]["unblocks"], 2)

    def test_a_fact_copied_into_several_places_is_one_step(self):
        fact = next(item for item in self.payload["scope"]["roles"] if item["basis"] == "unknown")
        self.payload["scope"]["size_and_sector"] = [*self.payload["scope"].get("size_and_sector", []), dict(fact)]
        steps = n.next_steps(v.verify_run(self.run_bundle()), top=10)
        self.assertEqual(sum(step["subject"] == fact["id"] for step in steps), 1)

    def test_every_open_requirement_has_a_step_and_changed_evidence_asks_to_ground_again(self):
        fact = next(item for item in self.payload["scope"]["roles"] if item["basis"] == "declared")
        fact["evidence_ids"] = ["evidence-example"]
        for requirement in self.payload["requirements"]:
            requirement["fact_refs"] = [{"id": fact["id"], "revision": fact["revision"]}]
        (self.root / "revalidation-synthetic/evidence.txt").write_bytes(b"changed after the declaration")
        bundle = v.verify_run(self.run_bundle())
        steps = n.next_steps(bundle, top=100)
        open_ids = {item.requirement.id for item in bundle.requirement_assessments if item.state != "supported"}
        self.assertTrue(open_ids)
        self.assertLessEqual(open_ids, set().union(*(step["requirements"] for step in steps)))
        again = [step for step in steps if step["kind"] == "fact" and step["subject"] == fact["id"]]
        self.assertEqual(len(again), 1)
        self.assertIn("again", again[0]["action"])

    def test_changed_evidence_routes_technical_facts_to_ground_and_organisational_ones_to_the_owner(self):
        technical = dict(self.payload["scope"]["roles"][0], id="fact-cookie", key="Fictional cookie lifetime")
        self.payload["scope"]["roles"].append(technical)
        for item in self.payload["scope"]["roles"]:
            if item["id"] in ("fact-declared", "fact-cookie"):
                item["evidence_ids"] = ["evidence-example"]
        (self.root / "revalidation-synthetic/evidence.txt").write_bytes(b"changed after the declaration")
        steps = {step["subject"]: step for step in n.next_steps(v.verify_run(self.run_bundle()), top=100)}
        self.assertEqual(steps["fact-cookie"]["command"], "eu-compliance-guard ground")
        # A role is an owner decision: `ground --apply` refuses it, so the step must not send the user there.
        self.assertIsNone(steps["fact-declared"]["command"])
        self.assertIn("Fictional owner", steps["fact-declared"]["action"])

    def test_a_recorded_decision_that_cannot_take_effect_names_its_blockers_not_a_new_decision(self):
        del self.payload["source_reviews"][0]["review_notes"]["case_law"]
        steps = n.next_steps(v.verify_run(self.run_bundle("run-note")), top=100)
        decision = next(step for step in steps if step["subject"] == "obligation-example")
        self.assertEqual(decision["kind"], "applicability")
        self.assertNotIn("Record whether", decision["action"])
        self.assertIn("recorded 'applicable' decision", decision["action"])
        self.assertIn("source provision or reviewed source support unresolved", decision["action"])
        source = next(step for step in steps if step["kind"] == "source" and step["subject"] == "target-example")
        self.assertIn("source note missing: case_law", source["action"])
        self.assertEqual(source["requirements"], ["requirement-example"])

        self.payload = json.loads(FIXTURE.read_bytes())
        (self.root / "revalidation-synthetic/evidence.txt").write_bytes(b"changed after the declaration")
        steps = n.next_steps(v.verify_run(self.run_bundle("run-evidence")), top=100)
        decision = next(step for step in steps if step["subject"] == "obligation-example")
        self.assertIn("applicability evidence unavailable", decision["action"])
        self.assertFalse([step for step in steps if step["kind"] == "source"])

        # Only an undecided record asks the reviewer for a decision.
        self.payload["applicability_decisions"][0]["applicability"] = "unresolved"
        steps = n.next_steps(v.verify_run(self.run_bundle("run-undecided")), top=100)
        decision = next(step for step in steps if step["subject"] == "obligation-example")
        self.assertTrue(decision["action"].startswith("Record whether obligation-example applies"))

    def test_targets_the_fetch_refuses_are_never_offered_for_retrieval(self):
        target = dict(self.payload["source_targets"][0], id="target-national", intended_type="national_act",
                      intended_url="https://www.legifrance.gouv.fr/example", intended_identifier="FICTIONAL-FR")
        self.payload["source_targets"].append(target)
        steps = n.next_steps(v.verify_run(self.run_bundle()), top=100)
        self.assertFalse([step for step in steps if step["kind"] == "retrieve"])
        self.assertTrue([step for step in steps if step["kind"] == "source" and step["subject"] == "target-national"])

    def test_a_language_the_fetch_refuses_is_never_offered_for_retrieval(self):
        official = dict(self.payload["source_targets"][0], intended_type="eu_act", intended_identifier="FICTIONAL-EU",
                        intended_url="https://eur-lex.europa.eu/example", jurisdiction="EU")
        self.payload["source_targets"] += [dict(official, id="target-language", language="english"),
                                           dict(official, id="target-fetchable")]
        steps = n.next_steps(v.verify_run(self.run_bundle()), top=100)
        retrieve = [step for step in steps if step["kind"] == "retrieve"]
        self.assertEqual(len(retrieve), 1)
        self.assertIn(" 1 declared source target(s)", retrieve[0]["action"])
        self.assertTrue([step for step in steps if step["kind"] == "source" and step["subject"] == "target-language"])

    def test_family_step_names_only_outcomes_the_model_accepts(self):
        steps = n.next_steps(v.verify_run(self.run_bundle()), top=100)
        family = next(step for step in steps if step["kind"] == "family")
        named = family["action"].partition("(")[2].partition(")")[0].split(" or ")
        accepted = [value.replace("_", " ") for value in get_args(m.Applicability) if value != "unresolved"]
        self.assertEqual(sorted(named), sorted(accepted))

    def test_cli_uses_the_newest_completed_run_and_reports_missing_runs(self):
        older = self.run_bundle("run-20261025T000000Z")
        newer = self.run_bundle("run-20261026T000000Z")
        (older.parent / "run-20261027T000000Z").mkdir()  # incomplete: no marker
        out, err = io.StringIO(), io.StringIO()
        with patch("eu_compliance_guard.authoring.state_dir", return_value=older.parent), \
                redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(main(["next", "--json", "--top", "1"]), 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["run"], str(newer))
        self.assertEqual(len(result["steps"]), 1)
        empty = self.root / "empty"
        empty.mkdir()
        out, err = io.StringIO(), io.StringIO()
        with patch("eu_compliance_guard.authoring.state_dir", return_value=empty), redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(main(["next"]), 2)
        self.assertEqual(err.getvalue(), "eu-compliance-guard: no-run: next step failed\n")

    def test_the_newest_run_is_the_last_completed_not_the_last_named(self):
        named_later = self.run_bundle("run-zzz-first")
        completed_later = self.run_bundle("run-aaa-second")
        os.utime(named_later / "complete.json", ns=(1_000_000_000, 1_000_000_000))
        os.utime(completed_later / "complete.json", ns=(2_000_000_000, 2_000_000_000))
        self.assertEqual(n.latest_run(named_later.parent), completed_later)
        os.utime(named_later / "complete.json", ns=(2_000_000_000, 2_000_000_000))
        self.assertEqual(n.latest_run(named_later.parent), named_later)  # same time: the later name

    def test_unreadable_run_storage_is_unsafe_path_never_no_run(self):
        older = self.run_bundle("run-20261025T000000Z")
        newer = self.run_bundle("run-20261026T000000Z")
        real_stat = os.stat

        def denied(path, *args, **kwargs):
            if os.fspath(path) == os.fspath(newer / "complete.json"):
                raise PermissionError(13, "Permission denied")
            return real_stat(path, *args, **kwargs)
        # Permissions do not bind root, so the refusals the kernel would give are simulated.
        for label, case in (("state dir", patch.object(Path, "iterdir", side_effect=PermissionError(13, "denied"))),
                            ("newest run", patch("os.stat", side_effect=denied))):
            out, err = io.StringIO(), io.StringIO()
            with self.subTest(label):
                with patch("eu_compliance_guard.authoring.state_dir", return_value=older.parent), case, \
                        redirect_stdout(out), redirect_stderr(err):
                    code = main(["next"])
                self.assertEqual((code, err.getvalue()), (2, "eu-compliance-guard: unsafe-path: next step failed\n"))
                self.assertEqual(out.getvalue(), "")
        # A state directory that does not exist yet still means no run.
        self.assertIsNone(n.latest_run(self.root / "missing"))

    def test_report_leads_with_next_steps(self):
        html = v.write_view(self.run_bundle()).read_text()
        self.assertLess(html.index("<h2>Next best steps</h2>"), html.index("<h2>Questions for the project owner</h2>"))
        self.assertIn('<ol class="next">', html)


if __name__ == "__main__":
    unittest.main()
