---
id: 006-release-checks
unit: 001-legal-revalidation-cli
intent: 001-read-only-legal-revalidation
status: draft
priority: must
created: 2026-10-18T19:01:39Z
assigned_bolt: 003-legal-revalidation-cli
implemented: false
---

# Story: 006-release-checks

## User Story

As a project owner, I want to verify contracts and reproducible delivery, so that my local legal review is traceable and explicit about its limits.

## Acceptance Criteria

- [ ] **AC-1**: Given completed model changes, when regenerating and checking, then JSON Schema and TypeScript derive solely from models.py, existing command contracts remain compatible and make check passes.
- [ ] **AC-2**: Given synthetic regressions, when running checks, then invalid references, unsafe URLs/redirects, retrieval failures, missing reviews/evidence, changed inputs/source bytes and history preservation are exercised, including input/download/duration/collection bounds.
- [ ] **AC-3**: Given wheel/sdist and the documented offline workflow, when inspecting/executing, then needed CLI/contracts/skill/example assets are available through the documented distribution route, the offline report/revalidation example succeeds, and credentials, private evidence, caches and installed dependencies are absent from archives.
- [ ] **AC-4**: Given results, when documenting delivery, then unit/fake checks and any separately authorized live smoke results are distinguished; neither is called a real legal audit or containment proof.
- [ ] **AC-5**: Given a completed development change and current authorization, when publishing during construction, then the exact stage is reviewed, local author/committer identity verified, no co-author or agent session trailers added, and each change committed/pushed individually without rewriting published history. This planning dispatch itself performs no commit/push.

## Technical Notes

Primary requirement ownership: NFR-2. See [unit traceability](../unit-brief.md) and the canonical requirements/context/design linked there. All fixtures are synthetic.

## Dependencies

### Requires
- [005-portable-skill-and-example](005-portable-skill-and-example.md)

### Enables
- Acceptance of the CLI unit.

## Edge Cases

Failure/ambiguity cases in the criteria remain safe failures or explicit gaps.

## Out of Scope

Deferred scanners, providers, remediation, dashboard, global installation and automated compliance verdicts.
