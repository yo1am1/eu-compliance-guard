# Read-only legal revalidation MVP — design

Status: approved by the Owner for construction, following approval of
[requirements](requirements.md) on 2026-10-18. This describes future implementation;
the foundation has no runnable legal workflow. No current law or legal corpus was
verified for this design. Historical `specs/**` remains unchanged.

## Delivery boundary

One local CLI unit accepts declared JSON, reads selected files, retrieves explicitly
selected public official sources when enabled, assembles accountable review records,
and writes a new private report. Python 3.12+, existing Pydantic, and the standard
library suffice. No API, database, queue, scheduler, browser, provider, scanner,
Graphify service, target-code execution, remediation or OS-policy change is needed.

Implementation responsibilities are small: `__main__.py` handles argparse and exit
codes; `revalidation.py` validates joins, assembles reports, compares dependencies
and retains artifacts; `sources.py` owns network policy; `report.py` renders escaped
Markdown. Keep persistence with orchestration until separation has a concrete need.
All public records originate in `models.py`. Existing `agent.py`, `execution.py`,
frontend UI, and the 16-operation `Command` union stay outside the MVP path.

## CLI contract and reproducible workflow

These are the exact intended commands after construction, not commands available
today. `--output` names the new run directory itself; it must not exist. Network is
disabled by default. `--offline` states that choice explicitly; it conflicts with
`--fetch-official`. The only subcommand is `revalidate`; a first run omits `--previous`.

```sh
uv run --locked python -m eu_compliance_guard --help
uv run --locked python -m eu_compliance_guard revalidate --help
eucg_example_dir=$(mktemp -d /tmp/eucg-example.XXXXXX)
uv run --locked python -m eu_compliance_guard revalidate \
  --input fixtures/revalidation-synthetic.json \
  --output "$eucg_example_dir/run-001" --offline
uv run --locked python -m eu_compliance_guard revalidate \
  --input fixtures/revalidation-synthetic-changed.json \
  --previous "$eucg_example_dir/run-001" \
  --output "$eucg_example_dir/run-002" --offline
```

The two future fixtures include explicit references to small fictional source and
evidence files. Paths resolve relative to the declaration file's parent, using the
existing normalized `RelativePath` rules. No implicit repository root, glob, walk,
URL-following evidence importer or environment credential lookup is permitted.

An opt-in smoke check uses a separately prepared declaration whose source targets
the owner selected and whose private evidence list is empty:

```sh
eucg_live_dir=$(mktemp -d /tmp/eucg-live.XXXXXX)
uv run --locked python -m eu_compliance_guard revalidate \
  --input /tmp/eucg-live-input/declarations.json \
  --output "$eucg_live_dir/run-001" --fetch-official
```

`mktemp -d` creates an unused private parent; keep the task-specific shell variables in
the same shell for these commands. Only the
selected immediate output parent must be private; public system ancestors such as
`/tmp` may remain public, but symlink components are rejected throughout the path.
The live command fetches only those targets; it is not legal research completeness or a real
compliance audit. Do not put a live target in the default offline example or tests.

Exit 0 means validated JSON and Markdown were durably published, including a
possibly partial report with review gaps. Exit 2 means invalid input, capacity
violation, unsafe output or an I/O failure preventing a usable report. Argparse
errors also exit 2. Interrupt exits 130 without a finalized report. Source failures
become attempts and partial reports rather than a fabricated successful source.
Stdout prints only run ID, report paths and processing state; stderr uses stable
safe codes, never raw validation payloads, evidence excerpts or URL queries.

## Records and validation

`Record`, `parse_record`, `canonical_json` and `content_digest` remain the shared
validation, canonicalization and exact-byte digest helpers. Frozen Pydantic records
are not a storage guarantee. `HttpURL` validates syntax and allows HTTP; it is not
the retrieval authorization policy. Add only missing records to `models.py` and
generate JSON Schema and TypeScript through `make contracts`.

