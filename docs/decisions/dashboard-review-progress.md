# Decision: review-progress meters, not a compliance score

Date: 2026-11-04. Decided by the Owner.

## Context

`specs_v2/design.md` says a report has "No compliance score". The dashboard proposal
asked for separate meters that show how far the recorded review of one run has come.
The specification snapshots under `specs/**` and `specs_v2/` stay unchanged; this
note records the refinement instead.

## Decision

1. **Separate review-progress meters are accepted.** Each meter counts recorded review
   steps of one run as points out of 10 (Alignment, Law text, Facts, Decisions,
   Mapping, Reviews). There is no total, sum, average or "k of N meters" figure
   anywhere: not in the code, the JSON contract, the CLI, the HTML view, the band or
   the React dashboard. Every surface calls them "review progress" and carries the
   fixed notice "Points count recorded review steps in this run. They are not a
   compliance score or verdict." A meter with nothing declared reads "not scored",
   never 0 or 10, and nothing is coloured as a pass.
2. **"Style" is not scored.** Writing quality cannot be measured deterministically,
   so the dashboard shows unscored *record hygiene* chips instead (requirements
   located in project files, requirements with evidence referenced, origins
   unchanged).
3. **Screening is not a meter.** The eleven legal families appear as a plain coverage
   line ("k of 11 families screened").
4. **A file for the React dashboard.** `view` also writes
   `views/<run>.scorecard.json` (mode 0600, written like the HTML view), and the
   local `frontend/` dashboard page renders it with types generated from
   `eu_compliance_guard/models.py`.

## How this refines "No compliance score"

The specification forbids a score that could read as a verdict on compliance. The
meters stay within that rule: they are computed only from the recorded run, they
measure review bookkeeping (which steps are recorded and closed), they are never
combined, and the same run always gives byte-identical output. A row of 10s means
every recorded step the meters count is closed in that run; it is not a legal
conclusion, and the view still lists notes outside the meters (scope exclusions,
jurisdiction coverage, technical checks this workflow never runs).
