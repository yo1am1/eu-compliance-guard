# EU compliance audit — implementation plan

Status: **task plan draft for user review; source implementation not started**.  
Date: 2026-10-14.  
Requirements approved: 2026-10-13. Design approved by the user: 2026-10-14.  
Approved design SHA-256: `45f79656ffb071265a83788ea9fca40fc1f46dce32fdce793606401667168a0b`.  
Basis: [requirements](requirements.md), [design](design.md), [design adjudication](reviews/design-adjudication.md), [task-plan review](reviews/tasks-adjudication.md).

Existing specifications and review documents are preserved snapshots; this new file records the user's latest design approval. Checkboxes below are pending coding/check tasks, not claims of execution or active worker authorization.

## Execution proposal and ownership

Proposed execution mode, requiring user approval: the supervisor and the four existing visible Codex Dreamteam sessions implement these tasks through blocking internal checkpoints, without a separate user-review pause after every task. This would explicitly override specs.md execute.md's single-task/stop rule for this approved plan. It does not expand permissions for secrets, unrelated source, production, global installation, publication or fresh native conversations. Preserve approved spec contents; keep measured execution progress in separately authorized status/check records rather than rewriting frozen documents.

Reuse the existing sessions with gpt-6.1-sol medium. Root issues exact assignments before each wave; proposed paths are not concurrent-write permission. Workers run only scoped fake/unit/static checks; root integrates, runs full/integration/browser/runtime/native acceptance and owns contracts/dependencies/release operations. No hidden workers, reset or newly created team sessions. Actual context counts remain unknown unless measured; native compaction follows the 230000-token rule at a safe permitted handoff.

Application paths below are relative to `apps/eu-compliance-audit/`; the portable package remains in `.agents/skills/eu-compliance-guard/`.

| Writer | Proposed exclusive scope |
| --- | --- |
| Root | Application models/shared schema, api.py, package/lock files, generated frontend contract, shared fixtures, integration/e2e execution, root validation/CI/manifests and final assembly. Root writes canonical skill/workflow source after host/legal handback. |
| dream-engine | engine.py, store.py, execution.py, permissions.py, evidence.py, remediation.py, checks/ and scanner/graph adapters except host adapters; owned unit tests. |
| dream-legal | legal.py, catalog/, organizational evidence/review code and owned legal tests; read-only technical-check code. |
| dream-ui | Non-contract frontend source/styles/tests and browser-test authoring; package/lock and generated contract read-only. |
| dream-hosts | cli.py, agent.py, host adapters, installer and owned unit/contract tests; existing library exports and all shared contracts read-only. |

One writer per file. Interface changes go through root before dependent edits. Split wide work into reviewed handbacks rather than overlap source ownership. The commerce project, its frozen specs, reference projects and protected datasets stay outside these assignments.

## Coding and checkpoint tasks

- [ ] 1. Create the isolated application package and shared contracts
  - Owner: Root. First coding task after plan approval.
  - Add the separate Python package/locked dependency set and frontend build metadata from the approved stack. Reuse standard libraries; preserve the current instruction-library toolchain and MIT license with separate third-party notices.
  - Implement validated shared records/closed commands for scope, sources/attempts, per-obligation dispositions, historical/current assessments, receipts, relationships, conversation/proposal and events. Generate frontend contract types from the same schema.
  - Add small schema/trust-boundary tests and shared synthetic fixtures; no empty future modules or copied consuming-backend runtime.
  - _Requirements: R1.1, R1.2, R1.4, R2.2, R2.4, R3.9, R5.1, R5.2, R5.3, R6.2, R6.10_

