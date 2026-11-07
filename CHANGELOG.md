# Changelog

## Unreleased

### Added

- Rust in the project graph (2.4): a small reader of its own (no Rust toolchain, no new
  dependency) finds functions, methods, structs, enums and traits, `use` imports, `mod`
  declarations and calls, with the same data tags and flows as Python. Test code
  (`#[cfg(test)]`, `#[test]`, `tests/`, `benches/`) is left out; macros are not expanded.
  Measured on three real crates (see `docs/decisions/rust-graph.md`). `reqwest` and `ureq` are
  third-party words.

### Changed

- "health" alone no longer marks special-category data in the graph; it needs a data word
  next to it ("health_data", "health_record"): `release-health` and health checks were
  tagged as health data on real projects.

## 2.3.0 — 2026-11-07

The laws software teams meet now: application dates quoted from the text, draft starter packs
for the GDPR, ePrivacy cookies, the Accessibility Act and the Cyber Resilience Act, and drafts
for record keeping. The US is not added (Owner decision); 2.4 is left to be decided.

Acceptance: the timeline was checked on the real final provisions of the AI Act, the CRA, the
EAA, NIS2 and the GDPR, every quotation verbatim. Every starter-pack pin was checked against
the official text; the GDPR pack was imported into a project, the GDPR fetched live and locked,
and a second import reported no text difference. The exports were tested on synthetic
activities, with hostile text kept out of Markdown and CSV formulas.

### Added

- Exports (2.3): `export ropa` drafts a record of processing activities in the shape of GDPR
  Article 30(1), with each fact's basis and every gap listed; `export dpia` drafts DPIA
  screening inputs (Article 35(3) and the WP248 criteria) with the signals the declarations
  show and no answers. Markdown, JSON, and CSV for the record.

- Application-date timeline (2.3): `timeline` lists the dated application, entry-into-force
  and transposition clauses of the retained text, word for word, reached or upcoming against
  the assessment date; also an MCP tool.
- The Cyber Resilience Act, the European Accessibility Act and NIS2 are part of the real-text
  test set (71, 35 and 46 articles).
- Draft starter packs: GDPR core (13 obligations), ePrivacy cookies and electronic marketing
  (2), European Accessibility Act services (2) and Cyber Resilience Act manufacturers (3),
  shipped in the package and listed by `pack starters`. Every pin is checked against the
  official text and every pinned article's digest is recorded. AI-assisted, reviewed by no
  one, no guarantee; imported with `--unsigned`, never as decisions.

## 2.2.0 — 2026-11-06

Jurisdictions become modules, and the United Kingdom is the second one, through
legislation.gov.uk. The EU behaves as before; the record formats do not change.

Acceptance: the UK GDPR, PECR and the Data Protection Act 2018 were fetched with the tool's own
retrieval and parse into 120 articles, 50 regulations and 259 sections, with titles checked
against the source (now a committed test set). A project with a PECR target ran
`revalidate --fetch-official` against the live site, locked 50 regulations, showed Regulation 6
with the UK version note in the report, and `cite-check` confirmed a verbatim quotation. See
`docs/decisions/jurisdictions.md`.

### Added

- Jurisdictions as modules (2.2): each jurisdiction registers its official hosts, its act
  identifiers and its well-known acts (`jurisdictions.py`). The EU is the first.
- The United Kingdom: `www.legislation.gov.uk` (The National Archives) is a registered host;
  UK identifiers (`ukpga/2018/12`, `uksi/2003/2426`, `eur/2016/679`, with an optional date)
  are read for `check`, the report's version note and the law lockfile; legislation.gov.uk
  XHTML is parsed into sections, regulations and articles, with amendment notes left out;
  the citation guard reads "section 170", "s. 170", "regulation 6" and "reg. 6" and knows
  the UK GDPR, the Data Protection Act 2018, PECR and other UK acts by name. The audit skill
  shows how to declare UK targets.
- A test set of UK texts (UK GDPR, PECR, Data Protection Act 2018) under the Open Government
  Licence, next to the EU texts.

### Fixed

- legislation.gov.uk may take over ten seconds to build a large act; its host gets a 30-second
  first-byte allowance, while an explicit retrieval budget always wins.
- `lock` counts provisions, not articles.

## 2.1.0 — 2026-11-06

Precision: the 2.0 base tested on hostile input, real law and real code, and fixed where it
fell short. No new jurisdiction yet; that is 2.2.

How it was tested:

