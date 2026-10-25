---
name: eucg-status
description: >
  Latest EU Compliance Guard run at a glance: run id and time, processing state,
  requirement and obligation counts by state, gap count, source attempts and
  freshness, and how old the assessment date is. One-shot, changes nothing. Use
  for "eucg status", "when did we last revalidate", "compliance status",
  /eucg-status.
---

Show where the project's legal revalidation stands, in one short card.

## Read

- Find the newest run under
  `${XDG_STATE_HOME:-$HOME/.local/state}/eu-compliance-guard/<project>/` that has
  `complete.json`. If there is none: `No run yet. Use /eucg-audit.`
- From `bundle.json`, read: `run.id`, `run.ended_at`, `run.state`,
  `declarations.scope.assessment_date`, `requirement_assessments[].state`,
  `obligation_dispositions[].applicability`, `len(gaps)`, and
  `source_attempts[].state` with `retrieval.comparison`.
- Compare `.eu-compliance-guard/declarations.json` with the run's `input.json`.
  If they differ, the run is out of date for the current declarations.

## Output

```
EU Compliance Guard · run <id> · <ended_at>
state <partial|completed> · assessment date <date> (<N> days old)
requirements: <s> supported · <c> conflicting · <u> unresolved
obligations: <a> applicable · <n> not applicable · <u> unresolved
sources: <r> retrieved (<same> same bytes, <changed> changed) · <f> failed · <o> offline only
gaps: <N> · declarations changed since run: <yes|no>
```

If the user wants the full picture, offer the browser view:
`<cli> view --run <run dir> --open` (or the band's Open report button).

Close with one line: the most urgent next action from `next_actions`, then
`Processing state is not a compliance verdict.`