| Record | Responsibility in this unit |
| --- | --- |
| Existing `Scope`, `ProcessingActivity`, `Fact` | Scope/date/jurisdictions and declared, assumed, observed or unknown facts. Preserve basis, conflicts and owner. `permission_id` is a reference, not proof of scanner authorization. |
| New `DeclaredRequirement` | Stable ID/revision, project, statement, origin digest/locator, fact/activity/evidence references. This is owner intent, separate from a sourced obligation. |
| New `SourceTarget` | Stable ID/revision, legal family, intended identifier/type/publisher/language/jurisdiction, selected official URL and explicit approved official redirect hosts. Candidate metadata is a declaration until reviewed. |
| Existing `LegalSource`, `SourceRef`, `SourceAttempt`, `ProvisionRef` | Immutable successful bytes/revisions, unsuccessful attempts, last-successful references and exact provision pins. Use final URL in `LegalSource.url`. No invented source for a first failure. |
| New nested retrieval provenance record | Attempt ID, requested/final URL, bounded redirect chain, UTC start/end, HTTP status/media type, byte count/digest and relative retained artifact path. Record failure codes; do not dump response headers or cookies. |
| Existing `SourceReview` | Named review for pinned source/date, act/amendment chain, case law, national overlays, entry/application/transition dates and gaps. Empty chain lists are not proof they were checked. |
| New `FamilyScreening` | One entry for each historical candidate family, pinned scope/date, three-state applicability, rationale, reviewer and supporting fact/source references or research questions. Unreviewed screening remains unresolved. |
| Existing `Obligation`, optional `Control` | Candidate duty/recommendation, provision pins, conditions/exceptions, methods and limitations. Keep controls only when supplied; no condition language or executable checks. |
| New `ApplicabilityDecision` | ID/revision, project, obligation revision, scope/fact/source pins, date/jurisdiction, condition/exception answers, applicability, rationale, evidence, named reviewer/time and unresolved questions. Fills `applicability_decision_id`. |
| Existing `Evidence` plus explicit local file reference | Provenance, digest, availability, redaction, retention and manifest/run identity. Input references declare expected digests and selected paths; output records actual observed availability. No evidence content in the report. |
| New `EvidenceReview` | ID/revision, project, obligation, requested evidence/period/owner, evidence pins, reviewed/insufficient/unresolved status, named reviewer/time, rationale and contrary/missing evidence. Fills method `review_ids`. |
| Existing `InputManifest`, `SourceFile`, `AuditRun`, `Budgets` | Selected file hashes, scope/fact/registry/config/source/tool pins, predecessor run and processing state. Empty browser/graph/attempt collections mean outside scope. Compute manifest digest from canonical fields excluding its own digest. |
| Existing `MethodDisposition`, `ObligationDisposition` | One disposition per candidate obligation, including obligations with no requirement mapping or technical finding. Keep applicability separate from documentary support. |
| New `RequirementAssessment` | Requirement pin, disposition/review/evidence dependencies, supported/conflicting/unresolved/outside-declared-assessment description, rationale and gaps. No legal-compliance Boolean. |
| Existing `CurrentAssessment` | Successor's freshness overlay targeting a historical obligation disposition. Preserve predecessor outcome. No new finding is needed to use this record. |
| New `RevalidationInput`, `RevalidationBundle` | Versioned input envelope and validated retained output; project/synthetic identity, the above collections, coverage/gaps, parent reference and dependency comparison. Do not repurpose UI `Snapshot` or add API commands. |

Input may carry explicitly selected prior source records/reviews and attestations;
it must pin their retained bytes. A bundle rebinds accepted evidence/dispositions to
the new run while retaining original review identity, time and dependency pins.
Historical references resolve only against the explicitly supplied predecessor,
never against ambient disk state. New review records need not be bound to one run;
the bundle records their use in a particular run.

