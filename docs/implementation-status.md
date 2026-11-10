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

- Shared validated records for scope, sources, evidence, obligations, decisions,
  assessments and progress.
- Generated JSON Schema with a drift check.
- An offline requirement/report CLI, synthetic first-run fixture, bounded selected
  file reads, accountable mapping/evidence gaps and private immutable run artifacts.
- Synthetic foundation, contract, offline workflow, CLI and escaped-report tests,
  with a generated schema drift check.
- (Removed in 2.6, Owner decision: the unused foundation for scanners of our own, namely the
  offline Linux executor helper, the agent-protocol inspection and about 60 record types for
  commands, conversations and patches. No command used them; Git history keeps them.)
- A locked Python environment (uv.lock), package selection, and license notices.

## Current state (v2.6.0, 2026-11-10) and what remains

2.5.1 fixes what a full audit of 2.5.0 found (see the changelog): official freshness for EU
acts, timeline dates, unknown articles and acts, unpinned signatures, linear graph readers and
graph limits, the macOS hook, pr-check and grounding precision, imports, and documentation that
claimed more than the code does (tamper evidence, licence statements, platform support).

2.6 added optional semantic ranking of article suggestions (a pinned local model merged with
word search; off by default), sealed runs (`seal`, a hash-chained log), `make e2e`, and removed
the unused scanner foundation and records.

Released: 1.0 to 2.6. 2.5 fixed what an audit of 2.2 to 2.4 found (three quadratic parsers,
CSV cells, duplicate names in the graph) and removed the unused React page and `api` extra.
2.4 taught the project graph Rust (`docs/decisions/rust-graph.md`). 2.3 added the application-date timeline, draft starter packs and the
Article 30 and DPIA exports. 2.2 added jurisdictions as modules and the UK (legislation.gov.uk); see
`docs/decisions/jurisdictions.md`. 2.1 tested the base on hostile input, real official texts and real
projects, and fixed what fell short (see the changelog). The 2.0 summary follows. The read-only workflow covers:

- declarations, `check`, official-source retrieval from six verified EU hosts, the
  version in force with a newer-consolidation notice, reports, and predecessor
  revalidation;
- the Claude Code plugin: band, side panel, a static dashboard and a graph view;
- grounding with an inverted index and explained matches, `accept`, and `next`;
- `pr-check` (graph-aware, monorepo-aware), `score`, and `make eval`;
- 2.0: `lock` and `impact` (law lockfile and change impact), `sign` and `verify` (SSH-
  signed decisions), `cite-check`, the `mcp` server (`cite_check`, `article_search`,
  `ground`, `pr_check`, `next_steps`; `timeline` from 2.3), the `pack` format, and `import-evidence` (EDPS
  Website Evidence Collector and SARIF).

CI runs `make check` on every pull request. Supply-chain, determinism, regex and
legal-notice rules are enforced by tests.

How 2.0 was verified: unit tests (a real throwaway ed25519 key for signing), then a
scripted end-to-end run of every new command on a synthetic project, with `mcp` driven
as a separate process over stdio. That run found three defects, fixed before release.
Not done: signing with the Owner's own key, a connected MCP client such as Claude Code,
and a live band and panel check inside a session (this environment cannot drive a
second Claude agent).

Candidates for 2.1 (see the [roadmap](roadmap.md)): exports to GRC tools, graph digests
in runs so a code change reopens decisions as a law change does, an application-date
timeline, quoted articles in the PR screen, and a Graphify import. A full audit for
defects is planned and waits for the Owner's approval. (2.5.0 removed the unused React
page in `frontend/` and the `api` extra; the plugin uses the static dashboard.)

Still not built: an operational compliance audit, an API or hosted service, a reviewed
legal corpus or reviewed packs, scanners of our own, browser checks, and managed
remediation. Outputs remain workflow evidence for a named reviewer, never a verdict.

## Review-progress dashboard (2026-11-04)

Owner decision recorded in `docs/decisions/dashboard-review-progress.md`: separate
meters, points out of 10, no total, never a compliance score. Implemented: the pure
`eu_compliance_guard/scorecard.py` (`Scorecard` contract in `models.py`), the `score`
command, a Review progress section at the top of the HTML view, `views/<run>.scorecard.json`
written by `view`, and meter lines in the band and panel. (A React page in `frontend/`
also rendered the file until 2.5.0 removed it.)
Screening is a coverage line and "style" is unscored record hygiene. All tests use the
synthetic fixture; a scorecard says nothing about real compliance.

## Hardening, 1.5 bolt 011 (2026-11-05)

Order of priority: security, then determinism, then features.

- **Supply chain.** New releases wait 14 days: `exclude-newer = "14 days"` for uv and
  Dependabot `cooldown` for uv and GitHub Actions. Security updates are exempt.
  Actions are pinned to commit SHAs.
- **Official hosts.** `docs/official-hosts.md` names each host's operator and purpose.
  `make verify-hosts` re-checks reachability with consent. On 2026-11-05 all six
  answered: EUR-Lex returned a bot challenge (202) and CURIA refused automated clients
  at its root (403).
- **Fewer regular expressions.** Parsing now uses explicit code, and tests check it
  against the old patterns. Six anchored validators remain, and
  `tests/test_regex_policy.py` blocks any new regex.
- **Legal notice.** Every human-readable output ends with `notice.LEGAL_NOTICE`.
- **Determinism.** `tests/test_determinism.py` compares every output across hash
  seeds, time zones and locales. A planted set-order dependency makes it fail.

