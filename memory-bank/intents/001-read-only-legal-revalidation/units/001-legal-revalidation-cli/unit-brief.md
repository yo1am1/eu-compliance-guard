---
unit: 001-legal-revalidation-cli
unit_type: cli
default_bolt_type: simple-construction-bolt
intent: 001-read-only-legal-revalidation
phase: inception
status: draft
created: 2026-10-18T19:01:39Z
updated: 2026-10-18T19:01:39Z
---

# Unit brief: Legal revalidation CLI

## Purpose and scope

Deliver one local CLI for declared requirements, selected official sources, accountable mapping, private retained JSON/Markdown reports and revalidation. Include the portable skill and offline example. The [canonical requirements](../../../../../specs_v2/requirements.md) define scope; all six FRs and both NFRs are Must.

Scanners, Graphify, provider bridges, remediation, dashboard, API/server, scheduling, global installation and automated verdicts are deferred. No laptop audit or OS change is needed.

## Assigned requirements and primary bolt ownership

Every requirement has exactly one accountable bolt below. Supporting downstream checks do not transfer ownership. NFR-1 is a unit-wide invariant established in bolt 001, with retrieval enforcement in story 003 / bolt 002 and verification at release.

| Requirement | Observable story criteria | Primary bolt |
|---|---|---|
| FR-1 | [001](stories/001-input-and-coverage.md) AC-1–3 | 001-legal-revalidation-cli |
| FR-2 | [003](stories/003-official-source-retrieval.md) AC-1–5 | 002-legal-revalidation-cli |
| FR-3 | [002](stories/002-accountable-mapping-and-report.md) AC-1–4 | 001-legal-revalidation-cli |
| FR-4 | [002](stories/002-accountable-mapping-and-report.md) AC-5–7; 001 AC-1 invalid input | 001-legal-revalidation-cli |
| FR-5 | [004](stories/004-revalidation.md) AC-1–3 | 003-legal-revalidation-cli |
| FR-6 | [005](stories/005-portable-skill-and-example.md) AC-1–3 | 003-legal-revalidation-cli |
| NFR-1 | [001](stories/001-input-and-coverage.md) AC-4–5; 002 AC-7; supporting 003 AC-1–2 and 006 AC-2 | 001-legal-revalidation-cli |
| NFR-2 | [006](stories/006-release-checks.md) AC-1–5 | 003-legal-revalidation-cli |

## Domain concepts and operations

Reuse Scope, Fact, LegalSource, SourceAttempt, SourceReview, ProvisionRef, Obligation, Evidence and assessment/history records in models.py. Extend declared-input/mapping/report records only where needed. Validate references, retain exact source versions, render reports and compare revisions. Legal interpretation/evidence sufficiency remain accountable reviewer decisions.

## Story summary

Six Must stories; all draft, unimplemented and awaiting Owner artifacts review. [Global index](../../../../story-index.md).

1. [001 Input/coverage](stories/001-input-and-coverage.md)
2. [002 Mapping/report](stories/002-accountable-mapping-and-report.md)
3. [003 Retrieval](stories/003-official-source-retrieval.md)
4. [004 Revalidation](stories/004-revalidation.md)
5. [005 Skill/example](stories/005-portable-skill-and-example.md)
6. [006 Release checks](stories/006-release-checks.md)

## Dependencies and technical context

No other units or dependent units. Optional public official HTTPS endpoints can fail; failures become recorded gaps. Offline workflows have no service dependency. Store bounded private per-run files/source versions under the selected output directory with no overwrite.

The proposed CLI is `python -m eu_compliance_guard revalidate --input ... --output ...`, adding `--previous ...` for comparison. Network is disabled by default; `--offline` makes that explicit and conflicts with the opt-in `--fetch-official`. `--output` names a new run directory. Follow the canonical design for exact commands and exit semantics.

Use the [tech stack](../../../../standards/tech-stack.md) and [coding standards](../../../../standards/coding-standards.md). Canonical [context](../../../../../specs_v2/system-context.md) and [design](../../../../../specs_v2/design.md) await Owner review. Read callers/tests before editing.

## Bolts and success criteria

[001](../../../../bolts/001-legal-revalidation-cli/bolt.md) → [002](../../../../bolts/002-legal-revalidation-cli/bolt.md) → [003](../../../../bolts/003-legal-revalidation-cli/bolt.md), all simple-construction-bolt; no cycles.

- [ ] Every linked story criterion is verified with synthetic checks/offline example.
- [ ] make check and package inspection pass; runtime artifacts stay private/out of Git.
- [ ] Owner approves artifacts/readiness before construction; every construction stage receives human validation.

Exact bounds and file/API changes are resolved in design and the first approved Plan stage. This draft does not claim implementation or an operational legal assessment.
