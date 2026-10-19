---
id: 001-input-and-coverage
unit: 001-legal-revalidation-cli
intent: 001-read-only-legal-revalidation
status: complete
priority: must
created: 2026-10-18T19:01:39.000Z
assigned_bolt: 001-legal-revalidation-cli
implemented: true
---

# Story: 001-input-and-coverage

## User Story

As a project owner, I want to validate declared inputs and coverage, so that my local legal review is traceable and explicit about its limits.

## Acceptance Criteria

- [ ] **AC-1**: Given versioned JSON, when validating, then stable IDs and existing scope/legal/evidence records are reused; malformed inputs, duplicate IDs and dangling/cross-project references fail with safe unsuccessful CLI diagnostics.
- [ ] **AC-2**: Given declared, assumed and unknown facts, when loading, then each remains distinct; applicability defaults unresolved unless a reasoned decision names its reviewer and pins scope, fact, obligation and source revisions.
- [ ] **AC-3**: Given empty requirements/registers or unassessed legal families, when calculating coverage, then explicit gaps, considered domains and exclusions appear without implying all EU law was searched; historical-scope legal families are screened and unsupported families/jurisdictions retain research gaps.
- [ ] **AC-4**: Given oversized inputs or collections, when loading, then documented finite bounds reject them before unbounded processing; only supplied files are read without laptop enumeration or target execution.
- [ ] **AC-5**: Given output selection and runtime inputs, when running, then output is private under the selected directory and runtime evidence stays out of Git; standard-library/existing-dependency use and public-official-source-only routine network policy hold across the unit. Story 003 supplies the transport bounds/security checks.

## Technical Notes

Primary requirement ownership: FR-1, NFR-1. See [unit traceability](../unit-brief.md) and the canonical requirements/context/design linked there. All fixtures are synthetic.

## Dependencies

### Requires
- None.

### Enables
- [002-accountable-mapping-and-report](002-accountable-mapping-and-report.md)

## Edge Cases

Failure/ambiguity cases in the criteria remain safe failures or explicit gaps.

## Out of Scope

Deferred scanners, providers, remediation, dashboard, global installation and automated compliance verdicts.
