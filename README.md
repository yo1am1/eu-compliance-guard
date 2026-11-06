# EU Compliance Guard

A Claude Code plugin and command-line tool that keeps a project's EU legal review
traceable. It maps declared project requirements to candidate EU obligations and
official sources, then keeps every unanswered question visible as a review gap. It
writes private, tamper-evident reports and revalidates them when the project or the
sources change.

It is read-only and never gives a compliance verdict. A named human reviewer makes
every legal decision, and the tool records who decided what, based on which sources
and evidence. No real compliance audit is implied by any output, test or example.

**Version 1.5.0.** The read-only workflow (declarations, official-source retrieval,
reports, predecessor revalidation and the Claude Code plugin), plus code-grounded
facts, article text beside each reference, the next best step, a pull-request check,
a side panel, a review-progress dashboard and a project graph that follows data through
the code. See the [changelog](CHANGELOG.md).

![Walkthrough: the band and side panel in Claude Code, then article text and articles to read in the report](docs/images/walkthrough.gif)

<details>
<summary>Screenshots</summary>

**In Claude Code:** the band above the prompt names the next step and shows progress;
the side panel lists the top steps, the questions for the owner and open items by area.

![The band and the side panel in Claude Code](docs/images/plugin-band-panel.png)

**In the report:** each declared article opens to its text, retrieved from the
Publications Office and labelled as an unreviewed candidate.

![Article text beside each declared legal reference](docs/images/report-article-text.png)

**Articles to read:** each requirement lists the articles a local text search ranks
highest. A suggestion, not a mapping.

![Articles to read under each requirement](docs/images/report-articles-to-read.png)

All screenshots show the fictional FitBox example project.

</details>

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
| `/eucg-next` | Walks through the step that unblocks the most open requirements |
| `/eucg-pr [target]` | Screens a branch or PR diff for legal touchpoints; can set up the GitHub Action |
| `/eucg-gaps` | Ledger of open review gaps from the latest run |
| `/eucg-status` | The latest run at a glance |
| `/eucg-panel` | Opens the side panel with the latest run's next steps, owner questions and gaps by area |
| `/eucg-help` | Reference card |

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
steps and the owner's open questions, with a link to the full report. Like Ponytail's
board, it is a single self-contained HTML file written beside the report, with no
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

### Fewer permission prompts

Each CLI step asks for permission by default. To allow the plugin's own read-only CLI
in a project, add this to `.claude/settings.json` (or run `/permissions` and add it):

```json
{
  "permissions": {
    "allow": ["Bash(uv run --project * --locked --no-dev python -P -m eu_compliance_guard *)"]
  }
}
```

`revalidate --fetch-official` still asks for your consent in the conversation before
any network use.

## Command-line tool

Install with `uv tool install <path-to-checkout>` or `pip install <path-to-checkout>`. This
provides the `eu-compliance-guard` command (also `python -m eu_compliance_guard`).

| Command | Purpose |
| --- | --- |
| `init --project-id <id> [--path <file>] [--assessment-date <date>] [--jurisdiction <j>]… [--synthetic]` | Write a valid starter declarations file; never overwrites |
| `check [--input <file>] [--previous <run dir>] [--json]` | Validate declarations: each problem with its JSON location, the observed digest of every selected file, whether each source target can be fetched, whether an offline run fits the output limits, and (with `--previous`) every record that needs a higher revision |
| `revalidate --input <file> --output <new run dir> [--offline \| --fetch-official] [--previous <run dir>]` | Assemble and publish a private run |
| `ground [--input <file>] [--top N] [--json] [--apply <fact>=<path>:<line>]…` | Rank code evidence for each assumed or unknown fact, and each fact whose pinned evidence changed, with a local index. `--apply` marks a confirmed technical fact `observed`, pinned to that file's digest |
| `state-dir [--input <file>]` | Print and create (0700) the private run storage for the declared `project_id` |
| `next [--run <run dir>] [--top N] [--json]` | Rank the open steps of the newest (or given) run by how many open requirements each unblocks |
| `score [--run <run dir>] [--against <run dir>] [--top N] [--json]` | Show the review progress of the newest (or given) run: separate meters, points out of 10, never a compliance score. Exit 0 whatever the points |
| `pr-check [--diff <file>\|-] [--input <file>] [--markdown\|--json] [--strict]` | Screen a diff's added lines for legal touchpoints, undeclared concepts and pinned evidence in changed files; `--strict` exits 1 when something needs attention |
| `view --run <run dir> [--dashboard] [--open]` | Verify a run and write `<parent>/views/<run>.html`, `<run>.dashboard.html` and `<run>.scorecard.json` (all 0600); print and optionally open the report, or with `--dashboard` the dashboard |

