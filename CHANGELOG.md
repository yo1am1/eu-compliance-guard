# Changelog

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