- [ ] 2. Implement reusable containment and native-capability feasibility probes
  - Owner: dream-engine + dream-hosts, disjoint executor/agent files; root runs native probes. Depends on task 1.
  - Implement fixed-argv child supervision and Linux capability probes using isolated outputs, read-only included inputs and seeded synthetic private files. Test forbidden file/egress access, hooks/environment leakage, descendants, output saturation and cleanup.
  - Inspect the installed Codex protocol and implement the minimal reusable capability/authentication/proposal admission checks; distinguish advertised/static support from observed native tool isolation. Never read/copy real auth values into test output.
  - Root may enable a bounded real native/provider probe only with explicit approved processing, synthetic targets and fresh-conversation scope. An unavailable/failed mechanism blocks the dependent capability; fake or skipped probes cannot satisfy the real boundary gate.
  - _Requirements: R4.4, R4.5, R4.6, R4.7, R4.8, R4.16, R6.8, R6.9, R7.11, R7.13_

- [ ] 3. Checkpoint — Verify foundation and feasibility tests
  - Owner: root. Blocking after tasks 1, 2. Run the full accumulated test suite, fix failures, and review scoped handbacks before advancing.
  - Require schema and observed local executor-denial cases to pass. A failed/unavailable essential boundary blocks dependent work; static/fake/native probes stay separately labelled.
  - _Requirements: R4.4, R4.8, R7.1, R7.3, R7.5, R7.13_

- [ ] 4. Implement private persistence, evidence durability and engine ownership
  - Owner: dream-engine. Depends on checkpoint 3 and prior tasks in the current block.
  - Create the SQLite schema/versioned records, foreign-key ownership checks, short read snapshots and durable artifact publication. Retain all attempts, source failures, per-obligation methods and immutable run-bound assessments.
  - Implement the initial bounded text/URL/DOM/network artifact sanitization and typed delivery gate before any durable evidence publication, API preview or provider use. Fabricated secret-bearing inputs, unknown/failed redaction and unsupported types must fail closed; implement shared private evidence handling in evidence.py.
  - Implement lifetime lock/endpoint discovery and recovery without a second writer. Every online owner, including headless CLI ownership, serves the ready shared API; offline inspection remains read-only.
  - Test two starters, inaccessible live owner, disk-full/corrupt/missing evidence, orphan quarantine and interrupted ownership; no success before required evidence is durable.
  - _Requirements: R2.7, R3.9, R3.19, R4.2, R4.7, R4.9, R4.17, R5.3, R5.8, R5.9, R6.10, R6.12, R6.13, R7.13_

- [ ] 5. Wire authorization, commands, queries and ordered progress
  - Owner: Root api/contracts; dream-engine dispatcher/permissions; dream-hosts CLI transport. Depends on checkpoint 3 and prior tasks in the current block.
  - Implement exact Host/Origin, authenticated owner/delegated identities, CSRF, scope/expiry/revocation checks, closed operation dispatch and request-ID/payload-digest deduplication. Model CLI calls never fall back to owner credentials.
  - Expose membership-checked snapshots/detail/request lookup, successor relationships, safe evidence and native SSE replay/terminal closure. Implement the shared CLI client/headless lifecycle using the same engine.
  - Test snapshot/subscription races, duplicate/wrong-run/future events, lost responses, current overlays, stale views, cancellation/completion ordering and late callbacks. No stream/replay starts a side effect.
  - _Requirements: R4.4, R4.5, R4.8, R4.16, R4.17, R5.15, R5.16, R5.17, R5.18, R5.20, R6.3, R6.10, R6.11, R6.12, R7.13_

- [ ] 6. Checkpoint — Verify state, permissions and transport tests
  - Owner: root. Blocking after tasks 4, 5. Run the full accumulated test suite, fix failures, and review scoped handbacks before advancing.
  - Run the full accumulated fake/unit suite and API/CLI integration cases for ownership, receipts, credential separation, replay and cancellation races.
  - _Requirements: R4.16, R5.15, R5.16, R6.10, R6.12, R7.13_

