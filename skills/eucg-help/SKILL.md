---
name: eucg-help
description: >
  Quick reference for EU Compliance Guard levels, skills and the CLI. One-shot
  display. Use for /eucg-help, "eucg help", "how do I use eu compliance guard".
---

# EU Compliance Guard help

Display this reference card when invoked. It is one-shot: do NOT change the mode,
write files or run the CLI.

## Levels

| Level | Trigger | What changes |
|-------|---------|--------------|
| **Lite** | `/eucg lite` | One line naming each legal touchpoint and its candidate family. No files written. |
| **Full** | `/eucg` | Lite, plus keeps `.eu-compliance-guard/declarations.json` updated with unresolved facts. Default. |
| **Strict** | `/eucg strict` | Full, plus asks the applicability questions before building and pushes back on unjustified data use. |
| **Off** | `/eucg off` | Stops noticing. |

## Skills

| Skill | Trigger | What it does |
|-------|---------|--------------|
| **eucg** | `/eucg` | The mode itself: notice touchpoints, keep declarations and gaps explicit. |
| **eucg-review** | `/eucg-review` | Maps a diff to the eleven candidate families and the facts to declare. |
| **eucg-audit** | `/eucg-audit` | Prepares declarations, runs the private report and ranks what needs attention. |
| **eucg-next** | `/eucg-next` | Walks through the step that unblocks the most open requirements. |
| **eucg-pr** | `/eucg-pr` | Screens a branch or PR diff for legal touchpoints; can set up the GitHub Action. |
| **eucg-gaps** | `/eucg-gaps` | Ledger of open review gaps from the latest run. |
| **eucg-status** | `/eucg-status` | The latest run at a glance. |
| **eucg-help** | `/eucg-help` | This card. |

## Band and report view

In Claude Code (terminal or desktop app), a band above the prompt shows the latest
run: review progress (separate meters, points out of 10, no total and not a compliance
score), state, assessment age and the next best step. It
has buttons for Next step, Audit, Review diff, Gaps, Dashboard, Open report, Panel and Help, plus `–` to fold it.
Panel (or `/eucg-panel`) opens a side pane with each meter, the top three steps, the facts still to
confirm and open gaps by area. Dashboard opens a one-page static view of the meters, next steps and
owner questions in your browser (no build, no server). Open report
writes a static HTML view of the verified run and opens it in your browser.

## CLI

- `init --project-id <id>` writes a valid starter `.eu-compliance-guard/declarations.json` (never overwrites).
- `check [--input <file>] [--previous <run dir>] [--json]` validates declarations with located problems, observed file digests, target fetchability and (with `--previous`) records that need a higher revision and withdrawn support not yet renewed.
- `revalidate --input <declarations.json> --output <new run dir> [--offline | --fetch-official] [--previous <run dir>]`

- Offline by default. `--fetch-official` GETs only the declared targets on six fixed
  official hosts, and only with your consent for that run.
- Runs are private (0700/0600) and immutable. Use a new directory per run.
- Exit 0: report written, possibly partial. Exit 2: invalid input or output.
- `ground [--apply <fact>=<path>:<line>]` finds code evidence for assumed facts with a local index and pins confirmed technical facts as observed.
- `next [--run <run dir>] [--top N] [--json]` ranks the open steps of the newest (or given) run by how many open requirements each unblocks.
- `score [--run <run dir>] [--against <run dir>] [--json]` shows review progress: separate meters (Alignment, Law text, Facts, Decisions, Mapping, Reviews), each points out of 10 for recorded review steps, plus a family screening line and unscored record hygiene. There is no total; the points are not a compliance score or verdict. Exit 0 whatever the points.
- `lock [--run <run>]` records each act's version and article digests in `eu-law.lock`; `impact [--run <run>] [--json] [--strict]` lists the articles changed since the lock and the obligations, decisions and requirements citing them.
- `accept <requirement>=<target>:<Article N> [--input <file>] [--json]` maps a requirement to a candidate obligation citing that article (reused or created); it never decides applicability.
- `graph [--input <file>] [--json] [--view [--open]]` maps the project's Python files, functions, imports and calls by parsing only (nothing is run); paths are possible paths, never proof.
- `pr-check [--diff <file>|-] [--input <file>] [--markdown|--json] [--strict]` screens a unified diff's added lines for legal touchpoints and compares them with the declarations.
- `state-dir` prints (and creates, 0700) the private run storage for this project's `project_id`.
- `view --run <run dir> [--dashboard] [--open]` writes
  `<parent>/views/<run>.html`, `<run>.dashboard.html` and `<run>.scorecard.json` from a verified run (the run itself is unchanged).

## Fewer permission prompts

Allow `Bash(uv run --project * --locked --no-dev python -P -m eu_compliance_guard *)`
in `.claude/settings.json` or with `/permissions`. Fetching still needs consent.

## Limits

No output is a compliance verdict. Reviewer names are self-attested. Retrieved pages
are unreviewed candidates. The eleven families are not all of EU law.

## Deactivate

Say "stop eucg" or "normal mode". Resume anytime with `/eucg`.
