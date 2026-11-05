# Decision: graph-closeness re-ranking is measured and not adopted (2026-11-05)

2.0 bolt 014 planned hybrid search: BM25 over code lines, re-ranked by closeness in the
project graph, with the two rankings fused by reciprocal rank (k = 60).

The fusion was implemented and measured with `make eval`:

| Set | BM25 (top-1, top-3) | BM25 + graph (top-1, top-3) |
|---|---|---|
| Grounding, single-file project, 10 facts | 7, 10 | 7, 10 |
| Grounding, multi-file graph project, 6 facts | 5, 6 | 5, 6 |

Nothing improved, so the change was not adopted. The project rule is that a search change
ships only with before/after numbers showing a gain. Why:

- With two candidates, equal-weight rank fusion ties whenever the rankings disagree, and
  the tie falls back to BM25 order. Tuning the weights to flip such cases would fit the
  test set rather than improve search.
- The remaining misses are within one function or one file (two lines about
  auto-renewal), or in non-Python files the graph does not parse (an HTML analytics tag).
  Graph distance cannot separate those.

What was kept:

- The six multi-file grounding cases (`graph_grounding` in `fixtures/eval/search-v1.json`),
  enforced at their BM25 baseline.
- The graph's real value in grounding: path evidence and uncovered data flows (bolt 013).

Revisit this only with a larger multi-file corpus, where candidates spread across
functions that call each other, and adopt it only if held-out numbers improve.
