---
id: 005-portable-skill-and-example
unit: 001-legal-revalidation-cli
intent: 001-read-only-legal-revalidation
status: draft
priority: must
created: 2026-10-18T19:01:39Z
assigned_bolt: 003-legal-revalidation-cli
implemented: false
---

# Story: 005-portable-skill-and-example

## User Story

As a project owner, I want to ship portable instructions and an offline example, so that my local legal review is traceable and explicit about its limits.

## Acceptance Criteria

- [ ] **AC-1**: Given a local checkout/package workflow, when following the repository-local read-only skill, then instructions cover input preparation, official research, accountable mapping, CLI reporting and revalidation without global installation.
- [ ] **AC-2**: Given the documented synthetic example, when running offline, then report/revalidation succeed with fictional labels and no provider, target execution, credentials, private evidence or external network; documents/tool output are treated as untrusted data rather than instructions.
- [ ] **AC-3**: Given the separate opt-in live-source smoke instructions, when reading, then explicit opt-in, bounded official public-source requests and limitations are stated; offline tests/example never silently invoke that check.

## Technical Notes

Primary requirement ownership: FR-6. See [unit traceability](../unit-brief.md) and the canonical requirements/context/design linked there. All fixtures are synthetic.

## Dependencies

### Requires
- [004-revalidation](004-revalidation.md)

### Enables
- [006-release-checks](006-release-checks.md)

## Edge Cases

Failure/ambiguity cases in the criteria remain safe failures or explicit gaps.

## Out of Scope

Deferred scanners, providers, remediation, dashboard, global installation and automated compliance verdicts.