Bundle validators reject duplicate IDs within each entity kind, duplicate
ID/revision pairs, dangling references, wrong revisions, cross-project references,
wrong run/manifest membership and provision/target mismatches. References include
their entity kind; equal text IDs in different kinds are not interchangeable.
Changed semantic content under an unchanged ID/revision is invalid when a previous
record is available. Same-byte retrieval metadata may differ without changing the
content revision. Validate nested collection bounds as well as top-level lists.

No requirement, candidate register or family screening can disappear because it
has no finding. An empty requirement list or register produces explicit coverage
gaps. Missing family entries are expanded into unresolved screenings with research
actions; supplied duplicate family entries are invalid. Unsupported jurisdictions,
including separately based EEA/non-EU extensions, retain gaps.

## Official-source retrieval boundary

The initial code-reviewed exact-host registry is `eur-lex.europa.eu`,
`curia.europa.eu`, `commission.europa.eu`, `digital-strategy.ec.europa.eu` and
`www.edpb.europa.eu`. This is an engineering retrieval policy, not a declaration
that these hosts exhaust official law. Every input target and allowed redirect
host must also belong to that registry. No suffix wildcard or input-added host is
accepted. National or other official hosts require a reviewed registry change;
until then leave an unsupported-source/jurisdiction gap. No discovery crawl.

For each explicitly enabled target:

1. Parse with `urllib.parse`; require HTTPS, port absent or 443, an exact normalized
   ASCII registered hostname and no userinfo, fragment, control/whitespace,
   backslash, IP literal or ambiguous encoded authority. Bound URL length at the
   existing 4,096 characters. Use only the selected URL path/query; never build it
   from project statements or evidence. Redirect URLs receive identical checks.
2. Resolve A/AAAA using `socket.getaddrinfo` inside a disposable standard-library
   `multiprocessing` retrieval helper. Reject the entire answer set if any address
   is non-global, loopback, private, link-local, multicast, reserved, unspecified
   or IPv4-mapped IPv6. Reject more than 16 addresses. Connect to a validated
   numeric address directly, then verify the connected peer address; never resolve
   the hostname again between checking and connecting. Retry addresses only within
   the same deadline. This closes the check/connect DNS-rebinding gap.
3. Use `http.client` over the pinned socket with
   `ssl.create_default_context()` and original host as TLS `server_hostname` and
   HTTP Host. Certificate and hostname verification remain mandatory. No proxy
   environment, cookies, authentication, `.netrc`, client certificate or provider
   credentials. Send only GET, a fixed user-agent/accept header and
   `Accept-Encoding: identity`; reject compressed bodies rather than decompressing
   unbounded content. Do not use a default opener with automatic redirects.
4. Follow only 301/302/303/307/308 with one Location each, at most three redirects,
   validating the resolved destination, DNS and peer afresh on every hop. Hosts
   must be selected for this target and in the fixed registry. Reject loops,
   scheme downgrade, credentials, disallowed hosts/ports and overlong locations.
   Do not forward response headers to another host.
5. Require status 200 and media type `text/html`, `application/xhtml+xml`,
   `text/plain` or `application/pdf` (case-insensitive, parameters parsed
   separately). Accept text for inspection only when valid UTF-8 with absent or
   UTF-8 charset; other encodings remain unsupported review gaps. PDFs must start
   with `%PDF-`; HTML/XHTML must resemble markup and must never resolve XML
   entities or load subresources. Require an identity-encoded body within bounds.
   Preserve exact entity
   bytes after HTTP transfer framing, with no normalization. Detect obvious
   login/challenge/error text and unexpected identifiers/language as rejected or
   uncertain content. Detection is conservative and cannot prove legal-text
   authenticity; reviewer acceptance of document identity/classification remains
   necessary. PDFs may be retained and manually reviewed; no PDF/OCR extraction
   engine is introduced. Unknown formats and uncertain translations remain gaps.
6. Retain safe attempt metadata and accepted bytes/digest. Rejected page bytes may
   be retained as explicitly quarantined retrieval artifacts, never a successful
   `LegalSource`. A rejected body or failed request cannot update successful
   verification time. A previously retained source is historical fallback only.

