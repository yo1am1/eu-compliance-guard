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
`uv run --project "${CLAUDE_PLUGIN_ROOT}" --locked --no-dev python -P -m eu_compliance_guard`.

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
  `www.edpb.europa.eu`, `publications.europa.eu`). For an act's text, prefer the
  Publications Office: `https://publications.europa.eu/resource/celex/<CELEX>` with the
  target's `language` (for example `en`); EUR-Lex itself blocks scripted requests.
  The base CELEX (`32002L0058`) returns the act as first published, without later
  amendments. For the law in force, use a consolidated CELEX, `0` + the act number +
  `-` + the consolidation date (for example `02002L0058-20091219` for ePrivacy as
  amended in 2009), and record that date. Never assume a consolidation is the latest
  one: ask the owner or a reviewer to confirm it. Set `"synthetic": false` only for a real project.
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

## Ground the assumptions in the code

With the default path, `init` sets `"files_root": "project"`, so selected paths resolve from the project folder.
Run `<cli> ground`. For each assumed or unknown fact it lists ranked `file:line`
candidates from a local index (no network, no model), flags organisational facts that
code can never show, and lists possible touchpoints that no fact covers.

- Show each fact's candidate lines to the owner. Pin only a line the owner confirms
  shows the technical fact (for example `set_cookie(..., max_age=…)` for a cookie
  lifetime): `<cli> ground --apply <fact-id>=<path>:<line>`. The fact becomes
  `observed`, with that file's digest as evidence. Later edits to the file make the evidence unavailable, and
  the gap returns until it is grounded again. `check` warns about it; never copy the new digest into the
  evidence, because only a line the owner confirms with `ground --apply` grounds the fact again.
- Never apply a candidate that only mentions a related word. Organisational facts
  (lawful basis, establishment, roles, size, sector) stay owner questions; the CLI
  refuses them.
- Offer to declare uncovered touchpoints as new `assumed` facts or requirements.
- Run `<cli> check` after applying, then a new run.

## Manually downloaded official documents

EUR-Lex answers scripted requests with a bot challenge, so `--fetch-official` records
a safe failure for it. When the user has downloaded the act (PDF or saved HTML):

1. Put the file under `.eu-compliance-guard/sources/` and keep a source target for it.
   With `"files_root": "project"`, its path is `.eu-compliance-guard/sources/<file>`.
2. Add a `sources[]` entry: `target_id`, `media_type` (`application/pdf`, `text/html`
   or `text/plain`), `charset` (`null` for PDF, else `utf-8`), `file.path` relative
   to the declarations file, and a `source` with a stable `id`, `revision: 0`, and
   `type`, `url`, `identifier`,
   `publisher`, `language` and `jurisdiction` equal the target's exactly. Set
   `retrieved_at` to when the user downloaded it (UTC), `provisions` to the
   article locators the obligations will cite (for example `Article 7`),
   `related_source_ids` to `[]`, and `synthetic` to `false`.
3. Use the same SHA-256 for `file.digest` and `source.content_digest`. Run `check`:
   a wrong digest is reported with the observed value to copy.
4. In 1.0 only text and HTML sources can support a mapping. A PDF can be declared and
   reviewed, but it always stays a "needs manual identity review" gap. If the act should
   support obligations, ask the user to also save the HTML version from EUR-Lex and
   declare that file. Never write the source review yourself.

## 2. Run

```sh
state="$(<cli> state-dir)"   # private 0700 run storage, keyed by the declared project_id
<cli> revalidate --input .eu-compliance-guard/declarations.json \
  --output "$state/run-$(date -u +%Y%m%dT%H%M%SZ)" --offline
```

- `--fetch-official` replaces `--offline` only when the user said yes to network
  access for this run. It GETs only the declared targets on the fixed registry.
  Fetched bytes are unreviewed candidates.
- For revalidation, pass the explicitly selected retained run directory with
  `--previous <run-directory>` and always choose a new output directory. When `$state`
  already holds a `run-*` directory with `complete.json`, offer the newest one to the
  user as the predecessor and use it only once they agree. Never choose one silently. The CLI verifies it and
  retains `comparison.json`, comparison evidence and historical freshness overlays.
- Increase revisions when changing versioned semantic records and update their
  explicit pins. A changed fact also changes the `scope` (and its activity) that
  contains it. `<cli> check --previous <run-directory>` names every record that
  still needs a higher revision before you run. Never invent renewed reviewer approval to clear a stale result.
  Explain stale dependencies and unknown freshness separately; unchanged bytes
  renew neither legal currency nor reviewer approval. Historical files stay intact.
- Exit 2: show the safe error code (for example `invalid-input`), fix the
  declarations and retry under a new run directory. Never overwrite a run.

## 3. Report

Lead with what to do, not with the gap count. A first run has many open items, and a
wall of them reads as failure.

1. Run `<cli> next --run <run dir> --top 5`. Show the five steps in plain words, each
   with how many open requirements it unblocks. Say that these five come first.
2. Then one line of context: `<N> open items in total; the rest are in the report
   (/eucg-gaps lists them all).` Do not list every gap unless the user asks.
3. If reviewed evidence deficiencies exist (read `report.md`, "What needs attention
   and the declared legal basis"), name them before the steps: they are a reviewer's
   recorded finding, not a missing answer.

For a full ledger on request, rank: reviewed evidence deficiencies, unresolved
applicability, missing source reviews, retrieval failures or changed bytes, unmapped
requirements and obligations, then family-screening gaps, one row each:
`<requirement or obligation id>, <what is wrong or unknown>. legal ref: <declared identifier — article>. next: <review action>.`

End with: `Run <id>: <partial|completed>. <N> gaps. Report: <path>. Processing state is not a compliance verdict.`