## Search evaluation, 1.5 bolt 005 (2026-11-05)

`make eval` runs the synthetic set in `fixtures/eval/`: a fictional act, 20 tuning and
20 held-out requirements, and 10 grounding facts over a fictional project. Baseline,
enforced as a floor by `tests/test_evaluation.py`:

| Set | Top-1 | Top-3 |
|---|---|---|
| Articles, tuning | 15/20 | 18/20 |
| Articles, held out | 14/20 | 17/20 |
| Grounding | 7/10 | 8/10 |

Misses to work on in bolt 006: parental consent, rectification wording ("correct",
"fix"), pseudonymisation, cancelling "a plan", and the auto-renew and encryption facts.

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

## Predecessor comparison and release checks — 2026-10-27

On the Owner's direction, the latest plugin/UI branch was pulled and predecessor
comparison implemented in `ed11d8f`. `--previous` verifies one explicitly selected
retained run and creates a linked successor with `comparison.json`, observed
comparison evidence and historical freshness overlays. Relevant dependency changes
withdraw effective review support; original declarations and every predecessor
byte are retained. Missing observations remain unknown; matching bytes renew
neither legal currency nor reviewer approval. Incomplete dependency attribution
withdraws support conservatively. Family screenings renew after any known change.

All 197 tests pass with schema/type drift checks and TypeScript compilation.
Claude plugin validation and all four band tests pass. Wheel/sdist builds,
archive inspection and the isolated installed-wheel first-run/successor/static-view
workflow pass outside the checkout with packaged fictional data, valid marker
digests and private modes. See the [Test walkthrough](../memory-bank/bolts/003-legal-revalidation-cli/test-walkthrough.md).
Technical implementation and release checks are recorded; formal stage and MVP
acceptance remain pending. No current-law or real-project audit was performed.

No live source/provider/scanner, interactive UI, global installation or host-policy
work ran. Historical `specs/**` remain unchanged. The plugin validator warns about
the missing marketplace icon. Native Herdr is unavailable in this session; work
used one writer, without hidden teammates. Two pre-existing local planning edits
remain in Git stash. The next authorized work is the separate recommender audit,
system improvements and Streamlit MVP.

## Version 1.0.0 — 2026-11-03

The Owner asked to review the latest commits and continue to a stable 1.0 MVP plugin.
The Owner's 2026-10-27 predecessor revalidation (`ed11d8f`, `c392935`) was reviewed
and kept. Those two commits carry `Co-authored-by: Codex` trailers, which the newer
commit rule excludes; they were left as published.

1.0.0 adds `init` and `check`. `check` gives located, value-free diagnostics, observed
file digests, target fetchability, and with `--previous` the records needing a new
revision. Cross-reference errors in the models now name their JSON location. 1.0.0
also adds the `eu-compliance-guard` console command and keeps only Pydantic as a
runtime dependency (FastAPI and Uvicorn were an optional `api` extra until 2.5.0). The plugin
audit flow now runs `init` → `check` → `revalidate` and covers manually downloaded
official documents. Other changes:

- the plugin CLI runs with `uv run --no-dev`, and the hook warns when uv is missing;
- the plugin has an icon, and `make plugin-check` exists;
- the README was rewritten and a changelog added;
- the fake executor tests are hermetic.

`make check` passes 205 tests, and the plugin validates with no icon warning and its
4 band tests pass. A fresh end-to-end check installed the wheel and the plugin from
GitHub through the marketplace, then ran every skill on a fictional project with the
Owner's GDPR PDF. See the [1.0 end-to-end report](../memory-bank/bolts/003-legal-revalidation-cli/v1-e2e-report.md).
The interactive band was not seen, and no live legal assessment was made. Owner
acceptance of the MVP remains pending.

## Release team audit — 2026-11-03/04

On the Owner's request, a read-only agentic team audit ran as workflows, since
native Herdr is unavailable here; all changes had one writer. Five lenses with
adversarial verification were followed by a confirmation round and a focused recheck.
It verified one blocker (withdrawn support restored by a plain rerun) and several
majors: runs shared by same-named folders, freshness confirmed by another source's
bytes, the documented maxima failing to revalidate, the band using the git root, and,
from the confirmation round, future-dated renewals and family screenings not carried
forward. It also found minor diagnostic, labelling and documentation issues. All are
fixed with regression tests; details are in the
[team audit report](../memory-bank/bolts/003-legal-revalidation-cli/v1-team-audit-report.md).
`make check` passes 217 tests, and the plugin validates and passes its 6 band tests.
A final recheck found a renewal deadlock and rename/re-add bypasses, which are now
fixed, and one documented limit: a run compares only against the predecessor it names.
Owner MVP acceptance remains pending.


## Version 1.1.0 — 2026-11-04

The Owner asked for a more meaningful basis for assumed facts, article text next to
each gap, the next best action, a PR check and a side panel, then to publish 1.1.0.
1.1.0 adds `ground` (a local BM25 index of the project's code with a legal-concept
lexicon; confirmed technical facts become `observed` with the file digest as
evidence), the Publications Office as the sixth official host, article text and
article suggestions in the report, `next` with `/eucg-next` and the band's Next step,
`pr-check` with `/eucg-pr` and a GitHub Actions example, and the `/eucg-panel` side
panel. A two-reviewer release review found eleven defects; all were fixed with
regression tests. `make check` passes 248 tests and the plugin's 14 band and panel
tests pass. See the [1.1 release record](../memory-bank/bolts/004-grounding-and-guidance/v1.1-release-report.md).
