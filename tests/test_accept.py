"""accept: one step from an article suggestion to a mapped candidate obligation; never a decision."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from eu_compliance_guard import authoring as a, mapping, models as m, nextstep as n, revalidation as r, view as v
from eu_compliance_guard.__main__ import main

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/revalidation-synthetic.json"


class AcceptTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="eucg-accept-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)
        shutil.copytree(FIXTURE.parent / "revalidation-synthetic", self.root / "revalidation-synthetic")
        self.path = self.root / "declarations.json"
        self.path.write_bytes(FIXTURE.read_bytes())

    def cli(self, *args) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main([str(arg) for arg in args])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_accept_creates_a_candidate_obligation_and_closes_the_mapping_step_without_a_decision(self):
        code, out, _ = self.cli("accept", "requirement-unmapped=target-example:Article 3", "--input", self.path)
        self.assertEqual(code, 0)
        self.assertIn("stays unresolved", out)
        declared = r.load_input(self.path)
        obligation = next(item for item in declared.obligations if item.id == "obligation-target-example-article-3")
        self.assertEqual([(pin.source_target_id, pin.locator) for pin in obligation.source_provisions], [("target-example", "Article 3")])
        self.assertEqual(obligation.required_methods, [])  # never invented
        requirement = next(item for item in declared.requirements if item.id == "requirement-unmapped")
        self.assertEqual((requirement.revision, [ref.id for ref in requirement.obligation_refs]),
                         (1, ["obligation-target-example-article-3"]))
        self.assertFalse(any(item.obligation.id == obligation.id for item in declared.applicability_decisions))
        self.assertTrue(a.check(self.path)["valid"])
        (self.root / "state").mkdir(mode=0o700)
        r.run(self.path, self.root / "state/run-1")
        bundle = v.verify_run(self.root / "state/run-1")
        steps = n.next_steps(bundle, top=50)
        self.assertFalse([step for step in steps if step["kind"] == "mapping" and step["subject"] == "requirement-unmapped"])
        decision = next(item for item in bundle.effective_applicability_decisions if item.obligation.id == obligation.id)
        self.assertEqual(decision.applicability, "unresolved")

    def write_lock(self, keys):
        from eu_compliance_guard import lawlock
        lock = m.LawLock(schema_version=1, lock_version=1, project_id="project-example", run_id="run-1", entries=[
            m.LawLockEntry(target_id="target-example", version=None, source_digest="sha256:" + "0" * 64,
                           articles=[m.LawLockArticle(key=key, digest="sha256:" + "1" * 64) for key in keys])])
        lawlock.write(lock, self.root / lawlock.LOCK_NAME)

    def test_accept_refuses_an_article_the_text_does_not_have(self):
        self.write_lock(["Article 1", "Article 3"])
        before = self.path.read_bytes()
        code, out, err = self.cli("accept", "requirement-unmapped=target-example:Article 999", "--input", self.path)
        self.assertEqual((code, out), (2, ""))
        self.assertIn("unknown-article", err)
        self.assertEqual(self.path.read_bytes(), before)
        code, out, _ = self.cli("accept", "requirement-unmapped=target-example:Article 3", "--input", self.path)
        self.assertEqual(code, 0)
        self.assertNotIn("not checked", out)

    def test_accept_says_when_there_is_no_text_to_check_against(self):
        code, out, _ = self.cli("accept", "requirement-unmapped=target-example:Article 3", "--input", self.path)
        self.assertEqual(code, 0)
        self.assertIn("Article 3 was not checked against the act: target-example has no retained text or lock entry yet.", out)

    def test_pack_build_refuses_a_pin_the_locked_text_does_not_have(self):
        from eu_compliance_guard import packs
        mapping.accept(self.path, "requirement-unmapped=target-example:Article 9")  # no lock yet: accepted, unchecked
        self.write_lock(["Article 1"])
        with self.assertRaises(packs.PackError) as raised:
            packs.build(self.path, "pack-x", "X")
        self.assertEqual(raised.exception.code, "unknown-article")
        self.write_lock(["Article 1", "Article 9"])
        pack = packs.build(self.path, "pack-x", "X")
        self.assertEqual([[a.key for a in entry.articles] for entry in pack.law], [["Article 9"]])

    def test_accept_reuses_an_obligation_pinning_the_same_article_and_is_idempotent(self):
        data = json.loads(self.path.read_text())
        pin = next(item for item in data["obligations"] if item["id"] == "obligation-unmapped")["source_provisions"][0]
        pin["locator"] = "Article 3(1)"
        self.path.write_text(json.dumps(data))
        result = mapping.accept(self.path, "requirement-unmapped=target-example:Art. 3")
        self.assertEqual((result["obligation"], result["created"]), ("obligation-unmapped", False))
        before = self.path.read_bytes()
        self.assertTrue(mapping.accept(self.path, "requirement-unmapped=target-example:Article 3")["already_linked"])
        self.assertEqual(self.path.read_bytes(), before)

    def test_bad_input_unknown_ids_and_links_change_nothing(self):
        before = self.path.read_bytes()
        for value, expected in (("requirement-unmapped", "bad-mapping"), ("requirement-unmapped=target-example:Recital 4", "bad-mapping"),
                                ("nope=target-example:Article 3", "unknown-id"), ("requirement-unmapped=nope:Article 3", "unknown-id")):
            code, _, err = self.cli("accept", value, "--input", self.path)
            self.assertEqual((code, expected in err), (2, True), value)
        self.assertEqual(self.path.read_bytes(), before)
        link = self.root / "linked.json"
        link.symlink_to(self.path)
        code, _, err = self.cli("accept", "requirement-unmapped=target-example:Article 3", "--input", link)
        self.assertEqual((code, "unsafe-path" in err), (2, True))
        self.assertEqual(self.path.read_bytes(), before)

    def test_json_output(self):
        code, out, _ = self.cli("accept", "requirement-unmapped=target-example:Article 3", "--input", self.path, "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["obligation"], "obligation-target-example-article-3")


if __name__ == "__main__":
    unittest.main()