- [ ] 7. Implement sourced scope, applicability and organizational review
  - Owner: dream-legal; root supplies shared contracts. Depends on checkpoint 6 and prior tasks in the current block.
  - Implement project/activity facts, all legal-family screening, three-state role/threshold/date/exemption decisions, targeted methods and per-obligation dispositions including obligations without findings.
  - Implement official source targets/attempts/snapshots/review chains, source typing, national overlays, failed first/refresh/translation handling, proposed registry changes and review acceptance. Add original functional starter registry resources; no model-generated executable law.
  - Implement evidence request/sufficiency/counter-evidence review and owner/action/residual-risk records. Add nuanced non-consent/sensitive-data/age/erasure/calendar-month, obsolete-source and hostile-document fixtures; mark fictional authorities explicitly.
  - _Requirements: R1.1, R1.2, R1.3, R1.4, R1.5, R1.6, R1.7, R1.8, R1.9, R1.10, R1.11, R2.1, R2.2, R2.3, R2.4, R2.5, R2.6, R2.7, R2.8, R2.9, R2.10, R4.1, R4.2, R4.3, R4.10, R4.11, R4.12, R4.13, R4.14, R4.15, R5.2, R5.4, R5.5, R5.10, R5.11, R7.10_

- [ ] 8. Implement the first repository/browser checks and synthetic target
  - Owner: dream-engine checks/adapters; root shared fixture/service harness. Depends on checkpoint 6 and prior tasks in the current block.
  - Implement included-input manifests, collection/store/log/recipient/journey inventory, a small reviewed Semgrep lead rule and normalized JSON/SARIF execution envelopes with errors/exclusions.
  - Implement Playwright assertions for fresh/reject/accept/withdraw against a resettable local synthetic optional tracker receiver, one passing control and one manual organizational gap. Retain expected/actual, route/state/locator, safe evidence and source-mapping basis.
  - Extend the task 4 evidence gate for browser capture and verified raster images/inert previews. Test fabricated secret-bearing browser artifacts and unknown/failed sanitization; prevent unsafe bytes reaching persistence, API preview or provider context. Unsupported image/trace mechanisms remain blocked.
  - Use only reviewed commands/pins and granted destinations. Preserve retry disagreement, blocked tools/access, unsupported mechanisms and unverified legal applicability; no cookie-count or empty-scan compliance verdict.
  - _Requirements: R1.9, R3.1, R3.2, R3.3, R3.8, R3.9, R3.10, R3.11, R3.12, R3.17, R3.18, R3.19, R4.6, R4.7, R4.8, R4.17, R7.5, R7.11_

- [ ] 9. Checkpoint — Verify starter control and check tests
  - Owner: root. Blocking after tasks 7, 8. Run the full accumulated test suite, fix failures, and review scoped handbacks before advancing.
  - Run the full accumulated suite and synthetic scanner/browser cases. Verify source attempts, per-obligation/manual gaps, legal counterexamples, expected/actual evidence and fail-closed redaction before persistence, API preview or model context.
  - _Requirements: R2.7, R3.9, R4.7, R4.8, R4.17, R5.3, R5.4, R7.5, R7.10, R7.11_

- [ ] 10. Implement the managed Codex discussion and proposal bridge
  - Owner: dream-hosts; root shared schema/API integration. Depends on checkpoint 9 and prior tasks in the current block.
  - Implement installed-schema stdio lifecycle, bounded authenticated native child, revision-bound curated context, safe attributed messages and the versioned structured reply envelope. Native deltas/notifications/exit status are never action authority.
  - Validate exact conversation/context/assessment binding, proposal size/path/preimage/registered retests and safe postimage-to-diff ingestion. Reject malformed envelopes, owner-credential escalation and native direct apply; route proposals through the dispatcher.
  - Add fake-protocol error/partial/restart/late-reply tests and explicit real-native admission harness cases. Managed execution stays disabled until observed private-read/mutation/egress/auth-isolation gates pass under root-enabled scope.
  - _Requirements: R4.4, R4.5, R4.7, R4.8, R5.15, R5.17, R5.18, R5.19, R6.8, R6.10, R6.13, R7.12, R7.13_

