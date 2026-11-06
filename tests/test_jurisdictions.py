"""Jurisdictions: the UK identifiers and version notes, and the registry's shape; no network."""
import unittest

from eu_compliance_guard import jurisdictions as j


class UkVersionTests(unittest.TestCase):
    def test_identifiers_and_urls(self):
        self.assertEqual(j.uk_version("ukpga/2018/12"),
                         {"jurisdiction": "UK", "id": "ukpga/2018/12", "consolidated": True, "date": None})
        self.assertEqual(j.uk_version(None, "https://www.legislation.gov.uk/uksi/2003/2426/2024-01-01/data.xht")["date"],
                         "2024-01-01")
        self.assertFalse(j.uk_version(None, "https://www.legislation.gov.uk/ukpga/2018/12/enacted/data.xht")["consolidated"])
        self.assertEqual(j.uk_version("http://www.legislation.gov.uk/id/eur/2016/679")["id"], "eur/2016/679")
        self.assertIsNone(j.uk_version(None, "https://example.invalid/ukpga/2018/12"))  # only the official host
        for bad in ("ukpga/18/12", "nonsense/2018/12", "ukpga/2018", "ukpga/2018/x", ""):
            self.assertIsNone(j.uk_version(bad), bad)

    def test_version_dispatches_by_jurisdiction(self):
        self.assertEqual(j.version("32016R0679")["jurisdiction"], "EU")
        self.assertEqual(j.version(None, "https://www.legislation.gov.uk/eur/2016/679/data.xht")["jurisdiction"], "UK")
        self.assertIn("latest revised text", j.version_note(j.uk_version("ukpga/2018/12")))
        self.assertIn("as on 2024-01-01", j.version_note(j.uk_version("uksi/2003/2426/2024-01-01")))
        self.assertIn("as first published", j.version_note(j.uk_version("ukpga/2018/12/enacted")))

    def test_registry(self):
        self.assertEqual([item.code for item in j.ALL], ["EU", "UK"])
        self.assertTrue(all(j.uk_version(key) for key in j.UK.known_acts))


if __name__ == "__main__":
    unittest.main()
