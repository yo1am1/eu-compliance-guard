---
stage: implement
bolt: 001-legal-revalidation-cli
created: 2026-10-19T08:05:24Z
status: approved
---

## Implementation Walkthrough: offline legal revalidation CLI

### Summary

The first offline slice accepts declared requirements and selected files, retains
accountable mappings and explicit gaps, and publishes private JSON and escaped
Markdown reports. Original claims remain visible alongside conservative effective
results. The Owner approved Stage 2 and starting Test on 2026-10-19T08:34:22Z;
the Test checkpoint, stories and bolt completion remain pending.

### Structure Overview

Python models remain the only public contract source. A separate validated output
envelope records effective review results without replacing the original supplied
claims. The schema and frontend types are generated from those models. One offline
workflow owns selected-file processing, assembly and publication; the CLI delegates
to it and a pure renderer presents metadata without reading evidence bodies.

### Completed Work

- [x] `eu_compliance_guard/models.py` — versioned declarations, review and report
  records, bounded reference joins and conservative output validation.
- [x] `eu_compliance_guard/contract.schema.json` — generated shared JSON definitions
  with the original sixteen-operation Command root.
- [x] `frontend/scripts/contract.mjs` — generation and export-completeness checks
  for every public schema definition.
- [x] `frontend/src/lib/contract.ts` — generated shared TypeScript definitions.
- [x] `fixtures/revalidation-synthetic.json` — fictional mapped and unmapped
  requirements and obligations, accountable attestations and fact bases.
- [x] `fixtures/revalidation-synthetic/source.txt` — explicitly fictional source.
- [x] `fixtures/revalidation-synthetic/evidence.txt` — selected fictional evidence.
- [x] `tests/test_revalidation_models.py` — compatibility, reference, provenance,
  bounds and unsupported-output regressions.
- [x] `eu_compliance_guard/revalidation.py` — bounded explicit file processing,
  conservative review assembly and private exclusive artifact publication.
- [x] `eu_compliance_guard/__main__.py` — offline CLI, safe diagnostics and explicit
  processing-state output; unavailable future arguments fail before reads.
- [x] `eu_compliance_guard/report.py` — bounded metadata-only Markdown with inert
  imported text, mapping chains and prominent fictional labels.
- [x] `tests/test_revalidation.py` — source/evidence admission, dependencies,
  bounded reads, private modes, failure markers and immutable output history.
- [x] `tests/test_revalidation_cli.py` — CLI routing, safe errors, future argument
  rejection and real package-only subprocess examples.
- [x] `tests/test_revalidation_report.py` — metadata coverage, escaping, mixed
  fictional labels, evidence-body exclusion and report bounds.
- [x] `README.md` — runnable offline example, prerequisites, exit semantics,
  privacy and current delivery limits.
- [x] `docs/implementation-status.md` — verified development progress and pending
  construction checkpoints.
- [x] `specs_v2/` — current first-slice availability alongside the remaining MVP.

### Key Decisions

- **Preserve claims and constrain conclusions**: incomplete input remains
  representable; resolved output needs the supplied accountable attestation and
  admitted source/evidence dependencies, including evidence cited by facts.
- **Keep review dimensions separate**: one documentary method can pass while a
  different method remains pending; manual status does not overwrite those results.
- **Retain only explicit files**: descriptor-relative regular-file reads reject
  symlink/FIFO/device access; source bytes may be retained, evidence bodies stay out
  of the report and artifact copies.
- **Publish a marker last**: exclusive private outputs are prevalidated, flushed
  and finalized only after their artifact digests are retained. Failure preserves
  an incomplete directory for inspection and requires a new retry path.
- **Keep dependencies accountable**: unavailable requirement facts/evidence/origins
  and explicit source amendment/case-law/national dependencies invalidate support,
  even when a narrower mapped review would otherwise pass.
- **Use visible teammates in one tab**: the Owner requested split panes on
  2026-10-19. Contract writing and independent review used two panes in the
  coordinator tab, then those panes were reused for workflow and CLI/report work.
  Conversations remain in Orca; one writer owns each file.

### Deviations from Plan

The installed TypeScript compiler ignored unreachable definitions under the union
root, despite its enabled option. The generator now uses an object wrapper only
while generating types and verifies every definition is exported. The public JSON
schema retains its original Command root; no competing contracts were introduced.

### Dependencies Added

None.

### Developer Notes

Mandatory development checks pass all 121 tests covering the foundation and new
synthetic model, workflow, CLI and report behavior, generated schema/type drift and
TypeScript compilation. Independent CLI checks verify mapping/coverage, marker digests,
private modes, collisions/history, safe failures and symlink refusal. Offline wheel
and sdist inspection excludes private runtime state, and the built wheel runs the
synthetic example outside the checkout.

Source identity and evidence sufficiency remain supplied reviewer attestations;
offline real-law freshness is unverified. Format/page detection is conservative,
PDF identity needs manual review, and processing budgets are cooperative. No live
law, scanner/provider execution, OS-policy change or containment proof is claimed.
The separate [Test walkthrough](test-walkthrough.md) records subsequent verification;
final test/bolt acceptance remains pending.
