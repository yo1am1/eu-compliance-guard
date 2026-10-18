---
stage: plan
bolt: 001-legal-revalidation-cli
created: 2026-10-18T19:12:24Z
status: approved
---

# Implementation Plan: offline legal revalidation CLI

✅ **Stage 1 Plan: approved by the Owner at 2026-10-18T19:15:48Z.** The Owner selected
`Approve plan; start implementation`. Stage 2 Implement is authorized; Stage 3 Test
and final bolt completion retain their human checkpoints. No story or MVP is
complete merely because this plan is approved.

## Objective and scope

1. **Deliver the first offline slice:** versioned declarations and explicitly
   selected local files → validated references → accountable requirement/obligation
   mappings and visible gaps → private validated JSON and escaped Markdown.
   Cover all five ACs of story 001 and all seven ACs of story 002.
2. **Reuse the foundation:** Pydantic records/helpers in `models.py`, schema exporter,
   generated frontend contract, stdlib argparse/filesystem/hashing/json/html and
   unittest. No dependency or lockfile changes. Existing 16-command union, old
   fixture semantics, agent/executor behavior and historical `specs/**` stay intact.
3. **Defer later bolts:** no `sources.py`, DNS/HTTP helper, live fetch, new retrieval
   provenance record, freshness overlays/comparison, predecessor reader, changed
   example, portable skill or release installation flow. `--fetch-official` and
   `--previous` are unimplemented arguments and must fail with exit 2 before file
   reads/output creation. Bolt 002 adds retrieval; Bolt 003 adds revalidation and
   skill/release. Do not prebuild their contracts or extension framework.

## Reviewed baseline and compatibility

1. **Inputs read:** approved `specs_v2/requirements.md` and `design.md`; unit brief;
   stories `001-input-and-coverage` and `002-accountable-mapping-and-report`;
   Bolt 001 and installed simple-construction definition; coding/stack standards;
   `models.py`, `schema.py`, frontend generator, Makefile and packaging metadata.
2. **Callers/tests read:** `agent.py` imports the shared bounded parser;
   `test_models.py` protects strict records, source review, canonical roundtrip,
   limits and exactly sixteen commands; `test_legal_contract.py` protects fictional
   classification, source failure semantics and independent legal dispositions;
   `test_frontend_contract.py` protects UI projections and safe evidence delivery.
   Do not broaden `parse_record` or change these projections for this CLI.
3. **Compatibility rule:** new public types subclass existing `Record`. Keep old
   fields/validators unchanged, except optional defaulted source-review metadata below.
   New workflow admission checks belong in the new envelope/workflow, so an old
   `SourceReview` still parses but cannot silently establish support in this CLI.
   New JSON Schema definitions are discovered automatically; generated TypeScript
   includes unreachable definitions. No separate handwritten contract or API route.

## Concrete contracts for this bolt

All shapes below are proposed additions in **`models.py`**, using existing aliases
(`Id`, `Revision`, `SourceRef`, `Text`, `Name`, `Digest`, `RelativePath`, `ISODate`,
`Timestamp`, `Ids`, `Texts`) and bounded lists. Reuse `SourceRef` structurally for
revision pins; the containing field fixes the entity kind. No generic reference
graph, legal condition interpreter or separate gap entity is needed.

1. **`DeclaredRequirement`:** `id`, `revision`, `project_id`, `synthetic: bool`, `statement: Text`,
   `origin: SourceFile | None = None`, `locator: Name | None = None`,
   `activity_ids: Ids`, `fact_refs: list[SourceRef]`,
   `obligation_refs: list[SourceRef]`, `evidence_ids: Ids`.
   Origin/locator must be supplied together or both omitted. Omission means a
   declaration supplied directly in JSON; the input digest remains its origin.
   Do not infer an obligation from requirement text.
2. **`SourceTarget`:** `id`, `revision`, `family: Name`, `intended_url: HttpURL`,
   `intended_identifier: Text | None`, `publisher: Name`, `intended_type: SourceType`,
   `language: Name`, `jurisdiction: Name`. These are candidate declarations, never
   fetch authorization. Add redirect host selection only in Bolt 002.
