---
id: 001-legal-revalidation-cli
unit: 001-legal-revalidation-cli
intent: 001-read-only-legal-revalidation
type: simple-construction-bolt
status: in-progress
stories: [001-input-and-coverage, 002-accountable-mapping-and-report]
created: 2026-10-18T19:01:39Z
started: 2026-10-18T19:06:25Z
completed: null
current_stage: implement
stages_completed:
  - name: plan
    completed: 2026-10-18T19:15:48Z
    artifact: implementation-plan.md
requires_bolts: []
enables_bolts: [002-legal-revalidation-cli]
requires_units: []
blocks: false
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 1
  testing_scope: 2
---

# Bolt: 001-legal-revalidation-cli

## Objective

Validated contracts and offline report. Plan is approved and Implement has started; included stories remain unimplemented.

## Stories Included

- [ ] [001-input-and-coverage](../../intents/001-read-only-legal-revalidation/units/001-legal-revalidation-cli/stories/001-input-and-coverage.md): Validate declared inputs and coverage (Must).
- [ ] [002-accountable-mapping-and-report](../../intents/001-read-only-legal-revalidation/units/001-legal-revalidation-cli/stories/002-accountable-mapping-and-report.md): Produce an accountable offline report (Must).

## Expected Outputs

Validated input/mapping/report records; regenerated contracts; runnable offline CLI; private retained outputs; synthetic reference, coverage and report checks.

## Bolt Type

Simple Construction; installed definition: `/home/user/.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`. The `type` field follows the bolt-instance schema.

## Stages

- ✅ **1. Plan**: Approved → implementation-plan.md.
- ⏳ **2. Implement**: In progress → source/docs + implementation-walkthrough.md.
- [ ] **3. Test**: Pending → tests + test-walkthrough.md, including make check.

Execute in this order, stopping for human validation after each stage before advancing/completing. These stage artifacts are created during construction; none exist or are claimed complete now.

## Dependencies

Requires: none. Enables: [002-legal-revalidation-cli](../002-legal-revalidation-cli/bolt.md). No cross-unit dependencies. `blocks` reflects incomplete required bolts only; Owner approval/readiness are separate gates.

## Success Criteria

- [ ] All included story criteria verified and make check passes.
- [ ] Changes reviewed; historical reports/specs and unrelated work preserved.
- [ ] All three stage checkpoints accepted.

## Approval Gate

The Owner approved inception artifacts, confirmed construction readiness and selected this bolt's Plan stage, then approved the concrete plan and starting Implement. Present implementation for human validation before Test. No live-source smoke run is authorized by this offline bolt.
