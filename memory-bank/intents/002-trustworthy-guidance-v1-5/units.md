---
intent: 002-trustworthy-guidance-v1-5
phase: inception
status: approved-2026-11-04; mostly built (see Status)
updated: 2026-11-05T18:30:00Z
---

# Unit decomposition

One deployable unit, the existing CLI plus plugin (`001-legal-revalidation-cli`),
extended. No new units.

## Proposed bolts (simple-construction-bolt each, in order)

| Bolt | Scope | Requirements | Depends on | Status |
|---|---|---|---|---|
| 005 Search evaluation | Versioned synthetic eval set and `make eval`, plus the baseline numbers | FR-8 | — | Done (1.3) |
| 006 Explainable suggestions | Matched terms in article search and grounding: report, `ground` and JSON | FR-1 | 005 | Done (1.3) |
| 007 Accept flow | The `accept` command and the `/eucg-next` mapping step | FR-2 | 006 | Done (1.4) |
| 008 Law in force | Consolidated CELEX checks, version date in the report, the newer-consolidation notice | FR-3, FR-4 | — | Done (part one in 1.4; the newer-consolidation notice after 1.4) |
| 009 Real repositories | Run ordering by end time, files root from `--input`, renames and binaries in `pr-check`, `..` handling, inverted index | FR-5, FR-6 | — | Done (1.4); renames and binaries were fixed in 1.2 |
| 011 Hardening | The stability rules in [2.0 decisions](../003-compliance-workspace-v2/requirements.md#stability-liability-and-supply-chain-owner-2026-11-04-binding-for-15-and-20): disclaimers on every output, a determinism test, the regex inventory and replacements plus a lint rule, `make verify-hosts`, SHA-pinned actions, the 14-day cooldown | NFR-5 to NFR-8 | — | Done (1.3) |
| 010 Panel grounding and CI | Panel candidates with Confirm, the project's own CI workflow, then the 1.5 release with the E2E agent team and live session | FR-7, FR-9 | 006, 007 | CI and panel grounding done (1.4); live-session check open |

Bolt 011 runs first, because the later bolts build on its rules. Bolts 005 and 006, 008, and 009 can then run in parallel, one writer per file. Bolt 010
closes the release.