3. **`SelectedSource`:** `target_id: Id`, `source: LegalSource`,
   `media_type: Name`, `charset: Name | None = None`, `file: SourceFile | None`.
   Media type and charset are explicit local owner declarations, not HTTP response
   headers. Media type contains only the case-insensitive MIME essence without
   parameters; charset is separate. Neither filename extension nor a supplied
   declaration establishes content identity. The optional file pins retained
   bytes. Its digest must match `source.content_digest`. No file means unavailable
   source content and an explicit gap, not a successful retrieval. Missing or
   mismatched bytes remain unavailable/corrupt candidates in the report.
4. **`SelectedEvidence`:** `evidence: Evidence`, `path: RelativePath | None`.
   Reuse the complete `Evidence` metadata rather than creating a parallel evidence
   schema. Its digest is the expected digest; path absence means metadata-only
   declaration. Run/manifest provenance must match the declaration namespace below.
   A declaration does not establish actual availability or sufficiency.
5. **`FamilyScreening`:** `family: Name`, `synthetic: bool`, `scope: SourceRef`,
   `assessment_date: ISODate`, `applicability: Applicability = 'unresolved'`,
   `rationale: Text`, `fact_refs: list[SourceRef]`, `source_refs: list[SourceRef]`,
   `reviewer: Name | None = None`, `reviewed_at: Timestamp | None = None`,
   `gaps: Texts`. Include only the eleven historical family keys; unsupported
   subjects/jurisdictions become gaps under the specialist/national family.
6. **`ApplicabilityDecision`:** `id`, `revision`, `project_id`, `synthetic: bool`,
   `obligation: SourceRef`, `scope: SourceRef`, `assessment_date`,
   `jurisdictions: Texts`, `fact_refs: list[SourceRef]`,
   `provisions: list[ProvisionRef]`, `evidence_ids: Ids`,
   `applicability: Applicability = 'unresolved'`, `rationale: Text`,
   `condition_answers: Texts`, `exception_answers: Texts`,
   `reviewer: Name | None = None`, `reviewed_at: Timestamp | None = None`,
   `gaps: Texts`. Text answers retain human reasoning; do not execute conditions.
7. **`EvidenceReview`:** `id`, `revision`, `project_id`, `synthetic: bool`,
   `obligation: SourceRef`, `method: Name`, `evidence_ids: Ids`,
   `period: Text`, `owner: Text`,
   `state: Literal['reviewed','insufficient','unresolved'] = 'unresolved'`,
   `rationale: Text`, `missing_evidence: Texts`, `contrary_evidence: Texts`,
   `reviewer: Name | None = None`, `reviewed_at: Timestamp | None = None`.
   Evidence IDs resolve to digest-pinned supplied evidence. At most one review per
   obligation/method in this bolt; conflicting duplicates are invalid input.
8. **Existing `SourceReview` extension:** `synthetic: bool = False` plus optional
   `review_notes: dict[Literal['identity','classification','amendments_repeal',
   'case_law','national_overlays','translation','application_transition_dates'], Text]`
   with empty-dict default. All seven nonblank notes are required by the workflow
   before accepting support, alongside existing reviewer/time/date/pin/gap checks.
   Notes may explicitly explain why a dimension does not apply. Old fixtures remain
   valid; absence of notes is an unresolved review in this workflow.
9. **`RequirementAssessment`:** `requirement: SourceRef`,
   `obligation_disposition_ids: Ids`, `evidence_ids: Ids`, `review_ids: Ids`,
   `state: Literal['supported','conflicting','unresolved','outside_declared_assessment']`,
   `rationale: Text`, `gaps: Texts`, `next_actions: Texts`.
   Outside scope requires an explicit reasoned exclusion; empty mappings otherwise
   mean unresolved. Supported means the recorded review supports the declared
   mapping, never overall compliance. No extra assessment ID is needed.
10. **`RevalidationInput`:** `schema_version: SchemaVersion`, `project_id: Id`,
    `synthetic: bool`, `declaration_run_id: Id`, `declaration_manifest_id: Id`,
    `scope: Scope`, `requirements`, `source_targets`, `sources: list[SelectedSource]`,
    `source_reviews: list[SourceReview]`, `obligations: list[Obligation]`,
    `controls: list[Control] = []`, `family_screenings`, `applicability_decisions`,
    `evidence: list[SelectedEvidence]`, `evidence_reviews`.
    Other collections default empty; missing data then produces coverage/review gaps.
    Each unannotated collection uses the record type named above, bounded by the
    limits below. `assessment_date` fields reuse `ISODate`. Facts come from existing
    nested `Scope`/activities, without a second fact store.
    Declaration namespace fields validate supplied evidence run/manifest membership;
    they do not assert a prior audit exists or allocate the new output run.
