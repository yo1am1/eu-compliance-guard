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
- `eu-compliance-guard` console command and `make plugin-check`.

### Changed

- Cross-reference errors name their JSON location and identifiers, for example
  `requirements[0].fact_refs[0]: fact-x is pinned at revision 7 but declared at revision 0`.
- Runtime dependencies are Pydantic only. FastAPI and Uvicorn moved to the optional
  `api` extra; the plugin runs the CLI with `uv run --no-dev`.
- The fake-process executor tests no longer depend on host sandbox tools, so
  `make check` completes on hosts without bubblewrap.

### Known limits

- EUR-Lex answers scripted clients with a bot challenge; declare manually
  downloaded acts as selected sources.
- Some official pages change bytes on every request, so exact-byte comparison reports
  them as changed.
- The band draws only in interactive Claude Code (terminal or desktop app).
- No output is a compliance verdict, and reviewer names are self-attested.
