# Changelog

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
