# EU Compliance Guard

Tools and portable agent instructions for revalidating project requirements against
applicable EU law, using current official sources and traceable evidence.

**Status: offline reporting, official-source retrieval and the Claude Code plugin are implemented; broader MVP acceptance is pending.**
No real compliance audit has run. This repository preserves the work originally
started in [agentic-setup](https://github.com/yo1am1/agentic-setup).

## Current implementation

- Validated records for project scope, legal sources and source failures,
  obligations, evidence, findings, review gaps, and historical/current assessments.
- A generated JSON Schema and TypeScript contract from the Python models.
- Versioned requirement declarations, accountable review attestations and validated
  mapping records, preserving unsupported claims as explicit effective gaps.
- An offline CLI that reads selected local files and writes private JSON/Markdown
  reports with immutable run directories and completion-marker digests.
- Native-agent protocol inspection and reply/admission validation, without a live
  provider bridge.
- A bounded Linux execution helper with fake-process tests. Real containment remains
  unverified; this is not an enabled repository scanner.
- Synthetic fixtures, 61 foundation tests and focused workflow/CLI/contract tests,
  plus schema/type drift checks.
- Preserved requirements, design, research, implementation plan, and team reviews.

Predecessor comparison now retains changed dependencies and historical freshness
overlays, invalidating affected effective reviews. A reviewed legal registry,
API, scanner integration and dashboard remain pending. `frontend/`
currently contains the generated contract and build metadata; `npm run build` is
not an implemented UI milestone.

## Claude Code plugin

The repository is also a Claude Code plugin. Its interface is inspired by
[ponytail](https://github.com/DietrichGebert/ponytail) and adapted for read-only
legal revalidation:

```text
/plugin install eu-compliance-guard --marketplace yo1am1/eu-compliance-guard
```

On older Claude Code versions, run `/plugin marketplace add yo1am1/eu-compliance-guard`,
then `/plugin install eu-compliance-guard@eu-compliance-guard`.
The CLI needs `uv` (preferred) or Python 3.12+ with Pydantic.

| Command | What it does |
| --- | --- |
| `/eucg [lite\|full\|strict\|off]` | Mode: notices EU legal touchpoints while coding and keeps declarations/gaps explicit |
| `/eucg-review [target]` | Maps a diff to the eleven candidate legal families and the facts to declare |
| `/eucg-audit [--fetch-official]` | Prepares `.eu-compliance-guard/declarations.json`, runs the private report and ranks what needs attention |
| `/eucg-gaps` | Ledger of open review gaps from the latest run |
| `/eucg-status` | The latest run at a glance |
| `/eucg-help` | Reference card |

**Band above the prompt** (Claude Code 2.1.290 or later, terminal or desktop app). In
projects with `.eu-compliance-guard/`, a band shows the latest completed run: its
state, open gaps, supported requirements, assessment-date age and source attempts.
Its buttons are **Audit**, **Review diff**, **Gaps**, **Open report** and **Help**,
and `–` folds it to one line. It reads run data as counts and fixed-format fields
only. The module is `hooks/band/register.tsx`, tested with `claude plugin test .`.

**Open report in the browser.** The button runs the plugin CLI's `view` command:

```sh
python -m eu_compliance_guard view --run <run dir> --open
```

It first verifies the run's completion marker and every artifact digest. It then
writes a static HTML page to `<parent>/views/<run>.html` (0700/0600) and opens it
with the default browser. The page has no scripts and loads nothing, and every
value is escaped. The run directory itself is never changed. In a cloud session
there is no local browser, so the page is only written and its path is shown.

A SessionStart hook (standard-library Python) adds the active level, the CLI
command for the machine and a fixed-format summary of the latest run. It only
activates in projects that have a `.eu-compliance-guard/` directory. Run output
goes to `${XDG_STATE_HOME:-~/.local/state}/eu-compliance-guard/<project>/`, never
into the repository. Set the default level with `EUCG_DEFAULT_MODE` or
`~/.config/eu-compliance-guard/config.json` (`{"defaultMode": "lite"}`).
The skills never invent reviewers or decisions. They never use the network
without consent for that run, and they never state a compliance verdict.

## Local checks

Prerequisites: Python 3.12+, uv, Node.js, npm, and make. Install the locked dependencies:

```sh
uv sync --locked
npm --prefix frontend ci --ignore-scripts
make check
```

The test suite uses synthetic data and fake subprocesses. These commands do not audit
the laptop, execute a target repository, contact a model provider, or change OS policy.
Dependency installation requires the package registries or populated local caches.

After intentionally changing the shared models, regenerate both contracts and check:

```sh
make contracts
make check
```

## Run the offline example

Use the visibly fictional declaration and selected files in `fixtures/`. Paths in
a declaration resolve relative to its JSON file. Only explicitly selected regular
files are read; the workflow does not discover or execute a target project.

```sh
uv run --locked python -m eu_compliance_guard revalidate --help
eucg_example_dir=$(mktemp -d /tmp/eucg-example.XXXXXX)
uv run --locked python -m eu_compliance_guard revalidate \
  --input fixtures/revalidation-synthetic.json \
  --output "$eucg_example_dir/run-001" --offline
uv run --locked python -m eu_compliance_guard revalidate \
  --input fixtures/revalidation-synthetic.json \
  --previous "$eucg_example_dir/run-001" \
  --output "$eucg_example_dir/run-002" --offline
```

Keep the task variable in the same shell. The output parent must already exist,
belong to the current user and exclude group/other permissions. The run directory
must be new; existing paths and symlink components are refused. New directories
use 0700 and files use 0600. Existing parents are never chmodded.

Read `report.md` and `bundle.json` in the new directory. A valid run also retains
normalized declarations, a manifest, accepted source bytes and `complete.json`
with exact artifact digests. Evidence bodies are not copied or rendered; the
remaining metadata and attestations are private too. Incomplete directories lack
a valid completion marker; retry under a new path. Keep reports out of Git.

The report starts with what needs attention: each reviewed deficiency or unanswered
question is shown beside its project requirement/location, declared legal
identifier and article/paragraph, evidence rationale and next review action.
Missing applicability or legal support stays a review gap; it is not presented as
an established violation. The example's laws and conclusions are explicitly fictional.

Exit 0 means artifacts were published, including an explicitly partial report.
Exit 2 means invalid input, capacity or file/output failure; interruption exits 130.
The example contains one supported fictional mapping and unresolved coverage,
facts and unmapped records. Neither its result nor a passing test establishes
legal compliance. Reviewer names are local attestations, not authenticated approval.
Offline real-source freshness remains unverified; PDF bytes require manual review.
Processing budgets are cooperative, without a hard CPU/filesystem deadline or
containment guarantee.

Network is disabled by default; `--offline` is explicit. `--fetch-official` opts in
to bounded GETs of each declared source target. Only five exact official hosts are
allowed, over HTTPS on port 443. DNS answers must be public, and the connection is
pinned to a validated address. TLS is verified. Up to three validated redirects
are followed, with 8 MiB per response and 20 s per target. Fictional fixture
targets are never contacted. Each target gets a recorded attempt, and accepted bytes
are retained as unreviewed candidates. Retrieval never establishes binding status,
completeness, applicability or currency. `--offline` and `--fetch-official`
conflict. Tests use fake transports only. A separately authorized historical
[live smoke check](memory-bank/bolts/002-legal-revalidation-cli/live-smoke-report.md)
records EUR-Lex challenge failures and variable page bytes; it establishes no legal conclusions.

`--previous` takes one explicitly selected retained run directory. Its completion
marker, listed artifact digests, declarations, manifest and required source bytes
are verified before comparison or retrieval. A corrupt, incomplete, cross-project
or symlinked predecessor fails with exit 2. Versioned semantic edits require an
increased revision; source retrieval timestamps alone do not change content.
The successor retains `comparison.json`, its evidence metadata and freshness
overlays, and links the parent run without changing any predecessor file.

Relevant changes make historical reviews stale and withdraw affected effective
support; original declarations remain visible. Missing evidence or failed/offline
refresh means unknown freshness. Known change takes precedence when both occur.
Matching downloaded bytes can establish only matching recorded inputs, never
current law or renewed reviewer approval. Incomplete dependency attribution
withdraws support conservatively; family screenings are renewed after any known
change because their dependency lists are incomplete.

## Next deliverables

[Specifications v2](specs_v2/README.md) record the approved three-bolt sequence:
offline declarations/reporting, official-source retrieval, then predecessor
revalidation and the portable skill/release. Bolt 001 implementation is approved;
its [Test report](memory-bank/bolts/001-legal-revalidation-cli/test-walkthrough.md)
passes all twelve offline acceptance criteria and is accepted. Bolt 001 is complete;
retrieval and plugin checks are recorded on this branch. Predecessor comparison and
[release verification](memory-bank/bolts/003-legal-revalidation-cli/test-walkthrough.md)
are implemented and recorded; Owner stage and MVP acceptance remain pending.

Scanners, Graphify, the dashboard, and authorized fix/retest automation remain later
layers. They do not require a PC vulnerability audit to begin the legal workflow.

## Project files

- `eu_compliance_guard/`: shared models, schema export, and foundation helpers.
- `tests/` and `fixtures/`: synthetic checks and examples.
- `frontend/`: generated TypeScript contract and package metadata.
- [Specifications](specs/eu-compliance-audit/requirements.md) and
  [implementation plan](specs/eu-compliance-audit/tasks.md): preserved planning snapshots.
- [Implementation status](docs/implementation-status.md): current progress and limits.
- [Implementation walkthrough](memory-bank/bolts/001-legal-revalidation-cli/implementation-walkthrough.md):
  the first offline slice and its construction checkpoint.
- [License](LICENSE) and [dependency notices](THIRD_PARTY_NOTICES.md).

The specification snapshots still refer to `agentic-setup` and the earlier
`apps/eu-compliance-audit/` placement. Application files now live at this repository's
root. Historical reviews also link to instruction-library files in the original
repository. Those references remain unchanged to preserve the reviewed documents.

Commit and push each completed development change separately as work progresses.
