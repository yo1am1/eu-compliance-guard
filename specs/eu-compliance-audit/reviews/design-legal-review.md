# Final integrated design review — legal controls

Date: 2026-10-14. Outcome: approval withheld pending two contract corrections. Review is document-only; no implementation or legal-corpus acceptance.

Sources inspected: [integrated design](../design.md), especially sections 3–5, 8 and 12–14; [preserved legal review](legal-controls.md); [approved requirements](../requirements.md); [research baseline](../research.md). Findings derive from these contracts, not new legal propositions. No additional external research was needed.

## Material corrections

1. **Preserve dispositions per obligation when findings share controls.** [design.md:167](../design.md#3-domain-models-and-interfaces) defines a Finding with multiple `obligation_ids` but only one applicability, rationale, outcome, freshness and manual-review state. Section 3 correctly retains supplementary applicability/review records; however, their projection into this shared finding is undefined. A shared tracking control can concern an applicable privacy obligation and an unresolved national device-access obligation. A single displayed disposition can obscure the unresolved item or imply that a technical pass discharges both.

   **Correction:** expose revision-bound applicability/review references per obligation in the finding projection, using the existing supplementary records. Retain the shared technical assertion separately; define summary states as summaries rather than dispositions for every obligation. Report completeness from the obligation register, including obligations without findings. Add an A2 case with one shared control, different applicability decisions and one outstanding manual review; each disposition must survive UI/CLI reporting. **Criteria:** R1.4, R1.7, R5.2–R5.4, R5.19–R5.20.

2. **Represent retrieval failure before any legal source has been fetched.** [design.md:115](../design.md#3-domain-models-and-interfaces) requires `LegalSource.retrieved_at` and `content_digest`; `SourceReview` requires an existing source revision. Sections 4 and 11 require failed attempts and unknown last-success dates to remain inspectable. The first inaccessible official source has neither retrieved bytes nor a previously verified revision. No concrete record currently distinguishes that attempted source from a successfully retrieved source.

   **Correction:** define a source-attempt record with intended official URL/identifier, attempted time, failure and optional last successful source revision, or an equivalent explicitly discriminated unavailable-source form. Do not fabricate a retrieval timestamp or hash the challenge/error page as legal text. Keep retained successful bytes and their review state separate from later failed attempts. A2 must cover first retrieval failure, later refresh failure and translation failure, all without a current-law claim. **Criteria:** R2.2, R2.7, R5.2, R6.13.

## Preserved coverage and remaining gates

The integration retains all eleven family screenings, conditional roles/exemptions, national-overlay gaps, source typing and review chains, declared versus documented versus independently verified evidence, targeted governance/vendor/incident/AI requests, counter-evidence validation and manual completeness. It carries all five R7.10 counterexamples and R7.11 adoption checks. Duty, recommendation, engineering practice and synthetic authority remain distinguished; synthetic passing cases do not establish real national coverage. These principles need no broader redesign.

Official source-chain/case-law acceptance, reviewed national overlays, deadline details and accessibility mappings remain future corpus gates. Containment, native-host compatibility and actual end-to-end acceptance remain future feasibility gates, not additional legal-design findings. No accepted country corpus or executed acceptance is asserted.

## Checks and completion

Read-only checks: read AGENTS.md, safety/Git rules and review workflow; read the preserved legal review; inspect numbered contract passages, assigned design sections and all relevant traceability rows; inspect scoped Git diff/status; compare SHA-256 hashes of requirements, research and all four first reviews before/after this write; read back this new report. Only this previously absent report was created, using exclusive creation. No prior report, master design, requirement, source, export or manifest was edited.

Completed: bounded final review. Remaining approval blockers: the two projection/retrieval contracts above. No tests, scans, runtime/provider work or agents launched. Actual context usage: unknown.
