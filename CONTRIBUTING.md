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
make plugin-check    # claude plugin validate . and the band tests (needs Claude Code)
```

The tests use synthetic data, fake transports and fake processes. They do not audit the
machine, contact official sources or a model provider, or change OS policy. Real
retrieval runs only with `make verify-hosts`, which asks for consent.

## Rules the checks enforce

- **Security, then determinism, then features.** The same inputs give byte-identical
  outputs; `tests/test_determinism.py` runs commands twice to prove it.
- **No new regular expressions.** Parse structure with the standard library;
  `tests/test_regex_policy.py` allows only a few anchored validators.
- **One contract.** JSON Schema and TypeScript types are generated from
  `eu_compliance_guard/models.py`: after changing it, run `make contracts`.
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
