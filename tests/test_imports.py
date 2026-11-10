"""Imports of other tools' results: untrusted, summarised by concept, never changing declarations."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from eu_compliance_guard import imports
from eu_compliance_guard.__main__ import main

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def cli(*args):
    stdout = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
        code = main([str(arg) for arg in args])
    return code, stdout.getvalue()


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="eucg-import-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.input = self.root / "declarations.json"
        shutil.copy(FIXTURES / "revalidation-synthetic.json", self.input)

    def test_wec_inspection_is_grouped_by_concept_with_safe_text(self):
        summary = imports.summarise((FIXTURES / "imports/wec-synthetic.json").read_bytes(), "wec")
        self.assertTrue(summary["untrusted"])
        self.assertEqual(summary["title"], "EDPS Website Evidence Collector inspection of https://shop.example.invalid/")
        self.assertEqual(sorted(summary["concepts"]), ["security", "third_party", "tracking"])
        self.assertEqual(summary["concepts"]["tracking"]["count"], 4)
        self.assertIn("cookie _fictional_id (third-party, .tracker.example.invalid)", summary["concepts"]["tracking"]["examples"])
        self.assertTrue(all(char.isprintable() for value in summary["concepts"].values()
                            for example in value["examples"] for char in example))

    def test_sarif_results_are_classified_and_unmatched_ones_kept(self):
        summary = imports.summarise((FIXTURES / "imports/sarif-synthetic.json").read_bytes(), "sarif")
        self.assertEqual(summary["title"], "SARIF results from fictional-scanner")
        self.assertIn("security", summary["concepts"])
        self.assertIn("tracking", summary["concepts"])
        self.assertEqual(summary["concepts"]["unclassified"]["count"], 1)
        self.assertEqual(imports.summarise(b'{"runs": []}', "sarif")["concepts"], {})
        odd = json.dumps({"runs": [{"results": [{"ruleId": "r", "message": {"text": "t"}, "locations": [
            {"physicalLocation": {"artifactLocation": {"uri": "a.py"}, "region": {"startLine": True}}}]}]}]}).encode()
        self.assertEqual(imports.summarise(odd, "sarif")["concepts"]["unclassified"]["examples"], ["warning r at a.py: t"])
        # A rule whose id is not a string is skipped; it used to fail the whole import.
        odd = json.dumps({"runs": [{"tool": {"driver": {"rules": [{"id": ["r"]}, {"id": "r", "name": "cookie"}]}},
                                    "results": [{"ruleId": "r"}]}]}).encode()
        self.assertEqual(sorted(imports.summarise(odd, "sarif")["concepts"]), ["tracking"])

    def test_cli_keeps_a_copy_and_summary_and_never_changes_the_declarations(self):
        before = self.input.read_bytes()
        code, out = cli("import-evidence", FIXTURES / "imports/sarif-synthetic.json", "--kind", "sarif", "--input", self.input)
        self.assertEqual(code, 0)
        self.assertIn("untrusted tool output", out)
        self.assertIn("declarations were not changed", out)
        self.assertEqual(self.input.read_bytes(), before)
        files = sorted(path.name for path in (self.root / "imports").iterdir())
        self.assertEqual(len(files), 2)
        self.assertEqual({(self.root / "imports" / name).stat().st_mode & 0o777 for name in files}, {0o600})
        summary = json.loads((self.root / "imports" / files[1]).read_text())
        self.assertEqual((self.root / summary["copy"]).read_bytes(), (FIXTURES / "imports/sarif-synthetic.json").read_bytes())
        # Importing the same file again is deterministic.
        self.assertEqual(cli("import-evidence", FIXTURES / "imports/sarif-synthetic.json", "--kind", "sarif", "--input", self.input)[1], out)

    def test_imported_files_are_never_grounded_as_project_code(self):
        from eu_compliance_guard import grounding
        self.assertEqual(cli("import-evidence", FIXTURES / "imports/sarif-synthetic.json", "--kind", "sarif",
                             "--input", self.input)[0], 0)
        (self.root / "eu-law.lock").write_text("{}")
        (self.root / "signatures").mkdir()
        (self.root / "signatures/decision.json").write_text('{"cookie": "tracking"}')
        files, _ = grounding.read_project(self.root, grounding._own_files(self.input, self.root))
        self.assertEqual([path for path, _, _ in files if path.startswith(("imports", "signatures", "eu-law"))], [])

    def test_invalid_or_linked_input_fails_safely(self):
        bad = self.root / "bad.json"
        bad.write_text("[1, 2]")
        self.assertEqual(cli("import-evidence", bad, "--kind", "wec", "--input", self.input)[0], 2)
        # The wrong --kind is refused, not summarised as an empty result.
        self.assertEqual(cli("import-evidence", FIXTURES / "imports/sarif-synthetic.json", "--kind", "wec",
                             "--input", self.input)[0], 2)
        self.assertEqual(cli("import-evidence", FIXTURES / "imports/wec-synthetic.json", "--kind", "sarif",
                             "--input", self.input)[0], 2)
        link = self.root / "link.json"
        link.symlink_to(FIXTURES / "imports/wec-synthetic.json")
        self.assertEqual(cli("import-evidence", link, "--kind", "wec", "--input", self.input)[0], 2)
        self.assertFalse((self.root / "imports").exists())


if __name__ == "__main__":
    unittest.main()
