# Task-plan review — frontend and first product loop

Date: 2026-10-14. Verdict: **CHANGES REQUIRED**. Approved architecture remains unchanged; two bounded sequencing/acceptance corrections are needed.

## 1. Tasks 8/10/13–15 depend on evidence handling deferred to task 22

[Task plan](../tasks.md), lines 76–93, 107–124 and 164–180. The first browser checks promise safe evidence and the bridge consumes curated context, but the explicit implementation and hostile-fixture testing of text/URL/DOM/network/image sanitization and unknown-redaction delivery blocking appears in task 22, after checkpoint 15's real conversation and evidence inspection. Task 13's rendering/component checks cannot establish safety before persistence or provider submission. The plan must make the initial safe-evidence prerequisite explicit rather than relying on the adjective “safe”.

**Smallest correction:** assign the minimal capture/sanitization and fail-closed delivery slice to dream-engine in task 8, integrated by root and checked at checkpoint 9 before task 10. Include fabricated secret-bearing text/URL/DOM/network/image inputs and unknown/failed redaction; prove no unsafe bytes reach durable evidence, API previews or provider context. Unsupported artifact types remain blocked. Keep broader lifecycle, purge, backup and report work in task 22. Carry these checks into tasks 14/15. **Criteria:** R4.7–8, R4.17, R5.13, R7.12; design sections 6/9 and A9.

## 2. Tasks 14/15 need explicit dashboard accessibility acceptance

[Task plan](../tasks.md), lines 107–124. Task 13 implements keyboard/focus/status/reflow with component tests, but task 14 lists only product-loop/state cases and checkpoint 15 does not explicitly require the approved browser/manual accessibility checks. Task 17 evaluates audited targets; that is distinct from accepting the dashboard itself. Listing R6.14 on checkpoint 15 does not define the missing observed result.

**Smallest correction:** add keyboard-only dashboard journey, focus retention during replay/navigation, meaningful status announcements, color-independent meaning and zoom/reflow checks to task 14's browser harness. Root runs the declared pinned browser matrix and records manual assistive-technology/status review at checkpoint 15; dream-ui authors the browser cases in root-assigned disjoint files. Block dashboard accessibility completion on failures or unperformed manual checks. **Criteria:** R6.14, R7.12; design section 9 and A9.

## Coverage, checks and limits

Otherwise, tasks 1/4/5/7/8/10/11 supply tasks 13/14's contracts, reads, obligations, receipts, conversations, successor runs, freshness and actual retests. Optional Graphify completion in task 19 does not block independent evidence review. Root-owned shared contracts/dependencies/integration and explicitly assigned browser-test files keep ownership manageable. Real-native admission and authorization gates are honestly separated from fake protocols.

Checks: assignment, AGENTS.md, safety/git/review rules, requirements, approved design, complete task plan/coverage index, scoped unstaged/staged diff, working-tree status, target absence and immutable-file digests. Only this new report written. No implementation, runtime/provider/browser execution or tests. Actual context usage unknown. Remaining blockers: the two corrections above; runtime feasibility remains untested.
