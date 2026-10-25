---
id: 002-legal-revalidation-cli
unit: 001-legal-revalidation-cli
intent: 001-read-only-legal-revalidation
type: simple-construction-bolt
status: in-progress
stories: [003-official-source-retrieval]
created: 2026-10-18T19:01:39Z
started: 2026-10-25T01:30:00Z
completed: null
current_stage: test
stages_completed: [plan, implement, test]
requires_bolts: [001-legal-revalidation-cli]
enables_bolts: [003-legal-revalidation-cli]
requires_units: []
blocks: true
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
---

# Bolt: 002-legal-revalidation-cli

## Objective

Official-source retrieval. Plan, Implement and Test are recorded in [implementation-plan.md](implementation-plan.md), [implementation-walkthrough.md](implementation-walkthrough.md) and [test-walkthrough.md](test-walkthrough.md). All three await Owner validation; story 003 is not marked complete.

## Stories Included

- [ ] [003-official-source-retrieval](../../intents/001-read-only-legal-revalidation/units/001-legal-revalidation-cli/stories/003-official-source-retrieval.md): Retrieve selected official sources safely (Must).

## Expected Outputs

Bounded validated official HTTPS transport; exact bytes/provenance; safe attempt failures; fake DNS/HTTP/redirect/bounds checks.

## Bolt Type

Simple Construction; installed definition: `/home/user/.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`. The `type` field follows the bolt-instance schema.

## Stages

- [ ] **1. Plan**: Recorded 2026-10-25, awaiting Owner validation → implementation-plan.md; confirm changes, bounds, fixtures and acceptance checks.
- [ ] **2. Implement**: Recorded 2026-10-25, awaiting Owner validation → source/docs + implementation-walkthrough.md.
- [ ] **3. Test**: Recorded 2026-10-25, awaiting Owner validation → tests + test-walkthrough.md, including make check.

Execute in this order, stopping for human validation after each stage before advancing/completing. These stage artifacts are created during construction; none exist or are claimed complete now.

## Dependencies

Requires: [001-legal-revalidation-cli](../001-legal-revalidation-cli/bolt.md). Enables: [003-legal-revalidation-cli](../003-legal-revalidation-cli/bolt.md). No cross-unit dependencies. `blocks` reflects incomplete required bolts only; Owner approval/readiness are separate gates.

## Success Criteria

- [ ] All included story criteria verified and make check passes.
- [ ] Changes reviewed; historical reports/specs and unrelated work preserved.
- [ ] All three stage checkpoints accepted.

## Approval Gate

Do not begin Plan/implementation until Owner artifacts review and construction-readiness confirmation. No live-source smoke run is authorized by this plan.
