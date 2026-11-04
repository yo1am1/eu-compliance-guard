---
stage: implement
bolt: 003-legal-revalidation-cli
created: 2026-10-27T10:37:33Z
status: recorded
---

# Predecessor revalidation implementation

`revalidate --previous <run-directory>` now creates a linked successor with a
retained dependency comparison, observed comparison evidence and freshness
overlays for every historical obligation disposition. No predecessor is rewritten.

`history.py` shares the workflow's descriptor-based bounded readers with the HTML
view. It verifies the completion marker, listed artifact digests, declaration and
manifest consistency, manifest digest, comparison proof and required supported or
retrieved source artifacts. Unsafe, incomplete, corrupt and cross-project runs
fail before retrieval/output. JSON duplicates, backwards revisions and semantic
edits under unchanged ID/revision are rejected; source retrieval timestamps are
observational metadata. Existing first-run bundles remain readable.

Comparison includes additions/removals and changes to requirements, scope/facts,
activities, obligations/controls, targets/sources, selected and observed evidence,
reviews, family screenings and tool/config dependencies. Relevant changes make
historical claims stale and withdraw dependent effective support; original
declarations and historical outcomes stay visible. Unavailable evidence and
failed/offline refresh remain unknown. Stale takes precedence with both reasons
retained. Incomplete attribution withdraws support conservatively. Family
screenings renew after any known change because their dependency lists are
incomplete. Matching bytes support only matching recorded inputs, never legal
currency or renewed approval.

Comparison records originate in `models.py`; JSON Schema and TypeScript are
generated. CLI, Markdown, static escaped HTML, audit instructions and README cover
the successor workflow. Tables have column headers and named keyboard-scrollable
regions. The sdist now includes the README alongside plugin and fixture assets.

The baseline passed all 181 tests plus generated-contract and TypeScript checks.
Implementation checks pass, including synthetic successor chains, relevant versus
unrelated changes, date changes, missing/changed evidence, source changes, matching
bytes, failed refresh, immutable history, integrity rejection, revision checks and
safe comparison rendering. Final package and release evidence is recorded
separately in the Test walkthrough. Owner stage acceptance remains pending.

No live-source request, real legal assessment, scanner/provider execution,
interactive plugin UI check, global installation or OS-policy change occurred.
Native Herdr is unavailable here; one writer performed the work and no hidden
teammates were created. Pre-existing planning edits remain in Git stash.