- Every parser of untrusted input was fuzzed (12,000 random and mutated rounds plus targeted
  edge cases); a seeded version now runs in CI.
- The article parser and citation guard ran on real official texts (GDPR, AI Act, consolidated
  ePrivacy Directive), now a committed test set with digests.
- The project graph was measured on three real projects (django-allauth, sentry-sdk, Django),
  parsed only, with hand-judged samples; see `docs/decisions/graph-precision.md`.
- The WEC importer's field names were checked against the EDPS collector's source code.
- Signing, packs, the lockfile, the reports and the plugin were read adversarially; HTML views
  were checked with injection payloads in every free-text field (all escaped).

### Fixed

- The MCP server no longer stops on one deeply nested JSON message, limits nesting to 64
  levels on every Python, and rejects invalid request ids and NaN.
- SARIF imports no longer print a boolean line number.
- WEC imports read the site from `targetUrl`, as current collector versions write it (field
  names checked against the collector's source); older `uri_ins` files still work.
- `verify` binds each signature file to the decision it is named after and lists reviewed
  decisions left unsigned; signature files are read without following links, size-limited.
- `pack import` imports exactly the bytes whose signature it verified.
- `impact` reports law text the newer run did not retain as not compared, never as removed,
  and refuses another project's lock.
- The project graph tags data from identifiers, not prose or generic words, starts no flow in
  test code, and follows at most one ambiguous call per flow. On three real projects the
  false children's-data tags fell from hundreds to none (see
  `docs/decisions/graph-precision.md`).

### Added

- Citations are checked in the act they name ("Article 17 GDPR", "Article 5(3) of the
  ePrivacy Directive", "Article 99 of Regulation (EU) 2016/679"); well-known acts the run
  did not retain are reported as not checked.
- Tests: seeded fuzzing of every parser of untrusted input, and a test set of real official
  texts (GDPR, AI Act, consolidated ePrivacy Directive) in `fixtures/official/`.

## 2.0.0 — 2026-11-06

From a review tool to a compliance workspace: the law a review read is pinned, a law
change reopens exactly the decisions that cite it, decisions are signed by their
reviewer, agent-written citations are checked against the official text, and other
tools' results come in as untrusted evidence. This completes the 2.0 intent as the
Owner adopted it; GRC exports and the graph side of change impact move to 2.1.

Acceptance, recorded honestly:

- Every new command ran end to end on a synthetic project, by script: `revalidate`,
  `lock`, `sign` and `verify` with a real ed25519 key (unchanged, then reported as
  changed after an edit), `cite-check` (a pass, then a missing article and a misattributed
  quotation), `pack build`, `sign`, `verify` and `import`, `import-evidence` and `impact`.
- `mcp` ran as a separate process driven over stdio through the MCP handshake
  (`initialize`, `tools/list`, every tool, and an invalid call). The official MCP
  Inspector could not be run in this environment; no Claude client was connected.
- The check found three defects, fixed before release (see Fixed).
- Signing with the Owner's own key and a live band and panel check in a session were
  not done.

### Added

- Law lockfile and change impact (2.0 bolt 017): `lock` writes `eu-law.lock` (each act's
  version, source digest and per-article digests, from a verified run). `impact` lists
  the articles changed since the lock and the obligations, decisions and requirements
  citing them, with `--strict` for CI. The contract is generated from `models.py`
  (`LawLock`).
- Signed decisions (2.0 bolt 018): `sign` signs a reviewed applicability decision with
  the reviewer's SSH key (`ssh-keygen -Y sign`), covering the decision, its obligation, the
  locked article digests, the evidence digests and the commit. `verify` checks each
  signature against an allowed-signers file and names what changed since signing.
- Citation guard: `cite-check` checks that cited articles exist in the retained text and
  quotations appear verbatim in the cited article. `mcp` serves it, `article_search` and
  `next_steps` as read-only MCP tools over stdio.
- Imports (2.0 bolt 019): `import-evidence --kind wec|sarif` keeps an EDPS Website
  Evidence Collector inspection or a SARIF log as untrusted evidence under
  `.eu-compliance-guard/imports/`, with a summary by concept. Declarations are never
  changed. Synthetic fixtures only.
- Obligation packs (2.0 bolt 020), format only: `pack build` drafts a pack of portable
  obligations with their article pins and the locked article digests; `pack sign` and
  `pack verify` use the reviewer's SSH key; `pack import` adds candidate obligations
  and targets, never overwrites a different record, and never maps or decides. The
  contract is generated from `models.py` (`ObligationPack`).
- MCP review tools (2.0 bolt 021): the `mcp` server also serves `ground` (read-only
  proposals) and `pr_check` (given a unified diff).
- `--version` prints the installed version.

### Changed

- The README is a short overview; the full command reference moved to `docs/cli.md`
  and the plugin's band, panel, dashboard and hook to `docs/plugin.md`.
- Package metadata (authors, classifiers, keywords, project links), a contributing
  guide, a security policy, and issue and pull-request templates.

### Fixed

- Grounding and the project graph no longer read the tool's own outputs (`imports/`,
  `signatures/`, `eu-law.lock`) as project code when the files root is the declarations
  folder: imported tool output is untrusted and was proposed as code evidence.