- [ ] 11. Implement guarded one-file remediation and retest orchestration
  - Owner: dream-engine; root controlled fixture reset integration. Depends on checkpoint 9 and prior tasks in the current block.
  - Implement reviewed path/preimage/postimage/diff/grant binding and controlled exclusive-write admission. Fsync staged file and commit journal before replacement; sync directory before applied publication. Uncontrolled live targets and wider patches remain reviewable proposals.
  - Implement crash/preimage/postimage/conflict recovery without overwriting user changes. Apply invalidates affected current assessments; new-manifest retests create discoverable successor runs and retain before/after/regression attempts.
  - Test external edits, dirty content, symlinks, denied scope, sync failures, cancellation races, ambiguous writes and failed/inconsistent retests. Technical verification never closes separate legal/manual review.
  - _Requirements: R1.8, R3.19, R4.5, R5.6, R5.7, R5.8, R5.9, R5.18, R5.19, R5.20, R6.12, R7.13_

- [ ] 12. Checkpoint — Verify agent admission and remediation tests
  - Owner: root. Blocking after tasks 10, 11. Run the full accumulated test suite, fix failures, and review scoped handbacks before advancing.
  - Run the full accumulated suite plus proposal-ingestion, native-isolation admission and journal/sync/conflict/retest cases. Real admission is required before enabling real managed execution; skipped/fake-only admission leaves that capability blocked.
  - _Requirements: R4.4, R4.8, R5.6, R5.7, R5.19, R7.12, R7.13_

- [ ] 13. Implement the complete local dashboard workflow
  - Owner: dream-ui; root generated contract/API. Depends on checkpoint 12 and prior tasks in the current block.
  - Build the project/scope form, stable filterable finding list, per-obligation detail, safe before/after evidence/source/legal views, bounded relationship drill-down, finding-scoped chat/diff/retest and live timeline.
  - Implement query/replay/receipt recovery, explicit successor navigation, origin/execution binding, separate current freshness, retained offline inspection and truthful proposed/running/applied-awaiting-verification/verified/failed/blocked states.
  - Implement keyboard/focus/status/reflow/reduced-motion and inert-content boundaries with meaningful component tests; source mapping, missing evidence, redaction and legal/manual gaps stay explicit.
  - _Requirements: R3.18, R4.7, R4.17, R5.2, R5.3, R5.12, R5.13, R5.14, R5.15, R5.16, R5.17, R5.18, R5.19, R5.20, R6.10, R6.11, R6.12, R6.13, R6.14, R7.12, R7.13_

- [ ] 14. Write and run the first integrated product-loop acceptance harness
  - Owner: Root integration/e2e/runtime; dream-ui browser-test author. Depends on checkpoint 12 and prior tasks in the current block.
  - Add automated synthetic backend/browser cases for scan → selected failure/evidence → bound conversation/proposal → authorized controlled patch → reset/redeploy → actual affected/regression retest, with matching CLI identifiers and retained history.
  - Add pass/unknown/stale-source/missing-tool/manual-gap and reload/lost-response/successor/current-freshness/cancellation cases. Assert the manual item stays open and no skipped/blocked check turns into success.
  - Extend the declared pinned browser-matrix harness with a keyboard-only dashboard journey, visible focus/focus retention during replay and navigation, accessible names, meaningful status announcements, color-independent status and zoom/reflow. Exercise hostile/secret-bearing evidence and blocked-redaction recovery in this actual built-app path.
  - Provide separate fake and root-enabled real native/provider modes. Fake protocol success cannot satisfy A1/R7.12; completion requires one bounded real conversation with observed enforced isolation and approved synthetic processing/fresh-conversation scope.
  - _Requirements: R3.9, R3.10, R4.4, R4.7, R4.8, R4.17, R5.4, R5.7, R5.15, R5.16, R5.17, R5.19, R6.10, R6.14, R7.5, R7.12, R7.13_

- [ ] 15. Checkpoint — Verify the first complete product loop
  - Owner: root. Blocking after tasks 13, 14. Run the full accumulated test suite, fix failures, and review scoped handbacks before advancing.
  - Run backend/frontend suites, the declared pinned browser matrix and explicitly authorized bounded real A1 case. Include fail-closed evidence handling and the dashboard accessibility journey; root also performs the declared manual assistive-technology/status-announcement review. Failed/unperformed checks block the corresponding accessibility acceptance. The milestone is incomplete without the real conversation, enforced boundary, actual retest and retained manual gap; fake-only success is partial evidence.
  - _Requirements: R4.7, R4.8, R4.17, R5.12, R5.15, R5.19, R6.14, R7.5, R7.12, R7.13_

