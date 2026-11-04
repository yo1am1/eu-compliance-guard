---
bolt: 003-legal-revalidation-cli
created: 2026-11-03T23:20:00Z
status: recorded
---

# Version 1.0.0 end-to-end check — 2026-11-03

The Owner asked to continue to a stable 1.0 MVP plugin. This check used the released
branch the way a new user would get it. The installed CLI was built from the wheel,
and the plugin was installed from GitHub through the real marketplace flow, not
`--plugin-dir`. A real headless Claude Code (2.1.310) then drove the installed
plugin on a new fictional project (a bakery shop). The Owner's own download of the
GDPR (Regulation (EU) 2016/679, OJ L 119, 4.5.2016, SHA-256 `bd84e63f…0c2499`) was
declared as a manually selected source. Nothing here establishes legal truth or
audits a real project.

| Step | Result |
| --- | --- |
| `make check` | 205 tests, schema and TypeScript drift, TypeScript compile: pass. The executor tests no longer need host sandbox tools. |
| `make plugin-check` | `claude plugin validate .` passes with no icon warning; 4 band tests pass on all four surfaces |
| Wheel and sdist | The wheel needs only `pydantic==2.14.1` (FastAPI and Uvicorn are the `api` extra) and has the `eu-compliance-guard` console script. The sdist carries the plugin files, icon, changelog and lock. No `.venv`, `node_modules`, caches or backups. |
| `uv tool install` wheel, outside the checkout | `init` → `check` → `revalidate` → `revalidate --previous` (records the scope change) → `view`: all exit 0 |
| Marketplace install from GitHub at the branch | Installs as 1.0.0 and is enabled |
| SessionStart hook from the plugin cache | The level, the `--no-dev` CLI command, declarations present, and the latest-run summary |
| `/eucg-audit` with the user's GDPR PDF | It ran `init`, drafted 5 requirements and 4 candidate GDPR obligations with every fact `assumed` or `unknown`, and declared the PDF with the exact digest and Articles 5/6/7/13. `check` passed and the run was `partial` with 60 gaps. No reviewer, review time or applicability was invented. The PDF bytes were retained as `sources/<digest>.bin` (0700/0600). |
| Code change, then `/eucg-audit` with the previous run | It raised revisions for the fact, the requirement and the scope. The first attempt hit `invalid-revision`, which led to adding `check --previous` with located messages. The successor made all four obligations stale, because attribution through the shared scope is incomplete, and kept the offline freshness gap separate. |
| `/eucg-status`, `/eucg-gaps`, `/eucg-review` | Correct cards and ledger. `/eucg-review` recognized that the change was already declared. Status miscounted "offline only" sources; the skill now defines the count. |
| `view` through the plugin's own uv environment | First use built a 6-package environment in about 1 s. The view was written and `no-browser` was reported, because the container has no browser. |

## Findings

- `claude plugin update` matches on the version number, so a fix shipped under the
  same version does not reach installed users. Every fix after 1.0.0 needs a new
  version (enforced across `pyproject.toml`, `__init__.py` and `plugin.json` by
  `tests/test_plugin.py`).
- A changed fact also changes the scope that contains it, so obligations sharing that
  scope all become stale. This is conservative by design, and the audit skill explains it.
- The band itself was not seen; it draws only in an interactive terminal or the
  desktop app.

Owner acceptance of the Bolt 003 stages and of the MVP remains pending.
