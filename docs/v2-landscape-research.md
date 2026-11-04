# EU Compliance Guard 2.0: landscape and unique bets

*Prepared 2026-11-04 from five research surveys: privacy-as-code, law-as-code, AI Act tools, GRC, and agent tools.*

**How far this was checked.** I could not re-check the GitHub data myself because this session has no GitHub API access to these repositories. All star counts, commit dates, licences and archive states below come from the surveys and have not been checked again. Where the surveys disagree, the item is marked **[unverified]**. The 2.0 brainstorm is not in the current working tree. It exists only on branch `claude/roadmap-v1.5-v2` (commit `5705092`, `memory-bank/intents/003-compliance-workspace-v2/requirements.md`), and I read it from there.

## 1. Landscape

| Segment | Notable projects | What they do well |
|---|---|---|
| Privacy code scanners | [Bearer](https://github.com/Bearer/bearer) (ELv2, active), [HoundDog.ai](https://github.com/hounddogai/hounddog) (open-core, has MCP), [Privado](https://github.com/Privado-Inc/privado) (dormant), [Presidio](https://github.com/data-privacy-stack/presidio) (MIT), [Fides](https://github.com/ethyca/fides) (archived 2026-08-28 **[unverified]**) | Trace personal-data flows from source to sink. Diff-aware CI scanning. Draft inputs for a records-of-processing (Art. 30) register. The fideslang taxonomy (Fides) and PII detection in data (Presidio). |
| Runtime web evidence | [EDPS Website Evidence Collector](https://code.europa.eu/EDPS/website-evidence-collector) (EUPL), [Blacklight](https://github.com/the-markup/blacklight-collector) | Cookie, tracker and beacon evidence from a deployed site. The EDPS format is the one a regulator uses. |
| EU law access and law-as-code | [eurlex-mcp-server](https://github.com/Honeyfield-Org/eurlex-mcp-server) (MIT, active), [eurmcp](https://github.com/hatt-io/eurmcp), [LexAPI](https://github.com/Lex-API/lexapi-mcp) (hosted, paid), [Ansvar EU_compliance_MCP](https://github.com/Ansvar-Systems/EU_compliance_MCP) (archived), [Catala](https://github.com/CatalaLang/catala), [W3C DPV](https://w3c.github.io/dpv/2.0/legal/eu) | Keyless Cellar access: consolidated text, transposition, case law and citation graph. Text as in force on a given date, structural diffs and quote checks (eurmcp). Change webhooks (LexAPI). Executable law with the legal text beside its encoding (Catala). An open privacy and legal vocabulary (DPV). |
| AI Act tools | [Regula](https://github.com/kuzivaai/getregula), [ComplianceLint](https://github.com/ki-sum/compliancelint) (BSL), [EuConform](https://github.com/Hiepler/EuConform), [VerifyWise](https://github.com/verifywise-ai/verifywise) (source-available), [COMPL-AI](https://github.com/compl-ai/compl-ai), [eu-ai-act-toolkit](https://github.com/AbdelStark/eu-ai-act-toolkit) | Risk-tier questionnaires and checklists. SARIF, GitHub Action and pre-commit output (Regula). An "insufficient information" outcome (Regula). Versioned evidence bundles and AI-BOM import (EuConform). Model benchmarks mapped to AI Act principles (COMPL-AI). |
| GRC | [CISO Assistant](https://github.com/intuitem/ciso-assistant-community) (AGPL), [Probo](https://github.com/getprobo/probo) (MIT), [Comp AI](https://github.com/trycompai/comp), [compliance-trestle / OSCAL](https://github.com/oscal-compass/compliance-trestle), [Lula](https://github.com/defenseunicorns/lula), [Prowler](https://github.com/prowler-cloud/prowler), [CNIL PIA](https://github.com/LINCnil/pia) | Large framework libraries: NIS2, DORA, AI Act and CRA annexes (CISO Assistant). Wide MCP coverage with read and write access (Probo). OSCAL format with signing (trestle). PRs that touch mapped controls get flagged (Lula). Infrastructure evidence (Prowler). An official DPIA method with sign-off steps (CNIL). |
| Agent and PR tools | ComplianceLint, [Systima Comply](https://github.com/systima-ai/comply) (stalled since 2026-03), [Privalyse](https://pypi.org/project/privalyse-cli/), HoundDog | PR comments with SARIF. Declared risk level checked against frameworks detected in code (Comply). Third-country transfer flags (Privalyse). Agent "human gates" (ComplianceLint). |

**How healthy the field is.** The open-source side is thinning:

- Archived: Fides, PIICatcher and Ansvar.
- Dormant: Privado core, Systima Comply, Comply (strongDM) and Horusec.
- Active but not fully open source: Bearer (ELv2), HoundDog, ComplianceLint (BSL) and VerifyWise (VCEL).

There is no maintained, fully open, offline tool in our space.

## 2. What nobody does

1. **No tool links a finding to pinned official EU text.**
   - Scanners stop at "PII flows to X" or a generic "GDPR" tag.
   - AI Act tools keep the Act as hand-edited JSON or JS. After the 2026 Digital Omnibus amendment they disagree on when the Annex III duties apply: 2 Dec 2026 or 2 Dec 2027. The regulation number given in the surveys, (EU) 2026/1744, is **[unverified]**.
   - GRC "libraries" are frozen copies of the law (CISO Assistant, VerifyWise).
2. **No tool turns a law change into reopened decisions.**
   - Some tools see that the law changed: eurmcp shows structural diffs, LexAPI has paid webhooks, and Ansvar ran a daily freshness check before it was archived.
   - Some tools see that code changed: Bearer and HoundDog scan diffs.
   - None joins the two to say "these reviews in your project are now stale, and this is the article-level diff".
3. **No tool records an accountable decision without a verdict.**
   - Every code-aware tool emits a verdict or a score: ComplianceLint (COMPLIANT/NON_COMPLIANT plus euro penalty exposure), Systima (a 0 to 1 score), ArkForge ("certified compliance"), Prowler (framework scores) and Comp AI ("get compliant").
   - None binds a named reviewer to a law version, an evidence hash and a commit. Regula's audit trail is self-attesting.
4. **No tool covers several EU regimes for one product.**
   - Each tool covers one area: AI Act only, privacy only, or retrieval only.
   - Only Ansvar's `check_applicability` crossed regimes, and it is archived.
   - No PR tool flags ePrivacy, CRA or EAA touchpoints alongside GDPR and the AI Act.
5. **No tool checks the legal citations agents write.**
   - eurmcp has anchored quote verification but no link to a project.
   - Nothing stops a coding agent from inventing an article number in a review or PR comment.
6. **No tool labels the authority of a source.** No tool consistently separates authentic OJ text, consolidated non-authentic text, delegated or implementing acts, guidance, standards and proposals. LexAPI only notes that consolidated text is not authentic.
7. **No tool connects code evidence with runtime evidence.**
   - Code scanners (Bearer, HoundDog, Privado) and runtime collectors (EDPS WEC, Blacklight) are not connected.
   - Nobody attaches "the code initialises an analytics SDK" and "the collector saw its cookie before consent" to the same consent obligation.
8. **No pinned, reproducible law snapshot exists.** Richer retrieval is hosted (LexAPI, the Ansvar gateway) or needs your own ingestion. Nothing gives CI or an air-gapped team a content-hashed, verifiable set of the official texts a project relies on.
9. **No benchmark exists for retrieving EU law in software contexts.** No test set says "this feature should surface these articles". Our 1.5 FR-8 is the start of one.

## 3. Where we already differ

- **No verdict, with named reviewers.** This is the opposite of how ComplianceLint, ArkForge, Comp AI and Prowler present themselves. Regula comes closest, but it covers the AI Act only, does not pin official text, and its audit trail is self-attesting.
- **Official text from the Publications Office with digests, shown beside each gap.** No scanner, AI Act tool or GRC tool does this.
- **Revalidation against a predecessor run.** Earlier reviews go stale when dependencies change. Nobody else invalidates human decisions.
- **Eleven candidate families in one declarations file.** The other tools each cover one regime.
- **Facts grounded in code, with "assumed" and "unknown" as visible states, and "an empty scan is not compliance" stated in the output.**
- **Read-only, local, inside the developer's agent session.** Probo's MCP writes compliance artefacts; ours never writes a legal decision.

Where others are ahead today:

- Consolidated text, transposition, citation graph and case law (eurlex-mcp-server).
- Text as in force on a given date and provision-level diffs (eurmcp).
- SARIF output and multi-language AST detection (Regula, Systima).
- Standard exports such as OSCAL and DPV JSON-LD (trestle, Regula).

## 4. Candidate unique bets for 2.0

### Bet 1: A lockfile for the law (`eu-law.lock`)

**The bet.** Each project gets a committed lockfile that pins every act it relies on: ELI or CELEX expression, consolidation date, authority tier and a content digest per article. CI checks it offline. A team without network access can verify it from a bundled snapshot.

**Why nobody has it.** Retrieval tools fetch live or hosted text (LexAPI, Ansvar gateway). The AI Act tools hard-code dates that have already drifted (gap 1, gap 8).

**Why we are positioned for it.**
- We already store digests of retrieved texts and keep a fixed host registry.
- 1.5 FR-3 introduces consolidated CELEX targets.
- `models.py` can generate the lockfile schema.

**Risk.**
- Cellar formats differ by act and era.
- Splitting text into articles is fragile.
- A digest proves the bytes match, not that the law is current. We already say this; it must stay visible.

**First proof (2 to 3 weeks).** A `lock` command plus `check --locked` for two acts (GDPR, and the AI Act consolidation). It covers article segmentation, digests, an authority-tier field and a CI job that fails when a declared article is missing from the lock. Synthetic fixtures for tests, one consented live fetch for the end-to-end report.

### Bet 2: Law-change impact on reviewed decisions

**The bet.** When the lockfile resolves to a newer consolidation, show the article-level diff and reopen only the requirements, facts and reviews that cite a changed article. Each reopened item gets the old and new text side by side.

**Why nobody has it.** eurmcp has diffs but no project. LexAPI has webhooks but no review records. The scanners know nothing about the law (gap 2).

**Why we are positioned for it.** Predecessor revalidation and staleness already exist for dependency changes. This bet adds the law as a new input to the same mechanism. 1.5 FR-4 already plans the "newer consolidation" notice.

**Risk.**
- Corrigenda and renumbering produce noisy diffs.
- Delegated or implementing acts and guidance do not show up in the consolidation diff, so they need a separate route.
- Throttling on the public Cellar endpoint.

**First proof.** Two fixture consolidations of one act, including one renumbered article. A `law-diff` command whose output lists the changed articles, the affected requirement IDs and the reviews that became stale. Then one live run on a real amended act. Which real AI Act consolidations exist after the Omnibus amendment is **[unverified]**.

### Bet 3: Decisions bound to inputs and signed (brainstorm D1, sharpened)

**The bet.** Each decision record is signed with the reviewer's Git SSH or GPG key. The signed record covers the reviewer, the decision, the lock digest of the cited articles, the hashes of the evidence files and the commit. The decision goes stale automatically when any of those inputs changes. Verification is offline with `git verify`-style tooling.

**Why nobody has it.** Every tool either gives verdicts or uses self-attested logs (gap 3). trestle signs OSCAL files but has no link to the law or the code.

**Why we are positioned for it.**
- We already have tamper-evident reports, named reviewers and staleness rules.
- The README admits that reviewer names are self-attested, so this closes a known gap.

**Risk.**
- Key management for non-developer reviewers such as lawyers.
- A signature shows who signed, not their legal competence. This must be stated in the output.

**First proof.** `attest` and `verify` commands using `ssh-keygen -Y sign/verify` (no new dependency). Tests: a signed record verifies, a tampered record fails, and a changed evidence file or lock digest makes the record stale.

### Bet 4: A citation guard for agents

**The bet.** A hook and a CLI or MCP tool scan agent-written text (review notes, PR comments, report drafts). Each "Art. N(x) of act Y" and each quoted passage is checked against the locked text. A citation that does not exist, or a quote that does not match, is flagged before the text is posted.

**Why nobody has it.** eurmcp checks quotes in isolation. No agent tool guards against invented citations inside a project (gap 5).

**Why we are positioned for it.** We already have the plugin, its hooks and the locked text (Bet 1). This also turns brainstorm item E2, the MCP server, from a wrapper into something only we can offer.

**Risk.**
- Parsing citations across languages and citation styles.
- False confidence: a citation that exists is not necessarily a relevant one, and the output must say so.

**First proof.** A `verify-citations` command over Markdown with a synthetic set of 50 citations, valid and invented, and measured precision and recall. It is then wired into `/eucg-pr` so the PR comment marks unverified citations.

### Bet 5: Cross-regime PR screen with official text and a "needs reviewer" state

**The bet.** Extend `pr-check` so that each touchpoint names its candidate families across all eleven, quotes the locked article excerpt in the PR comment, and opens a "needs reviewer" item instead of pass or fail. It adds role-change triggers, such as fine-tuning a model or a new intended purpose (AI Act Art. 25), and update-mechanism triggers (CRA).

**Why nobody has it.** PR tools cover PII flows only, or AI frameworks only, and use pass/fail. Lula needs manual UUID tags in the code (gap 4).

**Why we are positioned for it.** `pr-check`, the concept lexicon and the eleven families already exist. This is the most visible daily feature.

**Risk.**
- Keyword screening makes noise on large diffs.
- Detecting role changes from a diff is heuristic and must be labelled as a candidate.

**First proof.** A diff fixture set with expected families, extending FR-8, plus excerpts in the PR comment from the lockfile. Report before-and-after precision.

### Bet 6: One evidence model for code and runtime (import only)

**The bet.** Ingest SARIF from Bearer, HoundDog or Privalyse and EDPS WEC reports as labelled, untrusted evidence attached to facts. A correlation view joins, for example, "analytics SDK initialised in `src/x.ts:12`" and "cookie set before consent" on the ePrivacy Art. 5(3) gap.

**Why nobody has it.** Code tools and runtime tools are separate worlds (gap 7).

**Why we are positioned for it.** Grounded facts already carry file evidence. Importing files runs no scanner, so it stays within AGENTS.md: no laptop audit and no scanning without authorization.

**Risk.**
- Format drift in third-party output.
- The temptation to read an empty report as clean. That rule must stay in the output.

**First proof.** Importers for SARIF 2.1.0 and the WEC JSON format, built against synthetic fixtures, plus one correlated gap in the report.

### Bet 7: A dated obligation timeline quoted from the text

**The bet.** For each candidate obligation, show the application date and the transition period per operator role. Each date links to the article that sets it, such as AI Act Art. 113 and CRA Art. 71, and is shown as quoted locked text, never as a bare date in code.

**Why nobody has it.** The AI Act tools hard-code dates and contradict each other. A2 in our brainstorm has no source model (gap 1, and the law-as-code survey's gap on application dates).

**Why we are positioned for it.** It reuses the lockfile and the article excerpts.

**Risk.** Dates often need interpretation, for example "from 2 Aug 2026 except…". Every date has to stay a candidate until a reviewer confirms it.

**First proof.** A timeline for the AI Act and the CRA in the report, with each date quoted from its article. Any date that cannot be quoted is shown as a gap.

## 5. Recommendation

**Build three bets for 2.0, all local and all read-only toward the law.**

1. **Bets 1 and 2 together, the law lockfile with change impact.** This replaces A1 with a version nobody else has: an offline, verifiable lockfile plus reopened decisions. Everything else depends on it.
2. **Bet 3, signed decisions bound to their inputs.** This is D1, using Git or SSH signing rather than Sigstore. It is the strongest version of the no-verdict claim and closes the "self-attested names" limit.
3. **Bet 4, the citation guard, delivered as the MCP surface (E2).** It is cheap, visible, and only possible because of the lockfile.

Bet 5 is an incremental 2.x extension of `pr-check` once the lockfile exists. Bets 6 and 7 are 2.x as well.

**Defer or drop from the current brainstorm:**

- **D3 dashboard and D2 review queue: defer.** Team registers, approvals and dashboards are well served already (CISO Assistant, Probo, VerifyWise), and building them makes us a server product. Push reviewed gaps to those tools later through an OSCAL or MCP export.
- **B1 obligation packs: drop for 2.0.** They need named lawyers and carry liability. Ansvar's archiving shows how costly a curated corpus is to maintain. If kept at all, ship only the pack format, signed with Bet 3, and no content.
- **C1 scanners: defer, and replace with import-only evidence (Bet 6) in 2.x.** This avoids the authorization and containment problems.
- **B2 national overlays and A3 case-law and guidance links: defer to 2.x.** For A3, start by adding authority-tier labels to the lockfile.
- **E1 exports: defer.** When this work starts, target OSCAL assessment results and DPV rather than our own formats.

**Suggested answers to the brainstorm's open decisions:**

| Decision | Suggested answer |
|---|---|
| Audience | Solo developers and small teams working in the repository. The tool stays a plugin plus CLI. |
| Packs | Not in 2.0. |
| Identity | Git or SSH signing. |
| Hosting | Local only. |
| Scanners | Deferred, and import-only when they arrive. |

**Not verified:**

- **Repository facts.** I could not re-check any repository's stars, last commit, licence or archive state myself; they all come from the surveys.
- **Survey conflicts.**
  - eurlex-mcp-server: listed under both philrox and Honeyfield-Org, with releases given as both v2.1.1 and v2.4.4.
  - Privado: last activity given as Aug 2024, Nov 2025 and Oct 2026 (a CI fix).
  - Ansvar fleet repository: one survey says it exists, another got a 404.
  - HoundDog licence: unclear.
- **Legal facts.** The identifier and dates of the Digital Omnibus amendment, and the Annex III application date.
