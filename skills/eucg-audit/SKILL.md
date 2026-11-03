---
name: eucg-audit
description: >
  Full read-only revalidation of a project's declared requirements against
  candidate EU obligations: prepare or update .eu-compliance-guard/declarations.json,
  run the private offline report (or, with explicit consent, the official-source
  fetch), and present what needs attention, ranked. Use for "eucg audit",
  "run the compliance report", "revalidate against EU law", /eucg-audit.
argument-hint: "[--fetch-official] [--previous <run-directory>]"
---

Produce the project's traceable revalidation report. The report states what is
declared, what is supported by named reviews, and every gap. It is never a verdict.

Use the CLI command from the SessionStart context, written `<cli>` below, or
`uv run --project "${CLAUDE_PLUGIN_ROOT}" --locked --no-dev python -m eu_compliance_guard`.

## 1. Declarations

- The input is `.eu-compliance-guard/declarations.json` in the project root. It is a
  versioned `RevalidationInput` record. The shape is defined in
  `${CLAUDE_PLUGIN_ROOT}/eu_compliance_guard/contract.schema.json`
  (`$defs.RevalidationInput`), and a complete fictional example is in
  `${CLAUDE_PLUGIN_ROOT}/fixtures/revalidation-synthetic.json`.
- If it is missing, start from a valid file instead of writing one from scratch:
  `<cli> init --project-id <stable-id> [--jurisdiction EU --jurisdiction <country>]`.
  Then fill in the project scope, jurisdictions, assessment date
  (today unless the user names one), activities, and facts from the code, with
  `basis: "unknown"` or `"assumed"` unless the user confirms them. Add requirements
  with stable IDs and source targets on registry hosts only (`eur-lex.europa.eu`,
  `curia.europa.eu`, `commission.europa.eu`, `digital-strategy.ec.europa.eu`,
  `www.edpb.europa.eu`). Set `"synthetic": false` only for a real project.
- Never fill reviewer, `reviewed_at`, applicability, source reviews or evidence
  reviews yourself. They stay empty or unresolved until a named human supplies them.
  Evidence paths point to files the user selected; their bodies are not read into
  the report.
- After every edit run `<cli> check`. It prints each problem with its JSON location
  (for example `requirements[0].fact_refs[0]: fact-x is pinned at revision 7 but
  declared at revision 0`), the observed digest of every selected file, and whether
  each source target can be fetched. Fix errors until it says `valid`; warnings are
  review gaps the report will carry, not blockers.
- Show the user the draft diff before the first run.

## Manually downloaded official documents

EUR-Lex answers scripted requests with a bot challenge, so `--fetch-official` records
a safe failure for it. When the user has downloaded the act (PDF or saved HTML):

1. Put the file under `.eu-compliance-guard/sources/` and keep a source target for it.
2. Add a `sources[]` entry: `target_id`, `media_type` (`application/pdf`, `text/html`
   or `text/plain`), `charset` (`null` for PDF, else `utf-8`), `file.path` relative
   to the declarations file, and a `source` whose `type`, `url`, `identifier`,
   `publisher`, `language` and `jurisdiction` equal the target's exactly. Set
   `retrieved_at` to when the user downloaded it (UTC), `provisions` to the
   article locators the obligations will cite (for example `Article 7`),
   `related_source_ids` to `[]`, and `synthetic` to `false`.
3. Use the same SHA-256 for `file.digest` and `source.content_digest`. Run `check`:
   a wrong digest is reported with the observed value to copy.
4. A PDF always stays "needs manual identity review" until a named human records
   the source review. Do not write that review yourself.

## 2. Run

```sh
state="${XDG_STATE_HOME:-$HOME/.local/state}/eu-compliance-guard/$(basename "$PWD")"
mkdir -p -m 700 "$state"
<cli> revalidate --input .eu-compliance-guard/declarations.json \
  --output "$state/run-$(date -u +%Y%m%dT%H%M%SZ)" --offline
```

- `--fetch-official` replaces `--offline` only when the user said yes to network
  access for this run. It GETs only the declared targets on the fixed registry.
  Fetched bytes are unreviewed candidates.
- For revalidation, pass the explicitly selected retained run directory with
  `--previous <run-directory>` and always choose a new output directory. Do not
  discover history or choose a predecessor silently. The CLI verifies it and
  retains `comparison.json`, comparison evidence and historical freshness overlays.
- Increase revisions when changing versioned semantic records and update their
  explicit pins. Never invent renewed reviewer approval to clear a stale result.
  Explain stale dependencies and unknown freshness separately; unchanged bytes
  renew neither legal currency nor reviewer approval. Historical files stay intact.
- Exit 2: show the safe error code (for example `invalid-input`), fix the
  declarations and retry under a new run directory. Never overwrite a run.

## 3. Report

Read `report.md`, starting with "What needs attention and the declared legal
basis". Rank the items: reviewed evidence deficiencies first, then unresolved
applicability, missing source reviews, retrieval failures or changed bytes,
unmapped requirements and obligations, then family-screening gaps.

For each item give one row:
`<requirement or obligation id>, <what is wrong or unknown>. legal ref: <declared identifier — article>. next: <review action>.`

End with: `Run <id>: <partial|completed>. <N> gaps. Report: <path>. Processing state is not a compliance verdict.`
