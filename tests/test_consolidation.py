"""Newer consolidation notice: one fixed, registry-checked query per act target; offline here."""
import json
from pathlib import Path
import tempfile
import time
import unittest

from eu_compliance_guard import consolidation as c, models as m, revalidation as r, sources as s
from test_retrieval_workflow import CHANGED, PAGE, URL, real_target_payload
from test_sources import HTML, FakeResponse, FakeTransport

ROWS = (b'"celex","date"\n"02002L0058-20091219",2009-12-19\n"02002L0058-20060503",2006-05-03\n'
        b'"01995L0046-20180525",2018-05-25\n')
CSV_TYPE = [("Content-Type", "text/csv; charset=UTF-8")]
QUERY = c.query_url("32002L0058")


class ConsolidatedTransport(FakeTransport):
    """Picklable factory for the spawned helper: the act page and the consolidation query."""
    def __init__(self):
        super().__init__(responses={
            ("eur-lex.europa.eu", s.check_url(URL, s.OFFICIAL_HOSTS)[1]): lambda: FakeResponse(headers=HTML, body=CHANGED),
            ("publications.europa.eu", s.check_url(QUERY, s.OFFICIAL_HOSTS)[1]): lambda: FakeResponse(headers=CSV_TYPE, body=ROWS)})


class ConsolidationTests(unittest.TestCase):
    def test_the_query_is_fixed_registered_and_built_only_from_the_celex_number(self):
        host, target = s.check_url(QUERY, s.OFFICIAL_HOSTS)
        self.assertEqual(host, "publications.europa.eu")
        self.assertTrue(target.startswith("/webapi/rdf/sparql?query="))
        self.assertIn("format=text%2Fcsv", target)
        self.assertEqual(c.base_celex(s.celex_version("02016R0679-20160504")), "32016R0679")
        self.assertEqual(c.base_celex(s.celex_version("32016R0679")), "32016R0679")

    def test_only_this_acts_consolidations_count_and_the_newest_wins(self):
        self.assertEqual(c.latest(ROWS, "32002L0058"), ("02002L0058-20091219", "2009-12-19"))
        self.assertIsNone(c.latest(b'"celex","date"\n"01995L0046-20180525",2018-05-25\n', "32002L0058"))

    def test_csv_is_admitted_only_for_requests_that_ask_for_it(self):
        transport = FakeTransport(responses={("publications.europa.eu", s.check_url(QUERY, s.OFFICIAL_HOSTS)[1]):
                                             lambda: FakeResponse(headers=CSV_TYPE, body=ROWS)})
        deadline = time.monotonic() + 30
        allowed = s.fetch(s.TargetRequest("t", QUERY, media_types=c.CSV), transport, limit=s.MAX_RESPONSE_BYTES, deadline=deadline)
        self.assertEqual((allowed.failure, allowed.content), (None, ROWS))
        refused = s.fetch(s.TargetRequest("t", QUERY), transport, limit=s.MAX_RESPONSE_BYTES, deadline=deadline)
        self.assertEqual(refused.failure, "unsupported-media-type")

    def test_notes_name_a_newer_or_missing_answer_and_stay_quiet_when_current(self):
        payload = real_target_payload()
        payload["source_targets"][-1]["intended_identifier"] = "02002L0058-20060503"
        declared = m.RevalidationInput.model_validate(payload)
        found = c.requests(declared)
        self.assertEqual([item[2].target_id for item in found], ["target-real-consolidation"])

        def answer(**values):
            return [s.FetchResult(target_id="target-real-consolidation", requested_url=QUERY, started_at="x", ended_at="y", **values)]

        newer = c.notes(found, answer(status=200, content=ROWS))
        self.assertEqual(newer, ["Source target target-real: a newer consolidation exists (CELEX 02002L0058-20091219 "
                                 "of 2009-12-19) than the declared one of 2006-05-03. Review it and update the declaration."])
        self.assertIn("could not be checked (timeout)", c.notes(found, answer(failure="timeout"))[0])
        payload["source_targets"][-1]["intended_identifier"] = "02002L0058-20091219"
        current = c.requests(m.RevalidationInput.model_validate(payload))
        self.assertEqual(c.notes(current, answer(status=200, content=ROWS)), [])
        payload["source_targets"][-1]["intended_identifier"] = "32002L0058"
        base = c.requests(m.RevalidationInput.model_validate(payload))
        self.assertIn("declared as first published; the latest consolidation is CELEX 02002L0058-20091219",
                      c.notes(base, answer(status=200, content=ROWS))[0])

    def test_revalidate_with_consent_records_the_notice_as_a_review_gap_and_changes_no_declaration(self):
        with tempfile.TemporaryDirectory(prefix="eucg-consolidation-") as folder:
            root = Path(folder)
            root.chmod(0o700)
            fixture = Path(__file__).resolve().parents[1] / "fixtures/revalidation-synthetic"
            (root / "revalidation-synthetic").mkdir()
            for name in ("source.txt", "evidence.txt"):
                (root / "revalidation-synthetic" / name).write_bytes((fixture / name).read_bytes())
            (root / "revalidation-synthetic/real.html").write_bytes(PAGE)
            payload = real_target_payload()
            payload["source_targets"][-1]["intended_identifier"] = "02002L0058-20060503"
            path = root / "input.json"
            path.write_text(json.dumps(payload))
            before = path.read_bytes()
            bundle = r.run(path, root / "run-1", fetch_official=True, transport_factory=ConsolidatedTransport)
            self.assertIn("Source target target-real: a newer consolidation exists (CELEX 02002L0058-20091219 of 2009-12-19)"
                          " than the declared one of 2006-05-03. Review it and update the declaration.", bundle.gaps)
            self.assertEqual(path.read_bytes(), before)
            offline = r.run(path, root / "run-2")
            self.assertFalse([gap for gap in offline.gaps if "consolidation" in gap])


if __name__ == "__main__":
    unittest.main()
