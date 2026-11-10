"""The article parser and citation guard on real official texts (see fixtures/official/README.md)."""
import gzip
import hashlib
from pathlib import Path
import unittest

from eu_compliance_guard import articles, citations

OFFICIAL = Path(__file__).resolve().parents[1] / "fixtures/official"
TEXTS = {  # file stem: (sha256 of the uncompressed bytes, media type)
    "gdpr-32016R0679": ("962539af03738bf552319ff4ce42d69e5f95a576307c4dfed7bf87e81b646b9d", "application/xhtml+xml"),
    "ai-act-32024R1689": ("8f0b656302f9864cc87e040c371f209a9d65ae1a6cecc25ca5eb737e872d721a", "application/xhtml+xml"),
    "eprivacy-02002L0058-20091219": ("c2924162f0a6faf98ed18dda78655a2b0ce8c4e80403e1b5db08e76f6915f502", "application/xhtml+xml"),
    "cra-32024R2847": ("fe0cca4a0caec50e7cf5a91432b94a19b211f86be8584fdba56372bdcea571ed", "application/xhtml+xml"),
    "eaa-32019L0882": ("f1047e0732b744f5e7bd0e01c69d1db54a461de693ab375aa5b39a0c212fa50d", "application/xhtml+xml"),
    "nis2-32022L2555": ("6ee66d5c419d9a056fb98d94083cacf9b818803bd6b416435718e0d4919cb589", "application/xhtml+xml"),
    "uk-gdpr-eur-2016-679": ("804885cb4134ee6bb1dc1f69658dfb306a1ad270115a1e13e719d13334963f44", "application/xhtml+xml"),
    "pecr-uksi-2003-2426": ("bf91b37ab3c956f7b3c54ae246e953c1f97971d324f2f7ed3db63ad692530d60", "application/xhtml+xml"),
    "dpa-2018-ukpga-2018-12": ("c24aea0190a491bc09f6945eaf465d6ea46b3e8910f1e20c1a685529431ac479", "application/xhtml+xml"),
}


def load(stem: str) -> dict[str, dict]:
    raw = gzip.decompress((OFFICIAL / f"{stem}.html.gz").read_bytes())
    digest, media_type = TEXTS[stem]
    assert hashlib.sha256(raw).hexdigest() == digest, stem
    return articles.parse(raw, media_type)


class OfficialTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acts = {"gdpr": load("gdpr-32016R0679"), "ai-act": load("ai-act-32024R1689"),
                    "eprivacy": load("eprivacy-02002L0058-20091219")}

    def test_every_article_is_found_once_in_order_with_a_title_and_text(self):
        expected = {"gdpr": [f"Article {n}" for n in range(1, 100)],
                    "ai-act": [f"Article {n}" for n in range(1, 114)]}
        for act, keys in expected.items():
            self.assertEqual(list(self.acts[act]), keys, act)
        eprivacy = list(self.acts["eprivacy"])
        self.assertEqual(len(eprivacy), 23)
        self.assertIn("Article 15a", eprivacy)
        for act, parsed in self.acts.items():
            for key, item in parsed.items():
                self.assertTrue(item["title"].strip() and item["text"].strip(), (act, key))

    def test_known_titles_and_openings(self):
        self.assertEqual(self.acts["gdpr"]["Article 17"]["title"], "Right to erasure (‘right to be forgotten’)")
        self.assertTrue(self.acts["gdpr"]["Article 5"]["text"].startswith("1. Personal data shall be:"))
        self.assertEqual(self.acts["ai-act"]["Article 5"]["title"], "Prohibited AI practices")
        self.assertEqual(self.acts["ai-act"]["Article 50"]["title"],
                         "Transparency obligations for providers and deployers of certain AI systems")
        self.assertEqual(self.acts["eprivacy"]["Article 5"]["title"], "Confidentiality of the communications")
        # The footnotes of a consolidated page are not text of its last article.
        self.assertEqual(self.acts["eprivacy"]["Article 21"]["text"], "This Directive is addressed to the Member States.")

    def test_real_quotations_and_citations(self):
        text = ('Article 17 gives "the right to obtain from the controller the erasure of personal data concerning him or her '
                'without undue delay". Under Article 5, storing information is "only allowed on condition that the subscriber '
                'or user concerned has given his or her consent". Article 6 says "the right to obtain from the controller the '
                'erasure of personal data". Article 200 does not exist.')
        report = citations.check(text, self.acts)
        self.assertEqual([(item["article"], item["ok"]) for item in report["citations"]],
                         [("Article 17", True), ("Article 5", True), ("Article 6", True), ("Article 200", False)])
        self.assertEqual([(item["found_in"], item["ok"]) for item in report["quotations"]],
                         [(["gdpr Article 17"], True), (["eprivacy Article 5"], True), (["gdpr Article 17"], False)])

    def test_a_citation_naming_its_act_is_checked_in_that_act_only(self):
        from types import SimpleNamespace as Target
        names = citations.act_names([
            Target(id="gdpr", intended_identifier="32016R0679", intended_url=None),
            Target(id="ai-act", intended_identifier=None, intended_url="https://publications.europa.eu/resource/celex/32024R1689"),
            Target(id="eprivacy", intended_identifier="02002L0058-20091219", intended_url=None)])
        text = ('Article 5(3) of the ePrivacy Directive says "only allowed on condition that the subscriber or user concerned '
                'has given his or her consent". Article 99 of the AI Act and Article 99 of Regulation (EU) 2016/679 differ. '
                'Article 5 of the DSA applies. Article 17 GDPR: "the right to obtain from the controller the erasure".')
        report = citations.check(text, self.acts, names)
        self.assertEqual([(item["article"], item["act"], item["ok"]) for item in report["citations"]],
                         [("Article 5", "eprivacy", True), ("Article 99", "ai-act", True), ("Article 99", "gdpr", True),
                          ("Article 5", "DSA (not declared)", False), ("Article 17", "gdpr", True)])
        self.assertEqual([item["ok"] for item in report["quotations"]], [True, True])
        self.assertIn("NOT CHECKED, the latest run retained no text of DSA (not declared)", citations.format_check(report))
        wrong = citations.check('Article 17 of the AI Act says "the right to obtain from the controller the erasure".',
                                self.acts, names)
        self.assertEqual([item["ok"] for item in wrong["quotations"]], [False])

    def test_a_citation_of_an_unrecognised_act_is_not_checked_against_another(self):
        from types import SimpleNamespace as Target
        names = citations.act_names([Target(id="gdpr", intended_identifier="32016R0679", intended_url=None)])
        text = ("Article 9 of the Product Liability Directive applies. Article 4 of Directive (EU) 2019/770 too. "
                "Article 17 of this Regulation gives erasure. Article 6 of the GDPR is the basis.")
        report = citations.check(text, self.acts, names)
        self.assertEqual([(item["article"], item["act"], item["ok"]) for item in report["citations"]],
                         [("Article 9", citations.UNRECOGNISED, False), ("Article 4", citations.UNRECOGNISED, False),
                          ("Article 17", None, True), ("Article 6", "gdpr", True)])
        self.assertIn("Article 9: NOT CHECKED, it cites an act the tool does not recognise", citations.format_check(report))
        self.assertFalse(report["ok"])

    def test_citations_in_brackets_markdown_ranges_and_without_a_space_are_checked(self):
        text = ("Erasure (Article 200 GDPR) is covered by **Article 201**, Art.202(1)(a), `Article 203`, [Art. 17] "
                "and Articles 5–204. Sections 12-205 differ.")
        report = citations.check(text, self.acts)
        self.assertEqual([(item["article"], item["ok"]) for item in report["citations"]],
                         [("Article 200", False), ("Article 201", False), ("Article 202", False), ("Article 203", False),
                          ("Article 17", True), ("Article 5", True), ("Article 204", False), ("Section 12", False),
                          ("Section 205", False)])
        self.assertFalse(report["ok"])
        # A hyphen after a single citation is no range, and an act number is still no provision.
        self.assertEqual(citations._citations("Article 5-compliant; Regulation (EU) 2016/679; Art. 6(1)(f)"),
                         [(0, "Article 5"), (47, "Article 6")])

    def test_the_same_act_is_not_checked_because_it_may_be_an_unknown_one(self):
        report = citations.check("The Product Liability Directive covers defects. Article 6 of the same Directive defines them.",
                                 self.acts, {"gdpr": [["gdpr"]]})
        self.assertEqual([(item["article"], item["act"], item["ok"]) for item in report["citations"]],
                         [("Article 6", citations.UNRECOGNISED, False)])
        self.assertFalse(report["ok"])

    def test_search_finds_the_erasure_article(self):
        found = articles.suggest("users can delete their account and all personal data", self.acts, top=3)
        self.assertIn(("gdpr", "Article 17"), [(item["source"], item["article"]) for item in found])