```sh
eu-compliance-guard init --project-id shop --jurisdiction EU --jurisdiction DE
eu-compliance-guard check
runs=$(eu-compliance-guard state-dir)   # private, symlink-free run storage
eu-compliance-guard revalidate --input .eu-compliance-guard/declarations.json \
  --output "$runs/run-001" --offline
eu-compliance-guard revalidate --input .eu-compliance-guard/declarations.json \
  --previous "$runs/run-001" --output "$runs/run-002" --offline
eu-compliance-guard view --run "$runs/run-002" --open
```

Exit codes: 0 means the artifacts were published, even when the report is partial
(`check`: the declarations are valid). 2 means invalid input or an unusable path;
diagnostics are fixed codes such as `invalid-input` or `output-exists`, never input
values. Output that cannot be written (a closed pipe or a full disk) is
`io-failed: output failed` with exit 2, even when the command's work, such as a published
run or rewritten declarations, is already done. Characters the console cannot encode are
printed as backslash escapes. 130 means the run was interrupted.

### Declarations

`.eu-compliance-guard/declarations.json` is a versioned `RevalidationInput` record.
Its schema is `$defs.RevalidationInput` in
[`eu_compliance_guard/contract.schema.json`](eu_compliance_guard/contract.schema.json).
A complete fictional example is [`fixtures/revalidation-synthetic.json`](fixtures/revalidation-synthetic.json).
It holds the scope and facts, requirements, source targets, selected sources,
candidate obligations, applicability decisions, evidence references and reviews.

File paths resolve relative to the declarations file, or to the project folder (its
parent) when `"files_root": "project"`, which `init` sets for the default `.eu-compliance-guard/` folder (elsewhere it sets `"declarations_dir"`). Only explicitly selected
regular files are read; nothing is discovered, crawled or executed. Facts keep their
basis (`declared`, `observed`, `assumed`, `unknown`). Changing a versioned record
requires a higher `revision`; `check` names the exact location of every stale pin, and
with `--previous` every record that needs a higher revision, including those whose pins
must follow a raised revision.

### Run directories

The output parent must exist, belong to you and exclude group/other permissions, and
the run directory must be new. No component of an input, output or predecessor path may
be a symbolic link (`unsafe-path`, as for a missing output parent or an overlong name;
missing declarations, file or folder, are `io-failed` in every command); `state-dir` prints a resolved path, and on macOS
`$TMPDIR` lives under the `/var` symlink, so use `state-dir` or `pwd -P` paths. Runs use modes 0700/0600 and are never overwritten.
Each run holds:

- `input.json` (normalized declarations), `manifest.json`, `bundle.json` and `report.md`;
- the retained source bytes under `sources/`, and `comparison.json` when `--previous` was given;
- `complete.json`, which lists the exact digest of every artifact.

Evidence bodies are never copied or rendered. A directory without a valid completion
marker is incomplete; retry under a new path. A run path that names no directory, or a
run file that cannot be opened safely (permissions, a symbolic link), is `unsafe-path`
instead: correct the path or the permissions, because the run itself may be intact.

The report starts with what needs attention. Each reviewed deficiency or open
question sits beside its project requirement and location, declared legal
identifier and article, evidence reasoning and next review action. Missing
applicability or legal support stays a review gap, never an established violation.
An obligation reviewed as not applicable is not a violation either: its methods are
recorded as not assessed, which keeps the run partial, and a requirement mapped to it
stays unresolved.

### Official sources