- [ ] 16. Implement lifecycle and security verification profiles
  - Owner: dream-engine checks; dream-legal review/control resources. Depends on checkpoint 15 and prior tasks in the current block.
  - Add authorized synthetic access/export/correction/deletion/objection/expiry procedures, proportional identity and sourced deadline/extension/refusal/recipient cases, with primary/cache/index/log/downstream/restore coverage and justified exceptions.
  - Add bounded tenant/role/access, sensitive-log, dependency/configuration and recipient-flow checks using reviewed capabilities. Record unsupported probes, unavailable stores and unfrozen external inputs explicitly.
  - Wire profiles into planning/reporting and test observed failure, protective counter-evidence, missing access and disagreement without promoting detector heuristics to lawful-processing proof.
  - _Requirements: R1.9, R3.1, R3.4, R3.5, R3.8, R3.9, R3.10, R3.12, R3.13, R3.14, R4.6, R4.10, R5.10, R7.5, R7.11_

- [ ] 17. Implement commerce and accessibility process profiles
  - Owner: dream-engine checks; dream-legal control resources; dream-ui relevant views. Depends on checkpoint 15 and prior tasks in the current block.
  - Add synthetic disclosure/price/recurrence/extras/claims/reviews/marketing and confirmation/cancellation/withdrawal/refund/unsubscribe cases, classified by reviewed contract/customer/jurisdiction facts.
  - Integrate pinned local axe output and keyboard assertions, preserving incomplete/inapplicable and separate assistive-technology/document/whole-process review. Legal standard/version mapping remains explicit.
  - Wire process/role/consent/language/region sampling and evidence into the same finding/detail model; test technical passes with remaining manual/legal gaps.
  - _Requirements: R1.5, R1.11, R3.6, R3.7, R3.12, R3.15, R3.16, R4.5, R5.3, R5.4, R6.14, R7.5_

- [ ] 18. Checkpoint — Verify lifecycle, commerce and accessibility tests
  - Owner: root. Blocking after tasks 16, 17. Run the full accumulated test suite, fix failures, and review scoped handbacks before advancing.
  - Run the full accumulated suite and authorized synthetic profiles, including downstream gaps, exceptions, whole-process/manual outcomes and negative controls.
  - _Requirements: R3.4, R3.6, R3.7, R3.13, R3.14, R3.15, R3.16, R7.5_

- [ ] 19. Implement pinned Graphify import and authorized local discovery
  - Owner: dream-engine graph adapter; dream-ui relationship projection. Depends on checkpoint 18 and prior tasks in the current block.
  - Implement the tested producer/schema adapter, immutable pin/digest and source-manifest/version/diagnostic checks. Preserve structural/static-inferred/semantic/ambiguous/unknown origins and missing/external nodes.
  - Implement bounded finding → component → activity → obligation queries and graph-dependent freshness without a graph database or core inference engine. Missing graphs block only graph-backed navigation.
  - Add malformed endpoint/schema/path/size/stale fixtures and code-only producer admission tests. Semantic provider/media/hooks/database extras remain separately scoped, not automatic scan fallbacks.
  - _Requirements: R1.12, R3.9, R3.20, R4.8, R5.14, R5.20, R7.11, R7.13_

- [ ] 20. Implement maintainable family catalogs and source-review refresh
  - Owner: dream-legal; root approval/schema integration. Depends on checkpoint 18 and prior tasks in the current block.
  - Extend original executable control/source resources across all candidate families, role/threshold/date branches and targeted organizational/vendor/transfer/incident/AI evidence methods. Unsupported specialist/national methods stay registered gaps.
  - Wire on-demand national source targets, official act/amendment/correction/case-law/final-guidance and translation review, proposed updates, obsolete template checks and dependent reassessment. An accepted corpus entry requires verified official authority and reviewer acceptance, not a generated citation.
  - Add current/stale/unavailable/superseded and conditional/exception/country fixtures, plus import-provenance/license and legally incorrect-rule rejection cases. No all-country or full-catalog claim from fixture counts.
  - _Requirements: R1.3, R1.5, R1.6, R1.7, R1.10, R1.11, R2.1, R2.2, R2.3, R2.4, R2.5, R2.6, R2.7, R2.8, R2.9, R2.10, R4.1, R4.3, R4.10, R4.11, R4.12, R4.13, R4.14, R4.15, R5.4, R5.10, R7.10, R7.11_