11. **`RevalidationBundle`:** `schema_version`, `project_id`, `synthetic`,
    `input_digest: Digest`, `run: AuditRun`, `manifest: InputManifest`,
    `declarations: RevalidationInput`, `evidence: list[Evidence]`,
    `obligation_dispositions: list[ObligationDisposition]`,
    `requirement_assessments: list[RequirementAssessment]`,
    `effective_applicability_decisions: list[ApplicabilityDecision]`,
    `family_screenings: list[FamilyScreening]`, `gaps: Texts`, `next_actions: Texts`.
    Normalized input is nested once rather than copying each input collection into
    another mutable registry. Effective decisions include generated unresolved
    decisions when supplied reviews cannot be admitted. No `Snapshot`, event feed,
    `Finding`, `CheckAttempt`, `CurrentAssessment` or synthetic technical pass.
12. **`RunCompletion`:** `schema_version`, `run_id: Id`,
    `files: list[SourceFile]`. Each path is a generated run-relative artifact name;
    list every retained artifact except `complete.json` itself. It is the validated
    completion-marker contract, not a second bundle schema.

## Invariants and assembly

1. **Parse safely first:** read JSON at most limit + 1; use a bounded string-aware
   nesting scan before JSON decoding (ignore brackets inside escaped strings),
   reject duplicate keys with `object_pairs_hook`, then `parse_record` for strict
   envelope validation. Reject nonfinite constants. Preserve all existing generic
   parser behavior for its callers. Unknown keys remain errors.
2. **Validate all joins:** one active revision per ID/entity kind; no duplicate IDs
   or source ID/revision pairs. Resolve scope/activity/fact, target/source/provision,
   requirement/obligation/control, evidence/review references with exact revisions.
   `Scope.project_id`, requirements, decisions, evidence and reviews must match
   input project. Supplied evidence run/manifest must match declaration namespace;
   output evidence/dispositions must match generated run/manifest. Source review
   identity is `(source_id, source_revision, assessment_date)`; duplicates fail.
   Repeated embedded facts may share identity only when canonical content matches;
   contradictory copies fail. Every `Fact.conflicts`/evidence reference resolves.
   Related source IDs, SourceReview act/case-law/overlay IDs and Obligation overlay
   IDs resolve to supplied source candidates; absent material belongs in review
   gaps instead of dangling identifier lists. No invented national-law records.
3. **Coverage:** keep fixed keys for GDPR, ePrivacy/national implementations,
   online-service identity/disclosures, consumer law, accessibility, intermediary/
   platform law, AI, cybersecurity/software products, connected products/data,
   copyright/licensing and additional sector/national rules. Copy descriptions
   from the historical register as candidate families, not current legal claims.
   Expand missing screenings to unresolved with an action; supplied duplicates fail.
   Report empty requirement/register gaps, scope exclusions and unsupported
   jurisdictions/topics. Do not silently map an unknown family to a supported one.
4. **Admit reviews conservatively:** unresolved is the default. A resolved decision
   requires reviewer/time, nonblank rationale, matching scope/date/obligation/fact
   and provision pins, condition/exception reasoning and no unresolved dependency.
   Structurally malformed or dangling pins fail input; missing accountability or
   insufficient reasoning produces an effective unresolved decision and gap while
   retaining the supplied claim in normalized declarations. No automatic legal
   inference. Reviewer labels are unauthenticated local attestations.
5. **Source gate for local imported bytes:** check exact digest, then the declared
   MIME essence against `text/plain`, `text/html`, `application/xhtml+xml` or
   `application/pdf`. Unsupported declarations leave an unsupported-format gap.
   Text requires absent or UTF-8 charset (case-insensitive) and strict UTF-8 decode;
   other charsets or invalid bytes remain unsupported, without transcoding.
   PDF requires an absent charset and a `%PDF-` byte prefix; inspect no PDF text and
   require manual document-identity review. HTML/XHTML must resemble markup;
   markup served as declared plain text and other signature/type mismatches remain
   uncertain rather than silently changing type. Inspect decoded text for obvious
   login, challenge and error-page markers (including title/form signals); reject
   those as accepted legal content. Do not execute scripts, resolve XML entities,
   load subresources or infer legal authority from a successful content sniff.
   Unknown/ambiguous content or identity needs manual review. PDFs are retained
   for manual review without extraction/OCR. A supplied source review
   and all seven notes are necessary for support; offline loading never updates
   `retrieved_at` or `last_successful_verification`. Do not generate `SourceAttempt`
   as though a local import were a network retrieval. Missing content is a gap.