The network is off by default. `--fetch-official` sends bounded GETs to the declared
source targets, and only to six exact hosts: `eur-lex.europa.eu`, `curia.europa.eu`,
`commission.europa.eu`, `digital-strategy.ec.europa.eu`, `www.edpb.europa.eu` and
`publications.europa.eu` (the Publications Office's machine endpoint, Cellar). For
Cellar alone, its own same-host `http://` redirect is upgraded to https; every other
downgrade is refused. Requests carry the target's language as `Accept-Language`.
[docs/official-hosts.md](docs/official-hosts.md) names each host's operator and purpose
and the last reachability check; `make verify-hosts` repeats that check with consent.
A base CELEX (`resource/celex/32002L0058`) returns the act as first published; for the
law in force use a consolidated CELEX such as `02002L0058-20091219`, and have a reviewer
confirm that it is the latest consolidation. `check` warns when an `eu_act` target uses a
base CELEX and lists each target's version ("consolidated 2009-12-19" or "as first
published"). Each article excerpt in the report names the version it comes from. With
`--fetch-official`, the same consent also asks the Publications Office's official SPARQL
endpoint, once per act target with a CELEX number, whether a newer consolidation exists.
The query is built only from the CELEX number. A newer version, or an answer that could
not be read, becomes a review gap on the run; the declarations are never changed.

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
source; `/eucg-audit` walks through this, and `check` reports the digest to use. In
1.0, only text and HTML sources can support a mapping. A PDF can be declared and
reviewed, but it always remains a "needs manual identity review" gap, so also save
the HTML version of an act you want to rely on. Some official pages, such as EDPB's, change bytes on every request, so
exact-byte comparison reports them as changed. See the
[live smoke check](memory-bank/bolts/002-legal-revalidation-cli/live-smoke-report.md).

### Revalidation

`--previous` takes one explicitly selected run. Its completion marker, every listed
digest, declarations, manifest and required source bytes are verified first. A
corrupt, incomplete, cross-project or symlinked predecessor fails with exit 2. The
successor stores `comparison.json` and freshness overlays, and links the parent
without changing any predecessor file.

Relevant changes make historical reviews stale and withdraw affected support.
Withdrawn support stays withdrawn in later runs. It is restored only when the
obligation's applicability decision and every evidence review for it are new
revisions with a `reviewed_at` after the predecessor run and no later than the
current run. Withdrawn family screenings follow the same rule. Renewals are not counted
as new changes. A renewal recorded in the same run as another relevant change does not
count, because the review cannot be shown to follow that change: the run withdraws
support and says so, and the reviews must be renewed again after that run.
`check --previous` warns about withdrawn obligations and family screenings that the
declarations do not renew yet. A family screening that the declarations set back to
`unresolved` claims no support, so nothing is withdrawn from it; declaring an
applicability again is a changed record that needs a fresh `reviewed_at`. Any other new or changed review record, including one moved to a
renamed or re-added obligation, cannot carry support. An attestation dated after the
run that reads it is always a review gap.

Each run compares against the one predecessor you name. Naming an older run, or none,
compares against that state, so always use the newest completed run (`/eucg-audit`
offers it) unless you deliberately want another baseline. Offline and `--fetch-official` runs of the same tool version count as
the same configuration.
Missing evidence or an offline or failed refresh makes freshness unknown. Withdrawal
follows the reviews the predecessor declared, so a file it could not read does not
shield them from a later change; reading exactly the declared bytes again is no change. Matching
bytes establish only matching recorded inputs, never current law or renewed
approval. Incomplete dependency attribution and any known change to family
screenings withdraw support conservatively.

### Review progress

`score` (and the top of the HTML view, the band and the panel) shows how far the
recorded review of one run has come. Each meter gives points out of 10 for one stage
of the review chain. There is no total, sum or average, and no meter is a compliance
score or verdict: they count recorded review steps of that run only. The decision is
recorded in [`docs/decisions/dashboard-review-progress.md`](docs/decisions/dashboard-review-progress.md).

Points for `done` of `total` items: "not scored" when nothing is declared, 0 only when
none are closed, 10 only when all are, otherwise `10 × done ÷ total` rounded down and
kept between 1 and 9. Each meter names how many more items raise it.

| Meter | Counts | Raise it by |
| --- | --- | --- |
| Alignment | requirements the run records as supported | closing each requirement's named blockers (mapping, facts, evidence, origin, decisions, reviews) |
| Law text | obligations whose every pin points at a listed locator of a selected source with no open source gap (duties need a binding source) | retrieving or downloading the official text, reviewing it as a source and pinning listed locators |
| Facts | distinct declared facts that are declared or observed, without conflicts or changed evidence | `ground`, `ground --apply`, or the owner confirming organisational facts |
| Decisions | obligations with an accepted `applicable` or `not_applicable` decision | recording accountable applicability decisions |
| Mapping | requirements with at least one `obligation_refs` entry | mapping each requirement to a candidate obligation |
| Reviews | non-technical review methods of obligations that may apply, recorded as complete | recording accountable evidence reviews |

Alignment also shows a ceiling when this run cannot reach 10 for a structural
reason: technical methods (this workflow never runs them) or real sources an offline
run cannot confirm (`revalidate --fetch-official`). Unmapped or methodless
requirements are blockers, not ceilings. The eleven legal families appear as a
coverage line ("k of 11 families screened"), and record hygiene (requirements located
in project files, requirements with evidence referenced, origins unchanged) as
unscored counts. The status is one of `declarations incomplete`, `needs attention`
(a reviewer recorded insufficient evidence, a change needs re-review, declared
evidence or a requirement origin changed), `in review` or `recorded steps closed`;
none of them is a verdict. `--against` adds point changes only when that run is the
recorded parent and used the same tool version; the trend never changes the status.

![Review progress at the top of the HTML view of the synthetic fixture run](docs/images/review-progress-view.png)

`view` also writes `<parent>/views/<run>.scorecard.json` (0600) as data for other
tools. The plugin never needs it: its **Dashboard** button opens the static page above.
For a future hosted service, `frontend/` holds a React page that renders such a file
(`npm --prefix frontend run build`, then `npm --prefix frontend run preview`; choose
or drop the file). It is read in the browser only; the page's Content Security Policy blocks every
connection, and its types are generated from `eu_compliance_guard/models.py`.

### Law lockfile and change impact

`lock` records the law a run's reviews read. For each act whose text the run retained, it
stores the version (CELEX), the source digest and a digest per article, in
`.eu-compliance-guard/eu-law.lock`. The lockfile is deterministic and meant to be
committed with the declarations. After a newer run, for example one with
`--fetch-official` once the consolidated text has moved, `impact` compares that run with
the lock. It lists the changed, added and removed articles, then the obligations citing
them and their applicability decisions and mapped requirements: exactly those need
review again. Nothing is reopened or decided automatically. `--strict` exits 1 when a
declared obligation cites a changed article, so CI can flag it.

### Accepting a suggestion

`accept REQ=TARGET:ARTICLE` (for example `accept req-delete=target-gdpr:Article 17`)
turns an article suggestion into a mapping in one step. The requirement gains a
candidate obligation that pins the article. An obligation that already pins the same
target and article is reused; otherwise one is created, as a duty when the target is
binding law and a recommendation otherwise, with no invented review methods. Revisions
rise and every pin follows. The file is validated and written atomically, never
through a link, and running it again changes nothing. No applicability decision is
recorded: the obligation stays unresolved until a named reviewer decides.
`/eucg-next` offers this for mapping steps.

### Project graph

`graph` maps the Python files under the files root: files, classes and functions, the
imports between files, and the calls between functions. It also lists the concepts
each function touches (personal data, tracking, AI and others), using the same rule as
the pull-request check. It only parses code (`ast`). Nothing is imported or run, links
and dependency folders are skipped, and a file that does not parse is counted as
skipped.

Calls resolve the way Python looks names up: the same file first, then imported names
and modules. A name that only matches several definitions elsewhere is labelled
`ambiguous`, never guessed. The same files always give a byte-identical graph
(`--json`) with one digest. Static parsing misses dynamic calls, so paths through the
graph are possible paths, and an empty graph never shows compliance.

`ground` uses the graph to follow data. A flow is the shortest call path from a
function that handles personal, health or children's data to the first function that
reaches an AI model, tracking, a third party or marketing. Each hop carries its
`file:line`, and a flow through an ambiguous call is labelled `ambiguous`. A candidate
inside a flow shows that path. A flow with no pinned evidence on any of its functions
is listed under "data flows no fact covers", and pinning a line on it with `--apply`
accounts for it.

`graph --view [--open]` writes `<state-dir>/views/graph.html`, and the panel's **Graph**
button opens it. Like the dashboard, it is one static file with no script and no
request, kept private (0600). It draws the functions on data flows or touching a concept,
and their neighbours, in a fixed layout: one column per file. Flows are highlighted and
ambiguous calls are dashed, and each box links to its details. Tables list each flow
with the facts pinned on it, and each fact with the requirements and obligations
(and their articles) that rely on it. How many functions were left out is always stated.

![Graph view of a fictional project](docs/images/graph-view.png)

### Search evaluation

`make eval` scores article search and code grounding on a fixed synthetic set in
`fixtures/eval/`. The set is a fictional 28-article act written for this purpose (not
law), 40 developer-style requirements split into a tuning half and a held-out half, and
a small fictional code project with 10 facts. It reports top-1 and top-3 hits. A test
keeps the scores at or above `fixtures/eval/baseline.json`, and a search change ships
with its before/after numbers. The numbers measure ranking, not legal correctness.

### Grounding assumptions in the code

`ground` builds a local index of the project's text files: no network, model or
embeddings, a bounded number of files, and no symlinks or dependency folders. It uses
Okapi BM25 over identifier-split tokens, and a lexicon of legal concepts expands each
query (tracking, special-category data, children, AI, subscriptions, retention and
more). For every assumed or unknown fact, and every fact whose pinned evidence changed
or is missing, it lists ranked `file:line` candidates, and it also lists touchpoints
that no fact covers. Organisational facts are flagged, because code can never show
them. `--apply` accepts a line only if it shares terms with the fact. It then records
the fact as `observed` with the file as evidence, which closes that fact's gap until
the file changes; `ground` then lists it again to be pinned anew. Pinning it anew, in
the same or another file, drops its code evidence for a changed or deleted file.
Repeated `--apply` values are all checked first: if one is refused, none is written.

### Pull-request check

`pr-check` reads a unified diff (a file or standard input) and the declarations: the
`--input` file, which must then exist (`io-failed` if it does not), or `.eu-compliance-guard/declarations.json` if
present. A declarations folder it cannot read is an `unsafe-path` error, never an
absent file. It lists the legal concepts in added lines with their candidate families, says
whether the declarations already mention each concept, and flags code evidence or
requirements that live in a changed file. It is deterministic and offline. Colour codes
from `git diff --color` are ignored; input that names no changed file (prose or a
`--stat` summary) or holds hunk lines a unified diff cannot (such as `--word-diff`
output) exits 2 with `invalid-input` instead of passing unread. A merge's combined diff
(`git show <merge>`) is screened too: a line added against any parent counts. With
declarations, it also maps the checked-out Python code (as `graph` does) and lists each
data flow whose functions gained an added line, with the facts pinned on that flow, or
says that no fact covers it. Each counts as an item needing attention. In a monorepo,
run it from the repository top with `--input <project>/.eu-compliance-guard/declarations.json`;
diff paths are matched below that project's folder. To run it on
every pull request, copy [`examples/github/eu-compliance-guard-pr.yml`](examples/github/eu-compliance-guard-pr.yml)
into `.github/workflows/`; it keeps one comment updated, and `--strict` can fail the
check. It is keyword screening: a diff with no touchpoints is not a clean bill.

```bash
git diff origin/main...HEAD | eu-compliance-guard pr-check --markdown
```

## Limits

- No output is a compliance verdict, legal advice or an exhaustive search of EU
  law. The eleven candidate families are screening keys, not a corpus. Every text,
  markdown and HTML output ends with the same notice: the named reviewer decides and
  is responsible, and the tool comes without warranty (see `LICENSE` and `NOTICE`).
- Reviewer names are self-attested, not authenticated.
- Retrieval checks cannot prove a document's identity or currency; a reviewer must.
  National hosts and PDFs need manual review.
- Processing budgets are cooperative, not a hard CPU or filesystem deadline. The
  bounded Linux execution helper is not an enabled scanner, and its real
  containment is unverified.
- Scanners, Graphify, the API (optional `api` extra) and remediation automation are
  later work. The dashboard shows one run's review progress from a local file; it
  manages nothing.

## Development

Prerequisites: Python 3.12+, uv, Node.js, npm and make.

```sh
uv sync --locked
npm --prefix frontend ci --ignore-scripts
make check           # unit tests, JSON Schema and TypeScript drift, TypeScript compile, dashboard tests and build
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
- [License](LICENSE): GNU AGPL-3.0-only from 1.2.0 (1.0.0 and 1.1.0 stay MIT). If you
  modify it or run it as a service, publish your source under the AGPL and credit
  EU Compliance Guard as [NOTICE](NOTICE) requires. Contributions need the author's
  agreement to relicense, so the project can also offer a paid service.
- [Dependency notices](THIRD_PARTY_NOTICES.md).
