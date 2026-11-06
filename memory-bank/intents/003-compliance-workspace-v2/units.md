---
intent: 003-compliance-workspace-v2
phase: inception
status: approved-2026-11-05
updated: 2026-11-05T00:00:00Z
---

# Unit decomposition

The unit is the existing CLI plus plugin, extended. The service stays out of scope;
every bolt keeps files as the API and pure cores with thin edges.

| Bolt | Scope | Requirements | Depends on |
|---|---|---|---|
| 012 Graph core (done 2026-11-05) | Python `ast` code graph, concept tags, deterministic `graph.json` and digest, `graph` command. Recording the digest in each run moves to 013. | FR-G1, FR-G9 (corpus) | 1.5 bolt 005 (eval set) |
| 013 Path evidence (done 2026-11-05; the run-recorded graph digest moved to 015) | Path queries; `ground` confirms facts with extracted paths; uncovered-flow gaps | FR-G2, FR-G5 | 012 |
| 014 Hybrid search (measured 2026-11-05: no gain, not adopted; see docs/decisions/hybrid-search.md) | BM25 + graph closeness fused by reciprocal rank, with explanations and before/after numbers | FR-G3, FR-G9 | 012, 1.5 bolt 006 |
| 015 Graph-aware PR check (done 2026-11-05; runs do not record a graph, because revalidate never crawls the project) | A diff on a pinned path reopens dependent facts and obligations | FR-G4 | 013 |
| 016 Graph view (done 2026-11-05; static HTML, panel button; the React page can read graph --json later) | Self-contained HTML graph view and a React dashboard page | FR-G6, FR-G7 | 013 |
| 017 Law lockfile and change impact (done 2026-11-06) | `eu-law.lock`; reopen decisions citing changed articles or graph nodes | A1, research bets 1-2 | 012 |
| 018 Signed decisions and citation guard (done 2026-11-06; no graph digest, as runs record none) | SSH-signed review records bound to the law version, evidence and graph digests; citation checks for agent-written text, also as MCP tools | D1, research bets 3-4, E2 | 017 |
| 019 Imports (done 2026-11-06: WEC and SARIF; a Graphify import waits for a stable Graphify format) | EDPS Website Evidence Collector, SARIF and optional Graphify import as untrusted evidence | C, FR-G8 | 012 |
| 020 Obligation pack format (done 2026-11-06; format only, no lawyer-reviewed content) | Versioned packs of obligations with exact article pins and the article digests read; `pack build`, SSH `pack sign`/`verify`, `pack import` that adds candidate obligations only | B1 (format), Owner decision 2 | 017, 018 |
| 021 MCP review tools (done 2026-11-06; `ground` stays read-only, pinning is a person's step) | `ground` and `pr-check` as read-only MCP tools beside cite_check, article_search and next_steps | E2 | 018 |

Bolts 012 to 016 make up the graph track and 017 to 019 the law track. The two tracks
can run in parallel, with one writer per file.
