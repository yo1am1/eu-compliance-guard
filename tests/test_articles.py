"""Article segmentation and text-search suggestions on synthetic snippets."""

import tracemalloc
import unittest
from unittest import mock

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

    def test_media_types_match_without_regard_to_case(self):
        text = b"Article 1\nFictional title\nBody.\n"
        self.assertEqual(a.parse(text, "TEXT/PLAIN"), {"Article 1": {"title": "Fictional title", "text": "Body."}})
        self.assertEqual(a.parse(XHTML, "Application/XHTML+XML"), a.parse(XHTML, "application/xhtml+xml"))
        self.assertEqual(list(a.parse(b"<p>Article 1</p><p>Fictional title</p><p>Body.</p>", "Text/HTML")), ["Article 1"])

    def test_plain_text_untitled_article_keeps_its_first_paragraph_as_text(self):
        parsed = a.parse(b"Article 6\n\n1. Member States shall provide fictional fairness.\n2. It shall be for the controller.\n"
                         b"Article 7\n" + b"Fictional words " * 20 + b"\nArticle 8\nFictional title\nBody.\n", "text/plain")
        self.assertEqual(parsed["Article 6"], {"title": "", "text": "1. Member States shall provide fictional fairness. "
                                                                      "2. It shall be for the controller."})
        self.assertEqual(parsed["Article 7"]["title"], "")
        self.assertEqual(parsed["Article 8"], {"title": "Fictional title", "text": "Body."})

    def test_scripts_styles_and_page_chrome_are_not_article_text(self):
        page = (b'<!doctype html><html><head><style>p{color:red}</style></head><body>'
                b'<p class="oj-ti-art">Article 1</p><p class="oj-sti-art">Fictional title</p><p class="oj-normal">Fictional body.</p>'
                b"<script>track('cookie consent');</script><style>.x{margin:0}</style><script src='x.js'/>"
                b"<noscript><p>Enable JavaScript</p></noscript><template><p>Fictional cookie banner</p></template>"
                b'<p class="oj-ti-art">Article 2</p><p class="oj-sti-art">Last</p><p class="oj-normal">Last body.</p>'
                b'<nav><a href="#">Cookies</a></nav><footer><a href="#">Legal notice</a> | <a href="#">Cookies policy</a></footer>'
                b'</body></html>')
        parsed = a.parse(page, "text/html")
        self.assertEqual(parsed, {"Article 1": {"title": "Fictional title", "text": "Fictional body."},
                                  "Article 2": {"title": "Last", "text": "Last body."}})
        self.assertEqual(a.suggest("Cookie tracking banner", {"page": parsed}), [])

    def test_an_inserted_annex_heading_closes_the_article(self):
        text = b"Article 1\nFictional title\nBody one.\nANNEX IIIa\nFictional list.\n"
        self.assertEqual(a.parse(text, "text/plain")["Article 1"]["text"], "Body one.")
        page = b"<p>Article 1</p><p>Fictional title</p><p>Body one. Annex IIIa applies.</p><p>ANNEX IIIa</p><p>List.</p>"
        self.assertEqual(a.parse(page, "text/html")["Article 1"]["text"], "Body one. Annex IIIa applies.")
        self.assertEqual(a.parse(b"Article 1\nT\nBody.\nANNEX 2b\nList.\n", "text/plain")["Article 1"]["text"], "Body.")

    def test_chapter_and_section_headings_belong_to_no_article(self):
        page = (b'<p class="oj-ti-art">Article 2</p><p class="oj-sti-art">Fictional material scope</p>'
                b'<p class="oj-normal">This fictional Regulation applies to synthetic data.</p>'
                b'<p class="oj-ti-section-1">CHAPTER III</p><p class="oj-ti-section-2">Rights of the fictional data subject</p>'
                b'<p class="oj-ti-section-1">Section 3</p><p class="oj-ti-section-2">Rectification and erasure</p>'
                b'<p class="oj-ti-art">Article 10a</p><p class="oj-sti-art">Fictional erasure</p>'
                b'<p class="oj-normal">Erase on request.</p><table><tr><td>Part 2</td><td>Fictional row.</td></tr></table>'
                b'<p class="oj-ti-section-1">CHAPTER XI</p><p class="oj-ti-section-2">Final provisions</p>')
        parsed = a.parse(page, "application/xhtml+xml")
        self.assertEqual(parsed["Article 2"]["text"], "This fictional Regulation applies to synthetic data.")
        self.assertEqual(parsed["Article 10a"]["text"], "Erase on request. Part 2 Fictional row.")
        self.assertEqual([item["article"] for item in a.suggest("Rectification and erasure workflow", {"act": parsed})],
                         ["Article 10a"])
        consolidated = (b'<p>Article 1</p><p>Fictional subject</p><p>Body one. Chapter III applies.</p>'
                        b'<p class="title-division-1">CHAPTER II</p><p class="title-division-2">Fictional rights</p>'
                        b'<p>Article 2</p><p>Fictional erasure</p><p>Body two.</p>')
        self.assertEqual([item["text"] for item in a.parse(consolidated, "text/html").values()],
                         ["Body one. Chapter III applies.", "Body two."])
        text = (b"Article 1\nFictional scope\nBody one.\nCHAPTER II\nRIGHTS\nSection 1\nTransparency\nArticle 2\n"
                b"Fictional erasure\nBody two.\nTITLE IIIa\nFictional title\nPART 2\nFictional part\nArticle 3\nT\nBody three.\n")
        self.assertEqual([item["text"] for item in a.parse(text, "text/plain").values()], ["Body one.", "Body two.", "Body three."])

    def test_a_quoted_inserted_article_stays_in_the_amending_article(self):
        page = ('<p class="oj-ti-art">Article 4</p><p class="oj-sti-art">Fictional amendments</p>'
                '<p class="oj-normal">Directive 2098/1 is amended as follows:</p><p class="oj-normal">(1) the following'
                ' Article is inserted:</p><p class="oj-ti-art">‘Article 6a</p><p class="oj-sti-art">Fictional inserted'
                ' requirements</p><p class="oj-normal">Inserted text.’;</p><p class="oj-normal">(2) fictional third'
                ' amendment on erasure.</p><p class="oj-ti-art">Article 5</p><p class="oj-sti-art">Fictional transposition'
                '</p><p class="oj-normal">Transpose.</p>').encode()
        parsed = a.parse(page, "application/xhtml+xml")
        self.assertEqual(list(parsed), ["Article 4", "Article 5"])
        self.assertEqual(parsed["Article 4"], {
            "title": "Fictional amendments",
            "text": "Directive 2098/1 is amended as follows: (1) the following Article is inserted: ‘Article 6a "
                    "Fictional inserted requirements Inserted text.’; (2) fictional third amendment on erasure."})
        self.assertEqual(parsed["Article 5"], {"title": "Fictional transposition", "text": "Transpose."})

    def test_a_quoted_annex_or_chapter_stays_in_the_amending_article(self):
        page = ('<p class="oj-ti-art">Article 1</p><p class="oj-sti-art">Fictional amendments</p><p>(1) the following'
                ' Annex is added:</p><p class="oj-doc-ti">‘ANNEX IIIa</p><p>Fictional list.’;</p><p class="oj-ti-section-1">'
                '‘CHAPTER IIIa</p><p>Fictional chapter.’;</p><p>(2) Article 9 is deleted.</p><p class="oj-ti-art">Article 2'
                '</p><p class="oj-sti-art">Fictional transposition</p><p>Transpose.</p><p class="oj-ti-art">Article 3</p>'
                '<p class="oj-sti-art">Fictional entry into force</p><p>Enter.</p>').encode()
        parsed = a.parse(page, "application/xhtml+xml")
        self.assertEqual(list(parsed), ["Article 1", "Article 2", "Article 3"])
        self.assertEqual(parsed["Article 1"]["text"], "(1) the following Annex is added: ‘ANNEX IIIa Fictional list.’; "
                                                      "‘CHAPTER IIIa Fictional chapter.’; (2) Article 9 is deleted.")
        text = "Article 1\nT\n(1) inserted:\n‘CHAPTER IIa\nX.’;\n“ANNEX IIIa\nY.”;\n(2) Z.\n".encode()
        self.assertEqual(a.parse(text, "text/plain")["Article 1"]["text"], "(1) inserted: ‘CHAPTER IIa X.’; “ANNEX IIIa Y.”; (2) Z.")

    def test_correlation_tables_after_the_enacting_terms_open_no_articles(self):
        only = {"Article 1": {"title": "Fictional subject", "text": "Body."}}
        page = (b"<p>Article 1</p><p>Fictional subject</p><p>Body.</p><p>Done at Fictionville.</p><p>ANNEX II</p>"
                b"<p>CORRELATION TABLE</p><table><tr><td>Directive 2097/1</td><td>This Directive</td></tr>"
                b"<tr><td>Article 1</td><td>Article 1</td></tr><tr><td>Article 12</td><td>-</td></tr></table>")
        self.assertEqual(a.parse(page, "text/html"), only)
        self.assertEqual(a.parse(b"Article 1\nFictional subject\nBody.\nANNEX II\nCorrelation table\nArticle 12\n-\n",
                                 "text/plain"), only)
        marked = (b'<p class="oj-ti-art">Article 1</p><p class="oj-sti-art">Fictional subject</p><p>Body.</p>'
                  b'<p class="oj-doc-ti">ANNEX</p><p>Fictional annexed agreement</p><p class="oj-ti-art">Article 12</p><p>X.</p>')
        self.assertEqual(a.parse(marked, "application/xhtml+xml"), only)

    def test_a_stray_end_marker_inside_an_article_keeps_the_later_articles(self):
        text = b"Article 1\nT1\n(1) the following Annex is added:\nANNEX IIIa\nList.\nArticle 2\nT2\nB2.\nArticle 3\nT3\nB3.\n"
        self.assertEqual(list(a.parse(text, "text/plain")), ["Article 1", "Article 2", "Article 3"])
        page = (b'<p class="oj-ti-art">Article 1</p><p class="oj-sti-art">T1</p><p>B1.</p><p class="oj-doc-ti">ANNEX IIIa'
                b'</p><p>List.</p><p class="oj-ti-art">Article 1a</p><p class="oj-sti-art">T1a</p><p>B1a.</p>'
                b'<p class="oj-ti-art">Article 2</p><p class="oj-sti-art">T2</p><p>B2.</p><p>Done at Fictionville.</p>'
                b'<p class="oj-doc-ti">ANNEX</p><p class="oj-ti-art">Article 1</p><p class="oj-sti-art">Agreement</p><p>A1.</p>'
                b'<p class="oj-ti-art">Article 3</p><p class="oj-sti-art">Agreement</p><p>A3.</p>')
        parsed = a.parse(page, "application/xhtml+xml")
        self.assertEqual({key: item["text"] for key, item in parsed.items()},
                         {"Article 1": "B1.", "Article 1a": "B1a.", "Article 2": "B2."})

    def test_a_contents_list_does_not_empty_the_articles(self):
        text = (b"Contents\nArticle 1\nFictional subject-matter\nArticle 2\nFictional erasure\nANNEX I\n\nArticle 1\n"
                b"Fictional subject-matter\nThis fictional Regulation lays down rules.\nArticle 2\nFictional erasure\n"
                b"The fictional subject may obtain erasure of data.\n")
        parsed = a.parse(text, "text/plain")
        self.assertEqual(parsed, {
            "Article 1": {"title": "Fictional subject-matter", "text": "This fictional Regulation lays down rules."},
            "Article 2": {"title": "Fictional erasure", "text": "The fictional subject may obtain erasure of data."}})
        self.assertEqual(a.suggest("Users can delete their account", {"act": parsed})[0]["article"], "Article 2")

    def test_repeated_numbers_and_long_plain_text_stay_bounded(self):
        paragraphs = [((), "Article 1"), ((), "Fictional title"), ((), "Body.")] * 20000
        tracemalloc.start()
        try:
            parsed = a._segment(paragraphs)
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        self.assertEqual(parsed, {"Article 1": {"title": "Fictional title", "text": " Body."}})
        self.assertLess(peak, 1024 * 1024)  # one kept occurrence, not one per repeat
        with mock.patch.object(a, "MAX_PARAGRAPHS", 3):
            self.assertEqual(a.parse(b"Article 1\nT\nBody.\nMore.\nArticle 2\nT\nB.\n", "text/plain"),
                             {"Article 1": {"title": "T", "text": "Body."}})

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

    def test_each_suggestion_explains_its_matched_terms_and_where_they_came_from(self):
        catalogue = {"fixture": a.parse(XHTML, "application/xhtml+xml")}
        found = a.suggest("Users can delete their account", catalogue)[0]
        bridged = [item for item in found["matched"] if item["via"] == "legal vocabulary"]
        self.assertTrue(bridged and all(item["from"] == "delete" for item in bridged), found["matched"])
        for item in found["matched"]:
            self.assertIn(item["via"], ("statement", "legal vocabulary"))
            self.assertEqual("from" in item, item["via"] == "legal vocabulary")
        self.assertEqual(found["matched"], sorted(found["matched"], key=lambda item: item["term"]))


if __name__ == "__main__":
    unittest.main()
