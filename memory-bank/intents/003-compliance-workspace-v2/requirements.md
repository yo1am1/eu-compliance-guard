---
intent: 003-compliance-workspace-v2
phase: inception
status: brainstorm-awaiting-owner-decisions
created: 2026-11-04T18:00:00Z
---

# Brainstorm: Version 2.0, from a review tool to a compliance workspace

## Destination (proposed)

In 1.x, one developer keeps one project's legal review traceable from the terminal.
In 2.0, a team keeps it current over time:

- it learns when the law changes;
- it reuses reviewed obligations instead of re-deriving them;
- it collects evidence from the running system, not only from code;
- it hands an auditor an export they recognise.

2.0 is still never the judge: people decide, and the tool keeps the record.

## Themes and candidate capabilities

### A. Law that stays current (recommended core)

- **A1 Change watch.** On a schedule and with consent, check every declared act for a
  newer consolidation or amendment. Diff the article text between versions and list
  the requirements whose cited articles changed.
- **A2 Pending law.** Track proposals and adopted acts with later application dates
  (AI Act phases, the Data Act, the ePrivacy reform), and show what applies from which
  date.
- **A3 Case law and guidance links.** Link EDPB guidelines and CJEU judgments to
  articles, as reviewable sources, never as conclusions.

### B. Reusable, reviewed knowledge

- **B1 Obligation packs.** Versioned, signed packs per family (GDPR core, ePrivacy
  cookies, CRD distance contracts, AI Act transparency). Each pack holds the
  obligations, conditions, exceptions and the exact articles, reviewed by a named
  lawyer. Projects import a pack instead of drafting obligations themselves.
- **B2 National overlays.** Member-state rules layered on EU acts, for example
  digital-consent ages and cookie guidance per DPA.

### C. Evidence from the running system

- **C1 Scanners.** Cookie and tracker scanning of a staging URL, and a data-flow map
  from code (Graphify). Authorized scope only, as AGENTS.md requires, and evidence is
  recorded with provenance.
- **C2 Continuous evidence.** CI keeps evidence fresh, and a changed file reopens only
  the gaps that depend on it.

### D. Team workflow and accountability

- **D1 Real reviewer identity.** Attestations signed with Git signing or Sigstore,
  replacing self-attested names.
- **D2 Review queue.** Assign steps to people, track due dates, and add comments on
  obligations.
- **D3 Dashboard.** The existing `frontend/` grows into a multi-project read-only view
  of progress, open steps, law changes and evidence age.

### E. Outputs people already use

- **E1 Exports.** A records-of-processing (Art. 30) draft, DPIA screening inputs,
  cookie-policy facts and an AI-system register, all labelled as drafts for review.
- **E2 MCP server.** Expose `next`, `ground`, `pr-check` and the article search as MCP
  tools, so any agent can use them, not only Claude Code.

## Recommended shape

2.0 = A1 + B1 + D1 + D3, with E2 as the integration surface.

- A1 and B1 answer the two biggest 1.x costs: law going stale, and drafting
  obligations by hand.
- D1 is what turns the record into something an auditor accepts.
- D3 makes it a team product.

C1, B2 and E1 are good 2.x follow-ups. C1 also needs explicit scanning authorization
per environment.

## Constraints carried forward

- Read-only toward legal conclusions; no automated verdicts.
- Network only with consent; official hosts only for law text.
- `specs/**` are preserved byte for byte.
- Credentials, private evidence and runs stay out of Git.
- Contracts are generated from `models.py`.

## Decisions for the Owner

1. **Audience.** Solo developers (keep it a plugin) or small teams (the dashboard and
   review queue become core)?
2. **Obligation packs.** Who reviews them: the Owner, partner lawyers, or a community
   with named reviewers? Free or paid?
3. **Identity.** Git commit signing (simple, developer-native) or Sigstore/OIDC
   (stronger, more setup)?
4. **Hosting.** Local-only, as in 1.x, or an optional self-hosted service for the
   dashboard and schedules?
5. **Scanners.** In 2.0, or deferred to 2.x?

Once these are answered, inception continues: units, stories and bolts follow the
specsmd flow, as for [1.5](../002-trustworthy-guidance-v1-5/requirements.md).
