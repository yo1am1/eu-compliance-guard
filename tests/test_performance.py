"""Hostile input stays linear: inputs that took 10–15 s before the 2.5 audit finish far under the bound.

Each case was quadratic: a crafted project file, page or text could stall `pr-check` in CI or the
MCP server. The bound is generous so a slow machine does not fail; the old behaviour exceeds it.
"""
import time
import unittest

import ast

from eu_compliance_guard import articles, citations, graph, models as m, rust_graph, timeline

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

    def test_rust_reader_with_many_items_and_deep_nesting(self):
        # Each of these took minutes to hours at 2.5.0 (every item rescanned to the end of the file).
        for source in ("fn a(){\n" * 30000, "fn a(\n" * 30000, "mod a {\n" * 30000, "impl X {\n" * 30000,
                       "#[test] fn a(\n" * 30000, "macro_rules! m (\n" * 30000):
            with self.subTest(source=source[:12]):
                self.assertLess(self.timed(lambda: rust_graph.read_file("src/lib.rs", source)), BOUND)

    def test_python_reader_with_many_definitions(self):
        text = "def a():\n    pass\n" * 30000  # 131 s at 2.5.0 for a 340 KB file
        def read():
            graph._FileVisitor("x.py", text).visit(ast.parse(text))
        self.assertLess(self.timed(read), BOUND)

    def test_timeline_with_many_dates_in_one_clause(self):
        catalogue = {"a": {"Article 1": {"title": "t", "text": "It shall apply from " + "2 August 2026, " * 20000}}}
        self.assertLess(self.timed(lambda: timeline.timeline(catalogue, "2026-01-01")), BOUND)


class GraphLimitTests(unittest.TestCase):
    def test_a_project_over_the_limits_keeps_extracted_links_and_says_what_was_left_out(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "a.py").write_text("def g():\n    pass\n")
            (root / "b.py").write_text("def g():\n    pass\n")
            (root / "c.py").write_text("def h():\n    pass\n\ndef k():\n    g()\n    h()\n")
            full = graph.build_graph(root)
            with patch.object(m, "MAX_GRAPH_EDGES", len(full.edges) - 1):
                small = graph.build_graph(root)
        self.assertEqual([edge.provenance for edge in full.edges if edge.kind == "calls"].count("ambiguous"), 2)
        self.assertEqual((small.omitted_edges, len(small.edges)), (1, len(full.edges) - 1))
        dropped = set(full.edges) - set(small.edges)
        self.assertEqual([edge.provenance for edge in dropped], ["ambiguous"])  # extracted links are kept first
        self.assertIn("larger than the graph's limits: 0 definitions and 1 links left out", graph.format_graph(small))
        self.assertEqual(full.omitted_edges, 0)
        self.assertNotIn("graph's limits", graph.format_graph(full))


if __name__ == "__main__":
    unittest.main()
