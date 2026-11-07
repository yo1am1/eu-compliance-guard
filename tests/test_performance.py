"""Hostile input stays linear: inputs that took 10–15 s before the 2.5 audit finish far under the bound.

Each case was quadratic: a crafted project file, page or text could stall `pr-check` in CI or the
MCP server. The bound is generous so a slow machine does not fail; the old behaviour exceeds it.
"""
import time
import unittest

from eu_compliance_guard import articles, citations, rust_graph

BOUND = 5.0


class LinearTimeTests(unittest.TestCase):
    def timed(self, call):
        start = time.perf_counter()
        call()
        return time.perf_counter() - start

    def test_uk_parser_with_many_unmatched_end_tags(self):
        head = ('<html><body><!-- legislation.gov.uk --><a class="LegAnchorID" id="section-1"></a>'
                '<h4><span class="LegP1GroupTitle">T</span></h4><p class="LegP1Text">')
        page = (head + "<div>" * 20000 + "</span>" * 20000 + "text</p></body></html>").encode()
        self.assertLess(self.timed(lambda: articles.parse(page, "text/html")), BOUND)

    def test_citations_with_many_citations_and_quotations(self):
        text = 'Article 1 GDPR "x y z w". ' * 20000
        catalogue = {"a": {"Article 1": {"title": "t", "text": "x y z w"}}}
        self.assertLess(self.timed(lambda: citations.check(text, catalogue, {"a": [["gdpr"]]})), BOUND)

    def test_rust_reader_with_unclosed_turbofish_calls(self):
        source = "fn f() { " + "x::<" * 8000 + " }"
        self.assertLess(self.timed(lambda: rust_graph.read_file("src/lib.rs", source)), BOUND)


if __name__ == "__main__":
    unittest.main()