- [ ] 21. Checkpoint — Verify graph, source and catalog tests
  - Owner: root. Blocking after tasks 19, 20. Run the full accumulated test suite, fix failures, and review scoped handbacks before advancing.
  - Run the full accumulated suite, pinned producer fixtures and source/overlay/update/counterexample cases. Real source acceptance and graph capability proofs stay distinct from synthetic expectations.
  - _Requirements: R2.1, R2.8, R3.20, R5.20, R7.10, R7.11_

- [ ] 22. Complete private evidence lifecycle, reports and audit comparison
  - Owner: dream-engine persistence/reporting; dream-ui relevant views. Depends on checkpoint 21 and prior tasks in the current block.
  - Complete and broaden the evidence handling already gated in tasks 4/8/9: owner-controlled retention/purge/tombstones, backup/migration compatibility and additional proven artifact support. Unknown/failed redaction remains blocked; do not claim unrestricted trace sanitization.
  - Implement human/machine reports with per-obligation dispositions, impacts/parties/authority/method/owner/action/date/residual risk, separate fact/code/deployment/law/finding comparisons and partial/resumable history.
  - Test secret-bearing/hostile artifacts, cross-project references, missing/deleted evidence, denied destinations, disconnected providers/sources and disk-full/restart cases; no global compliance score.
  - _Requirements: R4.2, R4.7, R4.8, R4.9, R4.16, R4.17, R5.1, R5.2, R5.3, R5.4, R5.5, R5.8, R5.9, R5.11, R6.12, R6.13, R7.8, R7.13_

- [ ] 23. Build canonical host capability and conflict-safe installer
  - Owner: Root canonical instructions/provenance/manifest; dream-hosts adapters/installer. Depends on checkpoint 21 and prior tasks in the current block.
  - Create complete functional SKILL/workflow/resources for the shared CLI and wire the existing library metadata/adapters without truncating upstream instructions. Keep runtime/tool installation distinct from copying skill text.
  - Implement inventory and documented discovery adapters for detected hosts/aliases, separate discovery/engine-invocation/managed-bridge statuses and restricted delegated launch support where proved.
  - Implement plan/apply, owned receipts, idempotent repeated install, edited/unowned-path conflicts, staged upgrade/migration and precisely scoped uninstall. Test against temporary owned destination fixtures; no actual global settings mutation in a unit test.
  - _Requirements: R4.9, R6.1, R6.2, R6.3, R6.4, R6.5, R6.6, R6.8, R6.9, R6.10, R7.6, R7.8, R7.11_

- [ ] 24. Checkpoint — Verify evidence and installation lifecycle tests
  - Owner: root. Blocking after tasks 22, 23. Run the full accumulated test suite, fix failures, and review scoped handbacks before advancing.
  - Run the full accumulated suite plus malicious artifact, redaction/retention/purge, installer conflict/repeat/interruption and library packaging/adapters tests.
  - _Requirements: R4.7, R4.9, R6.5, R6.6, R7.6, R7.8_

- [ ] 25. Implement seven-host acceptance and restricted-invocation harnesses
  - Owner: dream-hosts tests/adapter fixes; root real acceptance execution. Depends on checkpoint 24 and prior tasks in the current block.
  - Add discovery/activation/shared-engine smoke harnesses for Codex, Claude, AGY, Gemini, Copilot, Cursor Agent and Pi, including actual executable identity/alias, unrelated/nested synthetic repositories, collisions and missing runtime/source outcomes.
  - Assert permission denial, owner-credential separation, structured errors, actual completed check evidence and provider failure despite accepted/zero-exit transport. Preserve existing host auth/settings/conversations; report each blocker independently.
  - Keep fake contract fixtures distinct from explicitly root-enabled real native/provider/global-install acceptance. New native test conversations and processing scope require Owner instruction; no all-host completion when a required case is skipped or unsupported.
  - _Requirements: R4.4, R4.5, R4.8, R6.1, R6.3, R6.4, R6.7, R6.8, R6.9, R6.10, R6.13, R7.5, R7.6, R7.9_