6. **Authority:** actual duty support requires consistent reviewed act/judgment
   authority and accepted provision pins; guidance/proposal/standard/engineering
   material cannot independently establish binding duties. Preserve inconsistent
   candidates and their gaps. Fictional duties may be represented only in synthetic
   output and never support real-law conclusions. Require `synthetic=true` on the
   envelope if any requirement, source, source review, applicability/evidence
   review or family screening is explicitly synthetic. Retain every supplied
   record's label in normalized input and output; do not strip labels on import.
   Effective reviews/decisions inherit synthetic provenance from referenced
   requirements, sources and reviews, and generated unresolved records inherit
   the envelope's synthetic label. A true label cannot be cleared by a downstream
   false declaration. `SourceReview`'s False default preserves foundation parsing;
   a linked synthetic source still makes its effective use synthetic.
   Mixed real/synthetic input requires a synthetic bundle and prominent labels
   on the whole report and every derived conclusion; it cannot yield an unlabelled
   real-law conclusion. Test mixed input and each fictional record kind with a
   falsely nonsynthetic envelope, including fictional requirements/reviews with
   otherwise real-labelled sources. This cannot detect a dishonest owner
   mislabelling arbitrary prose as real.
7. **Evidence:** hash only selected files; record missing/purged/corrupt/blocked
   state and actual provenance without exposing bodies. Expected digest stays in
   declarations; observed digest is retained in output metadata when available.
   File mutation during a read yields corrupt/unavailable, not a stable claim.
   Independent-verification labels need separately referenced retained proof;
   otherwise leave a provenance-review gap. A file/citation alone cannot support a
   method. Require method review, relevant period/coverage, no missing/contrary
   evidence and all source/applicability gates. Technical methods remain not_tested.
8. **Dispositions:** derive one per obligation including unmapped ones; no technical
   findings required. Use unresolved_review for incomplete documentary methods,
   observed_failure for an explicitly reviewed insufficient method, and passed
   only for fully supported documentary review. Manual status stays independent.
   Missing reviews remain pending; conflicting or unsupported ones remain explicit.
   Requirement assessments include every requirement and all mappings/questions.
9. **Processing state:** any coverage/source/evidence/review gap yields `partial`.
   Otherwise `completed` describes report assembly only. Offline real-source
   freshness is explicitly unverified and leaves a gap; fictional examples may
   demonstrate recorded support without real-law conclusions. No compliance score,
   verdict, freshness renewal or authenticated legal approval is emitted.

## Bounds, identifiers and retained output

1. **Approved fixed bounds:** input JSON 4 MiB; JSON depth 32; 200 requirements,
   obligations, controls, applicability decisions, evidence reviews and evidence
   references each; 500 facts and 100 activities; 16 source targets; exactly eleven
   family screenings after expansion. Apply 1,000 nested collection items per
   record and 5,000 across the serialized bundle, including derived references.
   Source/review collections are additionally
   capped by their 16 source targets. Bounds apply before expensive joins/hashing.
2. **File/output limits:** 32 selected files, 8 MiB each, 64 MiB aggregate, read in
   64 KiB chunks. Include source/evidence/requirement-origin paths, deduplicate only
   the same normalized path, and reject conflicting expected digests for one path.
   JSON input has its separate cap. Bundle at most 4 MiB and Markdown at most
   16 MiB; capacity failures exit 2, never silently drop records. No request budget
   or HTTP bounds are implemented here because there is no network operation.
3. **IDs:** generate `run-<uuid4hex>` and `manifest-<uuid4hex>`, revision 0. Derived
   dispositions use `disposition-<sha256(obligation ID) hex>`; generated unresolved
   decisions use `unresolved-<sha256(obligation ID) hex>`, checked against supplied
   IDs for collisions. Rebind output Evidence to new run/manifest without changing
   declaration provenance; preserve original metadata in `input.json`. Link
   assessments by requirement pin. Parent run is None. `terminal_sequence=0`
   satisfies existing terminal metadata, explicitly without claiming an event feed.
   `permission_id` copies scope's declared reference and grants no execution rights.
