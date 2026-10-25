---
bolt: 003-legal-revalidation-cli
created: 2026-10-25T07:25:00Z
status: recorded
---

# Plugin and UI end-to-end check — 2026-10-25

The Owner asked for an end-to-end real test. This exercised the v3 plugin branch
with a real Claude Code (2.1.310, headless `claude -p --plugin-dir`) on a
fictional sample project: a tiny shop with newsletter signup, auto-renew checkout
and a new uncommitted analytics cookie. The plugin's own runs went to a private
state directory outside the project. No real project was audited.

| Step | Result |
| --- | --- |
| Wheel built and installed in a fresh environment, offline example run outside the checkout | exit 0, `partial`, 0700/0600, marker valid |
| `/eucg-help` | Reference card printed from the plugin skill |
| `/eucg-review` on the uncommitted diff | Found the tracking cookie (`app.py:11-13`), mapped it to eprivacy plus gdpr, listed facts to declare as `assumed`/`unknown`, named reviewer questions, wrote nothing, drew no compliance conclusion. It also named the two touchpoints outside the diff. |
| `/eucg-audit` | Drafted `.eu-compliance-guard/declarations.json` (3 requirements, 3 EUR-Lex targets, facts `assumed`/`unknown`). It set no reviewer, review time or applicability and left all review lists empty. It ran the CLI offline into a new private run (`partial`, 34 gaps) and ranked the attention items with the "not a verdict" line. |
| `/eucg-status` | Correct card. It first reported "declarations changed: yes" falsely, because the skill compared against the normalized `input.json`. Fixed to compare the file's SHA-256 with the bundle's `input_digest`; it now reports "no". |
| `view` on the real and live runs | Static HTML written beside the runs (0600); no scripts; `no-browser` reported because the container has no browser |
| SessionStart hook on the live run | Injected level, CLI command and a fixed-format summary (52 gaps, 2 retrieved / 3 not confirmed) |
| `claude plugin validate .` / `claude plugin test .` | pass / 4 band tests pass on four surfaces |

## Not covered

- The band above the prompt draws only in an interactive terminal or the desktop app.
  `claude -p` reports that hook modules are not loaded, and a cloud session has no
  such surface. Its drawing and buttons are covered by `claude plugin test` only;
  an interactive local check is still needed.
- Opening the browser itself: this container has none.
- `--previous` revalidation (story 004) and release checks (story 006) are not built.