- Importing a pack into the project it came from no longer reports a conflict.
- `sign` says when no `eu-law.lock` exists, so the signature pins no article text.

## 1.5.0 — 2026-11-06

Trustworthy guidance: suggestions explain themselves, a suggestion becomes a mapping in
one step, and the law shown is the version in force, with a notice when a newer
consolidation exists. This completes the 1.5 intent.

Acceptance, recorded honestly:

- The plugin loaded in a real Claude Code session, its commands were listed, and
  `/eucg-audit` started (initialising a fictional project with `--synthetic`).
- The accept flow was verified on real runs, with screenshots. Before, Mapping was
  5/10 and the next step was to map the requirement. After `accept` and a new run,
  Mapping was 10/10, `check` stayed valid, and the next step was a reviewer's
  applicability decision. Nothing was decided automatically.
- Not verified live: the band and side panel updating inside an interactive
  session. This environment does not allow driving a second Claude agent; the
  automated band tests (33) cover them.

### Added

- Newer-consolidation notice (1.5 bolt 008, part two). With `revalidate --fetch-official`,
  each act target with a CELEX number gets one fixed query to the Publications Office's
  SPARQL endpoint, through the same registry-checked, bounded retrieval as act text. CSV
  answers are admitted for these requests only. A newer consolidation, a base CELEX with
  a consolidation in force, or an unreadable answer becomes a review gap; declarations
  are never changed.

## 1.4.0 — 2026-11-05

Act on suggestions in one step, see which version of the law you are reading, and use
the plugin on real repositories: faster grounding, monorepos, the newest run by
completion, CI on every pull request, and code evidence in the side panel.

### Added

- Panel grounding (1.5 bolt 010): each fact the owner still has to confirm shows its top
  code line (`code app/roles.py:12`), and a **Confirm code evidence** button opens
  `/eucg-next`, which asks the owner before pinning anything. Locations are validated
  (plain path segments, no `..`, a line number), and no run text is shown.
- Real repositories (1.5 bolt 009):
  - `ground` searches through an inverted index. 300 facts over about 60,000 lines of
    real Python now take 0.6 s instead of 33 s, with identical results (checked on 400
    queries and pinned by a full-scan test).
  - The newest run is the one completed last (its completion marker), not the last
    name, in the CLI and the band.
  - `pr-check` in a monorepo matches diff paths below the project folder: run it from
    the repository top with `--input services/api/.eu-compliance-guard/declarations.json`.
- `accept REQ=TARGET:ARTICLE` (1.5 bolt 007) maps a requirement to a candidate
  obligation citing that article, reused or created, with revisions and pins updated
  atomically. It never records an applicability decision. `/eucg-next` offers it for
  mapping steps.
- Law in force (1.5 bolt 008, part one): CELEX numbers are read from target identifiers
  and Cellar or EUR-Lex URLs without a regular expression. `check` warns when an act
  target uses a base CELEX (the act as first published) and lists each target's
  version. Each article excerpt in the report names the consolidation date or says the
  text is as first published.

## 1.3.0 — 2026-11-05

Review progress at a glance, a project graph that follows data through the code,
measured search, and hardening: a 14-day version cooldown, verified official hosts,
fewer regular expressions, a legal notice on every output and a determinism test.

### Added

- Review progress: `score` shows separate meters for one run (Alignment, Law text,
  Facts, Decisions, Mapping, Reviews), each points out of 10 for recorded review
  steps, with a family screening line and unscored record hygiene. There is no total
  and no verdict; see `docs/decisions/dashboard-review-progress.md`.
- The HTML view leads with a Review progress section, and `view` also writes
  `views/<run>.scorecard.json` (0600).
