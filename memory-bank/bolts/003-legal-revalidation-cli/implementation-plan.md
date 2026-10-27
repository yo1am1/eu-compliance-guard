---
stage: plan
bolt: 003-legal-revalidation-cli
created: 2026-10-27T10:37:33Z
status: recorded
---

# Predecessor comparison and release plan

Owner direction: continue `claude/bolt-003-plugin-ui`, complete this work before
moving to the separate recommendation project. Existing local Bolt 002 planning
edits are preserved in Git stash. This continues the implementation; formal stage
acceptance and bolt completion remain for the Owner.

Scope: story 004 predecessor comparison and story 006 reproducible delivery.
Story 005 already ships six repository-local plugin skills; extend the audit
instructions with the explicit predecessor workflow. Preserve `specs/**` exactly.

- Reuse bounded descriptor-based readers and existing `CurrentAssessment` and
  `Evidence` records. New comparison contracts originate only in `models.py`.
- Verify one supplied predecessor's marker, all listed artifact digests, normalized
  declarations, manifest digest and retained supported/retrieved source bytes.
  Reject unsafe, corrupt, incomplete or cross-project predecessors before fetching
  or creating output. Apply the same verifier to the browser view.
- Compare canonical semantic records and selected/observed dependencies. Include
  additions/removals, source bytes, review edits and tool/config changes. Reject
  semantic edits under unchanged revisions and backwards revisions. Ignore source
  retrieval timestamps for content comparison.
- Retain `comparison.json`, its observed evidence metadata and one existing
  freshness overlay per historical disposition. Link the parent, preserve every
  predecessor byte and retain declarations separately from effective reviews.
- Relevant change takes precedence as stale; unavailable observations remain
  unknown. Incomplete attribution withdraws support conservatively. Family
  screenings lack full dependency lists and therefore renew after any known change.
  No equality result renews legal currency or reviewer approval.
- Update CLI, Markdown/HTML reports, plugin instructions and the offline example.
  Regenerate JSON Schema/TypeScript. Add synthetic regressions; run `make check`,
  inspect wheel/sdist and execute offline first/successor runs outside the checkout.

One writer handles all files because this host is outside native Herdr; hidden
subagents are forbidden. No live legal-source run, provider execution, global
installation, scanner or host-policy change is part of this work.
