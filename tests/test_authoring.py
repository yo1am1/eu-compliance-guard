"""Starter declarations and located diagnostics on synthetic inputs; nothing is fetched."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest

from eu_compliance_guard import authoring as a, models as m
from eu_compliance_guard.__main__ import main

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/revalidation-synthetic.json"
SECRET = "PRIVATE-VALUE-SENTINEL"


class AuthoringTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="eucg-authoring-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        assets = self.root / "revalidation-synthetic"
        assets.mkdir()
        for name in ("source.txt", "evidence.txt"):
            (assets / name).write_bytes((FIXTURE.parent / "revalidation-synthetic" / name).read_bytes())
        self.payload = json.loads(FIXTURE.read_bytes())
        self.input = self.root / "declarations.json"

    def check(self, payload=None, raw=None):
        self.input.write_bytes(raw if raw is not None else json.dumps(payload or self.payload).encode())
        return a.check(self.input)

    def cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_init_writes_a_valid_starter_once(self):
        path = self.root / "project/.eu-compliance-guard/declarations.json"
        code, stdout, _ = self.cli("init", "--project-id", "shop", "--path", str(path), "--assessment-date", "2026-11-03",
                                   "--jurisdiction", "EU", "--jurisdiction", "DE")
        self.assertEqual(code, 0)
        self.assertIn(str(path), stdout)
        record = m.parse_record(m.RevalidationInput, path.read_bytes())
        self.assertEqual((record.project_id, record.synthetic, record.scope.assessment_date, record.scope.jurisdictions),
                         ("shop", False, "2026-11-03", ["EU", "DE"]))
        self.assertTrue(a.check(path)["valid"])
        before = path.read_bytes()
        code, _, stderr = self.cli("init", "--project-id", "other", "--path", str(path))
        self.assertEqual((code, path.read_bytes()), (2, before))
        self.assertIn("output-exists", stderr)
        code, _, stderr = self.cli("init", "--project-id", "bad id!", "--path", str(self.root / "x.json"))
        self.assertEqual(code, 2)
        self.assertFalse((self.root / "x.json").exists())
        self.assertEqual(record.files_root, "project")

    def test_init_outside_the_dedicated_folder_resolves_files_beside_the_declarations(self):
        path = self.root / "project/decl.json"
        self.assertEqual(self.cli("init", "--project-id", "shop", "--path", str(path))[0], 0)
        self.assertEqual(m.parse_record(m.RevalidationInput, path.read_bytes()).files_root, "declarations_dir")

    def test_init_rejects_an_empty_date_and_symlinked_folders(self):
        code, _, stderr = self.cli("init", "--project-id", "shop", "--path", str(self.root / "d.json"), "--assessment-date", "")
        self.assertEqual(code, 2)
        self.assertFalse((self.root / "d.json").exists())
        (self.root / "real").mkdir()
        (self.root / "link").symlink_to(self.root / "real")
        code, _, stderr = self.cli("init", "--project-id", "shop", "--path", str(self.root / "link/sub/d.json"))
        self.assertEqual(code, 2)
        self.assertIn("unsafe-path", stderr)
        self.assertFalse((self.root / "real/sub").exists())

    def test_valid_fixture_reports_counts_files_targets_and_warnings(self):
        report = self.check()
        self.assertTrue(report["valid"])
        self.assertEqual(report["counts"]["requirements"], 2)
        self.assertEqual([item["matches_declared"] for item in report["files"]], [True, True])
        self.assertEqual(report["targets"][0]["fetch"], "never fetched (fictional fixture)")
        self.assertTrue(any("no obligation_refs" in item["problem"] for item in report["warnings"]))

    def test_cross_reference_errors_are_located_with_identifiers(self):
        cases = [
            (lambda p: p["requirements"][0]["fact_refs"][0].update(revision=7),
             "requirements[0].fact_refs[0]", "pinned at revision 7 but declared at revision 0"),
            (lambda p: p["requirements"][0]["obligation_refs"][0].update(id="missing-obligation"),
             "requirements[0].obligation_refs[0]", "unknown reference missing-obligation"),
            (lambda p: p["sources"][0].update(target_id="nowhere"), "sources[0].target_id", "unknown reference nowhere"),
            (lambda p: p["requirements"].append(deepcopy(p["requirements"][0])), "requirements", "duplicate record identity"),
            (lambda p: p["evidence_reviews"][0].update(method="invented"), "evidence_reviews[0].method", "required_methods"),
        ]
        for change, at, problem in cases:
            payload = deepcopy(self.payload)
            change(payload)
            with self.subTest(at=at):
                report = self.check(payload)
                self.assertFalse(report["valid"])
                self.assertEqual(report["errors"][0]["at"], at)
                self.assertIn(problem, report["errors"][0]["problem"])

    def test_field_errors_json_errors_and_files_never_echo_values(self):
        payload = deepcopy(self.payload)
        payload["synthetic"] = SECRET
        payload["requirements"][0]["statement"] = 5
        report = self.check(payload)
        self.assertEqual({item["at"] for item in report["errors"]}, {"synthetic", "requirements[0].statement"})
        self.assertNotIn(SECRET, json.dumps(report))
        report = self.check(raw=b'{"schema_version": 1,\n "project_id": "x",,}')
        self.assertEqual(report["errors"][0]["at"], "line 2, column 20")
        report = self.check(raw=b'{"a": 1, "a": 2}')
        self.assertIn("duplicate JSON key", report["errors"][0]["problem"])
        (self.root / "revalidation-synthetic/evidence.txt").write_bytes(SECRET.encode())
        report = self.check()
        mismatch = next(item for item in report["errors"] if item["at"] == "evidence[0].path")
        self.assertIn("observed sha256:", mismatch["problem"])
        self.assertNotIn(SECRET, json.dumps(report))
        (self.root / "revalidation-synthetic/evidence.txt").unlink()
        self.assertIn("missing", next(item for item in self.check()["errors"] if item["at"] == "evidence[0].path")["problem"])
        self.assertIn("not found", a.check(self.root / "absent/declarations.json")["errors"][0]["problem"])

    def test_official_and_unofficial_targets_and_cli_exit_codes(self):
        payload = deepcopy(self.payload)
        for identifier, url in (("target-eurlex", "https://eur-lex.europa.eu/eli/reg/2016/679/oj"),
                                ("target-blog", "https://example.com/gdpr")):
            payload["source_targets"].append({"id": identifier, "revision": 0, "family": "gdpr", "intended_url": url,
                                              "publisher": "Example", "intended_type": "final_guidance",
                                              "language": "en", "jurisdiction": "EU"})
        self.input.write_text(json.dumps(payload))
        code, stdout, _ = self.cli("check", "--input", str(self.input))
        self.assertEqual(code, 0)
        self.assertIn("target  source_targets[1] target-eurlex: fetchable", stdout)
        self.assertIn("not fetchable: host-not-official", stdout)
        self.assertIn("not a compliance conclusion", stdout)
        code, stdout, _ = self.cli("check", "--input", str(self.input), "--json")
        self.assertEqual((code, json.loads(stdout)["valid"]), (0, True))
        payload["requirements"][0]["fact_refs"][0]["revision"] = 3
        self.input.write_text(json.dumps(payload))
        self.assertEqual(self.cli("check", "--input", str(self.input))[0], 2)

    def test_check_previous_names_records_needing_new_revisions(self):
        from eu_compliance_guard import revalidation as r
        runs = self.root / "runs"
        runs.mkdir(mode=0o700)
        self.input.write_text(json.dumps(self.payload))
        r.run(self.input, runs / "run-001")
        self.assertTrue(a.check(self.input, runs / "run-001")["valid"])
        payload = deepcopy(self.payload)
        payload["scope"]["roles"][0]["value"] = "changed fictional role"
        self.input.write_text(json.dumps(payload))
        report = a.check(self.input, runs / "run-001")
        self.assertFalse(report["valid"])
        located = {item["at"]: item["problem"] for item in report["errors"]}
        fact_id = payload["scope"]["roles"][0]["id"]
        self.assertIn(f"Fact {fact_id}", located)
        self.assertIn("raise it to 1", located[f"Fact {fact_id}"])
        self.assertIn("Scope scope-example", located)
        self.assertNotIn("changed fictional role", json.dumps(report))
        code, stdout, _ = self.cli("check", "--input", str(self.input), "--previous", str(runs / "run-001"))
        self.assertEqual(code, 2)
        self.assertIn(f"error   Fact {fact_id}: content changed but revision is still 0", stdout)
        missing = a.check(self.input, runs / "absent")
        self.assertIn("predecessor run is unusable (incomplete-run)", missing["errors"][0]["problem"])

    def test_state_dir_is_private_keyed_by_project_id_and_symlink_free(self):
        from unittest.mock import patch as env_patch
        project = self.root / "app"
        self.cli("init", "--project-id", "client-a", "--path", str(project / ".eu-compliance-guard/declarations.json"))
        real = self.root / "real-state"
        real.mkdir()
        (self.root / "linked-state").symlink_to(real, target_is_directory=True)
        with env_patch.dict("os.environ", {"XDG_STATE_HOME": str(self.root / "linked-state")}):
            code, stdout, _ = self.cli("state-dir", "--input", str(project / ".eu-compliance-guard/declarations.json"))
        expected = real.resolve() / "eu-compliance-guard/client-a"
        self.assertEqual((code, stdout.strip()), (0, str(expected)))
        self.assertEqual([oct(path.stat().st_mode & 0o777) for path in (expected.parent, expected)], ["0o700", "0o700"])
        expected.chmod(0o750)
        with env_patch.dict("os.environ", {"XDG_STATE_HOME": str(real)}):
            self.assertEqual(a.state_dir(project / ".eu-compliance-guard/declarations.json"), expected)
        self.assertEqual(expected.stat().st_mode & 0o777, 0o750)
        (project / ".eu-compliance-guard/declarations.json").write_text('{"project_id": "../escape"}')
        code, _, stderr = self.cli("state-dir", "--input", str(project / ".eu-compliance-guard/declarations.json"))
        self.assertEqual(code, 2)
        self.assertIn("invalid-input", stderr)

    def test_no_declared_string_value_ever_reaches_check_output(self):
        marker = "LEAK-MARKER-\x1b[2J"

        def leaves(node, path=()):
            if isinstance(node, dict):
                for key, value in node.items():
                    yield from leaves(value, (*path, key))
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    yield from leaves(value, (*path, index))
            elif isinstance(node, str):
                yield path

        for path in list(leaves(self.payload)):
            payload = deepcopy(self.payload)
            parent = payload
            for key in path[:-1]:
                parent = parent[key]
            parent[path[-1]] = marker
            with self.subTest(path=path):
                text = a.format_check(self.check(payload))
                self.assertNotIn("LEAK-MARKER", text)
                self.assertNotIn("\x1b", text)
        payload = deepcopy(self.payload)
        payload["scope"]["\x1b[2J" + SECRET] = 1
        text = a.format_check(self.check(payload))
        self.assertIn("scope.(unknown field)", text)
        self.assertNotIn(SECRET, text)
        self.assertNotIn("\x1b", text)


if __name__ == "__main__":
    unittest.main()
