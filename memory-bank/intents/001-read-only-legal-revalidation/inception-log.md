---
intent: 001-read-only-legal-revalidation
created: 2026-10-18T19:01:39Z
completed: null
status: in-progress
---

# Inception log: Read-only legal revalidation

## Overview

Brown-field enhancement of the existing foundation. Intent metadata lives here and in the requirements pointer. Requirements approval is recorded canonically; artifacts review and construction readiness are pending.

## Artifacts Created

- [x] [Requirements pointer](requirements.md) to the approved canonical requirements.
- [x] [Context/design pointer](system-context.md), separate canonical documents awaiting Owner review.
- [x] [Units](units.md) and [unit brief](units/001-legal-revalidation-cli/unit-brief.md).
- [x] Six draft stories; [global index](../../story-index.md) updated immediately after each creation.
- [x] Three actual bolt instances: [001](../../bolts/001-legal-revalidation-cli/bolt.md), [002](../../bolts/002-legal-revalidation-cli/bolt.md), [003](../../bolts/003-legal-revalidation-cli/bolt.md).
- [x] Minimal [tech stack](../../standards/tech-stack.md) and [coding standards](../../standards/coding-standards.md), critical context required by installed Construction configuration.

## Summary

6 FRs; 2 NFRs; 1 deployable CLI unit; 6 Must stories; 3 planned simple-construction bolts. No implementation completed.

## Decision Log

| Recorded | Decision | Authority/state |
|---|---|---|
| 2026-10-18T19:01:39Z | Keep canonical requirements/context/design in specs_v2, with pointers here. | Owner requirements approval already given with y; this timestamp records the entry only. |
| 2026-10-18T19:01:39Z | One CLI unit, six draft stories, three sequential simple bolts. | Dispatch scope; artifacts await review. |
| 2026-10-18T19:01:39Z | Use Orca rather than historical Herdr placement. | Current explicit user instruction; no hidden subagents. |
| 2026-10-18T19:01:39Z | Resolve external specsmd completion-tool dependencies before final bolt completion. | Coordinator preflight reports MODULE_NOT_FOUND for fs-extra/js-yaml via bolt-complete.cjs; no application dependencies added and no manual completion workaround. |

## Scope Changes

None beyond approved requirements. Historical specs/** remain preserved.

## Ready for Construction

- [x] Requirements documented and Owner-approved.
- [x] Context/design locations linked for joint review.
- [x] Unit decomposed; stories generated; bolt dependencies planned.
- [ ] Owner artifacts review (Checkpoint 3) complete.
- [ ] Owner readiness confirmation (Checkpoint 4) received.

## Next Steps

Coordinator presents context/design, unit, stories and bolts for Owner artifacts review. Keep status in-progress until approval; do not set inception-complete or begin construction. Obtain readiness confirmation before bolt 001 Plan and honor each stage checkpoint. External completion-tool prerequisites do not block planning.

## Dependencies

001-legal-revalidation-cli → 002-legal-revalidation-cli → 003-legal-revalidation-cli. No unit dependencies or cycles. Primary FR/NFR ownership and supporting criteria are in the unit brief.
