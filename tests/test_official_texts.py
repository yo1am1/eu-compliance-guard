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

    def test_search_finds_the_erasure_article(self):
        found = articles.suggest("users can delete their account and all personal data", self.acts, top=3)
        self.assertIn(("gdpr", "Article 17"), [(item["source"], item["article"]) for item in found])


if __name__ == "__main__":
    unittest.main()
