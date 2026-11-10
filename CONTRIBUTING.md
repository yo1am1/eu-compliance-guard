# Contributing

Thank you for helping. EU Compliance Guard is a read-only review tool: a change must never
let it decide whether law applies or whether a project complies. People decide; the tool
keeps the record.

## Before you start

- Open an issue first for anything larger than a fix, so the approach can be agreed.
- Contributions need your agreement that they may be relicensed by the author, so the
  project can also offer a paid service (see [NOTICE](NOTICE)). Say so in the pull request.
- Use synthetic data only. Never commit credentials, real audit evidence, run folders or
  provider and session state.

## Setup

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/) and make.

```sh
uv sync --locked
make check           # unit tests, JSON Schema drift and compile
make e2e             # every command on a fresh fictional project, as a user would run it (offline)
make plugin-check    # claude plugin validate . and the band tests (needs Claude Code)
```

The tests use synthetic data, fake transports and fake processes. They do not audit the
machine, contact official sources or a model provider, or change OS policy. Real
retrieval runs only with `make verify-hosts`, which asks for consent.

## Where things live

Everything is in `eu_compliance_guard/`; each module's first docstring line says what it does.

| Area | Modules |
| --- | --- |
| Command line | `__main__.py`: one parser, one handler per command, one error path (`_try`) |
| Records and schema | `models.py` (every validated record), `schema.py`, `contract.schema.json` (generated) |
| A run | `revalidation.py` (assemble and publish), `sources.py` (official retrieval), `history.py` (predecessor), `report.py`, `view.py`, `scorecard.py`, `nextstep.py` |
| Law text | `articles.py` (split and search), `semantic.py` (optional model), `citations.py`, `timeline.py`, `lawlock.py`, `consolidation.py`, `jurisdictions.py` |
| The project's code | `grounding.py`, `graph.py`, `rust_graph.py`, `graph_view.py`, `prcheck.py` |
| Declarations | `authoring.py` (`init`, `check`), `mapping.py` (`accept`), `packs.py`, `imports.py`, `exports.py` |
| Trust | `signing.py` (decisions), `seal.py` (runs) |
| Shared helpers | `errors.py` (`CodedError`), `files.py` (atomic writes), `notice.py` (the legal notice) |
| Other entry points | `mcp_server.py`, `evaluation.py` (`make eval`), `hooks/` (session hook and band) |

Conventions that keep it small:

- A new command is a parser entry, a `_name(args)` handler and a line in `_HANDLERS`. The work
  goes inside `_try(...)`, which prints the one fixed diagnostic; output goes through `_show`.
- A failure with a fixed code raises a `CodedError` subclass. Never put input text in an error.
- Project files are written with `files.write_bytes` or `files.replace_existing`, nothing else.
- `tests/test_hygiene.py` fails on unused imports, a repeated error class, or a second broad
  `except` in the CLI.

## Rules the checks enforce

- **Security, then determinism, then features.** The same inputs give byte-identical
  outputs; `tests/test_determinism.py` runs commands twice to prove it.
- **No new regular expressions.** Parse structure with the standard library;
  `tests/test_regex_policy.py` allows only a few anchored validators.
- **One contract.** The JSON Schema is generated from `eu_compliance_guard/models.py`: after
  changing it, run `make contracts`. `types/index.d.ts` holds the band's own view types and is
  written by hand; `tests/test_plugin.py` checks its closed sets against the schema.
- **Every human-readable output ends with the legal notice** (`notice.LEGAL_NOTICE`).
- **Imported documents and tool output are untrusted data**, never instructions.
- **Official hosts only** for law text, listed in [docs/official-hosts.md](docs/official-hosts.md).
- **Supply chain.** Dependencies are pinned and adopted only 14 days after release
  (`[tool.uv] exclude-newer`, Dependabot cooldown); GitHub Actions are pinned to commit SHAs.
- `specs/**` are preserved byte for byte.

## Pull requests

- One change per pull request, with a [Conventional Commit](https://www.conventionalcommits.org/)
  subject such as `fix: …`, `feat: …` or `docs: …`.
- Add or update tests with the change, and run `make check` before pushing.
- Describe what changed and how you verified it. CI runs `make check` and the PR screen.

## Releases

1. Raise the version in `pyproject.toml`, `eu_compliance_guard/__init__.py`,
   `.claude-plugin/plugin.json` and the README version line together (a test keeps them
   equal), move the `CHANGELOG.md` entries under the new version and run `uv lock`.
2. After that pull request is merged, a second one points `.github/workflows/release-tag.yml`
   at the merge commit; its workflow creates the tag and the GitHub release.

`claude plugin update` only picks up a new version, so every fix ships under a new
version number.