4. **Manifest:** use existing `SourceFile` entries for observed explicit files;
   hash canonical scope facts, candidate registry, source pins, fixed workflow
   policy/tool version and the raw declaration input. Use the latter for
   `fixture_digest` as the declared input dataset digest, without implying a real
   input is fictional. `browser_state`/`graph_digest` are None. Compute manifest
   digest over canonical fields excluding its digest field. No self-hash cycle.
   Use `Budgets(run_seconds=300, check_seconds=300)` as recorded processing budget
   with cooperative checks; document no hard CPU/local-filesystem deadline or
   containment guarantee. Do not spawn a deadline process for this offline bolt.
5. **Explicit files only:** normalized paths resolve from the input JSON's parent.
   Open directory components descriptor-relatively with no-follow flags, and final
   files with no-follow/nonblocking then verify regular-file type; never read
   FIFO/devices, enumerate a target, execute code, import local Python or follow
   document instructions. The input JSON path itself receives equivalent checks.
   Validate all syntax/references/bounds before output creation.
6. **Privacy/history:** output path must be absent, with an existing owner-controlled
   parent whose permission bits exclude group/other. Reject symlink components;
   public system ancestors such as `/tmp` may remain public. Never chmod existing
   paths. Create run directory 0700 and files 0600 exclusively. Fail closed when
   required descriptor/no-follow/privacy primitives are unavailable. No global
   umask change, ACL/OS-policy adjustment, or cleanup of a preexisting directory.
7. **Artifacts:** `input.json` normalized declarations, `manifest.json`, `bundle.json`,
   `report.md`, `sources/<digest-hex>.bin` for accepted explicitly selected source
   bytes, and `complete.json`. Do not retain rejected source page bytes in this
   first bolt; keep their safe diagnostic/gap. Do not copy evidence bodies.
   Check source digest again when writing retained bytes. Write referenced sources
   first, then validated/pre-rendered documents, fsync, create completion marker
   last and fsync marker/directory. On failure/interrupt no finalized marker is
   left; preserve any incomplete directory and require a different path to retry.
   The marker lists exact byte digests of every retained artifact except itself.
8. **Limits of privacy:** content digests detect changes but do not stop the local
   owner modifying files. Evidence references/attestations and normalized input are
   private too. Ignore patterns are a guardrail, not export authorization. No
   automatic deletion or private runtime artifacts in Git. Do not claim secret
   detection in arbitrary owner-supplied statements; never read evidence into the
   renderer or print raw validation input in diagnostics.

## Modules and visible-worker ownership after approval

One writer per file. Coordinator dispatches visible Orca workers and preserves
their conversations; no hidden agents. The Owner approved this ownership
for Stage 2 implementation; one writer per file remains mandatory.

1. **Contracts worker, first:** owns `eu_compliance_guard/models.py`,
   `eu_compliance_guard/contract.schema.json`, `frontend/src/lib/contract.ts`,
   `tests/test_revalidation_models.py`, `fixtures/revalidation-synthetic.json`,
   `fixtures/revalidation-synthetic/source.txt`,
   `fixtures/revalidation-synthetic/evidence.txt`.
   Define bounded records, semantic joins and fixture before publishing interface
   handoff. Run `make contracts` only after deliberate model edits. Existing
   `fixtures/contract-synthetic.json` and foundation tests remain unchanged.
2. **Offline workflow worker, after contract handoff:** owns
   `eu_compliance_guard/revalidation.py` and `tests/test_revalidation.py`.
   Provide `load_input(path) -> RevalidationInput`,
   `assemble(input, selected-file observations) -> RevalidationBundle`, and
   `run(input_path, output_path) -> RevalidationBundle`. Keep bounded I/O, local
   content admission and private publication here; no storage/network framework.
   Pass generated UTC time/UUID values into assembly so tests can fix them.
3. **CLI/report worker, after contract handoff, may overlap worker 2:** owns
   `eu_compliance_guard/__main__.py`, `eu_compliance_guard/report.py`,
   `tests/test_revalidation_cli.py`, `tests/test_revalidation_report.py`.
   Renderer interface is `render_report(bundle) -> str`, pure and bounded.
   CLI calls workflow `run`; no business logic duplication. Workflow lazily or
   directly calls renderer after assembly; avoid a circular module import by
   having report import only models. Workers agree these interfaces before edits.
