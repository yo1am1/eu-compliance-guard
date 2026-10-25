# Implementation status

## Standalone repository extraction

Owner direction: create a separate GitHub repository, publish existing progress, and
use one simple commit per update. Repository name: `eu-compliance-guard`.

The application was copied from `agentic-setup/apps/eu-compliance-audit/` to this
repository's root. All of `agentic-setup/specs/eu-compliance-audit/` was copied at the
same relative path. All 46 transferred files, including licenses and planning/review
snapshots, remain byte-identical to their extraction baseline. The original source
and unrelated working-tree changes are preserved. Private implementation handbacks,
probe output, session state, installed dependencies, and caches are excluded.

Original specification draft labels, pending checkboxes, repository destinations,
role assignments, and relative references are historical snapshots, not current
execution state. The user approved requirements, design, and implementation in the
prior session; this extraction does not rewrite those snapshots or claim their
acceptance criteria are complete. No original Git history or unrelated instruction
library is imported into the standalone repository.

## What exists

- Shared validated records and closed commands for scope, sources, evidence,
  findings, assessments, conversations, proposals, capabilities, and progress.
- Generated JSON Schema and frontend TypeScript definitions with drift checks.
- An offline requirement/report CLI, synthetic first-run fixture, bounded selected
  file reads, accountable mapping/evidence gaps and private immutable run artifacts.
- Synthetic foundation, contract, offline workflow, CLI and escaped-report tests,
  with generated schema/type drift checks and TypeScript compilation.
- Static native-protocol inspection and bounded reply validation.
- An offline Linux executor helper that rejects unverified cleanup. Its live
  containment/admission requirements remain unmet; fake tests are not that evidence.
- Separate Python/frontend lock files, package selection, and license notices.

## Current priority and remaining work

The first offline reporting script is implemented. Official-source retrieval and
predecessor comparison, followed by the portable skill/release, remain the next
implementation work. The earlier OS isolation investigation is not a prerequisite to
this text/evidence workflow. No OS security policy was changed and no PC vulnerability
audit was performed. Do not continue that detour as the next task.

No operational compliance audit, API, reviewed legal corpus, real scanner,
browser checks, provider bridge, remediation loop, dashboard, Graphify integration,
global host installation, or completed legal audit exists yet. These obligations
remain pending. Research links are a starting register, not a current vetted corpus.

## Verification for this extraction

- `make check`: all 61 synthetic tests passed; JSON Schema and generated TypeScript
  drift checks passed; TypeScript compilation check passed.
- `uv build --offline --out-dir /tmp/eu-compliance-guard-standalone-dist`: source
  distribution and wheel built successfully. Archive inspection verified contracts,
  license notices, and absence of dependencies, caches, and private runtime state.
- SHA-256 comparison: all 46 transferred files and five pre-existing modified files
  in the original repository remained unchanged.
- Publication candidates were checked against the explicit transfer list plus the
  four new standalone metadata documents; sensitive-pattern screening found no
  matches. This screening is not a security audit of the laptop or target projects.
- Staged whitespace review: implementation and new metadata passed. The preserved
  specifications retain their original Markdown hard breaks (two trailing spaces);
  they were not reformatted to satisfy Git's generic whitespace warning.
- No real legal audit, live scanner/provider execution, dashboard/browser acceptance,
  global installation, or OS-policy change was performed for this extraction.

## Read-only MVP continuation — 2026-10-18

The Owner selected the read-only requirements-to-law revalidation MVP. Two visible
Orca workers completed architecture and legal-workflow reviews; the new scope and
acceptance requirements are recorded separately in [specifications v2](../specs_v2/README.md).
The Owner approved requirements, design/system context, the CLI unit, six stories
and the three-bolt sequence, then selected Bolt 001 Plan with `let's roll`.
Inception is complete. The Owner approved Bolt 001 Plan and starting Implement;
implementation acceptance and later stage checkpoints remain pending. No MVP implementation is complete. Historical
`specs/**` files remain unchanged. Baseline `make check` passed all 61 tests,
generated contract checks and TypeScript compilation; it was not repeated for
this documentation-only update. No live-law verification ran.