The helper exists solely to impose a wall deadline on blocking system DNS/TLS/I/O;
it does not run target code or provide a security sandbox. Parent process receives
bounded metadata and a private staged file, not unbounded response bytes over IPC.
Terminate and join it on timeout; a worker that cannot be stopped is a fatal run
failure. Do not claim thread/future cancellation bounds `getaddrinfo`.

## Fixed MVP bounds

Use constants, not a new configuration framework. Reject one item beyond each
bound; test the boundary and one-over cases. Byte units below are binary.

| Resource | Bound / behavior |
| --- | --- |
| Input JSON and previous bundle | 4 MiB each, read limit + 1 before `parse_record`; JSON nesting depth 32 before Pydantic, duplicate JSON keys rejected |
| Collections | 200 requirements, 200 obligations, 200 controls, 500 facts, 100 activities, 200 applicability decisions, 200 evidence reviews, 200 evidence references, 16 source targets; 1,000 items across nested collections per record and 5,000 across the bundle |
| Coverage | Exactly eleven historical candidate families; unsupported topics remain research gaps |
| Selected local files | 32 files total, 8 MiB per file and 64 MiB total; includes declarations' selected source/evidence/origin files, excludes input JSON and predecessor bundle already separately capped |
| Download | 8 MiB per response, 64 MiB total including rejected and redirect bodies; read in 64 KiB chunks; excess Content-Length rejected early, actual stream limit always enforced |
| HTTP headers | 64 KiB total per response, at most 100 headers, at most 8 KiB per line; reject before accepting a body |
| Requests | One active helper, at most 16 targets, at most four GETs per target including redirects; no automatic retry or conditional 304 path |
| Time | 5 seconds per connect/TLS/read operation, 20 seconds wall time per target including DNS and all redirects, 300 seconds network budget for a run |
| Output | 4 MiB validated bundle JSON and 16 MiB Markdown; preflight/render before publication; capacity failure exits 2 rather than silently truncating records |

Each operation's timeout is capped by the remaining monotonic deadline. The parent
enforces the target deadline across slow trickles and blocking resolution. At run
network-budget exhaustion, remaining targets receive explicit budget-exhausted
attempts and the report is partial. These bounds limit application work and bytes;
they are not a claim of kernel resource containment or a strict whole-process CPU
deadline. Local reads are limited to regular files; no FIFO/device blocking reads.

## Accountable assembly and reporting

Before assembling a duty, verify a pinned accepted source identity and consistent
classification. A proposal, guidance, standard or engineering-practice record
cannot establish a binding duty by itself. A fictional fixture supports only a
prominently fictional example. A bundle containing fictional requirements,
sources or reviews must be synthetic; reject attempts to label it a real-law run.
Official hosting alone proves none of binding
authority, applicable date, completeness, jurisdiction or reviewer acceptance.
Unsupported/conflicting candidate classifications retain a disposition with gaps
rather than becoming an accepted real duty or disappearing from coverage.

Applicability defaults to unresolved. Accept applicable/not_applicable only with a
named reviewer, reasoned conditions/exceptions and exact scope, relevant facts,
obligation and source pins for the assessment date. Unknown connecting factors,
thresholds, roles, exemptions or national implementation remain explicit questions.
Require source-review rationale for amendment/repeal chain, relevant case law,
national overlays, translations, application and transition dates; an empty list
without an explicit review explanation leaves a gap. Extend `SourceReview` with
bounded rationale/dependency fields only where existing fields cannot retain this.

Evidence presence/digest establishes recorded availability, not legal sufficiency.
Require `EvidenceReview` for period, coverage, relevance, contrary evidence and
remaining requests. Reviewer names are supplied attestations, not authenticated
signatures or independent proof. Independently verified provenance requires retained
proof and may not be inferred from a label. Missing/purged/corrupt/blocked evidence
cannot support a reviewed method. Keep technical methods `not_tested`; do not invent
`CheckAttempt`, `Finding` or a pass to accommodate a legal/document review.

