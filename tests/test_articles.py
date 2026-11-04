"""Article segmentation and text-search suggestions on synthetic snippets."""

import unittest

from eu_compliance_guard import articles as a

XHTML = """<html><body>
<p class="oj-ti-art">Article 9</p><p class="oj-sti-art">Fictional special categories</p>
<div><p class="oj-normal">1. Fictional health data &amp; biometrics shall not be processed.</p></div>
<p class="oj-ti-art">Article 17</p><p class="oj-sti-art">Fictional erasure</p>
<p class="oj-normal">The fictional subject may obtain erasure of data.</p>
<p class="ti-art">Article 17</p><p class="sti-art">Duplicate ignored</p>
</body></html>""".encode()


class ArticleTests(unittest.TestCase):
    def test_xhtml_marks_number_title_and_text(self):
        parsed = a.parse(XHTML, "application/xhtml+xml")
        self.assertEqual(list(parsed), ["Article 9", "Article 17"])
        self.assertEqual(parsed["Article 9"]["title"], "Fictional special categories")
        self.assertEqual(parsed["Article 9"]["text"], "1. Fictional health data & biometrics shall not be processed.")
        self.assertEqual(parsed["Article 17"]["title"], "Fictional erasure")

    def test_plain_text_and_unsupported_formats(self):
        parsed = a.parse(b"Preamble\nArticle 2a\nFictional title\nBody one.\nBody two.\n", "text/plain")
        self.assertEqual(parsed, {"Article 2a": {"title": "Fictional title", "text": "Body one. Body two."}})
        self.assertEqual(a.parse(b"%PDF-1.7", "application/pdf"), {})
        self.assertEqual(a.parse(b"\xff\xfe", "text/plain"), {})

    def test_locators_normalise_to_article_keys(self):
        self.assertEqual(a.article_key("Article 9(2)(a)"), "Article 9")
        self.assertEqual(a.article_key("Art. 17"), "Article 17")
        self.assertEqual(a.article_key("article 8"), "Article 8")
        self.assertIsNone(a.article_key("Recital 38"))

    def test_suggestions_bridge_engineering_words_to_legal_vocabulary(self):
        catalogue = {"fixture": a.parse(XHTML, "application/xhtml+xml")}
        self.assertEqual(a.suggest("Users can delete their account", catalogue)[0]["article"], "Article 17")
        self.assertEqual(a.suggest("Weight goes to the model", catalogue)[0]["article"], "Article 9")
        self.assertEqual(a.suggest("zzz qqq", catalogue), [])
        self.assertEqual(a.suggest("anything", {}), [])


if __name__ == "__main__":
    unittest.main()
