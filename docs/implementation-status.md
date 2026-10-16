# Implementation status

## Standalone repository extraction

Owner direction: create a separate GitHub repository, publish existing progress, and
use one simple commit per update. Repository name: `eu-compliance-guard`.

The application was copied from `agentic-setup/apps/eu-compliance-audit/` to this
repository's root. All of `agentic-setup/specs/eu-compliance-audit/` was copied at the
same relative path. All 46 transferred files, including licenses and planning/review
snapshots, remain byte-identical to their extraction baseline. The original source
and unrelated working-tree changes are preserved. Private implementation handbacks,
probe output, session state, installed dependencies, and caches are excluded.

Original specification draft labels, pending checkboxes, repository destinations,
role assignments, and relative references are historical snapshots, not current
execution state. The user approved requirements, design, and implementation in the
prior session; this extraction does not rewrite those snapshots or claim their
acceptance criteria are complete. No original Git history or unrelated instruction
library is imported into the standalone repository.

## What exists

- Shared validated records and closed commands for scope, sources, evidence,
  findings, assessments, conversations, proposals, capabilities, and progress.
- Generated JSON Schema and frontend TypeScript definitions with drift checks.
- Synthetic contract fixtures and 61 model, legal-record, frontend-record,
  agent-admission, and fake-executor tests.
- Static native-protocol inspection and bounded reply validation.
- An offline Linux executor helper that rejects unverified cleanup. Its live
  containment/admission requirements remain unmet; fake tests are not that evidence.
- Separate Python/frontend lock files, package selection, and license notices.

## Current priority and remaining work

The next implementation is a read-only skill and scripts for requirements-to-law
revalidation using current official sources, recorded applicability, evidence, and
explicit unknowns. The earlier OS isolation investigation is not a prerequisite to
this text/evidence workflow. No OS security policy was changed and no PC vulnerability
audit was performed. Do not continue that detour as the next task.

No operational audit engine, persistence/API/CLI, reviewed legal corpus, real scanner,
browser checks, provider bridge, remediation loop, dashboard, Graphify integration,
global host installation, or completed legal audit exists yet. These obligations
remain pending. Research links are a starting register, not a current vetted corpus.

## Verification for this extraction

- `make check`: all 61 synthetic tests passed; JSON Schema and generated TypeScript
  drift checks passed; TypeScript compilation check passed.
- `uv build --offline --out-dir /tmp/eu-compliance-guard-standalone-dist`: source
  distribution and wheel built successfully. Archive inspection verified contracts,
  license notices, and absence of dependencies, caches, and private runtime state.
- SHA-256 comparison: all 46 transferred files and five pre-existing modified files
  in the original repository remained unchanged.
- Publication candidates were checked against the explicit transfer list plus the
  four new standalone metadata documents; sensitive-pattern screening found no
  matches. This screening is not a security audit of the laptop or target projects.
- Staged whitespace review: implementation and new metadata passed. The preserved
  specifications retain their original Markdown hard breaks (two trailing spaces);
  they were not reformatted to satisfy Git's generic whitespace warning.
- No real legal audit, live scanner/provider execution, dashboard/browser acceptance,
  global installation, or OS-policy change was performed for this extraction.