class TimelineTests(unittest.TestCase):
    """Application dates quoted from the real final provisions, against an assessment date."""

    @classmethod
    def setUpClass(cls):
        cls.acts = {"ai-act": load("ai-act-32024R1689"), "cra": load("cra-32024R2847"), "eaa": load("eaa-32019L0882"),
                    "nis2": load("nis2-32022L2555"), "gdpr": load("gdpr-32016R0679")}

    def test_new_acts_parse_completely(self):
        self.assertEqual([len(self.acts[act]) for act in ("cra", "eaa", "nis2")], [71, 35, 46])
        self.assertEqual(self.acts["cra"]["Article 14"]["title"], "Reporting obligations of manufacturers")

    def test_dates_are_quoted_and_compared_with_the_assessment_date(self):
        from eu_compliance_guard import timeline
        entries = timeline.timeline(self.acts, "2026-11-06")
        final = {(e["date"], e["act"], e["kind"], e["status"]) for e in entries
                 if e["article"] in ("Article 113", "Article 71", "Article 31", "Article 41", "Article 99")}
        self.assertLessEqual({("2025-02-02", "ai-act", "applies", "reached"), ("2026-08-02", "ai-act", "applies", "reached"),
                              ("2027-08-02", "ai-act", "applies", "upcoming"), ("2026-06-11", "cra", "applies", "reached"),
                              ("2026-09-11", "cra", "applies", "reached"), ("2027-12-11", "cra", "applies", "upcoming"),
                              ("2022-06-28", "eaa", "transposition", "reached"), ("2025-06-28", "eaa", "applies", "reached"),
                              ("2024-10-17", "nis2", "transposition", "reached"), ("2018-05-25", "gdpr", "applies", "reached")},
                             final)
        for entry in entries:  # every quotation is the act's own text
            self.assertIn(entry["quote"].rstrip("…"), " ".join(self.acts[entry["act"]][entry["article"]]["text"].split()))
        self.assertEqual(entries, sorted(entries, key=lambda e: (e["date"], e["act"], e["article"], e["quote"])))
        self.assertEqual(timeline.timeline(self.acts, "2026-11-06"), entries)  # deterministic
        self.assertIsNone(timeline.timeline(self.acts)[0]["status"])

    def test_dates_are_read_without_guessing(self):
        from eu_compliance_guard import timeline
        self.assertEqual(timeline._dates("shall apply from 2 August 2026 and from August 3, 2027"), ["2026-08-02", "2027-08-03"])
        self.assertEqual(timeline._dates("shall apply from 31 February 2026 or 2 Augustus 2026 or 2 August 26"), [])
        self.assertIsNone(timeline._kind("The Commission shall report by 2 August 2028."))
        # The date of a cited act is not an application date; "as of" is.
        self.assertEqual(timeline._dates("Directive 2002/21/EC of 7 March 2002 shall apply."), [])
        self.assertEqual(timeline._dates("It shall apply as of 2 August 2026."), ["2026-08-02"])
        # A non-ASCII digit is not a day and never crashes the timeline.
        self.assertEqual(timeline._dates("shall apply from ² August 2026 or 2 August ²⁰²⁶"), [])
        self.assertEqual(timeline._kind("Member States shall bring into force the provisions"), "transposition")

    def test_eprivacy_dates_are_its_own(self):
        from eu_compliance_guard import timeline
        entries = timeline.timeline({"eprivacy": load("eprivacy-02002L0058-20091219")}, "2026-11-06")
        self.assertEqual([(e["date"], e["article"], e["kind"], e["status"]) for e in entries],
                         [("2003-10-31", "Article 17", "transposition", "reached")])

    def test_a_uk_commencement_date_with_an_ordinal_day_is_read(self):
        from eu_compliance_guard import timeline
        entries = timeline.timeline({"pecr": load("pecr-uksi-2003-2426")}, "2026-11-06")
        self.assertIn(("2003-12-11", "Regulation 1", "in force", "reached"),
                      [(e["date"], e["article"], e["kind"], e["status"]) for e in entries])
        self.assertEqual(timeline._dates("come into force on 1st May 2021, 2nd May 2021 or May 3rd, 2021"),
                         ["2021-05-01", "2021-05-02", "2021-05-03"])
        self.assertEqual(timeline._dates("come into force on the 4th of May 2021 or 32nd May 2021 or th May 2021"), [])

    def test_status_boundary_and_text_output(self):
        from eu_compliance_guard import timeline
        acts = {"cra": self.acts["cra"]}
        on_the_day = {e["date"]: e["status"] for e in timeline.timeline(acts, "2026-09-11")}
        self.assertEqual((on_the_day["2026-09-11"], on_the_day["2027-12-11"]), ("reached", "upcoming"))
        text = timeline.format_timeline(timeline.timeline(acts, "2026-09-11"), "2026-09-11", ["cra"])
        self.assertIn("- 2026-09-11 (reached) · cra Article 71 · applies", text)
        self.assertIn("- 2027-12-11 (upcoming) · cra Article 71 · applies", text)
        self.assertIn("not reflected unless that version includes it", text)
        self.assertTrue(text.endswith("a reviewer decides."))
        self.assertEqual(timeline.format_timeline([], None, ["cra"]),
                         "No dated application, entry-into-force or transposition clause in the retained text of cra.")


