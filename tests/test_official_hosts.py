"""The retrieval host registry is documented and limited to EU institution domains; no network."""
from pathlib import Path
import unittest

from eu_compliance_guard.sources import HTTPS_UPGRADE_HOSTS, OFFICIAL_HOSTS

DOC = Path(__file__).resolve().parents[1] / "docs/official-hosts.md"


def documented() -> dict[str, list[str]]:
    """Rows of the first table: host -> [operator, purpose]."""
    text = DOC.read_text(encoding="utf-8")
    table = text.split("| Host | Operator | Purpose |", 1)[1].split("\n\n", 1)[0]
    rows = {}
    for line in table.splitlines()[2:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows[cells[0].strip("`")] = cells[1:]
    return rows


class OfficialHostTests(unittest.TestCase):
    def test_every_host_is_an_eu_institution_domain(self):
        for host in OFFICIAL_HOSTS:
            self.assertTrue(host.endswith(".europa.eu"), host)
            self.assertEqual(host, host.lower())
        self.assertLessEqual(HTTPS_UPGRADE_HOSTS, OFFICIAL_HOSTS)

    def test_registry_and_documentation_match_with_operator_and_purpose(self):
        rows = documented()
        self.assertEqual(set(rows), set(OFFICIAL_HOSTS))
        for host, (operator, purpose) in rows.items():
            self.assertTrue(operator and purpose, host)

    def test_reachability_is_recorded_for_every_host(self):
        text = DOC.read_text(encoding="utf-8").split("## Reachability", 1)[1]
        for host in OFFICIAL_HOSTS:
            self.assertIn(f"| `{host}` |", text)


if __name__ == "__main__":
    unittest.main()
