# Task-plan review — engine

Date: 2026-10-14. Verdict: **APPROVED** for task-plan review. No material engine-domain planning blockers found. This verdict does not authorize implementation or certify feasibility.

Reviewed [tasks.md](../tasks.md) against the [approved design](../design.md) and [requirements](../requirements.md):

- Tasks **1–6** establish shared validated contracts before persistence, dispatcher/API/CLI wiring and transport integration. Tasks 2/3 cover observed executor denial and descendant cleanup; tasks 4/5/6 cover lifetime ownership, headless API readiness, durable evidence, receipts, delegated authorization, replay and cancellation/completion ordering. These cover **R3.9/R3.19, R4.4–R4.8/R4.16–R4.17, R5.9/R5.15–R5.16/R5.20 and R6.10–R6.13** without duplicating business logic.
- Tasks **7–12** precede dashboard acceptance with source/manual dispositions, isolated scanner/browser assertions, managed-agent admission and durable one-file remediation. Task 11 explicitly orders staged-file synchronization, committed journal, replacement and directory synchronization; it retains conflict recovery, successor manifests and failed/inconsistent retests. **R3.1–R3.3/R3.8–R3.12/R3.17–R3.19, R5.6–R5.8/R5.18–R5.20 and R7.13** are concretely planned.
- Checkpoint **3** requires observed local executor denial. Checkpoint **12** permits no real managed execution without observed native isolation admission. Tasks **14/15** require separately authorized real conversation, enforced boundaries, actual before/after retests and a retained manual gap. Native unknowns and fake-only success cannot satisfy **R7.5/R7.12**.
- Tasks **16–21** cover lifecycle/security, commerce/accessibility and pinned Graphify provenance, schema, freshness and admission; **R3.4–R3.7/R3.13–R3.16/R3.20 and R5.14** remain explicit rather than being inferred from starter scans. Tasks **22/24/26/27** complete evidence/reporting/lifecycle and regression gates.

Ownership is disjoint at file level: root owns shared contracts/API/dependencies/fixtures, engine owns persistence/execution/checks/remediation, and host/UI/legal workers use those contracts read-only. Exact wave assignments are required before edits. “Prior tasks in the current block” establishes sequential prerequisites; checkpoints integrate cross-owner work.

Checks performed: read the named assignment first, then AGENTS.md, the complete task plan/coverage index and relevant requirement/design contracts and acceptance passages using `cat` and `sed`. Used `sha256sum` to confirm the design matches the plan's approved digest and to record requirements/tasks digests; verified the new review path was absent before exclusive creation. No external research was needed.

Remaining limits: every runtime/native/containment/browser/source/host acceptance result remains untested. Operational authorization and plan approval are still required. Only this new review file was written; no implementation, tests, providers, installation or publication occurred. Actual context usage is unknown. Awaiting supervisor handoff.
