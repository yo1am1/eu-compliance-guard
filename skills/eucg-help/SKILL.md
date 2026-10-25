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
| **eucg-gaps** | `/eucg-gaps` | Ledger of open review gaps from the latest run. |
| **eucg-status** | `/eucg-status` | The latest run at a glance. |
| **eucg-help** | `/eucg-help` | This card. |

## Band and report view

In Claude Code (terminal or desktop app), a band above the prompt shows the latest
run: state, gaps, supported requirements and assessment age. It has buttons for
Audit, Review diff, Gaps, Open report and Help, plus `–` to fold it. Open report
writes a static HTML view of the verified run and opens it in your browser.

## CLI

`python -m eu_compliance_guard revalidate --input <declarations.json> --output <new run dir> [--offline | --fetch-official]`

- Offline by default. `--fetch-official` GETs only the declared targets on five fixed
  official hosts, and only with your consent for that run.
- Runs are private (0700/0600) and immutable. Use a new directory per run.
- Exit 0: report written, possibly partial. Exit 2: invalid input or output.
- `python -m eu_compliance_guard view --run <run dir> [--open]` writes
  `<parent>/views/<run>.html` from a verified run (the run itself is unchanged).

## Limits

No output is a compliance verdict. Reviewer names are self-attested. Retrieved pages
are unreviewed candidates. The eleven families are not all of EU law.

## Deactivate

Say "stop eucg" or "normal mode". Resume anytime with `/eucg`.
