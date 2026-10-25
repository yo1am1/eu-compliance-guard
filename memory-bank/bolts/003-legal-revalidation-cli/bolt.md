---
id: 003-legal-revalidation-cli
unit: 001-legal-revalidation-cli
intent: 001-read-only-legal-revalidation
type: simple-construction-bolt
status: planned
stories: [004-revalidation, 005-portable-skill-and-example, 006-release-checks]
created: 2026-10-18T19:01:39Z
started: null
completed: null
current_stage: null
stages_completed: []
requires_bolts: [002-legal-revalidation-cli]
enables_bolts: []
requires_units: []
blocks: true
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 3
---

# Bolt: 003-legal-revalidation-cli

## Objective

History/revalidation, portable skill and release. Planned only; included stories remain unimplemented.

## v3 plugin and UI branch — 2026-10-25

Owner direction: the Claude Code plugin interface is Bolt 003 work (v3) and lives on
its own branch, `claude/bolt-003-plugin-ui`, built on the Bolt 002 retrieval branch.
It delivers story 005's portable instructions as a plugin (`/eucg` mode, review,
audit, gaps, status and help skills, plus a SessionStart hook), with a band above
the prompt and a browser view of verified runs. Story 004 (predecessor revalidation)
and story 006 (release checks) are not started. No stage of this bolt has been
validated by the Owner, and no story is marked complete.

## Stories Included

- [ ] [004-revalidation](../../intents/001-read-only-legal-revalidation/units/001-legal-revalidation-cli/stories/004-revalidation.md): Compare retained assessments and invalidate review claims (Must).
- [ ] [005-portable-skill-and-example](../../intents/001-read-only-legal-revalidation/units/001-legal-revalidation-cli/stories/005-portable-skill-and-example.md): Ship portable instructions and an offline example (Must).
- [ ] [006-release-checks](../../intents/001-read-only-legal-revalidation/units/001-legal-revalidation-cli/stories/006-release-checks.md): Verify contracts and reproducible delivery (Must).

## Expected Outputs

Revision comparison/invalidation; repository-local skill and offline example; separate opt-in smoke instructions; package/release verification.

## Bolt Type

Simple Construction; installed definition: `/home/user/.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`. The `type` field follows the bolt-instance schema.

## Stages

- [ ] **1. Plan**: Pending → implementation-plan.md; confirm changes, bounds, fixtures and acceptance checks.
- [ ] **2. Implement**: Pending → source/docs + implementation-walkthrough.md.
- [ ] **3. Test**: Pending → tests + test-walkthrough.md, including make check.

Execute in this order, stopping for human validation after each stage before advancing/completing. These stage artifacts are created during construction; none exist or are claimed complete now.

## Dependencies

Requires: [002-legal-revalidation-cli](../002-legal-revalidation-cli/bolt.md). Enables: unit acceptance. No cross-unit dependencies. `blocks` reflects incomplete required bolts only; Owner approval/readiness are separate gates.

## Success Criteria

- [ ] All included story criteria verified and make check passes.
- [ ] Changes reviewed; historical reports/specs and unrelated work preserved.
- [ ] All three stage checkpoints accepted.

## Approval Gate

Do not begin Plan/implementation until Owner artifacts review and construction-readiness confirmation. No live-source smoke run is authorized by this plan.