- [ ] 26. Implement reproducible release checks and final regression coverage
  - Owner: Root package/CI/validator/integration; workers scoped fixes. Depends on checkpoint 24 and prior tasks in the current block.
  - Implement distribution inventory, runtime/static-asset/skill bundling, dependency/rule license/pin checks, managed adapter drift, private-file/symlink exclusions and clean candidate verification. Preserve existing edits and source attribution.
  - Implement scoped diff/candidate and read-only remote-revision/package-version verification commands with mocked transport tests. This codes publication verification; it does not commit, push, deploy or install globally.
  - Complete regression cases A1–A10 and a requirement/acceptance ledger that reports actual passed/blocked/not-run gates, role handback evidence and unknown context counts without manufactured benchmark or completeness claims.
  - _Requirements: R2.8, R5.4, R6.2, R7.1, R7.2, R7.3, R7.4, R7.5, R7.6, R7.7, R7.8, R7.9, R7.10, R7.11, R7.12, R7.13_

- [ ] 27. Checkpoint — Verify all required tests and final gates
  - Owner: root. Blocking after tasks 25, 26. Run the full accumulated test suite, fix failures, and review scoped handbacks before advancing.
  - Run library checks, application/backend/frontend/build/browser suites, release-content validation and all separately authorized actual host/product acceptance. Resolve failed tests before completion; blocked/skipped real gates remain explicit and prevent corresponding completion claims.
  - _Requirements: R6.7, R6.8, R7.5, R7.6, R7.8, R7.9, R7.12, R7.13_

## Operational completion outside coding checkboxes

The task-generation workflow excludes deployment, user testing and publication operations from coding tasks. Code/harness completion therefore does not equal the owner's entire goal. Real source/country review, permitted native conversation/host acceptance, actual conflict-safe global installation and scoped GitHub publication/remote verification remain required operational follow-through under applicable Owner authorization. Do not mark a blocked real gate satisfied because its harness exists. No such operation happens in this planning wave; no commits/pushes or global settings changes are authorized by this document alone.

The first concrete implementation objective is checkpoint 15's tested local product loop, with the earlier feasibility/admission gates preserved. Checkpoint 27 adds broader controls, all-host results and release readiness; unresolved countries/domains/host capabilities remain explicit rather than silently excluded.

## Requirement coverage index

Every approved criterion is referenced by at least one coding/check task. Operational requirements are linked to their supporting enforcement or acceptance code, with real operator completion distinguished above.