- The band and panel show the meters in fixed format (one `score --json` call per run
  replaces the `next` call).
- `frontend/` has a local, offline dashboard page that renders a scorecard file.
- **Dashboard** button (band hotkey `d`, also in the panel): `view --dashboard --open`
  opens `views/<run>.dashboard.html`. It is one static, at-a-glance page with no build,
  no server and no script.
- `make verify-hosts` checks, with consent, that each official host answers over
  HTTPS. `docs/official-hosts.md` names each host's operator and purpose, and a test
  keeps it in step with the code.
- `make eval`: a versioned synthetic evaluation set (1.5 bolt 005) for article search
  and grounding, with a baseline floor enforced by a test. Baseline: articles top-1
  15/20 and top-3 18/20 on tuning, 14/20 and 17/20 held out; grounding top-1 7/10 and
  top-3 8/10.
- Graph view (2.0 bolt 016): `graph --view [--open]` and the panel's **Graph** button
  open a static, script-free page. It shows a fixed-layout picture of the functions on
  data flows or touching a concept, with flows highlighted and ambiguous calls dashed.
  It also lists each flow with its pinned facts, and law to code: fact, then the
  requirements and obligations relying on it.
- Graph-aware `pr-check` (2.0 bolt 015): with declarations, a diff that adds lines inside
  a function on a data flow lists that flow and the facts pinned on it, or says no
  fact covers it. The graph comes from the checked-out code; `revalidate` still reads
  only selected files, so runs do not record a graph.
- Hybrid search (2.0 bolt 014) was measured and not adopted. Re-ranking code
  candidates by graph closeness gave no gain on either grounding set (7/10 and 5/6
  top-1 with or without it); see `docs/decisions/hybrid-search.md`. Six multi-file
  grounding cases now join `make eval`.
- Path evidence (2.0 bolt 013): `ground` follows data through the project graph.
  Candidates inside a flow show the call path, for example `plan_meals → ask_model`,
  with each hop's `file:line`. Flows from personal, health or children's data to AI,
  tracking, third parties or marketing that no pinned evidence covers are listed for
  review. `make eval` now reports flows found (1/1) and unexpected flows (0).
- `graph` (2.0 bolt 012) builds a deterministic project graph by static parsing only:
  Python files, classes and functions, imports and calls (resolved like Python, with
  `ambiguous` labels instead of guesses), and the concepts each function touches. The
  contract is generated from `models.py` (`ProjectGraph`). It maps 60k lines in about
  3 s.
- Explained suggestions (1.5 bolt 006): each article suggestion and grounding
  candidate lists the terms that matched. Each term is marked as coming from the
  statement or fact, or bridged through the legal or concept vocabulary (with the word
  it came from). This appears in the view, in `ground` text and in JSON. The search
  also improved:

  | Set | Before (top-1, top-3) | After |
  |---|---|---|
  | Articles, tuning | 15, 18 | 17, 20 |
  | Articles, held out | 14, 17 | 14, 17 |
  | Grounding | 7, 8 | 7, 10 |

  The changes are rectification and parental-consent bridge terms, and base word
  forms ("renews" finds `auto_renew`) in grounding. Only tuning misses were used.
- Every text, markdown and HTML output ends with one legal notice: not legal advice,
  the named reviewer decides and is responsible, no warranty.

### Changed

- Hardening (1.5 bolt 011):
  - Dependency resolution waits 14 days for new releases (`[tool.uv] exclude-newer`).
    Dependabot updates uv, npm and GitHub Actions with a 14-day cooldown, while
    security updates go through without the wait.
  - The pull-request check example pins its actions to commit SHAs.
  - Parsing regular expressions are replaced by explicit parsers, and tests compare
    each parser with the old pattern on random inputs. Only short, anchored validators
    remain, and a lint test blocks any new regular expression in Python or in the band.
  - A test runs the pipeline under different hash seeds, time zones and locales and
    requires byte-identical outputs.
- Gap phrases that other modules read back and the provision pin checks are shared
  constants and one helper in `revalidation.py`; recorded output is unchanged.

## 1.2.0 — 2026-11-05

Licence change and the Great Auditor fixes: 83 confirmed defects found by an agent
audit that tested every command, option and flow, each fixed with a regression test.

### Changed

- Licence changed from MIT to GNU AGPL-3.0-only, with an attribution notice
  (`NOTICE`, section 7(b)). Releases 1.0.0 and 1.1.0 remain MIT.
