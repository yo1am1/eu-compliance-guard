---
id: 002-accountable-mapping-and-report
unit: 001-legal-revalidation-cli
intent: 001-read-only-legal-revalidation
status: complete
priority: must
created: 2026-10-18T19:01:39.000Z
assigned_bolt: 001-legal-revalidation-cli
implemented: true
---

# Story: 002-accountable-mapping-and-report

## User Story

As a project owner, I want to produce an accountable offline report, so that my local legal review is traceable and explicit about its limits.

## Acceptance Criteria

- [ ] **AC-1**: Given requirements and candidate obligations, when reporting, then every requirement has pinned provisions, applicability rationale, supporting evidence and unresolved questions or an explicit unmapped gap; obligations with no mapping or technical finding are included.
- [ ] **AC-2**: Given unresolved applicability, missing/unavailable evidence, unchecked amendments/case law/national overlays, unverified translations or unreviewed application/transition dates, when reporting, then each remains a visible review gap with next actions.
- [ ] **AC-3**: Given evidence declarations and reviewer attestations, when reporting, then labels stay distinct; presence of files/citations cannot establish sufficiency, recommendations/proposals cannot establish binding duties, and inconsistent/unresolved source classifications cannot establish real duties.
- [ ] **AC-4**: Given imported login, challenge or error content, when accepting legal text, then it is rejected; uncertain text requires review and no empty run or technical test produces a compliance verdict.
- [ ] **AC-5**: Given valid synthetic input, when invoking the runnable CLI offline, then validated JSON and readable Markdown show scope/date, coverage/exclusions, mappings, provenance, evidence references, accountable decisions, gaps and next actions with prominent fictional labels; retrieval/review gaps yield an explicitly partial report.
- [ ] **AC-6**: Given prior outputs/source versions, when selecting a run directory, then a new directory is required and overwrites are refused; history remains byte-identical, including after failure.
- [ ] **AC-7**: Given private evidence and hostile imported text, when rendering, then evidence contents are omitted by default and safe diagnostics/Markdown expose no secrets or active imported HTML.

## Technical Notes

Primary requirement ownership: FR-3, FR-4. See [unit traceability](../unit-brief.md) and the canonical requirements/context/design linked there. All fixtures are synthetic. Invoke `python -m eu_compliance_guard revalidate --input ... --output ...`; network is disabled by default, with explicit `--offline` supported. Follow design exit semantics: report publication exits 0 even when partial; invalid input/output exits 2 and interruption exits 130 without a finalized report.

## Dependencies

### Requires
- [001-input-and-coverage](001-input-and-coverage.md)

### Enables
- [003-official-source-retrieval](003-official-source-retrieval.md)

## Edge Cases

Failure/ambiguity cases in the criteria remain safe failures or explicit gaps.

## Out of Scope

Deferred scanners, providers, remediation, dashboard, global installation and automated compliance verdicts.
