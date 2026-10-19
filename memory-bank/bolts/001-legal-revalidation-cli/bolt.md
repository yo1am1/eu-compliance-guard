---
id: 001-legal-revalidation-cli
unit: 001-legal-revalidation-cli
intent: 001-read-only-legal-revalidation
type: simple-construction-bolt
status: complete
stories:
  - 001-input-and-coverage
  - 002-accountable-mapping-and-report
created: 2026-10-18T19:01:39.000Z
started: 2026-10-18T19:06:25.000Z
completed: "2026-10-19T09:08:42Z"
current_stage: null
stages_completed:
  - name: plan
    completed: 2026-10-18T19:15:48.000Z
    artifact: implementation-plan.md
  - name: implement
    completed: 2026-10-19T08:34:22.000Z
    artifact: implementation-walkthrough.md
  - name: test
    completed: 2026-10-19T09:08:42Z
    artifact: test-walkthrough.md
requires_bolts: []
enables_bolts:
  - 002-legal-revalidation-cli
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

Validated contracts and offline report. The Owner approved implementation and
starting Test on 2026-10-19. The Test report passes all twelve offline criteria;
the Owner accepted Test and bolt completion on 2026-10-19T09:08:42Z.

## Stories Included

- [x] [001-input-and-coverage](../../intents/001-read-only-legal-revalidation/units/001-legal-revalidation-cli/stories/001-input-and-coverage.md): Validate declared inputs and coverage (Must).
- [x] [002-accountable-mapping-and-report](../../intents/001-read-only-legal-revalidation/units/001-legal-revalidation-cli/stories/002-accountable-mapping-and-report.md): Produce an accountable offline report (Must).

## Expected Outputs

Validated input/mapping/report records; regenerated contracts; runnable offline CLI; private retained outputs; synthetic reference, coverage and report checks.

## Bolt Type

Simple Construction; installed definition: `/home/user/.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`. The `type` field follows the bolt-instance schema.

## Stages

- ✅ **1. Plan**: Approved → implementation-plan.md.
- ✅ **2. Implement**: Approved → source/docs + implementation-walkthrough.md.
- ✅ **3. Test**: Accepted → test-walkthrough.md.

Execute in this order, stopping for human validation after each stage before
advancing/completing. Plan and implementation are accepted; Test is authorized.
All three stage checkpoints are accepted.

## Dependencies

Requires: none. Enables: [002-legal-revalidation-cli](../002-legal-revalidation-cli/bolt.md). No cross-unit dependencies. `blocks` reflects incomplete required bolts only; Owner approval/readiness are separate gates.

## Success Criteria

- [x] All included story criteria verified and make check passes.
- [x] Changes reviewed; historical reports/specs and unrelated work preserved.
- [x] All three stage checkpoints accepted.

## Approval Gate

The Owner approved inception, Plan and Implement, then explicitly approved starting
Test and final completion. The required completion script updated both stories. No live-source smoke
run is authorized by this offline bolt.