Planning validation checked 22 documents: YAML metadata and full timestamps, local
Markdown links, unique assignment of all six stories, and three acyclic bolt
dependencies. Construction stage checkpoints remain pending. The installed
specsmd completion script now has a preflighted private temporary tool environment
with `fs-extra` and `js-yaml`; module loading and script startup were verified,
without completing any bolt or adding an application dependency.

## Bolt 001 implementation start

Plan approved at 2026-10-18T19:15:48Z. The saved implementation plan covers every
criterion in stories 001–002 and defines contract, workflow and CLI/report file
ownership. Independent review corrections cover full metadata timestamps, explicit
local source media metadata and transitive synthetic provenance. Planning checks
verified 24 documents, including links, YAML/timestamps, all twelve acceptance
criteria, stage state and acyclic story/bolt assignments. No application code was
changed while preparing the plan. Stage 2 implementation is now authorized.

## Bolt 001 implementation checkpoint — 2026-10-19

The Owner requested visible teammates in split panes of the coordinator's Orca tab.
Two panes were created there and reused for contract writing/review, workflow and
CLI/report implementation, and independent integration review. Each file had one
writer; conversations remain in Orca rather than Git.

The first offline slice now accepts versioned declarations and selected local
files, retains the original claims, derives accountable effective reviews and
explicit gaps, and publishes validated JSON with escaped Markdown. It covers every
declared requirement and candidate obligation and expands eleven candidate-family
screenings. Unsupported source content/reviews, unknown facts and unavailable
evidence cannot silently support the result. Requirement-specific facts, origin and
evidence are checked independently of a mapped obligation's review. Missing explicit
amendment/case-law/national/related source dependencies also block derived support.

New public records originate in `models.py`. The generated JSON schema retains the
sixteen-operation Command root. A generator correction makes all public definitions
available in TypeScript; previously the compiler silently omitted unreachable
definitions under a union root. Contracts and the synthetic fixture were committed
and pushed as c617705; dependency hardening followed as 9d8daaa and f95002c.

`python -m eu_compliance_guard revalidate` is offline by default. Fetching and
predecessor arguments fail with exit 2 before reads/output. Outputs require a new
directory under a private owner-controlled parent, use 0700/0600 modes and a final
artifact-digest completion marker. Selected evidence bodies are not copied or
rendered; declarations and metadata remain private. Existing reports are preserved.

Stage 2 verification observed `make check` passing all 121 synthetic tests, generated
schema/type drift checks and TypeScript compilation. Independent CLI checks confirmed
the supported fictional mapping plus partial/unmapped coverage, marker digests, private modes,
collision/history preservation, unsupported flags, safe errors and symlink refusal.
Wheel and source distribution built offline; archive inspection found the expected
modules/schema and synthetic sdist resources without dependencies, caches or private
runtime artifacts. The built wheel also ran the offline synthetic example in an
isolated Python invocation outside the checkout.

The [implementation walkthrough](../memory-bank/bolts/001-legal-revalidation-cli/implementation-walkthrough.md)
is the Stage 2 handoff. Human validation is pending before the separate Test stage;
no story, bolt or MVP completion is asserted. No live-law, scanner or provider run,
real containment verification, global installation or OS-policy change occurred.
Offline freshness and reviewer identity remain unverified; source-page detection
is conservative and budgets impose cooperative checks rather than hard containment.

## Bolt 001 Test verification — 2026-10-19

The Owner approved Implement and starting Test, and clarified that audit reports
must clearly state what is wrong and the applicable legal point. The report now
starts with an actionable summary joining each reviewed deficiency or question to
the declared project requirement/location, source identifier and exact provision,
evidence rationale, applicability/reviewer and next action. It distinguishes
reviewed evidence insufficiency from unresolved support and legal violations.

`make check` passes all 130 tests. Five new boundary tests cover actual 32-file and
64 MiB aggregate limits, remaining bounded collections, and exact nested/aggregate
item limits. Four new renderer tests include a private offline insufficiency run
with a fictional article next to the project issue. Independent read-only review
verified all twelve acceptance criteria, CLI/history/privacy and the final report.
The wheel/sdist and isolated built-wheel offline example also passed after these
changes. No real laws or project compliance conclusions were established by fixtures.

