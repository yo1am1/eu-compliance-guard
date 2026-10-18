---
intent: 001-read-only-legal-revalidation
phase: inception
status: units-decomposed
updated: 2026-10-18T19:01:39Z
---

# Unit decomposition

One deployable unit: [001-legal-revalidation-cli](units/001-legal-revalidation-cli/unit-brief.md), delivering a local Python CLI, generated contracts, retained reports, a repository-local skill and an offline synthetic example. No other units or unit dependencies.

## Execution order

1. [Bolt 001](../../bolts/001-legal-revalidation-cli/bolt.md): stories 001–002, validated contracts and offline report.
2. [Bolt 002](../../bolts/002-legal-revalidation-cli/bolt.md): story 003, official-source retrieval; requires 001.
3. [Bolt 003](../../bolts/003-legal-revalidation-cli/bolt.md): stories 004–006, history/revalidation, skill/example and release; requires 002.

All bolts use simple-construction-bolt. This acyclic sequence is planned only; Owner artifacts review and construction-readiness confirmation remain pending.
