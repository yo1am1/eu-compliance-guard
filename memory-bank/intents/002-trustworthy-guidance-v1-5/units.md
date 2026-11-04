---
intent: 002-trustworthy-guidance-v1-5
phase: inception
status: draft-awaiting-owner-approval
updated: 2026-11-04T18:00:00Z
---

# Unit decomposition

One deployable unit, the existing CLI plus plugin (`001-legal-revalidation-cli`),
extended. No new units.

## Proposed bolts (simple-construction-bolt each, in order)

| Bolt | Scope | Requirements | Depends on |
|---|---|---|---|
| 005 Search evaluation | Versioned synthetic eval set and `make eval`, plus the baseline numbers | FR-8 | — |
| 006 Explainable suggestions | Matched terms in article search and grounding: report, `ground` and JSON | FR-1 | 005 |
| 007 Accept flow | The `accept` command and the `/eucg-next` mapping step | FR-2 | 006 |
| 008 Law in force | Consolidated CELEX checks, version date in the report, the newer-consolidation notice | FR-3, FR-4 | — |
| 009 Real repositories | Run ordering by end time, files root from `--input`, renames and binaries in `pr-check`, `..` handling, inverted index | FR-5, FR-6 | — |
| 010 Panel grounding and CI | Panel candidates with Confirm, the project's own CI workflow, then the 1.5 release with the E2E agent team and live session | FR-7, FR-9 | 006, 007 |

Bolts 005 and 006, 008, and 009 can run in parallel, one writer per file. Bolt 010
closes the release.