- `init` keeps file paths inside the project: outside `.eu-compliance-guard/` it sets
  `"files_root": "declarations_dir"`. It refuses symlinked folders and an empty date.
- A missing declarations file is reported as `io-failed`; an unreadable or linked path
  as `unsafe-path`. A named `pr-check --input` must exist.
- Commits are unsigned and carry only the Owner's identity. Some earlier commits on
  `main` (up to 1.1.0) carry co-author trailers, one carries an agent identity, and
  some show as Unverified on GitHub; history was not rewritten.

### Fixed

- `next` gives every open requirement a step (new `review` kind), asks to ground a
  fact again when its pinned file changed, names what blocks a recorded decision, and
  never offers to fetch a target the fetch policy refuses.
- `ground` never grounds legal facts (lawful basis, roles, size) in code, lists facts
  whose pinned file changed, re-pins them cleanly, keeps uncited touchpoints visible,
  checks every `--apply` before writing any, accepts only plain line numbers, keeps the
  file mode and reports unreadable folders as skipped. `--json` works with `--apply`.
- `check` reports every problem in one pass with its JSON location (including stale
  pins and the revision cascade), encoding problems, oversized files and truncation,
  and never prints unknown keys. A changed grounded code file is a warning to ground
  again, not a digest to copy.
- Run history never restores withdrawn support because a file was briefly missing;
  same-run renewals are explained; unreadable runs report `unsafe-path`.
- Article text: chapter and section headings, scripts, tables of contents, correlation
  tables and annex suffixes no longer leak into or split articles; BOM and upper-case
  media types are handled.
- `pr-check` rejects coloured or non-diff input, strips mnemonic prefixes, counts
  renames once and keeps added lines of combined merge diffs.
- Output that cannot be written is `io-failed` (never a traceback or exit 1); text the
  console cannot encode is escaped. A relative `XDG_STATE_HOME` is ignored.
- The view and report name removed historical obligations, show each source's type and
  style only admitted retrievals as confirmed. The band shows the run state and says
  when the default level is off.
- `revalidate` handles up to the bundle's gap limit, and its requirement gaps name the
  real blocker.

## 1.1.0 — 2026-11-04

Grounded assumptions, article text and guidance on what to do next.

### Added

- **Grounding (`ground`):** a local, explainable index of the project's code (Okapi
  BM25 over identifier-split tokens with a legal-concept lexicon; no network, model
  or embeddings). It ranks `file:line` candidates for each assumed or unknown fact and
  lists touchpoints no fact covers. `ground --apply FACT=PATH:LINE` pins a confirmed
  technical fact as `observed`, with the file's digest as evidence; organisational
  facts are refused. A later change to the file reopens the gap.
- **Act text from the Publications Office:** `publications.europa.eu` (Cellar) joins
  the fixed host registry as the sixth host, with the target's language tag sent as
  `Accept-Language` and a same-host http→https redirect upgrade only for that host.
- **Article text in the report:** each declared "Article N" reference expands to the
  article's title and text from the act bytes the run retained. Each requirement
  lists up to three articles to read, ranked by a local text search that bridges
  everyday words to legal vocabulary. Both are labelled unreviewed candidates.
- **Next best step (`next`, `/eucg-next`):** open steps ranked by how many open
  requirements each one unblocks (retrieve text, confirm a fact, review a source,
  decide applicability, map a requirement, screen families), in the CLI, the report,
  the band and a skill that walks through step 1 without filling in review data.
- **Pull-request check (`pr-check`, `/eucg-pr`):** deterministic screening of a
  diff's added lines for legal concepts with candidate families, whether the
  declarations mention each one, and evidence or requirements in changed files.
  Markdown for a PR comment, JSON, and `--strict`. A GitHub Actions example keeps one
  marked comment updated.
- **Side panel (`/eucg-panel`, band Panel button):** a pane beside the chat with the
  top three steps, the facts the owner still has to confirm and open gaps by area.

### Changed

- The band shows the next best step and has Next step and Panel buttons.
- Report IDs wrap at hyphens.

### Fixed (release review)

- `ground --apply` never follows a planted temp-file symlink and reads declarations
  without following links; a bare relative `--input` resolves the project root.
- Oversized project files are skipped without being read whole.
- Plain-text acts no longer open an article at a reference such as "Article 6(1)".
- Source targets with an invalid language tag fail as `invalid-language` instead of
  being fetched in English.
- Diff paths can no longer break out of PR comment code spans; broad words alone no
  longer count as a concept being mentioned.
