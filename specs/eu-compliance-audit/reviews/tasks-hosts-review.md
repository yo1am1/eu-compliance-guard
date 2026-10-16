# Host and release task-plan review

Date: 2026-10-14. Verdict: **APPROVED** for task-plan review. No material planning blocker found in the assigned domain. This does not approve implementation or operational execution.

## Coverage and ordering

- Tasks **1–3** establish shared contracts, installed Codex protocol/capability inspection and reusable admission probes before dependent implementation. Static/advertised support is explicitly separate from observed executor/native isolation. Failure disables the relevant capability; existing authentication must not leak into probe output. Covers **R4.4–R4.8, R6.8–R6.9, R7.13**.
- Tasks **4–6** cover one online HTTP owner, headless lifecycle, owner/delegated identities, no owner-credential fallback, scope/revocation, request recovery and replay. Root owns shared contracts/API; engine and CLI writers have separate files. Covers **R4.16, R5.15–R5.18, R6.10–R6.12**.
- Tasks **10–12** implement installed-schema structured proposal ingestion and guarded remediation with separate native admission. Tasks **14–15** require the real managed conversation and actual before/after retest; fake protocols cannot complete the first milestone. New native conversations/processing need explicit owner scope. Covers **R5.6–R5.7, R5.17–R5.20, R7.12–R7.13**.
- Tasks **23–25** separate canonical instructions, runtime installation, discovery, shared-engine invocation and managed bridges. All seven named hosts plus detected aliases receive actual identity/discovery/audit checks; unsupported or skipped hosts prevent an all-host claim. Receipt ownership, repeat/conflict/upgrade/uninstall and temporary-destination testing preserve unrelated state. Covers **R6.1–R6.10**.
- Tasks **26–27** and operational follow-through distinguish release-verification code from actual installation/publication. Candidate exclusions, provenance/license checks, remote revision/package verification and measured gates cover **R7.3, R7.6–R7.9, R7.11** without authorizing a push or global mutation.

## Checks and limits

Read assignment, AGENTS.md, safety/Git rules, review workflow, tasks 1–27 and coverage index, relevant requirements and approved design contracts. Compared the actual design SHA-256 with the plan's recorded approved digest: exact match. Inspected Git diff statistics; confirmed this report did not exist and created it exclusively. Existing specification/review bytes were checked unchanged across report creation.

Remaining gates: plan/assignment approval, installed native schema/authentication/containment feasibility, real product/host acceptance, authorized global installation and remote publication verification. None was executed here. Only this new review was written; no source, dependencies, tests or configuration changed.
