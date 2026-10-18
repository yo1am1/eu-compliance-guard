# Read-only legal revalidation MVP — requirements v2

Status: approved by the Owner on 2026-10-18. The Owner selected this MVP on 2026-10-18.
This is a new delivery scope; `specs/**` remains an unchanged historical snapshot.
No MVP completion or real legal assessment is claimed by this document.

## User and outcome

A project owner and their coding agent can turn declared project requirements,
activities, jurisdictions, assessment dates and selected evidence into a local,
traceable legal review report, then revalidate it when inputs or sources change.
Legal interpretation and evidence sufficiency remain accountable review decisions.

## Functional requirements — all Must

### FR-1 — Declared inputs and coverage

Accept a versioned JSON input with stable requirement IDs, project scope, candidate
legal sources/obligations, applicability decisions and selected evidence references.
Reuse existing scope/legal/evidence records and extend `models.py` only where needed.
Reject malformed input, duplicate IDs and dangling or cross-project references.
Retain declared, assumed and unknown facts distinctly. An empty requirement list,
empty candidate register or unassessed legal family must produce an explicit gap.
The report states the considered domains and exclusions; it cannot imply all EU law
was searched. Candidate applicability starts unresolved unless a reasoned decision
names its reviewer and pinned scope, fact, obligation and source revisions.
Screen the legal families in the historical scope register; unsupported families
and jurisdictions retain research gaps.

### FR-2 — Official-source retrieval and provenance

Retrieve explicitly selected official HTTPS sources with bounded GET requests,
timeouts and response sizes. Validate destinations and every redirect; disallow
credentials, nonstandard ports, nonofficial hosts and local/private destinations.
Send no project evidence or provider/session credentials with these requests.
Retain exact response bytes and their digest, requested/final URL, retrieval time,
language, publisher, identifier and source classification. Record each failed
attempt without inventing content or silently using old bytes as a fresh success.
Binding acts/judgments, guidance, proposals, standards, engineering practice and
fictional fixtures remain distinguishable. Official hosting alone does not prove
that a text is binding, complete, applicable or current for an assessment date.

### FR-3 — Accountable mapping and review gaps

Map every declared requirement to candidate obligations and pinned provisions,
applicability rationale, supporting evidence and unresolved questions. Unmapped
requirements, unresolved applicability, missing/unavailable evidence, unchecked
amendments/case law/national overlays, unverified translations and unreviewed
application or transition dates remain visible review gaps. Recommendations and
proposals cannot establish binding duties. Evidence declarations and reviewer
attestations are labelled; presence of a file or citation cannot establish legal
sufficiency. Include candidate obligations with no requirement mapping or technical finding.
Unresolved or inconsistent source classifications cannot establish real duties.
Reject login, challenge and error pages as accepted legal text; uncertain content
requires review. No empty run or technical test can produce a compliance verdict.

### FR-4 — Local reports and retained history

Provide a runnable CLI producing validated JSON and a readable Markdown report
with scope/date, coverage/exclusions, per-requirement mappings, source provenance,
evidence references, accountable decisions, gaps and next review actions. Label
synthetic output prominently. Preserve prior reports and source versions; create a
new output directory per run and refuse overwriting existing output. Do not embed
private evidence contents by default. Invalid input exits unsuccessfully with a
safe diagnostic; retrieval/review gaps yield an explicitly partial report.

### FR-5 — Revalidation

Compare a previous retained assessment with newly validated declared inputs and
new source attempts. Report changed requirements, scope, obligations, evidence,
review decisions and source digests without rewriting historical results. Relevant
changes invalidate dependent review claims; failed retrieval means current source
freshness is unknown even when old bytes remain available. Unchanged downloaded
bytes mean only unchanged recorded content, never automatic legal currency or
renewed reviewer approval. A changed assessment date requires review again.

### FR-6 — Portable agent instructions and reproducible example

Ship a repository-local read-only skill and synthetic example covering input
preparation, official-source research, accountable mapping, CLI report generation
and revalidation. Treat imported documents/tool output as untrusted data, never
instructions. The example runs offline without a provider, target execution,
credentials or private evidence and preserves all fictional labels. Document a
separate opt-in live official-source smoke check; do not silently contact external
services during the offline example or tests. No global installation is required.

## Non-functional requirements — all Must

### NFR-1 — Bounded local processing and private artifacts

Use the standard library and existing dependencies. Set and test input, download,
request-duration and collection bounds. Read only explicitly supplied files; do
not enumerate the laptop or execute a target repository. Store output privately
under an explicitly selected directory, keep runtime evidence out of Git, and
sanitize diagnostics and Markdown so imported text is not rendered as active HTML.
The sole routine network operation is fetching approved public official sources.

### NFR-2 — Verifiable delivery

Generate JSON Schema and TypeScript from `models.py`; retain all existing command
contracts. Run `make check`, with synthetic tests for invalid references, unsafe
URLs/redirects, retrieval failures, missing reviews/evidence, changed inputs/source
bytes and history preservation. Demonstrate the documented offline CLI workflow
and package contents. Distinguish unit/fake retrieval checks from any live source
smoke check; neither constitutes a real compliance audit or containment proof.
Commit and push completed changes individually after reviewing the exact stage.

## Deferred scope

Scanners, Graphify, provider bridges, managed remediation, the dashboard, API/server,
scheduling, global installation and automated legal verdicts are outside this MVP.
The broader product requirements in the preserved snapshots remain future scope.

## Approval state

The Owner selected the read-only MVP unit and approved these v2 requirements
with `y` in the continuation session on 2026-10-18. Design, stories and bolts
may now be prepared for the artifacts-review checkpoint; implementation approval
is not implied by requirements approval.