Every report includes project/date, synthetic warning, covered/excluded domains,
family screening, all requirements and all candidate obligations, pinned provisions
and source types, applicability rationale/reviewer, evidence provenance and
availability, source attempts/failures, verification dates, gaps and next reviewer
actions. Any open retrieval/coverage/review question makes processing state partial.
Completed means assembly finished; it never means compliant. No compliance score.

Escape HTML and Markdown metacharacters in imported text, collapse control
characters and avoid imported raw HTML, images, autolinks and executable URI links.
Render imported URLs and paths as escaped text; only tool-generated local artifact
links use fixed safe relative paths. JSON contains data, not executable actions.

## Private immutable artifacts

Require an explicit output path under an existing owner-controlled private parent.
Reject symlink components, existing output paths and group/world-accessible parents;
never chmod existing directories. Create the new directory exclusively with mode
0700, files exclusively with mode 0600, and use no-follow descriptor-relative
operations for explicitly selected regular input files and run artifacts. Fail
closed if required privacy/no-follow primitives are unavailable. File mutation
detected during hashing produces an availability gap, not a stable evidence claim.

The run retains `input.json` (normalized declarations), `manifest.json`,
`bundle.json`, `report.md`, `sources/<digest-hex>.bin`, bounded rejected retrieval
artifacts when present, and a final `complete.json` marker listing file digests.
No private evidence bytes are copied by default; only paths/locators, digests,
metadata and review attestations are retained. Reports therefore remain private
even without evidence bodies. Offline synthetic source bytes are copied only from
explicit fictional source-file references, preserving their synthetic type.

Write source files before referring to them in a bundle, validate/render everything,
flush/fsync files and directory, and write the completion marker last via exclusive
creation, then fsync the marker and directory. Readers require marker and matching
digests. Interrupted output is an
incomplete directory, never a valid report; use a new output directory to retry.
No overwrite, mutable latest pointer or rewriting historical bundles is needed.
Immutability is an application invariant with tamper detection, not protection
against the local account modifying its own files. OS encryption/backups and
filesystem durability remain owner responsibilities.

Use private directories outside the checkout in the example. Existing ignored
`/audit-data/` and `/artifacts/` are alternatives for local use, not permission to
publish reports. No automatic deletion: retain runs until owner removal; show
retention metadata and explain that external evidence may later be unavailable.
No runtime files, handbacks or credentials enter packages or Git.

## Conservative revalidation

Validate the predecessor's completion marker, bundle and source-byte digests before
comparison. Reject corrupt/incomplete or cross-project predecessors with exit 2.
Read only that directory's explicit manifest-listed artifacts; no history crawling.
Create a successor `AuditRun.parent_run_id` and new manifest without editing it.

Compare stable IDs/revisions and canonical semantic digests for requirements,
scope/facts/date, obligations/registry, source targets and actual source digests,
evidence digests/availability, review decisions and tool/config versions. New,
removed and changed records all appear in the retained comparison. Ignore purely
observational retrieval timestamps for content comparison, but preserve them as
provenance. Changed dependencies invalidate claims even if a supplied reviewer
label still says supported. A new assessment date invalidates all dated reviews.

Use explicit dependency lists on assessments/reviews and the existing freshness
overlay. Changed relevant input makes the historical claim stale; failed fetch,
offline freshness observation or unavailable evidence makes freshness unknown.
If change and uncertainty coexist, mark stale with both reasons. Incomplete
dependency attribution invalidates the whole assessment. Record comparison proof
as an `Evidence` metadata artifact
so `CurrentAssessment.comparison_evidence_ids` resolves in the successor bundle.

Unchanged dependencies can justify `current_for_recorded_inputs` only for the
precisely compared historical claim, with observed manifest and comparison proof;
the label describes recorded inputs only. An offline run cannot renew source
verification, and equal bytes never renew reviewer approval or establish current
law. New bytes create a candidate source revision requiring new review. An online
fetch with unchanged bytes still leaves amendment-chain/case-law/date review to
the named reviewer. Preserve prior accepted source pins while displaying current
unreviewed candidates and affected gaps separately.

