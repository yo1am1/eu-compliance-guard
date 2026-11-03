---
bolt: 003-legal-revalidation-cli
created: 2026-11-04T00:30:00Z
status: recorded
---

# Version 1.0.0 team audit — 2026-11-03/04

The Owner asked for an agentic team audit to confirm that 1.0.0 is ready. Native
Herdr was unavailable in this cloud session. The audit therefore ran as Claude Code
workflows that anyone could watch under `/workflows`. Every auditor was read-only,
so one writer (the coordinating session) made every change, and the findings are
recorded here.

## Method

1. **Audit:** five independent auditors, one lens each: security and privacy,
   functional correctness, plugin usability, legal-safety semantics, and release
   readiness. Each paired with an adversarial verifier that tried to refute every
   finding by reproducing it. 10 agents.
2. **Confirmation:** after the fixes, five agents reproduced every original finding
   against the fixed code and hunted for regressions the fixes introduced.
3. **Recheck:** one adversarial agent tried to bypass the tightened renewal rules.

## Verified findings and resolution

| Finding | Severity | Resolution | Commit |
| --- | --- | --- | --- |
| A plain rerun with `--previous` restored withdrawn support; renewing reviews made it stale again | blocker | Withdrawal carries forward until a genuine renewal; renewal edits are not new changes | `7013a36` |
| Run storage keyed by folder name, so another project's run, report and predecessor were shown | major | `state-dir` keys storage by the declared `project_id`; hook and band refuse other projects' runs | `f9d2b13` |
| Two sources on one target: freshness confirmed by the first source's bytes | major | Each source is confirmed only by its own bytes (assembly, bundle validator, history) | `a19f92c` |
| Documented maxima (200 obligations/requirements) could not publish or revalidate | major | Root lists bounded by their own limits; 16 MiB bundle; 5,000 gaps; ≤20 listed changes per overlay | `91e3de4`, `59dd588` |
| Band used the git root while hook/skills used the session project folder | major | Band uses `$.session.root()` | `f9d2b13` |
| `check` quoted malformed dates, timestamps and URL ports | minor | Fixed validator messages; fuzz test over every string value | `50b5360` |
| `check` printed unknown JSON keys raw (terminal escapes) | minor | Unknown keys print as `(unknown field)` | `50b5360` |
| `python -m` let a project's own `eu_compliance_guard` package run | minor | `python -P` in hook, band and skills | `f9d2b13` |
| The hook re-injected the default level after compaction | minor | It now states the default and keeps a level chosen in the session | `f9d2b13` |
| `mkdir -p -m 700` left the state parent 0755 | minor | `state-dir` creates every level 0700 | `f9d2b13` |
| Manual-source steps omitted `id` and `revision` | minor | Skill lists them | `f9d2b13` |
| Docs promised a reviewed PDF could clear its gap | minor | Docs now say PDFs always remain a gap in 1.0; save the HTML too | `f9d2b13` |
| Session hook did not label fictional runs | minor | `FICTIONAL / SYNTHETIC run.` prefix | `f9d2b13` |
| Symlinked path components reported `io-failed` | minor | `unsafe-path`; README explains symlink-free paths | `6b58b69` |
| *(confirmation)* A future-dated `reviewed_at` counted as a renewal forever | major | Renewal needs a higher revision and a review time between the two runs; attestations dated after the run are gaps | `a8a4b8a` |
| *(confirmation)* Family-screening withdrawal was not carried forward | major | Carried forward like obligations, until a genuine renewal | `a8a4b8a` |
| *(confirmation)* CHANGELOG did not describe the fixes | minor | Updated with this report | this change |

The verifiers refuted two findings. **Hand-edited review pins** was refuted because it
needs someone to edit human review records, which the skills forbid. **Revision
problems not named as JSON paths** was refuted because naming by record type and id
is intended. Testing also showed that switching between offline and fetch runs
changed the recorded policy digest and would have withdrawn every review. Offline and
fetch policies of the same tool version are now one configuration, since fetched
bytes are compared separately.

## Checks after the fixes

- `make check`: 214 tests, schema/TypeScript drift and compile.
- `make plugin-check`: validation passes; 6 band tests on all four surfaces.
- Each blocker/major fix has a regression test. The tests for the laundering blocker,
  freshness leak, value echo, future-dated renewal and family carry-forward were run
  against the pre-fix code and fail there.
- No live legal source was contacted and no real project was audited. The
  interactive band still needs a local check.

Owner acceptance of the MVP remains pending.
