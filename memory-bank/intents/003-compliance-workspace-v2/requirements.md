---
intent: 003-compliance-workspace-v2
phase: inception
status: direction-approved
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

## Owner decisions (2026-11-04)

1. **Audience: open core.** Everything one developer needs is free, open source and
   local. Team features (law-change alerts, maintained packs, signed review workflow,
   a review queue, a multi-project dashboard) are designed as a later paid tier. They
   use the same files and formats, so no user has to migrate.
2. **Obligation packs.** The Owner or AI drafts them; a named, qualified lawyer reviews
   and signs each pack version. Basic GDPR and cookie packs are free. Specialised packs
   (AI Act, consumer law, national rules) and updates when the law changes are
   candidates for the paid tier. A pack never replaces a reviewer's applicability
   decision.
3. **Signing.** 2.0 uses Git SSH signing for reviews: it works offline, stays private,
   and uses keys developers already have. Sigstore, or the service's own signing, is a
   later paid-tier option, because Sigstore publishes the signer's email in a public
   log.
4. **Hosting.** 2.0 stays local and open source; no service is built yet. Everything
   is prepared for a fast move to a service later (see the principles below).
5. **Scanners.** 2.0 includes one narrow scanner: cookies and trackers on a URL the user
   owns, with consent for each scan, recorded as evidence beside the ePrivacy rule.
   Cloud and data-flow scanners come later.

## Service-ready principles (binding for 2.0 work)

- **Files are the API.** Runs, reviews, packs and evidence remain versioned files with
  contracts generated from `models.py`. A future service syncs and indexes these files;
  it never replaces their formats.
- **Stable identities.** Every record keeps a stable id and revision, so a service can
  merge records from many machines without conflicts.
- **No hidden local state.** Settings and caches that a service would need are declared
  in files, never assumed from one laptop.
- **Pure cores, thin edges.** Ranking, search, comparison and pack logic stay pure
  functions over records, callable from the CLI today and from a service tomorrow.
  Input/output and network sit at the edges.
- **Open by default.** Nothing in 2.0 requires an account, a server or a licence key.
  Paid-tier features are additive modules.
- **Signing and scanning are pluggable.** One interface for signing (SSH now; Sigstore
  or the service later) and one for evidence collection, so new backends do not change
  the records.

## Landscape research (2026-11-04)

[Full report](../../../docs/v2-landscape-research.md): five agents surveyed privacy
scanners, law-as-code, AI Act tools, GRC platforms and agent/PR tools on GitHub.
Star counts and dates come from the surveys and were not checked again.

**Findings:**
- No maintained, fully open, offline tool exists in this space.
- Every code-aware tool gives a verdict or a score.
- None pins official text, turns a law change into reopened decisions, or checks the
  citations that agents write.

**Unique bets proposed:**

1. A law lockfile (`eu-law.lock`) that pins act versions and article digests.
2. Law-change impact: when the lock moves, reopen only the reviews that cite a changed
   article.
3. Signed decisions bound to the law version, evidence hashes and commit.
4. A citation guard for agent-written text, also served as MCP tools.
5. A cross-regime PR screen with quoted articles.
6. Import-only evidence (SARIF from code scanners, EDPS Website Evidence Collector).
7. An application-date timeline quoted from the text.

**Owner answer (2026-11-04): the research version is adopted.** 2.0 ships the law
lockfile, law-change impact, signed decisions and the citation guard. Packs ship as a
signed *format* only, with no lawyer-reviewed content yet. Evidence comes from importing
EDPS Website Evidence Collector and SARIF results, not from our own scanner. The
dashboard and review queue are deferred; exports to existing GRC tools come first.

## Stability, liability and supply chain (Owner, 2026-11-04; binding for 1.5 and 2.0)

Priorities, in order: **security, then determinism, then features.**

1. **No liability for outcomes.** The MIT licence already disclaims warranty. In
   addition, every output, export, pack and signed record states that it is workflow
   evidence, not legal advice or a compliance verdict. The decision always belongs to
   the named person who signed it. Failures are reported as explicit gaps, never as
   silent success.
2. **Determinism.** The same inputs (declarations, lockfile, retrieved bytes) give
   byte-identical outputs. No wall-clock, locale, random or dictionary-order effects
   in ranking, search or rendering, and a test proves it by running twice.
3. **Fewer regular expressions.** Heuristic text parsing moves to structured parsers:
   HTML structure through `html.parser`, CELEX and ELI identifiers through small
   explicit parsers, diffs through a line-state parser. A regular expression stays
   only as an anchored `fullmatch` validator on a short, bounded input, with no nested
   quantifiers. A lint check enforces this rule. Today there are 23 uses in 7 modules.
4. **Verified services only.** Every host in the registry is an official EU institution
   domain, and a recorded check confirms its owner, its purpose and that it is still
   reachable. That check is a consented, on-demand `make verify-hosts`, never part of
   ordinary tests. A host that fails the check raises a gap; there is no silent fallback
   to another site. Third-party CI actions are pinned to full commit SHAs.
5. **14-day version cooldown.** A dependency, tool or action version is adopted only
   14 days after its release (`[tool.uv] exclude-newer = "14 days"`, and Dependabot
   `cooldown.default-days: 14`). Security fixes and hotfixes for a published advisory
   are exempt, each with a recorded reason. Exact pins and the lockfile stay.

Inception continues now: units, stories and bolts follow the specsmd flow, as for
[1.5](../002-trustworthy-guidance-v1-5/requirements.md).