4. **Coordinator/integrator, after worker handoffs:** owns `README.md`,
   `docs/implementation-status.md`, planning/lifecycle/walkthrough documents and
   any future `pyproject.toml` packaging correction if inspection proves needed.
   Current package includes all package `.py` files and schema; sdist already
   includes fixtures/tests, so no console entry point or metadata change is needed
   for `python -m`. Wheel fixture installation and skill packaging belong to
   Bolt 003. Coordinator resolves cross-file issues by returning edits to owners,
   not by racing them, and runs full integration checks after handoffs.
5. **Stage gates:** Implement may add focused checks alongside nontrivial logic,
   but does not mark Test complete. Present implementation walkthrough for human
   validation before Stage 3's full acceptance run/test walkthrough. External
   specsmd completion-tool dependencies are now verified for startup: the coordinator installed
   `fs-extra` 11.4.1 and `js-yaml` 4.3.2 in a private temporary `NODE_PATH`
   environment and invoked the actual completion script with no bolt ID. No bolt
   was completed. Preserve that external environment or recreate it for the later
   authorized completion check; no application dependency change is required.
   No worker manually completes stories to bypass that tooling.

## Fixtures and focused tests

1. **One checked-in example:** visibly fictional project, requirement, candidate
   obligation/source/provision, source-review notes, reasoned applicability and
   documentary evidence review. Include a second unmapped obligation and an
   unmapped requirement, incomplete family screening and a declared/assumed/unknown
   fact. Expected output is partial with retained supported fictional mapping plus
   visible unresolved gaps. Fictional text is not represented as an actual EU act.
2. **Generate variants in tests:** mutate this fixture in memory for duplicate IDs,
   dangling pins, cross-project/run/manifest joins, empty lists, missing notes,
   inconsistent classifications, unavailable evidence, hostile text and content
   rejection. Use temporary files/directories. Do not add a JSON fixture per edge
   case or the Bolt 003 changed-input fixture now.
3. **Untrusted local content:** synthetic HTML login/challenge/error snippets,
   uncertain HTML, absent/UTF-8/unsupported declared charsets, MIME/signature
   mismatches, invalid UTF-8 and a minimal PDF-signature case are temporary
   files. Content checks share one local admission function; Bolt 002 will reuse
   its accepted/rejected/needs-review result for downloaded bytes. No current-law
   assertions or network fake needed in this bolt.
4. **Privacy/integrity tests:** output collision and symlink, FIFO/device rejection,
   corrupt/missing/mutating evidence/source, limits at boundary and one over,
   injected write/fsync/interrupt failure, marker/digest consistency and history
   byte identity. Patch socket calls, subprocess/provider execution and directory
   walking to fail if the workflow uses them. CLI subprocess test may launch this
   package only; that is not target repository execution.
5. **Renderer tests:** HTML and Markdown metacharacters, backticks, images,
   executable URI, controls and table-breaking text remain escaped/inert; imported
   URLs/paths render as text. Only fixed generated artifact links are clickable.
   Raw evidence secret sentinel is absent from both reports and diagnostics;
   normalized declarations may retain private metadata by design. Test semantic
   content, not whole-report timestamp snapshots.

## Acceptance criteria, individually observable

All implementation acceptance entries remain pending. Tests below describe future
evidence, not passing results from this Plan stage.

1. [ ] **001 AC-1:** schema-version/strict/duplicate-key/ID/pin/project validation
   variants exit 2 with a stable safe code and no marker; valid fixture roundtrips
   through new records. Existing contract tests still assert exactly 16 commands.
2. [ ] **001 AC-2:** preserve all Fact bases and original claims; missing reviewer,
   rationale or scope/fact/obligation/source pins yields unresolved effective
   applicability with explanation. A complete fictional pinned attestation is
   admitted only as fictional; wrong structural references fail validation.
3. [ ] **001 AC-3:** empty requirement/register and omitted family cases show
   explicit gaps, eleven screenings, considered domains and scope exclusions;
   unsupported jurisdiction/topic remains a research action. Neither empty nor
   complete fixture claims all EU law searched.
4. [ ] **001 AC-4:** boundary/one-over tests cover 4 MiB, depth 32, each collection,
   32 files/8 MiB/64 MiB and output caps; malformed data fails before hashing or
   output creation. Read-set assertions prove only named regular files are read;
   no walk, external network or target execution occurs.
