# Roadmap

| Version | Destination | Status |
|---|---|---|
| 1.0 | Stable read-only workflow and Claude Code plugin | Released |
| 1.1 | Code-grounded facts, article text, next step, PR check, side panel | Released |
| 1.2 | AGPL-3.0 licence and the Great Auditor fixes (83 confirmed defects) | Released |
| 1.3 | Review-progress dashboard, hardening, search evaluation, explained suggestions, project graph with data flows and graph view | Released |
| 1.4 | One-step accept, law-in-force CELEX checks, real-repository fixes, CI, panel grounding | Released |
| 1.5 | Trustworthy guidance: [the intent](../memory-bank/intents/002-trustworthy-guidance-v1-5/requirements.md) completed with the newer-consolidation notice | Released (live band and panel check in a session not done; see CHANGELOG) |
| 2.0 | Compliance workspace: law lockfile and change impact, signed decisions, citation guard and MCP tools, obligation pack format, evidence imports ([bolts 012–021](../memory-bank/intents/003-compliance-workspace-v2/units.md)) | Released (scripted end-to-end check; signing with the Owner's key and a live session check not done; see CHANGELOG) |
| 2.1 | Precision: full audit, fuzz tests for untrusted inputs, real law-text and real-repository test sets, fixes ([intent 004](../memory-bank/intents/004-precision-and-jurisdictions-v2-5/requirements.md)) | Released |
| 2.2 | Jurisdictions as modules; the UK (legislation.gov.uk) | Released |
| 2.3 | CRA, EAA, NIS2, AI Act dates; application-date timeline; draft starter packs; exports | Released |
| 2.4 | The project graph reads Rust (a hand-written reader, no new dependency) | Released |
| 2.5 | Stabilisation for 3.0: full audit, open choices (the live session check is the Owner's) | Released |
| 2.5.1 | Fixes from a full audit of 2.5.0; documentation that claims only what the code does | Released |
| 2.6 | Optional semantic search for article suggestions; sealed runs (tamper evidence); unused code removed; an end-to-end test of every command; a README built from real output | Released |
| 3.0 | A breakthrough once 2.5 is stable; candidates in the intent | Not approved |

The tool covers the EU and the UK; the US is not planned (Owner decision, 2026-11-06).

The plan follows the specsmd flow: the Owner approves an intent's requirements, then
units, stories and bolts are generated and built one bolt at a time.
