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

    def test_unmarked_html_uses_paragraphs_that_read_article_n(self):
        page = (b"<html><body><p>See Article 4 of another act.</p><p>Article 5</p><p>Fictional confidentiality</p>"
                b"<p>1. Fictional storing of information in terminal equipment.</p><p></p><p>Article 6</p>"
                b"<p>1. Fictional traffic data.</p></body></html>")
        parsed = a.parse(page, "text/html")
        self.assertEqual(list(parsed), ["Article 5", "Article 6"])
        self.assertEqual(parsed["Article 5"], {"title": "Fictional confidentiality",
                                               "text": "1. Fictional storing of information in terminal equipment."})
        self.assertEqual(parsed["Article 6"]["title"], "")

    def test_plain_text_references_do_not_open_articles(self):
        parsed = a.parse(b"Article 5\nFictional principles\nArticle 6(1) applies here too.\nMore text.\n"
                         b"Article 6\nFictional lawfulness\nBody.\n", "text/plain")
        self.assertEqual(parsed["Article 5"]["text"], "Article 6(1) applies here too. More text.")
        self.assertEqual(parsed["Article 6"], {"title": "Fictional lawfulness", "text": "Body."})

    def test_annexes_and_repeated_numbers_stay_out_of_articles(self):
        page = (b'<html><body><p class="oj-ti-art">Article 113</p><p class="oj-sti-art">Entry into force</p>'
                b'<p>It enters into force.</p><p>Done at Brussels.</p><p class="oj-doc-ti">ANNEX III</p>'
                b'<p>Biometric categorisation systems.</p></body></html>')
        self.assertEqual(a.parse(page, "text/html")["Article 113"]["text"], "It enters into force.")
        text = (b"Article 1\nSubject\nText. Annex III shall apply.\nArticle 2\nScope\nText2.\nANNEX I\n"
                b"Correlation table\nArticle 1\nArticle 1 of Directive 95/46\n")
        parsed = a.parse(text, "text/plain")
        self.assertEqual(parsed["Article 1"]["text"], "Text. Annex III shall apply.")
        self.assertEqual(parsed["Article 2"]["text"], "Text2.")

    def test_inflected_words_reach_the_legal_vocabulary(self):
        catalogue = {"fixture": a.parse(XHTML, "application/xhtml+xml")}
        self.assertEqual(a.suggest("Accounts are deleted on request", catalogue)[0]["article"], "Article 17")

    def test_an_index_searches_many_statements_quickly(self):
        import time
        words = " ".join(f"word{n}" for n in range(1500))
        catalogue = {f"act{n}": {f"Article {k}": {"title": f"Title {k}", "text": words} for k in range(100)} for n in range(5)}
        catalogue["act0"]["Article 7"]["text"] += " erasure"
        index = a.ArticleIndex(catalogue)
        started = time.monotonic()
        for _ in range(200):
            found = index.suggest("Users can delete their account", top=1)
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual(found[0]["article"], "Article 7")

    def test_plain_text_and_unsupported_formats(self):
        parsed = a.parse(b"Preamble\nArticle 2a\nFictional title\nBody one.\nBody two.\n", "text/plain")
        self.assertEqual(parsed, {"Article 2a": {"title": "Fictional title", "text": "Body one. Body two."}})
        self.assertEqual(a.parse(b"%PDF-1.7", "application/pdf"), {})
        self.assertEqual(a.parse(b"\xff\xfe", "text/plain"), {})

    def test_a_utf8_byte_order_mark_does_not_hide_the_first_article(self):
        text = "Article 1\nFictional subject-matter\nBody one.\nArticle 2\nFictional erasure\nBody two.\n".encode()
        parsed = a.parse(b"\xef\xbb\xbf" + text, "text/plain")
        self.assertEqual(parsed, a.parse(text, "text/plain"))
        self.assertEqual(parsed["Article 1"], {"title": "Fictional subject-matter", "text": "Body one."})

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