5. [ ] **001 AC-5:** run under an explicit private temporary parent; observe
   0700/0600 modes, no-follow/collision failures, unchanged inputs and no runtime
   output in checkout/package. No dependencies are added. Default and --offline
   paths make zero network calls; unsupported fetching fails rather than bypassing
   the unit's future official-only policy.
6. [ ] **002 AC-1:** every requirement appears with all resolved mapping chains or
   an unmapped gap; every candidate obligation appears, including the unmapped one
   and one without any technical finding. Provision/date/reviewer/evidence links
   resolve to pinned records, with unresolved questions retained.
7. [ ] **002 AC-2:** individual missing applicability/evidence/amendment/case-law/
   national/translation/application/transition variants each produce a visible gap
   and next action. Multiple gaps are not collapsed into a misleading supported
   result, and a source note's absence is not interpreted as a completed review.
8. [ ] **002 AC-3:** distinguish declared/documented/observed provenance and named
   attestations. A file alone cannot pass a review; proposals/guidance and
   inconsistent classifications cannot establish real duties. Shared evidence may
   support one documentary method while another stays pending. Synthetic types
   cannot be silently converted into real authority. Fictional requirements and
   reviews retain machine-readable labels, and mixed declarations cannot emit
   unlabelled real-law conclusions.
9. [ ] **002 AC-4:** imported login/challenge/error bodies are excluded from accepted
   source bytes and support; uncertain content remains unreviewed. Empty input and
   a historical technical-pass record never produce a legal verdict. No imported
   document can execute or instruct the workflow.
10. [ ] **002 AC-5:** exact offline command below exits 0, publishes a parseable
    `RevalidationBundle` plus readable escaped report with all listed story fields,
    a prominent fictional label and explicit partial state; no network call occurs.
11. [ ] **002 AC-6:** same output path exits 2; a different child creates a new run
    with separate IDs. Hash prior directory files before/after both successful and
    failed invocations and assert byte identity. No `--previous` is needed or
    implemented to verify no-overwrite history preservation.
12. [ ] **002 AC-7:** evidence bytes never reach renderer/diagnostics; secrets in
    selected evidence files remain absent. Hostile imported markup is inert;
    diagnostic output contains stable tool-owned messages without raw input,
    sensitive paths or URL queries. No automatic HTML/URL preview is generated.

## Expected commands and checkpoint

These commands are construction acceptance instructions, not available workflow
claims or commands run in this planning dispatch. Dependencies are assumed already
installed; no live source, target or provider operation is authorized.

```sh
make contracts
make check
uv run --locked python -m eu_compliance_guard --help
uv run --locked python -m eu_compliance_guard revalidate --help
eucg_bolt001_dir=$(mktemp -d /tmp/eucg-bolt001.XXXXXX)
uv run --locked python -m eu_compliance_guard revalidate \
  --input fixtures/revalidation-synthetic.json \
  --output "$eucg_bolt001_dir/run-001" --offline
uv run --locked python -m eu_compliance_guard revalidate \
  --input fixtures/revalidation-synthetic.json \
  --output "$eucg_bolt001_dir/run-002"
uv build --offline --out-dir "$eucg_bolt001_dir/dist"
```

1. **Expected evidence:** both runs exit 0 with fictional partial reports, different
   run IDs and valid completion markers. Running again against run-001 exits 2
   without modifying it. Explicit --fetch-official or --previous exits 2 while
   those bolts are unavailable. Inspect JSON via `parse_record(RevalidationBundle,
   ...)` in tests, verify marker digests and modes, and inspect wheel/sdist members
   with stdlib zipfile/tarfile for package/schema and no private artifacts. Fixture
   files are expected in sdist; wheel-installed examples are a later release gate.
2. **Required checks:** `make check` runs old and new unittest tests, JSON Schema
   drift, generated TypeScript drift and compilation. Schema root remains Command;
   added envelope types live in `$defs`. Do not replace old 61-test expectations
   with a claim of compliance or real process containment.
3. **Review handoff:** Owner approval is recorded and the coordinator advances
   to `current_stage: implement`; story completion and the Test checkpoint remain
   separate. No code, make check, live-law research, commit or push occurred
   in this plan-writing task. Principal limits remain manual legal review,
   unauthenticated attestations, conservative content detection and unavailable
   offline legal freshness.
