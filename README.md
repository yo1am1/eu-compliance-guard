# EU Compliance Guard

Tools and portable agent instructions for revalidating project requirements against
applicable EU law, using current official sources and traceable evidence.

**Status: the first offline reporting slice is implemented; the broader MVP is pending.**
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

Official-source fetching, predecessor comparison, the portable skill, a reviewed
legal registry, API, scanner integration and dashboard remain pending. `frontend/`
currently contains the generated contract and build metadata; `npm run build` is
not an implemented UI milestone.

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

Exit 0 means artifacts were published, including an explicitly partial report.
Exit 2 means invalid input, capacity or file/output failure; interruption exits 130.
The example contains one supported fictional mapping and unresolved coverage,
facts and unmapped records. Neither its result nor a passing test establishes
legal compliance. Reviewer names are local attestations, not authenticated approval.
Offline real-source freshness remains unverified; PDF bytes require manual review.
Processing budgets are cooperative, without a hard CPU/filesystem deadline or
containment guarantee.

Network is disabled by default; `--offline` is explicit. `--fetch-official` and
`--previous` currently fail with exit 2 before input reads or output creation.

## Next deliverables

[Specifications v2](specs_v2/README.md) record the approved three-bolt sequence:
offline declarations/reporting, official-source retrieval, then predecessor
revalidation and the portable skill/release. Bolt 001 implementation is awaiting
its human checkpoint before the separate Test stage.

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
