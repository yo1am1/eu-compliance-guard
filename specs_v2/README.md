# Specifications v2

This directory records the new read-only legal revalidation MVP selected by the
Owner on 2026-10-18. It does not replace or modify the historical `specs/**` files.

[Requirements](requirements.md) are drafted for Owner review. Design, construction
units, stories and bolts are pending that review under the invoked specsmd flow.
No implementation or MVP acceptance is claimed at this checkpoint.

## Recovered baseline

The standalone repository starts at `5951623`, following the foundation extraction
at `e171036`. README and implementation status describe 61 synthetic tests, generated
contracts, agent admission predicates and a fake-tested execution helper. Baseline
`make check` passed on 2026-10-18: 61 tests, JSON Schema/TypeScript drift checks and
TypeScript compilation. This establishes the development baseline only.

Local session search recovered the original `agentic-setup` design/task reviews
and foundation sessions from October 2026. Their decisions remain historical;
the standalone repository and its preserved documents are the implementation
baseline. Raw conversations and private handbacks are excluded from Git.

## Team review outcomes

Two visible Codex workers ran through Orca orchestration, as explicitly requested
for this session. This superseded the earlier Herdr-specific placement instruction
for this run; no hidden internal agents were used. Conversations stay in Orca,
not in the public repository.

- Architecture review: complete. Reuse existing scope, legal source/attempt/review,
  obligation, evidence, disposition and freshness records. Missing workflow pieces
  are declared requirements, retained accountable review decisions, validated joins,
  official retrieval, report generation and dependency revalidation.
- Legal-workflow review: complete. Source validation/download does not establish
  binding authority or current applicability. Retain coverage gaps, version pins,
  temporal/jurisdiction reasoning and human evidence assessments independently of
  technical checks. An obligation without a technical finding must remain visible.

## Implementation direction for review

Use a local synchronous CLI and the existing Pydantic/standard-library stack.
Accept declared JSON inputs, fetch explicitly selected official sources, retain
private immutable run artifacts and render a traceable report. Revalidation compares
pinned inputs and source attempts without rewriting history. A repository-local
skill guides research and accountable review; no automated legal interpreter or
provider is required. All new public data contracts originate in `models.py`.

The first implementation must reach models and generated contracts, CLI/retrieval/
report/revalidation modules, synthetic fixtures and tests, portable skill resources,
packaging where needed, and user documentation. Existing scanner/agent helpers and
frontend UI are outside that change. Exact file ownership and acceptance checks
will be assigned in the construction plan after requirements review.

## Outstanding acceptance

Requirements approval, design review, construction stage checkpoints, implemented
end-to-end synthetic examples and MVP release checks remain pending. No current
legal corpus was accepted and no real legal assessment, scanner/provider execution,
containment verification, global installation or OS-policy change was performed.
