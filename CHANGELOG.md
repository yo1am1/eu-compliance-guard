# Changelog

## Unreleased

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
