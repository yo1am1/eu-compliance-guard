"""Exports: a draft Article 30 record and DPIA screening inputs, from synthetic declarations only."""
from contextlib import redirect_stderr, redirect_stdout
import csv
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest

from eu_compliance_guard import exports, models as m
from eu_compliance_guard.__main__ import main
from eu_compliance_guard.notice import LEGAL_NOTICE

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/revalidation-synthetic.json"


def declarations() -> dict:
    data = json.loads(FIXTURE.read_text())
    role = data["scope"]["roles"]

    def fact(identity, key, value, basis):
        item = deepcopy(role[0])
        item.update(id=identity, key=key, value=value, basis=basis)
        if basis in ("assumed", "unknown"):
            item["evidence_ids"] = []
        return item

    data["scope"]["activities"] = [
        {"id": "activity-signup", "purpose": "Fictional account sign-up and personalised recommendations",
         "subjects": ["fictional customers", "children under 16"], "data_categories": ["email", "health data", "location"],
         "roles": [], "lawful_basis": deepcopy(role[0]),
         "recipients": [fact("fact-recipient", "Fictional email provider", "processor", "assumed")],
         "locations": [], "stores": [], "retention": [], "evidence_owner": "Fictional owner"},
        {"id": "activity-newsletter", "purpose": "=HYPERLINK(\"x\") fictional <b>newsletter</b>\nsecond line",
         "subjects": [], "data_categories": [], "roles": [], "lawful_basis": deepcopy(role[0]),
         "recipients": [], "locations": [], "stores": [], "retention": [], "evidence_owner": "Fictional owner"}]
    m.parse_record(m.RevalidationInput, json.dumps(data).encode())
    return data


def cli(*args):
    stdout = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
        code = main([str(arg) for arg in args])
    return code, stdout.getvalue()


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.declared = m.parse_record(m.RevalidationInput, json.dumps(declarations()).encode())

    def test_record_keeps_every_basis_and_lists_gaps_without_filling_them(self):
        record = exports.ropa(self.declared)
        self.assertTrue(record["status"].startswith("DRAFT"))
        signup = record["activities"][0]
        self.assertEqual(signup["recipients"][0]["basis"], "assumed")
        self.assertIsNone(signup["security_measures"])
        self.assertIn("activity-signup: 'Fictional email provider' is assumed", record["gaps"])
        self.assertIn("activity-newsletter: categories of data subjects (Art. 30(1)(c)) not declared", record["gaps"])
        self.assertIn("activity-signup: time limits for erasure (Art. 30(1)(f)) not declared", record["gaps"])

    def test_dpia_inputs_show_signals_and_never_answer(self):
        screening = exports.dpia(self.declared)
        by_id = {item["id"]: item for item in screening["criteria"]}
        self.assertEqual(len(screening["criteria"]), 12)
        self.assertTrue(all(item["answer"] is None for item in screening["criteria"]))
        self.assertEqual(by_id["wp248-7"]["signals"], [{"activity": "activity-signup", "words": ["children"]}])
        self.assertIn("health", by_id["art35-3-b"]["signals"][0]["words"])
        self.assertEqual(by_id["wp248-5"]["signals"], [])  # large scale is never guessed from words
        self.assertEqual(by_id["art35-3-a"]["kind"], "law")
        self.assertEqual(by_id["wp248-1"]["kind"], "guidance")
        expected = sum(1 for item in screening["criteria"] if item["kind"] == "guidance" and item["signals"])
        self.assertGreater(expected, 0)
        self.assertEqual(screening["guidance_criteria_with_signals"], expected)

    def test_formats_are_safe_and_deterministic(self):
        record = exports.ropa(self.declared)
        markdown = exports.to_markdown(record)
        self.assertNotIn("<b>", markdown)
        self.assertIn("&lt;b&gt;newsletter&lt;/b&gt; second line", markdown)
        self.assertTrue(markdown.rstrip().endswith(LEGAL_NOTICE))
        rows = list(csv.reader(io.StringIO(exports.to_csv(record))))
        self.assertEqual(rows[2][2][:1], "'")  # a formula is kept as text
        data = declarations()
        data["scope"]["activities"][1]["purpose"] = "\tcmd|' /C calc'!A0"
        tab_declared = m.parse_record(m.RevalidationInput, json.dumps(data).encode())
        tab_rows = list(csv.reader(io.StringIO(exports.to_csv(exports.ropa(tab_declared)))))
        self.assertEqual(tab_rows[2][2][:2], "'\t")
        self.assertEqual(exports.to_markdown(exports.ropa(self.declared)), markdown)
        with self.assertRaises(ValueError):
            exports.to_csv(exports.dpia(self.declared))

    def test_cli_prints_or_writes_and_refuses_csv_for_dpia(self):
        with tempfile.TemporaryDirectory(prefix="eucg-export-") as folder:
            source = Path(folder) / "declarations.json"
            source.write_text(json.dumps(declarations()))
            code, out = cli("export", "dpia", "--input", source, "--format", "json")
            self.assertEqual((code, json.loads(out)["kind"]), (0, "dpia"))
            code, out = cli("export", "ropa", "--input", source, "--format", "csv", "--output", Path(folder) / "ropa.csv")
            self.assertEqual(code, 0)
            self.assertTrue((Path(folder) / "ropa.csv").read_text().startswith("status,activity"))
            self.assertEqual(cli("export", "dpia", "--input", source, "--format", "csv")[0], 2)


if __name__ == "__main__":
    unittest.main()
