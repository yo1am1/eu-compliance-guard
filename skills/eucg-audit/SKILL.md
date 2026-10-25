---
name: eucg-audit
description: >
  Full read-only revalidation of a project's declared requirements against
  candidate EU obligations: prepare or update .eu-compliance-guard/declarations.json,
  run the private offline report (or, with explicit consent, the official-source
  fetch), and present what needs attention, ranked. Use for "eucg audit",
  "run the compliance report", "revalidate against EU law", /eucg-audit.
argument-hint: "[--fetch-official]"
---

Produce the project's traceable revalidation report. The report states what is
declared, what is supported by named reviews, and every gap. It is never a verdict.

## 1. Declarations

- The input is `.eu-compliance-guard/declarations.json` in the project root. It is a
  versioned `RevalidationInput` record. The shape is defined in
  `${CLAUDE_PLUGIN_ROOT}/eu_compliance_guard/contract.schema.json`
  (`$defs.RevalidationInput`), and a complete fictional example is in
  `${CLAUDE_PLUGIN_ROOT}/fixtures/revalidation-synthetic.json`.
- If it is missing, draft one: the project scope, jurisdictions, assessment date
  (today unless the user names one), activities, and facts from the code, with
  `basis: "unknown"` or `"assumed"` unless the user confirms them. Add requirements
  with stable IDs and source targets on registry hosts only (`eur-lex.europa.eu`,
  `curia.europa.eu`, `commission.europa.eu`, `digital-strategy.ec.europa.eu`,
  `www.edpb.europa.eu`). Set `"synthetic": false` only for a real project.
- Never fill reviewer, `reviewed_at`, applicability, source reviews or evidence
  reviews yourself. They stay empty or unresolved until a named human supplies them.
  Evidence paths point to files the user selected; their bodies are not read into
  the report.
- Show the user the draft diff before the first run.

## 2. Run

Use the CLI command from the SessionStart context, or
`uv run --project "${CLAUDE_PLUGIN_ROOT}" --locked python -m eu_compliance_guard`:

```sh
state="${XDG_STATE_HOME:-$HOME/.local/state}/eu-compliance-guard/$(basename "$PWD")"
mkdir -p -m 700 "$state"
<cli> revalidate --input .eu-compliance-guard/declarations.json \
  --output "$state/run-$(date -u +%Y%m%dT%H%M%SZ)" --offline
```

- `--fetch-official` replaces `--offline` only when the user said yes to network
  access for this run. It GETs only the declared targets on the fixed registry.
  Fetched bytes are unreviewed candidates.
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