The [Test report](../memory-bank/bolts/001-legal-revalidation-cli/test-walkthrough.md)
is ready for final human acceptance. Bolt/stories remain incomplete until that
approval and the required completion procedure. Official retrieval, revalidation
and the portable skill remain the next bolts; automatic repository inspection is
still deferred. Existing teammate panes/conversations remain in the same Orca tab.

## Bolt 001 accepted — 2026-10-19

The Owner accepted the Test report, completion of Bolt 001 and preparing Bolt 002
Plan. At 2026-10-19T09:08:42Z the mandatory specsmd completion script succeeded:
Bolt 001 is complete and both included stories are complete/implemented, with zero
script errors. Unit and intent remain open because two bolts are unfinished.
The final Test stage was recorded in bolt metadata after verifying the cascade.
The 130-test acceptance evidence remains unchanged; no new application code or
live-source operation was run for this lifecycle update.

## Bolt 002 official-source retrieval — 2026-10-25

On the Owner's direction to proceed, Bolt 002 Plan, Implement and Test were recorded
on branch `claude/bolt-002-official-retrieval`. All three await Owner validation.
`--fetch-official` now performs bounded opt-in retrieval through `sources.py`,
which applies the fixed host registry, pinned DNS/TLS, validated redirects and
the design bounds, using a disposable spawned helper. Attempts and unreviewed
candidate sources are retained in the bundle and run directory, and the report
lists them. See the [plan](../memory-bank/bolts/002-legal-revalidation-cli/implementation-plan.md),
[implementation walkthrough](../memory-bank/bolts/002-legal-revalidation-cli/implementation-walkthrough.md)
and [test report](../memory-bank/bolts/002-legal-revalidation-cli/test-walkthrough.md).

151 tests pass outside `test_execution.py`, and the contract drift and TypeScript
checks pass. In this container the existing executor tests fail or hang because
their sandbox binary is unavailable, so `make check` could not complete here.
That module is unchanged. No live official-source request, real legal assessment
or OS-policy change occurred. Predecessor revalidation and the portable skill
(Bolt 003) remain pending.

## Commit attribution — 2026-10-25

Owner correction: commits carry no `Co-authored-by` or agent session trailers.
Commits not yet merged into `main` were rewritten to remove those lines; their trees
and author/committer are unchanged. `main` history was deliberately left unchanged.
AGENTS.md, the coding standards and story 006 AC-5 now state the rule.

## Claude Code plugin interface — 2026-10-25

Owner direction: package the project more like a Claude Code plugin, with an
interface inspired by ponytail 5.3.2 (DietrichGebert/ponytail, reviewed at its
2026-10-18 head) and adapted for this workflow. The repository now carries
`.claude-plugin/plugin.json` and `marketplace.json`. It ships six skills (`eucg`
mode with lite/full/strict/off levels, `eucg-review`, `eucg-audit`, `eucg-gaps`,
`eucg-status`, `eucg-help`) and a standard-library SessionStart hook. The skills
drive the existing CLI and keep its limits: no invented reviews, no network
without consent, private runs outside the repository and no verdicts. These
plugin skills take the place of the single `skills/legal-revalidation/SKILL.md`
planned for Bolt 003. Predecessor comparison and release checks remain in Bolt 003.
`claude plugin validate .` passed, and 10 synthetic plugin/hook tests pass. No
real project was audited and the plugin was not installed globally.

The Owner then asked for real UI inside Claude Code and a button to open results in
the browser, following ponytail's band. The plugin now has a hooks module
(`hooks/band/register.tsx`, contract `types/index.d.ts`) that draws a band above the
prompt. It shows the latest run summary and has Audit / Review diff / Gaps / Open
report / Help buttons. A new `view` CLI command verifies a run and writes an
escaped, script-free HTML page beside it, then opens it in the browser. Checks:
`claude plugin validate .` passes, `claude plugin test .` passes 4 band tests on
all four surfaces, the band type-checks against Claude Code 2.1.310's API, and
165 Python tests pass outside `test_execution.py`. The band has not been seen in
an interactive local session yet.