- The band ranks each run once, keeps a failed ranking instead of retrying every turn,
  and never lets an older run's ranking replace the newest.
- Skills never pin evidence or record review fields the owner did not give.

## 1.0.0 — 2026-11-03

First stable MVP of the read-only requirements-to-law revalidation workflow.

### Added

- **Declarations and reports (Bolt 001):** versioned declarations with accountable
  review attestations. Private, immutable run directories with completion-marker
  digests. JSON and escaped Markdown reports that put each issue beside its declared
  legal provision.
- **Official-source retrieval (Bolt 002):** `--fetch-official` with a fixed
  five-host registry, pinned DNS and verified TLS, validated redirects, byte and time
  bounds, and a disposable helper process. Retrieved bytes become unreviewed
  candidates; every failure is a safe recorded attempt.
- **Revalidation (Bolt 003):** `--previous` verifies one retained run, records
  `comparison.json` and freshness overlays, and makes changed dependencies stale.
- **Claude Code plugin:** the `/eucg` mode (lite, full, strict, off) and the
  `eucg-review`, `eucg-audit`, `eucg-gaps`, `eucg-status` and `eucg-help` skills.
  Also a SessionStart hook, a band above the prompt with Audit, Review, Gaps,
  Open report and Help buttons, and the plugin icon.
- `view` writes a verified, script-free HTML view of a run and can open it in the browser.
- `init` writes a valid starter declarations file. `check` reports each problem with
  its JSON location, the observed digest of every selected file, and whether each
  source target can be fetched. `check --previous` names every record whose content
  changed without a higher revision.
- `state-dir` prints and creates (0700, symlink-free) the private run storage, keyed by
  the declared `project_id`. The hook, band and skills use the same location.
- `eu-compliance-guard` console command and `make plugin-check`.
- The report view opens with "Questions for the project owner": each assumed or
  unknown fact, its current answer and the requirements relying on it. Open gaps are
  grouped by area with counts, collapsing the long fact and family lists. The
  predecessor comparison says added, removed or changed and names obligations instead
  of digests.

### Changed

- Cross-reference errors name their JSON location and identifiers, for example
  `requirements[0].fact_refs[0]: fact-x is pinned at revision 7 but declared at revision 0`.
- Runtime dependencies are Pydantic only. FastAPI and Uvicorn moved to the optional
  `api` extra; the plugin runs the CLI with `uv run --no-dev`.
- The fake-process executor tests no longer depend on host sandbox tools, so
  `make check` completes on hosts without bubblewrap.

### Fixed (release team audit)

- **Withdrawn support persists.** A plain rerun with `--previous` no longer restores
  withdrawn support. Support returns only when the applicability decision and every
  evidence review are new revisions reviewed between the two runs. Family screenings
  follow the same rule, and attestations dated after a run are review gaps. Renaming
  or removing and re-adding an obligation cannot reuse old reviews, and renewing an
  obligation and its family screening together restores both.
- **Freshness per source.** Retrieved bytes confirm only the source with those same
  bytes, even when several sources share one target.
- **Storage per project.** Runs are stored per declared `project_id`, not per folder
  name. Runs of another project are never shown, and the band follows the session's
  project folder (worktrees included).
- **Documented maxima.** 200 requirements and 200 obligations publish and revalidate
  across runs. The bundle limit is 16 MiB.
- **Diagnostics.** `check` never echoes declared values or raw unknown keys. Symlinked
  path components report `unsafe-path`. The CLI runs with `python -P`, so a project's
  own package cannot replace it.
- **Band report link.** The band hides its report link once a newer run exists.
- **Labels and levels.** The session hook labels fictional runs and keeps a level
  chosen earlier in the session. Offline and fetch runs of one version count as the
  same configuration.

See [the audit report](memory-bank/bolts/003-legal-revalidation-cli/v1-team-audit-report.md).

### Known limits

- EUR-Lex answers scripted clients with a bot challenge; declare manually
  downloaded acts as selected sources. Only text and HTML sources can support a
  mapping; a PDF always remains a manual-identity-review gap.
- All input, output and predecessor paths must be free of symbolic links.
- Revalidation compares only against the predecessor you name; naming an older run (or
  none) compares against that state.
- Some official pages change bytes on every request, so exact-byte comparison reports
  them as changed.
- The band draws only in interactive Claude Code (terminal or desktop app).
- No output is a compliance verdict, and reviewer names are self-attested.
