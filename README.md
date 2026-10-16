# EU Compliance Guard

Tools and portable agent instructions for revalidating project requirements against
applicable EU law, using current official sources and traceable evidence.

**Status: foundation implemented; the legal revalidation workflow is not yet usable.**
No real compliance audit has run. This repository preserves the work originally
started in [agentic-setup](https://github.com/yo1am1/agentic-setup).

## Current implementation

- Validated records for project scope, legal sources and source failures,
  obligations, evidence, findings, review gaps, and historical/current assessments.
- A generated JSON Schema and TypeScript contract from the Python models.
- Native-agent protocol inspection and reply/admission validation, without a live
  provider bridge.
- A bounded Linux execution helper with fake-process tests. Real containment remains
  unverified; this is not an enabled repository scanner.
- Synthetic fixtures and 61 foundation tests, plus schema/type drift checks.
- Preserved requirements, design, research, implementation plan, and team reviews.

There is no runnable audit CLI/API, reviewed legal registry, globally installed skill,
scanner integration, or dashboard yet. `frontend/` currently contains the generated
contract and build metadata; `npm run build` is not an implemented UI milestone.

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

## Next deliverable

Build the read-only legal revalidation skill and scripts first:

1. Accept declared project requirements, activities, jurisdictions, dates, and selected
   evidence.
2. Retrieve and record current official sources, distinguishing binding law from
   guidance, drafts, and engineering practice.
3. Map applicable obligations to requirements and evidence, retaining unresolved
   applicability and manual review gaps.
4. Produce a traceable report and revalidate changes in requirements or legal sources.

Scanners, Graphify, the dashboard, and authorized fix/retest automation remain later
layers. They do not require a PC vulnerability audit to begin the legal workflow.

## Project files

- `eu_compliance_guard/`: shared models, schema export, and foundation helpers.
- `tests/` and `fixtures/`: synthetic checks and examples.
- `frontend/`: generated TypeScript contract and package metadata.
- [Specifications](specs/eu-compliance-audit/requirements.md) and
  [implementation plan](specs/eu-compliance-audit/tasks.md): preserved planning snapshots.
- [Implementation status](docs/implementation-status.md): current progress and limits.
- [License](LICENSE) and [dependency notices](THIRD_PARTY_NOTICES.md).

The specification snapshots still refer to `agentic-setup` and the earlier
`apps/eu-compliance-audit/` placement. Application files now live at this repository's
root. Historical reviews also link to instruction-library files in the original
repository. Those references remain unchanged to preserve the reviewed documents.

Commit and push each completed development change separately as work progresses.
