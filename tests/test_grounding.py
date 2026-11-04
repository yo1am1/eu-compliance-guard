"""Local evidence grounding on a synthetic project; no network, model or target execution."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

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

    def test_lawful_basis_slots_and_plural_role_keys_are_never_grounded_in_code(self):
        data = json.loads(self.declarations.read_text())
        data["scope"]["roles"].append(fact("fact-roles", "Processor roles for analytics cookie"))
        data["scope"]["activities"] = [{"id": "activity-web", "purpose": "Fictional analytics", "subjects": [],
            "data_categories": [], "roles": [], "lawful_basis": fact("fact-basis", "Analytics cookie max age"),
            "recipients": [], "locations": [], "stores": [], "retention": [], "evidence_owner": "Fictional owner"}]
        self.declarations.write_text(json.dumps(data, indent=2))
        facts = {item["fact"]: item for item in g.ground(self.declarations)["facts"]}
        self.assertEqual((facts["fact-basis"]["observable"], facts["fact-roles"]["observable"]), (False, False))
        for fact_id in ("fact-basis", "fact-roles"):
            code, _, stderr = self.cli("ground", "--input", str(self.declarations), "--apply", f"{fact_id}=app/web.py:2")
            self.assertEqual((code, "not-observable" in stderr), (2, True))

    def test_a_cited_line_hides_only_itself_from_uncovered_touchpoints(self):
        (self.project / "app/web.py").write_text(CODE["app/web.py"]
            + "def notify(user):\n    send(user.email, user.phone, user.address)\n")
        self.assertEqual(self.cli("ground", "--input", str(self.declarations), "--apply",
                                  "fact-cookie-lifetime=app/web.py:2")[0], 0)
        examples = [example for item in g.ground(self.declarations)["undeclared"] for example in item["examples"]]
        self.assertTrue(any(example.startswith("app/web.py:4 ") for example in examples), examples)
        self.assertFalse(any(example.startswith("app/web.py:2 ") for example in examples))

    def test_concept_vocabulary_finds_lines_the_fact_key_does_not_name(self):
        (self.project / "web").mkdir()
        (self.project / "web/head.html").write_text(
            '<script>gtag("config", "G-FICTION"); hotjar.init(1234); mixpanel.init("fictional")</script>\n')
        data = json.loads(self.declarations.read_text())
        data["scope"]["roles"].append(fact("fact-tracking", "Tracking"))
        self.declarations.write_text(json.dumps(data, indent=2))
        report = g.ground(self.declarations)
        facts = {item["fact"]: item for item in report["facts"]}
        self.assertEqual([item["location"] for item in facts["fact-tracking"]["candidates"]][:1], ["web/head.html:1"])
        examples = [example for item in report["undeclared"] for example in item["examples"]]
        self.assertFalse(any(example.startswith("web/head.html:1 ") for example in examples), examples)
        # Lines that name the fact's own terms still rank first.
        self.assertEqual(facts["fact-cookie-lifetime"]["candidates"][0]["location"], "app/web.py:2")

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

    def test_a_refused_apply_in_a_batch_writes_none_of_them(self):
        before = self.declarations.read_bytes()
        for second in ("fact-cookie-basis=app/web.py:2", "fact-cookie-lifetime=app/billing.py:1", "no-separator"):
            with self.subTest(second=second):
                code, stdout, stderr = self.cli("ground", "--input", str(self.declarations),
                                                "--apply", "fact-cookie-lifetime=app/web.py:2", "--apply", second)
                self.assertEqual((code, stdout), (2, ""))
                self.assertIn("grounding failed", stderr)
                self.assertEqual(self.declarations.read_bytes(), before)
        code, stdout, _ = self.cli("ground", "--input", str(self.declarations), "--apply",
                                   "fact-cookie-lifetime=app/web.py:2", "--apply", "fact-llm-weight=app/chat.py:2")
        self.assertEqual(code, 0)
        self.assertIn("fact-llm-weight: observed, pinned to app/chat.py:2", stdout)
        facts = {item.id: item for item in m.scope_facts(r.load_input(self.declarations).scope)}
        self.assertEqual({facts[name].basis for name in ("fact-cookie-lifetime", "fact-llm-weight")}, {"observed"})

    def test_apply_with_json_prints_json(self):
        code, stdout, stderr = self.cli("ground", "--input", str(self.declarations), "--json",
                                        "--apply", "fact-cookie-lifetime=app/web.py:2")
        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(json.loads(stdout), {"applied": [{"fact": "fact-cookie-lifetime", "location": "app/web.py:2"}]})

    def test_apply_keeps_the_declarations_mode_and_refuses_a_read_only_file(self):
        for mode in (0o644, 0o640, 0o600):
            with self.subTest(mode=oct(mode)):
                self.declarations.chmod(mode)
                g.apply(self.declarations, "fact-cookie-lifetime", "app/web.py:2")
                self.assertEqual(stat.S_IMODE(self.declarations.stat().st_mode), mode)
        self.declarations.chmod(0o444)
        before = self.declarations.read_bytes()
        code, _, stderr = self.cli("ground", "--input", str(self.declarations), "--apply", "fact-llm-weight=app/chat.py:2")
        self.assertEqual((code, "io-failed" in stderr), (2, True))
        self.assertEqual((self.declarations.read_bytes(), stat.S_IMODE(self.declarations.stat().st_mode)), (before, 0o444))

    def test_apply_replaces_a_planted_temp_symlink_instead_of_writing_through_it(self):
        victim = Path(self.temporary.name) / "victim.txt"
        victim.write_text("untouched")
        (self.declarations.parent / ".declarations.json.tmp").symlink_to(victim)
        g.apply(self.declarations, "fact-cookie-lifetime", "app/web.py:2")
        self.assertEqual(victim.read_text(), "untouched")
        self.assertFalse(self.declarations.is_symlink())
        self.assertFalse((self.declarations.parent / ".declarations.json.tmp").exists())

    def test_a_bare_relative_input_still_indexes_the_project(self):
        import os
        previous = os.getcwd()
        os.chdir(self.declarations.parent)
        self.addCleanup(os.chdir, previous)
        report = g.ground("declarations.json")
        self.assertEqual(Path(report["root"]), self.project.resolve())
        self.assertEqual(report["files"], len(CODE))

    def test_the_declarations_file_is_never_indexed_or_pinned(self):
        data = json.loads(self.declarations.read_text())
        data["files_root"] = "declarations_dir"
        self.declarations.write_text(json.dumps(data, indent=2))
        report = g.ground(self.declarations)
        self.assertFalse(any("declarations.json" in item["location"] for fact in report["facts"] for item in fact["candidates"]))
        with self.assertRaises(g.GroundingError) as raised:
            g.apply(self.declarations, "fact-cookie-lifetime", "declarations.json:2")
        self.assertEqual(raised.exception.code, "bad-location")

    def test_line_numbers_match_editors_despite_form_feeds_and_no_null_term(self):
        (self.project / "app/web.py").write_text("import os\n\x0c\n# section\nx = 1\n" + CODE["app/web.py"])
        index = g.build_index(self.project)
        line = next(item for item in index.lines if "set_cookie" in item.text)
        self.assertEqual((line.path, line.number), ("app/web.py", 6))
        self.assertNotIn("null", g._fact_query(m.Fact.model_validate(fact("f", "Cookie lifetime"))))

    def test_regrounding_one_fact_keeps_others_stale_and_the_next_run_accepts_revisions(self):
        data = json.loads(self.declarations.read_text())
        data["scope"]["roles"].append(fact("fact-cookie-name", "Analytics cookie name"))
        self.declarations.write_text(json.dumps(data, indent=2))
        g.apply(self.declarations, "fact-cookie-lifetime", "app/web.py:2")
        g.apply(self.declarations, "fact-cookie-name", "app/web.py:2")
        runs = Path(self.temporary.name) / "runs"
        runs.mkdir(mode=0o700)
        r.run(self.declarations, runs / "run-1")
        web = self.project / "app/web.py"
        web.write_text("# moved\n" + web.read_text())
        g.apply(self.declarations, "fact-cookie-lifetime", "app/web.py:3")
        self.assertEqual(a.check(self.declarations, runs / "run-1")["valid"], True)
        bundle = r.run(self.declarations, runs / "run-2", previous=runs / "run-1")
        declared = {item.id: item for item in m.scope_facts(bundle.declarations.scope)}
        [evidence] = bundle.declarations.evidence
        self.assertEqual(evidence.evidence.source_refs, ["app/web.py:3"])
        self.assertEqual(declared["fact-cookie-lifetime"].basis, "observed")
        # The other fact was confirmed against the old bytes: it is a question again.
        self.assertEqual((declared["fact-cookie-name"].basis, declared["fact-cookie-name"].evidence_ids), ("assumed", []))

    def test_an_unreadable_folder_counts_as_skipped(self):
        # Simulated, so the test also holds as root, whom chmod 000 does not stop.
        blocked, scandir = os.path.join(os.path.realpath(self.project), "app"), os.scandir

        def refuse(path="."):
            if os.fspath(path) == blocked:
                raise PermissionError(13, "Permission denied")
            return scandir(path)

        with mock.patch("os.scandir", refuse):
            report = g.ground(self.declarations)
        self.assertEqual((report["files"], report["skipped"]), (0, 1))
        self.assertIn("(1 skipped)", g.format_ground(report))

    def test_oversized_files_are_skipped_without_reading_them_whole(self):
        (self.project / "dump.sql").write_bytes(b"cookie " * (g.MAX_FILE_BYTES // 7 + 10))
        index = g.build_index(self.project)
        self.assertNotIn("dump.sql", index.digests)
        self.assertEqual(index.skipped, 1)

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
