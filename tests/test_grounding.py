"""Local evidence grounding on a synthetic project; no network, model or target execution."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from eu_compliance_guard import authoring as a, grounding as g, models as m, revalidation as r
from eu_compliance_guard.__main__ import main

CODE = {
    "app/web.py": 'def landing(response, visitor_id):\n    response.set_cookie("_analytics", visitor_id, max_age=60 * 60 * 24 * 395)\n',
    "app/chat.py": 'def coach(user, llm):\n    return llm.complete("weight=" + str(user["weight_kg"]))\n',
    "app/billing.py": "def renew(plan):\n    return {\"auto_renew\": True}  # cancellation only by email\n",
}


def fact(identity, key, basis="unknown", value=None):
    return {"id": identity, "revision": 0, "key": key, "value": value, "basis": basis, "evidence_ids": [],
            "owner": "Fictional owner", "observed_at": "2026-11-04T00:00:00Z", "conflicts": []}


class GroundingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="eucg-ground-")
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name) / "shop"
        for relative, content in CODE.items():
            (self.project / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.project / relative).write_text(content)
        self.declarations = a.init(self.project / ".eu-compliance-guard/declarations.json", "shop", synthetic=True)
        data = json.loads(self.declarations.read_text())
        data["scope"]["roles"] = [fact("fact-cookie-lifetime", "Analytics cookie lifetime"),
                                  fact("fact-llm-weight", "Member weight is sent to the LLM", "assumed", True),
                                  fact("fact-cookie-basis", "Lawful basis for the analytics cookie")]
        data["requirements"] = [{"id": "req-cookie", "revision": 0, "project_id": "shop", "synthetic": True,
                                 "statement": "Fictional cookie requirement.", "origin": None, "locator": None,
                                 "activity_ids": [], "fact_refs": [{"id": "fact-cookie-lifetime", "revision": 0}],
                                 "obligation_refs": [], "evidence_ids": []}]
        self.declarations.write_text(json.dumps(data, indent=2))

    def cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_tokens_split_identifiers(self):
        self.assertEqual(g.tokens("response.set_cookie(maxAge=395)"), ["response", "set", "cookie", "max", "age", "395"])

    def test_index_reads_only_bounded_text_files_without_symlinks_or_skipped_folders(self):
        (self.project / "node_modules/pkg").mkdir(parents=True)
        (self.project / "node_modules/pkg/index.js").write_text("set_cookie()")
        (self.project / "logo.png").write_bytes(b"\x89PNG\0cookie")
        (self.project / "blob.py").write_bytes(b"x\0cookie")
        (self.project / "linked.py").symlink_to(self.project / "app/web.py")
        index = g.build_index(self.project)
        self.assertEqual(set(index.digests), set(CODE))
        self.assertEqual(index.digests["app/web.py"], m.content_digest((self.project / "app/web.py").read_bytes()))

    def test_ground_ranks_code_evidence_and_refuses_organisational_facts(self):
        report = g.ground(self.declarations)
        facts = {item["fact"]: item for item in report["facts"]}
        self.assertEqual(facts["fact-cookie-lifetime"]["candidates"][0]["location"], "app/web.py:2")
        self.assertIn("tracking", facts["fact-cookie-lifetime"]["candidates"][0]["concepts"])
        self.assertEqual(facts["fact-llm-weight"]["candidates"][0]["location"], "app/chat.py:2")
        self.assertFalse(facts["fact-cookie-basis"]["observable"])
        self.assertEqual(facts["fact-cookie-basis"]["candidates"], [])
        self.assertTrue(any(item["concept"] == "subscription" for item in report["undeclared"]))
        code, stdout, _ = self.cli("ground", "--input", str(self.declarations))
        self.assertEqual(code, 0)
        self.assertIn("organisational: code cannot show this", stdout)
        self.assertIn("no output is a compliance conclusion", stdout)

    def test_apply_pins_observed_evidence_and_bumps_revisions_and_pins(self):
        record = g.apply(self.declarations, "fact-cookie-lifetime", "app/web.py:2", now="2026-11-04T01:00:00Z")
        observed = next(item for item in m.scope_facts(record.scope) if item.id == "fact-cookie-lifetime")
        self.assertEqual((observed.basis, observed.revision, record.scope.revision), ("observed", 1, 1))
        self.assertEqual(record.requirements[0].fact_refs[0].revision, 1)
        evidence = record.evidence[0]
        self.assertEqual((evidence.path, evidence.evidence.provenance, evidence.evidence.source_refs),
                         ("app/web.py", "observed", ["app/web.py:2"]))
        self.assertEqual(evidence.evidence.digest, m.content_digest((self.project / "app/web.py").read_bytes()))
        self.assertTrue(a.check(self.declarations)["valid"])

    def test_apply_refusals_leave_the_file_unchanged(self):
        before = self.declarations.read_bytes()
        (self.project / "outside.py").write_text("set_cookie()")
        (self.project / "app/link.py").symlink_to(self.project / "outside.py")
        for fact_id, location, code in (("fact-cookie-basis", "app/web.py:2", "not-observable"),
                                        ("fact-cookie-lifetime", "app/billing.py:1", "unrelated-line"),
                                        ("fact-cookie-lifetime", "app/web.py:99", "bad-location"),
                                        ("fact-cookie-lifetime", "../outside.py:1", "bad-location"),
                                        ("fact-cookie-lifetime", "app/link.py:1", "bad-location")):
            with self.subTest(location=location), self.assertRaises(g.GroundingError) as caught:
                g.apply(self.declarations, fact_id, location)
            self.assertEqual(caught.exception.code, code)
        self.assertEqual(self.declarations.read_bytes(), before)
        code, _, stderr = self.cli("ground", "--input", str(self.declarations), "--apply", "fact-cookie-basis=app/web.py:2")
        self.assertEqual((code, "not-observable" in stderr), (2, True))

    def test_grounded_fact_closes_its_gap_until_the_code_changes(self):
        runs = Path(self.temporary.name) / "runs"
        runs.mkdir(mode=0o700)
        before = r.run(self.declarations, runs / "run-1")
        self.assertIn("Fact fact-cookie-lifetime: assumed, unknown or conflicting declaration needs review.", before.gaps)
        g.apply(self.declarations, "fact-cookie-lifetime", "app/web.py:2")
        grounded = r.run(self.declarations, runs / "run-2")
        self.assertFalse(any(gap.startswith("Fact fact-cookie-lifetime") for gap in grounded.gaps))
        (self.project / "app/web.py").write_text(CODE["app/web.py"].replace("395", "30"))
        changed = r.run(self.declarations, runs / "run-3")
        self.assertTrue(any("evidence-code-" in gap for gap in changed.gaps))


if __name__ == "__main__":
    unittest.main()
