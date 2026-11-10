"""Law in force: base and consolidated CELEX numbers are told apart, offline, without a regex."""
import json
from pathlib import Path
import tempfile
import unittest

from eu_compliance_guard import authoring as a, jurisdictions as j, sources as s, view as v

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/revalidation-synthetic.json"


class CelexTests(unittest.TestCase):
    def test_base_and_consolidated_numbers_from_identifiers_and_urls(self):
        self.assertEqual(s.celex_version("32016R0679"), {"celex": "32016R0679", "consolidated": False, "date": None})
        self.assertEqual(s.celex_version("02002L0058-20091219"),
                         {"celex": "02002L0058-20091219", "consolidated": True, "date": "2009-12-19"})
        self.assertEqual(s.celex_version(None, "https://publications.europa.eu/resource/celex/02016R0679-20160504?language=en")["date"],
                         "2016-05-04")
        self.assertFalse(s.celex_version(None, "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679")["consolidated"])
        for value in ("FICTIONAL-EU-EXAMPLE", "", "3201", "32016R", "x2016R0679", "32016R0679-2016", "3２016R0679"):
            self.assertIsNone(s.celex_version(value), value)

    def test_check_warns_on_a_base_celex_act_and_reports_the_version(self):
        payload = json.loads(FIXTURE.read_bytes())
        target = dict(payload["source_targets"][0], id="target-gdpr", intended_type="eu_act", intended_identifier="32016R0679",
                      intended_url="https://publications.europa.eu/resource/celex/32016R0679", language="en")
        consolidated = dict(target, id="target-eprivacy", intended_identifier="02002L0058-20091219",
                            intended_url="https://publications.europa.eu/resource/celex/02002L0058-20091219")
        payload["source_targets"] += [target, consolidated]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "declarations.json"
            path.write_text(json.dumps(payload))
            report = a.check(path)
        warnings = [item for item in report["warnings"] if "base CELEX" in item["problem"]]
        self.assertEqual([item["at"] for item in warnings], ["source_targets[1]"])
        versions = {item["id"]: item.get("version") for item in report["targets"]}
        self.assertEqual((versions["target-gdpr"], versions["target-eprivacy"]), ("as first published", "consolidated 2009-12-19"))

    def test_report_excerpts_name_the_version_they_come_from(self):
        self.assertIn("consolidated version of 2009-12-19", j.version_note(s.celex_version("02002L0058-20091219")))
        self.assertIn("not the law in force", j.version_note(s.celex_version("32016R0679")))
        self.assertIn("check the official consolidated version", j.version_note(None))


if __name__ == "__main__":
    unittest.main()