## Three sequential construction bolts

One CLI unit is delivered in these three dependent bolts; no parallel service or
extra product unit is implied.

1. **Contracts plus offline reporting:** missing records and reference validation;
   generated JSON/TypeScript; CLI/parser, private append-only storage, escaped
   JSON/Markdown reports and synthetic first run. Network fails closed. Demonstrate
   empty coverage, unmapped obligation, missing reviews and evidence gaps.
2. **Official retrieval:** fixed host policy, pinned DNS/TLS/redirect requests,
   bounded helper/deadlines, retained bytes/attempts and classification gate.
   Integrate with the same CLI. Fake transport/resolver tests are mandatory; live
   smoke remains a separate opt-in check, never acceptance evidence of legal truth.
3. **Revalidation plus skill/release:** predecessor integrity, dependency comparison,
   stale/unknown overlays, changed synthetic example, repository-local
   `skills/legal-revalidation/SKILL.md`, user instructions and package inspection.
   Skill tells an agent to prepare declarations/reviews and invoke the CLI; it
   does not call a provider, treat imported text as instructions or issue verdicts.

## Verification and acceptance trace

Read existing callers and `test_models.py`, `test_legal_contract.py` and
`test_frontend_contract.py` before changing contracts. Existing fixtures and closed
commands must keep their meaning; any new required field needs a deliberate
backward-compatible shape or documented schema decision. Do not weaken old tests.

| Requirement | Construction evidence |
| --- | --- |
| FR-1 | Invalid/duplicate JSON keys, IDs/revisions, dangling/cross-project joins, missing families, unknown facts and empty inputs; all requirements/obligations visible. |
| FR-2 | Fake DNS sets including mixed public/private, rebinding and pinned peer; unsafe URLs/redirects, proxy non-use, TLS errors, headers/body limits, slow DNS/trickle, timeout cleanup, first/refresh failures, exact bytes/digests and classification. |
| FR-3 | Missing/contradictory reviews, nonbinding duties, challenged text, unknown dates/translations/overlays, evidence corruption, shared evidence with distinct obligation decisions, obligation without finding. |
| FR-4 | CLI exit semantics, private modes, collisions/symlinks, interrupted writes/marker checks, safe errors/Markdown injection and JSON roundtrip. No evidence body exposure. |
| FR-5 | Requirement/fact/date/obligation/evidence/reviewer/source changes and removals, stale/unknown precedence, failed refresh after success, unchanged bytes, conservative invalidation and unchanged predecessor digests. |
| FR-6 | Both documented offline commands run with socket/network calls forbidden; fictional warning in every output; local skill and resources present in distribution; separate opt-in smoke instructions. |
| NFR-1 | Boundary/one-over resource tests, fixed-byte reads, no walks or target execution, no credentials in requests, file access limited to explicit paths and private output. |
| NFR-2 | Existing tests plus focused synthetic CLI/retrieval/revalidation tests, generated-contract drift checks, package build/inspection and example outputs. |

Implementation verification commands:

```sh
make contracts
make check
uv build --offline --out-dir /tmp/eucg-mvp-dist
```

Run `make contracts` only for deliberate model changes. Inspect wheel/sdist entries
for required schema, skill and synthetic resources and absence of private state;
update packaging's explicit allowlist deliberately. Execute offline examples from
the built distribution as well as the checkout. Unit retrieval uses fake sockets,
resolvers, clocks and worker control; it does not establish real containment or
live-source acceptance. A local controlled helper-timeout test verifies actual
process cleanup without contacting external services. No live-law test is required
for this planning change; design review precedes implementation approval.

Delivery remains limited by a declared candidate register, manual interpretation,
source identity review, unsupported national hosts/formats and self-attested reviewer
identity. Successful checks establish software behavior on synthetic inputs, never
coverage of all EU law or a legal compliance verdict.