| Criterion | Coding/check tasks |
| --- | --- |
| R1.1 | 1, 7 |
| R1.2 | 1, 7 |
| R1.3 | 7, 20 |
| R1.4 | 1, 7 |
| R1.5 | 7, 17, 20 |
| R1.6 | 7, 20 |
| R1.7 | 7, 20 |
| R1.8 | 7, 11 |
| R1.9 | 7, 8, 16 |
| R1.10 | 7, 20 |
| R1.11 | 7, 17, 20 |
| R1.12 | 19 |
| R2.1 | 7, 20, 21 |
| R2.2 | 1, 7, 20 |
| R2.3 | 7, 20 |
| R2.4 | 1, 7, 20 |
| R2.5 | 7, 20 |
| R2.6 | 7, 20 |
| R2.7 | 4, 7, 9, 20 |
| R2.8 | 7, 20, 21, 26 |
| R2.9 | 7, 20 |
| R2.10 | 7, 20 |
| R3.1 | 8, 16 |
| R3.2 | 8 |
| R3.3 | 8 |
| R3.4 | 16, 18 |
| R3.5 | 16 |
| R3.6 | 17, 18 |
| R3.7 | 17, 18 |
| R3.8 | 8, 16 |
| R3.9 | 1, 4, 8, 9, 14, 16, 19 |
| R3.10 | 8, 14, 16 |
| R3.11 | 8 |
| R3.12 | 8, 16, 17 |
| R3.13 | 16, 18 |
| R3.14 | 16, 18 |
| R3.15 | 17, 18 |
| R3.16 | 17, 18 |
| R3.17 | 8 |
| R3.18 | 8, 13 |
| R3.19 | 4, 8, 11 |
| R3.20 | 19, 21 |
| R4.1 | 7, 20 |
| R4.2 | 4, 7, 22 |
| R4.3 | 7, 20 |
| R4.4 | 2, 3, 5, 10, 12, 14, 25 |
| R4.5 | 2, 5, 10, 11, 17, 25 |
| R4.6 | 2, 8, 16 |
| R4.7 | 2, 4, 8, 9, 10, 13, 14, 15, 22, 24 |
| R4.8 | 2, 3, 5, 8, 9, 10, 12, 14, 15, 19, 22, 25 |
| R4.9 | 4, 22, 23, 24 |
| R4.10 | 7, 16, 20 |
| R4.11 | 7, 20 |
| R4.12 | 7, 20 |
| R4.13 | 7, 20 |
| R4.14 | 7, 20 |
| R4.15 | 7, 20 |
| R4.16 | 2, 5, 6, 22 |
| R4.17 | 4, 5, 8, 9, 13, 14, 15, 22 |
| R5.1 | 1, 22 |
| R5.2 | 1, 7, 13, 22 |
| R5.3 | 1, 4, 9, 13, 17, 22 |
| R5.4 | 7, 9, 14, 17, 20, 22, 26 |
| R5.5 | 7, 22 |
| R5.6 | 11, 12 |
| R5.7 | 11, 12, 14 |
| R5.8 | 4, 11, 22 |
| R5.9 | 4, 11, 22 |
| R5.10 | 7, 16, 20 |
| R5.11 | 7, 22 |
| R5.12 | 13, 15 |
| R5.13 | 13 |
| R5.14 | 13, 19 |
| R5.15 | 5, 6, 10, 13, 14, 15 |
| R5.16 | 5, 6, 13, 14 |
| R5.17 | 5, 10, 13, 14 |
| R5.18 | 5, 10, 11, 13 |
| R5.19 | 10, 11, 12, 13, 14, 15 |
| R5.20 | 5, 11, 13, 19, 21 |
| R6.1 | 23, 25 |
| R6.2 | 1, 23, 26 |
| R6.3 | 5, 23, 25 |
| R6.4 | 23, 25 |
| R6.5 | 23, 24 |
| R6.6 | 23, 24 |
| R6.7 | 25, 27 |
| R6.8 | 2, 10, 23, 25, 27 |
| R6.9 | 2, 23, 25 |
| R6.10 | 1, 4, 5, 6, 10, 13, 14, 23, 25 |
| R6.11 | 5, 13 |
| R6.12 | 4, 5, 6, 11, 13, 22 |
| R6.13 | 4, 10, 13, 22, 25 |
| R6.14 | 13, 14, 15, 17 |
| R7.1 | 3, 26 |
| R7.2 | 26 |
| R7.3 | 3, 26 |
| R7.4 | 26 |
| R7.5 | 3, 8, 9, 14, 15, 16, 17, 18, 25, 26, 27 |
| R7.6 | 23, 24, 25, 26, 27 |
| R7.7 | 26 |
| R7.8 | 22, 23, 24, 26, 27 |
| R7.9 | 25, 26, 27 |
| R7.10 | 7, 9, 20, 21, 26 |
| R7.11 | 2, 8, 9, 16, 19, 20, 21, 23, 26 |
| R7.12 | 10, 12, 13, 14, 15, 26, 27 |
| R7.13 | 2, 3, 4, 5, 6, 10, 11, 12, 13, 14, 15, 19, 22, 26, 27 |
