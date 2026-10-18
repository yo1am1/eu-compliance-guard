---
id: 004-revalidation
unit: 001-legal-revalidation-cli
intent: 001-read-only-legal-revalidation
status: draft
priority: must
created: 2026-10-18T19:01:39Z
assigned_bolt: 003-legal-revalidation-cli
implemented: false
---

# Story: 004-revalidation

## User Story

As a project owner, I want to compare retained assessments and invalidate review claims, so that my local legal review is traceable and explicit about its limits.

## Acceptance Criteria

- [ ] **AC-1**: Given a retained assessment and newly validated input/source attempts, when comparing, then changed requirements, scope, obligations, evidence, review decisions and source digests are reported without rewriting historical reports/source versions.
- [ ] **AC-2**: Given relevant revision changes or a changed assessment date, when revalidating, then dependent review claims are invalidated and renewed review actions appear; unrelated historical claims are not silently rewritten.
- [ ] **AC-3**: Given failed retrieval with old bytes available, when revalidating, then current freshness is unknown; identical downloaded bytes mean only unchanged recorded content, never automatic legal currency or renewed reviewer approval.

## Technical Notes

Primary requirement ownership: FR-5. See [unit traceability](../unit-brief.md) and the canonical requirements/context/design linked there. All fixtures are synthetic.

## Dependencies

### Requires
- [003-official-source-retrieval](003-official-source-retrieval.md)

### Enables
- [005-portable-skill-and-example](005-portable-skill-and-example.md)

## Edge Cases

Failure/ambiguity cases in the criteria remain safe failures or explicit gaps.

## Out of Scope

Deferred scanners, providers, remediation, dashboard, global installation and automated compliance verdicts.