class UkOfficialTextTests(unittest.TestCase):
    """legislation.gov.uk XHTML: sections, regulations and articles, with amendment notes left out."""

    @classmethod
    def setUpClass(cls):
        cls.acts = {"uk-gdpr": load("uk-gdpr-eur-2016-679"), "pecr": load("pecr-uksi-2003-2426"),
                    "dpa-2018": load("dpa-2018-ukpga-2018-12")}

    def test_provisions_are_found_with_their_own_titles(self):
        pecr, dpa, gdpr = self.acts["pecr"], self.acts["dpa-2018"], self.acts["uk-gdpr"]
        self.assertEqual((len(pecr), list(pecr)[0], list(pecr)[-1]), (50, "Regulation 1", "Regulation 37"))
        self.assertEqual(pecr["Regulation 6"]["title"], "Storing information in the terminal equipment of a subscriber or user")
        self.assertTrue(pecr["Regulation 6"]["text"].startswith("—(1) Subject to Schedule A1, a person must not store"))
        self.assertEqual((len(dpa), list(dpa)[0], list(dpa)[-1]), (261, "Section 1", "Section 215"))
        # Sections 74AA and 74AB are provisions of their own, not a second and third section 74A.
        self.assertEqual([key for key in dpa if key.startswith("Section 74")],
                         ["Section 74", "Section 74A", "Section 74AA", "Section 74AB", "Section 74B"])
        self.assertTrue(dpa["Section 74AA"]["title"] and dpa["Section 74AA"]["title"] != dpa["Section 74A"]["title"])
        self.assertIn("Article 8ZA", gdpr)
        # A prospective section without an anchor (164B) must not shift the titles after it.
        self.assertEqual(dpa["Section 165"]["title"], "Complaints by data subjects to the Commission")
        self.assertEqual(dpa["Section 170"]["title"], "Unlawful obtaining etc of personal data")
        self.assertTrue(dpa["Section 170"]["text"].startswith("(1) It is an offence for a person knowingly or recklessly"))
        self.assertEqual(len(gdpr), 120)
        self.assertIn("Article 22A", gdpr)
        self.assertEqual(gdpr["Article 17"]["title"], "Right to erasure (‘right to be forgotten’)")
        untitled = []
        for act, parsed in self.acts.items():
            for key, item in parsed.items():
                self.assertTrue(item["text"].strip(), (act, key))
                self.assertNotIn("Textual Amendments", item["text"], (act, key))
                if not item["title"].strip():
                    untitled.append((act, key))
        self.assertEqual(untitled, [("pecr", "Regulation 29A")])  # its title element is empty in the source
        # Signatures and the "SCHEDULES" heading follow the last provision; they are not its text.
        self.assertTrue(pecr["Regulation 37"]["text"].endswith("the day on which that report is published."))
        self.assertEqual(dpa["Section 215"]["text"], "This Act may be cited as the Data Protection Act 2018.")
        self.assertNotIn("Done at Brussels", gdpr["Article 99"]["text"])

    def test_uk_citations_are_checked_in_the_act_they_name(self):
        from types import SimpleNamespace as Target
        names = citations.act_names([
            Target(id="uk-gdpr", intended_identifier=None, intended_url="https://www.legislation.gov.uk/eur/2016/679/data.htm"),
            Target(id="pecr", intended_identifier="uksi/2003/2426", intended_url=None),
            Target(id="dpa-2018", intended_identifier="ukpga/2018/12", intended_url=None)])
        text = ('Regulation 6 of PECR says "a person must not store information, or gain access to information stored". '
                'Section 170 of the Data Protection Act 2018 makes it an offence. Article 17 UK GDPR gives a right to '
                'erasure; s. 999 of the DPA 2018 does not exist, and Article 5 of the GDPR (the EU one) is not retained '
                'here. Regulation (EU) 2016/679 is an act number, not a provision.')
        report = citations.check(text, self.acts, names)
        self.assertEqual([(item["article"], item["act"], item["ok"]) for item in report["citations"]],
                         [("Regulation 6", "pecr", True), ("Section 170", "dpa-2018", True), ("Article 17", "uk-gdpr", True),
                          ("Section 999", "dpa-2018", False), ("Article 5", "GDPR (not declared)", False)])
        self.assertEqual([item["ok"] for item in report["quotations"]], [True])


if __name__ == "__main__":
    unittest.main()
