# EU Compliance Guard

A Claude Code plugin and command-line tool that keeps a project's EU legal review
traceable. It maps declared project requirements to candidate EU obligations and
official sources, then keeps every unanswered question visible as a review gap. It
writes private, tamper-evident reports and revalidates them when the project or the
sources change.

It is read-only and never gives a compliance verdict. A named human reviewer makes
every legal decision, and the tool records who decided what, based on which sources
and evidence. No real compliance audit is implied by any output, test or example.

**Version 1.0.0.** This is the stable MVP of the read-only workflow: declarations,
official-source retrieval, reports, predecessor revalidation and the Claude Code
plugin. See the [changelog](CHANGELOG.md).

## Quick start (Claude Code)

```text
/plugin install eu-compliance-guard --marketplace yo1am1/eu-compliance-guard
```

On older Claude Code versions, run `/plugin marketplace add yo1am1/eu-compliance-guard`,
then `/plugin install eu-compliance-guard@eu-compliance-guard`. The plugin runs its CLI
with [uv](https://docs.astral.sh/uv/), which downloads Pydantic on first use.
Without uv it needs a `python3` (3.12 or later) that has Pydantic installed. The
session hook says so when neither is available.

In your project:

1. Run `/eucg-audit`. It creates `.eu-compliance-guard/declarations.json` with
   `init`, drafts requirements and facts from the code (marked `assumed` or `unknown`),
   and runs `check` until the file is valid. It then writes a private report and
   ranks what needs attention.
2. Answer the open questions and add reviews as the named reviewer. The agent never
   fills in a reviewer, a review time or a legal decision.
3. Run `/eucg-audit` again later. It offers the previous run as `--previous`, so
   changed dependencies make earlier reviews stale instead of silently carrying over.

| Command | What it does |
| --- | --- |
| `/eucg [lite\|full\|strict\|off]` | Mode: notices EU legal touchpoints while coding and keeps declarations and gaps explicit |
| `/eucg-review [target]` | Maps a diff to the eleven candidate legal families and the facts to declare |
| `/eucg-audit [--fetch-official] [--previous <run>]` | Prepares declarations, runs the private report and ranks what needs attention |
| `/eucg-gaps` | Ledger of open review gaps from the latest run |
| `/eucg-status` | The latest run at a glance |
| `/eucg-help` | Reference card |

**Band above the prompt.** This needs Claude Code 2.1.290 or later, in the terminal or
the desktop app. In projects with `.eu-compliance-guard/`, it shows the latest run's
state, open gaps, supported requirements, assessment-date age and source attempts. It
has **Audit**, **Review diff**, **Gaps**, **Open report** and **Help** buttons, and `–`
folds it to one line. It shows counts and fixed-format fields only, never gap text.

**Open report** writes a static HTML view of the verified run and opens it in your
browser. The page has no scripts, loads nothing and escapes every value.

**Session hook.** In projects with `.eu-compliance-guard/`, it adds the active level,
the CLI command for this machine and a summary of the latest run. Set the default
level with `EUCG_DEFAULT_MODE` or `~/.config/eu-compliance-guard/config.json`
(`{"defaultMode": "lite"}`).

Runs are stored in `${XDG_STATE_HOME:-~/.local/state}/eu-compliance-guard/<project>/`,
outside the repository. Keep them out of Git.

## Command-line tool

Install with `uv tool install <path-to-checkout>` or `pip install <path-to-checkout>`. This
provides the `eu-compliance-guard` command (also `python -m eu_compliance_guard`).

| Command | Purpose |
| --- | --- |
| `init --project-id <id> [--path <file>] [--assessment-date <date>] [--jurisdiction <j>]… [--synthetic]` | Write a valid starter declarations file; never overwrites |
| `check [--input <file>] [--previous <run dir>] [--json]` | Validate declarations: each problem with its JSON location, the observed digest of every selected file, whether each source target can be fetched, and (with `--previous`) every record that needs a higher revision |
| `revalidate --input <file> --output <new run dir> [--offline \| --fetch-official] [--previous <run dir>]` | Assemble and publish a private run |
| `view --run <run dir> [--open]` | Verify a run and write `<parent>/views/<run>.html`; optionally open it |

```sh
eu-compliance-guard init --project-id shop --jurisdiction EU --jurisdiction DE
eu-compliance-guard check
runs=$(mktemp -d)   # any existing private (0700) directory you own
eu-compliance-guard revalidate --input .eu-compliance-guard/declarations.json \
  --output "$runs/run-001" --offline
eu-compliance-guard revalidate --input .eu-compliance-guard/declarations.json \
  --previous "$runs/run-001" --output "$runs/run-002" --offline
eu-compliance-guard view --run "$runs/run-002" --open
```

Exit codes: 0 means the artifacts were published, even when the report is partial
(`check`: the declarations are valid). 2 means invalid input or an unusable path;
diagnostics are fixed codes such as `invalid-input` or `output-exists`, never input
values. 130 means the run was interrupted.

### Declarations

`.eu-compliance-guard/declarations.json` is a versioned `RevalidationInput` record.
Its schema is `$defs.RevalidationInput` in
[`eu_compliance_guard/contract.schema.json`](eu_compliance_guard/contract.schema.json).
A complete fictional example is [`fixtures/revalidation-synthetic.json`](fixtures/revalidation-synthetic.json).
It holds the scope and facts, requirements, source targets, selected sources,
candidate obligations, applicability decisions, evidence references and reviews.

File paths resolve relative to the declarations file. Only explicitly selected
regular files are read; nothing is discovered, crawled or executed. Facts keep their
basis (`declared`, `observed`, `assumed`, `unknown`). Changing a versioned record
requires a higher `revision`; `check` names the exact location of a stale pin.

### Run directories

The output parent must exist, belong to you and exclude group/other permissions, and
the run directory must be new. Runs use modes 0700/0600 and are never overwritten.
Each run holds:

- `input.json` (normalized declarations), `manifest.json`, `bundle.json` and `report.md`;
- the retained source bytes under `sources/`, and `comparison.json` when `--previous` was given;
- `complete.json`, which lists the exact digest of every artifact.

Evidence bodies are never copied or rendered. A directory without a valid completion
marker is incomplete; retry under a new path.

The report starts with what needs attention. Each reviewed deficiency or open
question sits beside its project requirement and location, declared legal
identifier and article, evidence reasoning and next review action. Missing
applicability or legal support stays a review gap, never an established violation.

### Official sources

The network is off by default. `--fetch-official` sends bounded GETs to the declared
source targets, and only to five exact hosts: `eur-lex.europa.eu`, `curia.europa.eu`,
`commission.europa.eu`, `digital-strategy.ec.europa.eu` and `www.edpb.europa.eu`.

- Requests use HTTPS on port 443 only, with no credentials and no proxy.
- DNS answers must all be public, and the connection is pinned to a validated
  address. TLS is verified.
- At most three validated redirects are followed. Limits are 8 MiB per response,
  20 s per target and 300 s per run.
- Fictional fixture targets are never contacted.

Each target gets a recorded attempt. Accepted bytes are retained as unreviewed
candidates, and login, challenge and error pages are rejected. Hosting alone
establishes neither binding status, completeness, applicability nor currency.

EUR-Lex answers scripted clients with a bot challenge, which is recorded as a safe
failure. Download the act yourself (PDF or HTML) and declare it as a selected
source; `/eucg-audit` walks through this, and `check` reports the digest to use. A PDF
stays "needs manual identity review" until a named reviewer records the source
review. Some official pages, such as EDPB's, change bytes on every request, so
exact-byte comparison reports them as changed. See the
[live smoke check](memory-bank/bolts/002-legal-revalidation-cli/live-smoke-report.md).

### Revalidation

`--previous` takes one explicitly selected run. Its completion marker, every listed
digest, declarations, manifest and required source bytes are verified first. A
corrupt, incomplete, cross-project or symlinked predecessor fails with exit 2. The
successor stores `comparison.json` and freshness overlays, and links the parent
without changing any predecessor file.

Relevant changes make historical reviews stale and withdraw affected support.
Missing evidence or an offline or failed refresh makes freshness unknown. Matching
bytes establish only matching recorded inputs, never current law or renewed
approval. Incomplete dependency attribution and any known change to family
screenings withdraw support conservatively.

## Limits

- No output is a compliance verdict, legal advice or an exhaustive search of EU
  law. The eleven candidate families are screening keys, not a corpus.
- Reviewer names are self-attested, not authenticated.
- Retrieval checks cannot prove a document's identity or currency; a reviewer must.
  National hosts and PDFs need manual review.
- Processing budgets are cooperative, not a hard CPU or filesystem deadline. The
  bounded Linux execution helper is not an enabled scanner, and its real
  containment is unverified.
- Scanners, Graphify, the dashboard, the API (optional `api` extra) and remediation
  automation are later work.

## Development

Prerequisites: Python 3.12+, uv, Node.js, npm and make.

```sh
uv sync --locked
npm --prefix frontend ci --ignore-scripts
make check           # unit tests, JSON Schema and TypeScript drift, TypeScript compile
make plugin-check    # claude plugin validate . and the band tests (needs Claude Code)
```

After intentionally changing `eu_compliance_guard/models.py`, run `make contracts`
and `make check`.

To release, raise the version in `pyproject.toml`, `eu_compliance_guard/__init__.py` and
`.claude-plugin/plugin.json` together (a test keeps them equal), add a `CHANGELOG.md`
entry and run `uv lock`. `claude plugin update` only picks up a new version, so every
fix ships under a new version number. The tests use synthetic data, fake transports and fake processes.
They do not audit the machine, contact official sources or a model provider, or
change OS policy.

## Project files

- `eu_compliance_guard/`: models, CLI, retrieval, history, reports and authoring helpers.
- `.claude-plugin/`, `skills/`, `hooks/`, `types/`: the Claude Code plugin.
- `tests/` and `fixtures/`: synthetic checks and examples.
- `frontend/`: generated TypeScript contract for the later dashboard.
- [Specifications v2](specs_v2/README.md), the [memory bank](memory-bank/) bolts and
  [implementation status](docs/implementation-status.md): decisions, plans and test reports.
- [Specifications](specs/eu-compliance-audit/requirements.md): preserved historical snapshots
  from [agentic-setup](https://github.com/yo1am1/agentic-setup). Their paths and draft labels
  describe their original home and are kept unchanged.
- [License](LICENSE) and [dependency notices](THIRD_PARTY_NOTICES.md).
