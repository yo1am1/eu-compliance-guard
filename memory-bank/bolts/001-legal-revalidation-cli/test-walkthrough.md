---
stage: test
bolt: 001-legal-revalidation-cli
created: 2026-10-19T08:41:29Z
status: awaiting-human-validation
---

## Test Report: offline legal revalidation CLI

### Summary

- **Tests**: 130/130 passed through `make check`, including the original 61 tests.
- **Acceptance coverage**: 12/12 criteria verified for the approved offline slice.
  Line/branch coverage percentage was not instrumented or claimed.
- **Contracts**: JSON Schema drift, generated TypeScript drift and TypeScript
  compilation pass; the sixteen-operation Command union remains unchanged.
- **Owner clarification**: the early report now puts an issue beside its project
  requirement/location, exact declared legal identifier and article/paragraph,
  evidence rationale and next review action. Unsupported claims remain gaps.
- **Independent review**: a read-only teammate separately verified boundaries,
  CLI/history/privacy and the final issue/citation chain, with no blocker found.

### Test Files

- [x] `tests/test_revalidation_models.py` — 25 contract, dependency, provenance,
  synthetic-label and unsupported-conclusion checks.
- [x] `tests/test_revalidation.py` — 24 source/evidence, content, assembly,
  publication, failure, no-execution and history checks.
- [x] `tests/test_revalidation_cli.py` — six routing, safe-diagnostic, exit-code
  and real package-only subprocess checks.
- [x] `tests/test_revalidation_report.py` — nine metadata, actionable-citation,
  fictional-label, escaping, secrecy and report-bound checks.
- [x] `tests/test_revalidation_acceptance.py` — five exact capacity-boundary tests,
  including actual 32-file and 64 MiB aggregate reads.
- [x] Foundation model, legal/frontend-record, admission and fake-executor tests —
  all 61 pre-existing checks retained and passing.

### Acceptance Criteria Validation

1. ✅ **001 AC-1 — Validated input**: strict schema/revision/identity/project and
   reference checks, duplicate JSON keys, nonfinite/malformed data and safe exit-2
   diagnostics reject invalid input before selected-file observation/publication.
   The fixture and output roundtrip through the shared models.
2. ✅ **001 AC-2 — Facts and applicability**: declared, assumed and unknown bases
   are preserved. Missing accountability, reasoning or relevant dependency support
   yields an effective unresolved decision while the supplied claim remains visible.
   Complete fictional attestations admit only explicitly fictional conclusions.
3. ✅ **001 AC-3 — Coverage**: empty requirements/registers and missing screenings
   produce explicit gaps and all eleven candidate-family entries. Unmapped records,
   exclusions and unsupported topic/jurisdiction questions remain visible; neither
   empty nor completed fictional processing asserts all EU law was searched.
4. ✅ **001 AC-4 — Bounds and selected reads**: exact/one-over checks cover 4 MiB
   input, depth 32, 200-item collections, 100 activities, 500 fact occurrences,
   16 source/target/review records, eleven families, 1,000 nested items, 5,000
   aggregate items, 32 selected files, 8 MiB/file, actual 64 MiB aggregate bytes,
   and output caps. Only named regular files are observed; socket, subprocess,
   directory-walk and enumeration guards reject unintended operations.
5. ✅ **001 AC-5 — Privacy and scope**: actual private-temp runs use directory
   mode 0700 and file mode 0600. Symlinks, special files, unsafe parents and existing
   outputs fail safely; inputs remain unchanged. Default/explicit offline runs make
   no network calls. Unsupported fetching fails before reads/output. No dependency
   or OS-policy changes were introduced.
6. ✅ **002 AC-1 — Complete mappings**: every requirement and obligation appears,
   including unmapped obligations without technical findings. A private offline
   insufficient-evidence variant places the reviewed issue beside requirements.md,
   Requirement R-7, a project activity and Fictional Article 7(2)(a), with its
   fictional source identifier/revision, reviewer, evidence and next action.
7. ✅ **002 AC-2 — Review gaps**: missing applicability/evidence and each of the
   seven source-review dimensions produce visible gaps/actions. Explicit unavailable
   related, act-chain, case-law, national and obligation-overlay dependencies block
   upstream support; valid cycles remain representable.
8. ✅ **002 AC-3 — Evidence and authority**: declarations, observations, reviewer
   attestations and evidence provenance remain distinct. Files/citations alone,
   inconsistent/nonbinding sources, missing proof and synthetic relabelling cannot
   establish real duties. Methods retain separate outcomes; technical checks remain
   untested. Requirement-specific evidence/facts/origins independently constrain support.
9. ✅ **002 AC-4 — Untrusted content**: login, challenge and error-page cases are
   rejected, including plain sign-in requirements and HTML 404 headings. Unsupported
   or ambiguous formats/encodings and PDF identity retain review gaps. Imported
   content is never executed; empty inputs and technical results yield no verdict.
10. ✅ **002 AC-5 — Runnable report**: actual default/offline CLI invocations exit
    zero with validated private JSON and readable escaped Markdown, a partial
    fictional report, supported fictional mapping and explicit unresolved records.
    The report's early attention section supplies the clarified issue/citation chain.
11. ✅ **002 AC-6 — History**: collisions exit two without changing the first run;
    another child creates distinct run IDs. Prior artifacts remain byte-identical
    after success and failure. Marker digests and injected write/fsync/interrupt
    behavior are checked; unsuccessful publication leaves no finalized marker.
12. ✅ **002 AC-7 — Secrecy and inert rendering**: raw evidence sentinels stay out
    of reports and diagnostics. Imported HTML, Markdown images/links, executable
    URLs, controls and paths render as inert text. Only fixed generated artifact
    links are clickable. The pure renderer performs no evidence-body I/O.

### Issues Found

- The first report exposed traceable records but required readers to reconstruct
  the issue/citation chain. The attention summary and four focused renderer tests
  now make that chain explicit, including an actual offline insufficiency run.
- Earlier aggregate checks scaled the byte budget and did not retain every exact
  collection boundary. Five acceptance tests now cover real configured byte/file
  bounds and the remaining collection boundaries. No production limit was relaxed.
- No unresolved blocking software defect was found within this bolt's scope.

### Notes

Wheel and sdist built offline. Archive inspection verified expected modules/schema,
synthetic sdist resources and the new acceptance tests without dependencies, caches
or private runtime artifacts. An isolated Python invocation outside the checkout
ran the built wheel's offline example and confirmed the actionable report section.
Historical `specs/**` matches baseline 5951623 byte-for-byte; public contracts remain
models-derived. Teammates used the same two split panes in the coordinator tab.

These checks establish software behavior on synthetic declarations, not legal
correctness or a real project compliance audit. Current-law fetching, predecessor
comparison and portable skill/release remain Bolts 002/003. Reviewer identity is
self-attested, content sniffing is conservative, and budgets are cooperative rather
than hard containment. No live legal corpus, scanner/provider execution, target-code
execution, global installation or OS-policy changes were used.

The Owner approved starting Test; final test/bolt acceptance is still required.
Stories and bolt are not marked complete until that approval and the mandatory
specsmd completion procedure.
