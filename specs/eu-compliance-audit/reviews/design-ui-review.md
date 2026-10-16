# Integrated design — final frontend review

Date: 2026-10-14. Outcome: **changes required before frontend contract approval**. Scope: integrated design sections 3, 6–9, 11–14 and assigned traceability rows. Three material findings; no implementation requested.

## 1. Define the read contract needed to inspect and recover the first loop

**Blocker.** [design.md](../design.md), lines 191–198, 283–303 and 331–333: snapshots contain findings, attempts and patch metadata, but neither the snapshot nor query surface returns retained conversation messages, legal/control detail, graph neighborhoods or reviewable diff content. A diff digest identifies bytes without supplying them. Lost-response recovery says to look up a persisted request, but exposes no corresponding query. The preserved frontend report defines these needs; the integrated transport still lacks their mapping.

**Correction:** specify one membership-checked run-detail query with bounded entity selectors/cursors for the required retained records, plus a request-ID lookup returning its receipt/action and successor-run identity. Include revision/context bindings and safe diff bytes matching the reviewed digest; keep unknown-redaction content blocked. This can extend the snapshot/read projection rather than introduce separate services. Define receipts for pending, blocked and failed discussion as well as patches. **Acceptance:** reload after losing a proposal/apply response; recover its original conversation, diff and action without repeating execution. **Criteria:** R5.12/14/16–18, R6.10/12–13, R7.12–13.

## 2. Make terminal-to-successor navigation recoverable across clients

**Blocker.** [design.md](../design.md), lines 299–307 and 333: post-terminal discussion/remediation creates a successor run, closes the predecessor stream and keeps historical records immutable. Only the initiating command response supplies the successor identity. A reload on the predecessor URL, another attached CLI/dashboard, or a lost response cannot discover later work through the specified snapshot/events surface. The late-response rule also needs to distinguish originating context from execution in a successor.

**Correction:** retain a queryable project-level run relationship index outside immutable historical snapshots, including parent, successor, creating request and operation. Return this relationship on recovery and offer explicit “Continue in run …” navigation without silently switching historical views. Conversation/action records should distinguish `origin_run_id` and bound finding revision from `execution_run_id`; preserve links to original evidence. **Acceptance:** client A starts remediation after completion while client B inspects history; B reloads, discovers the successor, and follows deliberately. Late replies remain under their recorded context. **Criteria:** R5.15–17, R6.10/12, R7.13.

## 3. Separate current freshness from immutable historical finding payloads

**Blocker.** [design.md](../design.md), lines 167–174, 191–195 and 307–309: findings carry freshness directly, snapshots carry only an optional input-check timestamp, and terminal histories stay immutable. The prose correctly requires a separate current assessment, but its response shape and refresh operation are undefined. Re-reading a terminal snapshot cannot communicate newly observed staleness without changing history or overloading historical fields.

**Correction:** return a separately versioned current assessment keyed by project, run, finding revision and compared input manifest, with check time, freshness and reasons. Define an explicit scoped refresh command/read result; unavailable inputs produce unknown/stale assessment without rewriting the original outcome. Preserve established dependency-specific invalidation. **Acceptance:** complete a run, change deployment/law/graph inputs, reload history and refresh; retain the old pass while showing affected current conclusions stale and unrelated browser proof unchanged. **Criteria:** R5.19–20, R6.12–13, R7.13.

## Approval and checks

Dashboard composition, guarded one-file apply, inert evidence display and accessible interaction direction are approved within scope. Containment, provider compatibility, sanitization and browser acceptance remain correctly identified future gates, not additional design findings.

Read-only checks: assignment; AGENTS.md; safety/git rules and review workflow; preserved frontend report; complete line-numbered integrated design and assigned traceability; relevant requirement text; `git status --short`, scoped unstaged/staged diffs, file-absence check and SHA-256 comparison of requirements, research and four prior reports. No new external technical/legal fact was derived; references are the existing design and approved criteria.

Completed: this new report only. Remaining blockers: the three contracts above. No implementation, runtime/provider work or acceptance tests executed. Actual context usage: unknown. Risk: recovery and freshness cannot be accepted until these contracts and their future cases are resolved.
