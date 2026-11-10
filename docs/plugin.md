# Claude Code plugin

The plugin adds slash commands, a band above the prompt, a side panel, a static dashboard and a session hook. Install it as the [README](../README.md#quick-start-claude-code) shows.
It runs on Linux and macOS; Windows is not supported.

**Band above the prompt.** This needs Claude Code 2.1.290 or later, in the terminal or
the desktop app. In projects with `.eu-compliance-guard/`, it shows the latest run's
state, open gaps, supported requirements, assessment-date age and source attempts, plus
the next best step (for example `Next: confirm fact-minimum-age · unblocks 2 open
requirements`). It has **Next step**, **Audit**, **Review diff**, **Gaps**, **Dashboard**,
**Open report**, **Panel** and **Help** buttons, and `–` folds it to one line. It shows counts and
fixed-format fields only, never gap text.

**Side panel.** **Panel** (or `/eucg-panel`) opens a pane beside the chat, docked in
the desktop app and in a wide fullscreen terminal. It shows the top three next steps,
the facts the owner still has to confirm (by id, with each one's best code line from
`ground` and a **Confirm code evidence** button that opens `/eucg-next`), and open gaps
counted by area, with
buttons to work on step 1, open the report, list gaps or refresh.

**Dashboard** opens a one-page view of review progress: the meters, the next best
steps and the owner's open questions, with a link to the full report. Like the board of
the Ponytail plugin, it is a single self-contained HTML file written beside the report, with no
build, no server and no scripts, opened straight from disk in your browser
(`view --run <run dir> --dashboard --open`).

**Open report** writes a static HTML view of the verified run and opens it in your
browser. The page has no scripts, loads nothing and escapes every value. When the run
retains an act's text (a declared file or a `--fetch-official` retrieval), each declared
"Article N" reference expands to that article's text, and each requirement lists up to
three articles to read, ranked by a local text search. Both are unreviewed candidates:
the excerpt is not the consolidated version and a suggestion is not a mapping.

**Session hook.** In projects with `.eu-compliance-guard/`, it adds the active level,
the CLI command for this machine and a summary of the latest run. Set the default
level with `EUCG_DEFAULT_MODE` or `~/.config/eu-compliance-guard/config.json`
(`{"defaultMode": "lite"}`).

Runs are stored outside the repository in
`${XDG_STATE_HOME:-~/.local/state}/eu-compliance-guard/<project_id>/`, keyed by the
declared `project_id`. `eu-compliance-guard state-dir` prints and creates it with
mode 0700. A relative `XDG_STATE_HOME` is ignored, as the XDG Base Directory spec
requires, so the path never depends on the current folder. Keep runs out of Git.

## Fewer permission prompts

Each CLI step asks for permission by default. To allow the plugin's own CLI in a project,
add the exact command the session hook prints ("CLI for this machine"), with the plugin's
own path, to `.claude/settings.json` (or run `/permissions` and add it), for example:

```json
{
  "permissions": {
    "allow": ["Bash(uv run --project <plugin path> --locked --no-dev python -P -m eu_compliance_guard *)"]
  }
}
```

Never use a wildcard for `--project`: `--project *` would also let uv build and run any other
project's code, including a hostile repository's own package. Update the path after a plugin
update. The rule covers every CLI command, including the ones that write the project's
`.eu-compliance-guard/` records and `revalidate --fetch-official`; once it is allowed, asking
for your consent before network use is an instruction to the agent, not a prompt.
