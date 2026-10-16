# Legal applicability and control architecture review

Date: 2026-10-13. Status: bounded design proposal; no application implementation or legal corpus acceptance.

Baseline: [approved requirements](../requirements.md), [prior research](../research.md), repository AGENTS.md and safety, Git and review rules. Requirements take precedence over the older research statement that requirements remained a draft. The repository is an instruction library; the proposed application is not executable here.

## 1. Recommended minimum

Use one local engine with a versioned, human-reviewable control registry, retained source snapshots and the application’s shared local persistence. Plain records and explicit joins are sufficient. Do not add a legal inference service, graph database, country plugins or a new agent framework. Scanner and graph outputs supply investigation leads; check results establish bounded technical assertions; accountable reviewers determine remaining legal and organizational conclusions.

Keep three independent dimensions: applicability, verification and freshness. An applicable obligation can have a passing browser check and an unresolved organizational review at the same time. An unresolved national source must never become an exemption. A technical failure can remain visible even when its legal consequence is unresolved.

Evaluate all candidate families from the requirements: GDPR; ePrivacy/marketing; service identity; consumer contracts/practices; accessibility; intermediaries/platforms; AI Act; NIS2/CRA; Data Act; copyright/licensing; additional sector/national rules. Each family receives a recorded decision or a coverage gap. Starter controls below cover only four synthetic domains. Other families receive screening questions and an explicit unsupported-review disposition, not fabricated check coverage.

Tradeoff: this keeps legal reasoning inspectable and avoids a general legal rules language. It requires manual source and interpretation review, which is preferable to silently guessing a jurisdiction or exception.

## 2. Records and invariants

The following are logical interfaces, not a prescribed database migration. Use stable IDs plus immutable revisions; historical runs reference the exact revisions they used. Mutable display labels never identify legal obligations.

| Record | Required fields |
| --- | --- |
| Scope | scope ID/revision, assessment date, project/environment references, activities, establishment, markets, customer types, size/sector facts, regulatory roles, allowed targets/operations, exclusions, processing boundary |
| Fact | fact ID/revision, activity/entity, value/unit or unknown, observed/declared/assumed classification, evidence/source reference, observation date, conflicts, accountable owner |
| Processing activity | purpose, subjects/categories, controller/processor and other role decisions, declared legal basis, recipients/subprocessors, storage and remote-access countries, lifecycle stores, retention rule/exception, evidence owner |
| Source | source ID/revision, publisher, authority jurisdiction, official identifier/CELEX/ELI/ECLI when available, direct URL, language, source type, document/version date, publication date, retrieval timestamp, digest or recorded equivalent version evidence, article/paragraph locators, original/translation relationship |
| Source review | source revision, assessment date/jurisdiction, publication/amendment/correction/case-law/guidance review results, entry/application/transition/repeal dates, last successful verification, attempted retrieval/error, reviewer, review status and gaps |
| Obligation | stable ID/revision, family, binding-duty/recommendation classification, provision-level source links, subject/activity/role, applicability conditions and exceptions, national overlay references, required review methods, completeness boundaries |
| Applicability decision | obligation revision, scope/fact revisions, jurisdiction and connecting-factor rationale, applicable/not-applicable/unresolved, condition outcomes, factual/legal rationale, evidence, reviewer, date, unresolved facts/sources |
| Control | ID/revision, linked obligations, intended outcome, technical assertion or review question, required inputs, check references, evidence requirements, owner, limitations, registry provenance |
| Check definition/result | control/check revisions, required authorization, fixture/input/environment/tool/rule versions, included/excluded scenarios, expected/actual result, evidence references, retries, outcome, interruption/error |
| Evidence request/review | request ID, linked obligation/control/activity, purpose, minimum artifact or declaration, owner, requested period, status, redaction/access/retention rules; evidence ID/digest/date/scope, declared/documented/independently-verified level, reviewer rationale and missing evidence |
| Finding/validation/action | stable IDs, source/applicability/control/check/evidence revisions, technical assertion, separate legal assessment, impact/affected parties, counter-evidence validation, status/freshness, owner, completion condition, justified target date, residual risk, before/after references |

Invariants:

1. Every applicability decision names its facts, jurisdiction, assessment date and legal provisions. Missing facts produce unknown conditions; unresolved connecting factors produce jurisdiction gaps. A known decisive exclusion may support non-applicability only with recorded reasoning, including why other unknowns cannot change it.
2. A legal conclusion depends on reviewed source status as well as substantive conditions. A retrieved page is not proof that amendments, translations or case law were reviewed. Digests identify bytes; they do not establish legal validity.
3. Standards, guidance and optional practice remain separately typed. A standard becomes part of a legal assessment only through a reviewed legal mapping, including applicable version and any official harmonization citation. WCAG-EM supplies evaluation methodology, not legal applicability [S9].
4. One control may serve several obligations; one obligation may require multiple controls and methods. Passing one linked assertion does not satisfy all linked obligations.
5. Source pages and submitted artifacts are untrusted evidence. Extract structured facts; do not follow embedded commands, change permissions or execute documents.
6. Findings retain every contradictory observation and retry. No successful retry replaces a failing attempt without explaining changed conditions or nondeterminism.
7. Source, fact, code, deployed environment and relevant graph changes invalidate dependent conclusions. Historical evidence remains inspectable; no historical pass verifies new inputs.
8. Public registry exports contain generic definitions and provenance only. Private evidence and reviewer identities remain in private audit storage; public examples use synthetic data.

## 3. Source authority, freshness and national overlays

Authority is contextual, not a single numerical ranking. Record enacted EU legislation, national implementation, judgments, final guidance, draft guidance, proposals, standards and engineering practice as distinct source types. Review judgments for court, case identifier, provision, holding and relevance; publication alone does not automatically invalidate every existing control.

Maintain explicit source-chain relationships: consolidates, amends, corrects, repeals, interprets and implements. Use consolidated text to navigate, and review the underlying official acts for the assessment date. The baseline explains the documentation status of consolidations; this pass could not retrieve the EUR-Lex explanatory page [S12]. Do not claim that review has been completed.

At audit preparation, attempt official refresh for every screened family. Persist attempted time, successful time and failed tasks separately. Proposed statuses are unreviewed, reviewed-for-assessment, stale, unavailable and superseded. Do not invent a universal freshness interval: a same-day download can still miss an amendment. Scheduled rechecks may help operations but cannot substitute for the required audit-time source-chain review. Offline runs may inspect retained evidence and perform authorized technical checks, while affected current-law conclusions remain unresolved.

Each national overlay is a record keyed by country, legal subject, provision and effective interval. It carries official national act/provision, regulator/case-law references, language and translation status, changed conditions and reviewer approval. Select overlays using establishment, targeted markets, subject/activity and relevant legal connecting factors, not browser locale alone. Country eligibility means research can be requested; it does not mean that country has an accepted overlay. National transposition records are discovery aids, not proof that every implementation provision is correct [S12]. EEA, UK and Swiss coverage requires separate legal bases.

Conflicting overlays or authorities create a specialist review item. Preserve both sources and the unresolved interpretation rather than selecting whichever yields a pass. Never overwrite EU conditions with a national value without identifying the legal permission for national variation.

Registry changes are proposed first: source diff, interpretation change, affected obligation/control/check revisions, acceptance fixtures and affected historical conclusions. A named reviewer accepts a new revision. Earlier runs remain immutable and receive an explicit reassessment notice; adopted changes do not retroactively relabel them as compliant.

## 4. Evidence requests and review lifecycle

Request only what supports the applicable condition. Offer a structured declaration initially, then request the relevant dated artifact; assess artifact sufficiency separately from its presence. Evidence requests are requested, supplied, insufficient, reviewed or withdrawn. Withdrawal leaves the coverage gap visible.

| Review area | Minimum targeted request and completion question |
| --- | --- |
| Lawful basis | Per-purpose basis, necessity or balancing assessment, consent records where relevant, and additional sensitive-data condition; does evidence support this particular purpose and role? [S2] |
| Lifecycle/rights | Store inventory, request procedure, identity-verification rationale, deadline/extension decision, recipient notifications, retention exception and restore handling; which stores and periods remain unverified? [S3] |
| Governance/risk | Processing records and threshold decisions; DPIA screening and applicable authority lists; DPO/representative/competent-authority reasoning and accountable owners. Article-level governance derivation remains pending [S1, baseline research]. |
| Vendors/transfers | Agreement and subprocessor schedule, actual storage/support/remote-access locations, transfer mechanism and any necessary assessment/measures; hosting location alone cannot close the request. Detailed final transfer guidance remains pending [S6]. |
| Incident response | Synthetic awareness/decision timeline, separate authority/individual notification decisions and sourced deadlines; inspect exercise evidence without sending real notifications. Final article/source-chain review remains pending [S1]. |
| AI processing | Separate development/training and operational activities; provenance/reuse decisions, provider retention/training settings, dataset and derived-artifact rights handling. GDPR evidence does not establish AI Act classification [baseline research]. |
| Accessibility/consumer | Service/product classification, size/date/exemption facts, legally mapped standard version, manual complete-process results; consumer type, contract type, disclosures, cancellation/refund records and any relied-on exception [S7–S9]. |

Verification outcomes: passed assertion, observed failure, unresolved human review, blocked, not tested. Human review records have pending, supported, unsupported or unresolved disposition, with reviewer, rationale and evidence. A declaration is never automatically upgraded to independent verification. A signed policy may be documented yet insufficient to establish operational behavior.

Material findings need a separate validation record: claimed impact; applicable legal condition; protective controls and contrary evidence; validation method; confirmed/refuted/unresolved outcome. This can be a second explicit review step in the same process; it does not require another service or agent. Refuted leads remain in history. Legal and organizational review must remain separate from a technically verified fix.

Remediation states follow R5.19: proposed, running, applied-awaiting-verification, verified, failed and blocked. Verification needs retained before/after results and relevant regression outcomes under current inputs. Risk acceptance records an owner decision and residual risk; it does not turn a failed check into a pass. An audit may have complete dispositions within declared scope while unresolved obligations remain visible. Interrupted or budget-expired work is a partial report, with unfinished work explicitly identified.

## 5. Bounded starter matrix

These are candidate definitions for synthetic acceptance, not an accepted EU or national law catalog. All binding-law rows require final source-chain review. A fixture may provide an explicitly fictional reviewed overlay to test architecture; it must never be published as an actual national law.

| Law/provision candidate | Obligation/condition | Control | Check and required evidence | Disposition boundary |
| --- | --- | --- | --- | --- |
| GDPR Articles 6–9 [S1, S2] | Purpose-specific lawful processing and applicable additional conditions | PRIV-BASIS: maintain basis and supporting assessment per activity | Review synthetic activity register, necessity/consent/balancing records; compare notice and observed recipients | Software confirms supplied records and discrepancies; legal sufficiency remains reviewable |
| GDPR Articles 12–22 [S1, S3] | Applicable rights and response procedure | PRIV-RIGHTS: request intake, deadline, restriction/objection and recipient handling | Synthetic request timeline, proportionate identity step, action/refusal/extension rationale and recipient evidence | Supported rights depend on basis and condition; not every right applies identically |
| GDPR Articles 5 and 17 [S1–S3] | Lifecycle and justified retention | PRIV-RETENTION: per-store deletion/expiry/exception | Synthetic primary/index/cache/log and restore records; exception source and limited retained fields | Primary deletion does not prove downstream deletion; exceptions require evidence |
| ePrivacy Article 5(3), national implementation; GDPR where relevant [S4, S5] | Consent-dependent device access/storage with sourced exceptions | TRACK-STATE: enforce documented decisions across consent states | Fresh/reject/accept/withdraw browser states, network/storage and identified server forwarding; necessity review | Cookie count alone establishes neither tracking absence nor legality |
| Accessibility Directive scope/requirements, applicable national act and standards [S8, S9] | Covered service/product and conditional exemption | ACCESS-PROCESS: assess complete synthetic purchase process | Automated results plus keyboard, assistive-technology and downloadable-document review; classification/exemption evidence | Automated pass remains partial; legal mapping and manual items can remain unresolved |
| Consumer Rights Directive and national implementation [S7, S10] | Applicable B2C contract disclosures and contract-type-dependent rights | CONSUMER-JOURNEY: price, recurring terms, optional extras, confirmation, withdrawal/refund | Synthetic offer/order/confirmation/cancellation; durable confirmation artifact and exception evidence | B2B and digital-content/service branches require distinct applicability |
| Relevant national marketing/price/review rules | Sourced claims and permissions | CONSUMER-CLAIMS: inspect discount/review/marketing journeys | Price history, review-verification claim evidence, permission/unsubscribe scenarios | No accepted national sources in this pass; legal assessment unresolved |
| ODR repeal [S11] | Retired template requirements must not be reinstated | SOURCE-OBSOLETE: source-history review | Synthetic template requiring an old ODR link, paired with reviewed repeal snapshot | Baseline repeal date is a research lead until final official text is reviewed; other redress duties remain separate |

## 6. Acceptance cases to retain in the eventual implementation

Each case records inputs, expected dispositions and both supporting and contrary evidence. These cases were designed, not executed.

| Case | Expected behavior |
| --- | --- |
| A1 — No consent checkbox for necessary contract fulfillment | Do not report consent absence alone as failure; request evidence of necessity and separate optional advertising. Candidate basis: Article 6(1)(b) [S2]. |
| A2 — Hash-linked identifier; encrypted customer table with retained key | Keep personal-data screening active; transformation does not establish anonymity. Record identifiability/key-access facts [S1, S2a]. |
| A3 — Consent-based online child service in France | Test a declared 15-year-old against the French source candidate; contrast a fictional 16-year threshold overlay and an unknown jurisdiction. No global age cutoff; statutory Article 45 and translation review remain open [S2, S2b]. |
| A4 — Erasure request with supported legal-retention exception | Retain only justified fields within the verified exception; unexplained analytics copies remain a gap. Compare with unsupported blanket retention refusal [S3]. |
| A5 — Request received 15 February in a non-leap year | Ordinary one-calendar-month branch yields 15 March, not receipt plus 30 days. Test valid extension notice separately; retain prompt-action obligation. Month-end/holiday/time-zone rules need final deadline-source review [S3]. |
| A6 — No cookie, tracking pixel fires on rejection | Observed network failure remains visible; confirm device-access condition, national consent/exception rule and counter-evidence before legal confirmation [S5]. |
| A7 — Essential storage and optional tracker | Rejection may leave justified essential storage while blocking optional tracking; national necessity review remains explicit [S5]. |
| A8 — Automated accessibility pass, keyboard-blocked checkout | Keep observed manual failure and remaining assistive-technology/document checks; no overall legal pass. Contrast service microenterprise claim with product-provider facts; review precise statutory thresholds [S8, S9]. |
| A9 — B2C subscription with hidden recurrence; B2B comparator | Inspect recurring-price disclosure and confirmation in the consumer branch; classify B2B separately. Digital-content withdrawal exception needs its own conditions and evidence [S7, S10]. |
| A10 — Stale law, failed translation or unavailable overlay | Show last successful verification or unknown; technical evidence remains usable within its bounds; affected current-law conclusions stay unresolved. |
| A11 — Missing vendor agreement and denied store access | Organizational review remains unresolved; store check blocked; neither becomes a pass or non-applicable item. |
| A12 — Authorized fix, rerun pass, later source/fact change | Technical fix becomes verified only after retained rerun/regressions; human review remains pending. Later change marks dependent conclusions stale. |
| A13 — Imported detector suppresses hashed data or uses 30 days | Preserve provenance/license and reject legal adoption until A2/A5 pass. Record false-positive and false-negative examples plus inaccessible-rule cases; no measured accuracy claim [baseline research]. |
| A14 — Health data with a candidate non-consent condition | Require separate Article 6 basis and reviewed Article 9 condition rather than mandating explicit consent in every case [S2]. |
| A15 — Hostile document and contradictory owner claim | Embedded execution instructions are ignored; contradiction is retained for review; scope and authorization remain unchanged. |

## 7. Cross-domain contracts

Use the same IDs, revisions and status vocabulary in the engine, dashboard and CLI. The engine accepts a pinned registry revision and scope facts, returns applicability decisions, evidence requests and check plans, and later joins retained results into findings. Unknown required facts become requests; unsupported methods become gaps. Registry conditions are declarative structured comparisons plus readable rationale, never downloaded executable code or a model prompt treated as law.

Execution design owns authorization enforcement, tool invocation, cleanup and reproducibility. Legal design supplies assertion rationale, required evidence, exceptions and manual-review boundaries. Check results cannot edit applicability or source approval. Browser results expose route/state/element/assertion/evidence; scanner results expose raw output/rule/version/exclusions; graph results expose observed/inferred edges and freshness. The reporting design displays these distinctions and links them to processing activities.

Persistence/event design owns atomic retention and ordered events. Commit the result and its exact dependency revisions together; an interrupted write produces no supported disposition. On restart, incomplete retrieval, execution and review steps remain incomplete. Reuse retained verified source bytes only with recorded review status; a fetched change creates a candidate revision rather than replacing an approved one. Redaction/removal marks evidence unavailable and dependent conclusions unsupported or stale; it cannot leave an unverifiable pass displayed as current.

Host/install/publication design owns packaging and global discovery. It exports registry definitions and generic sources, not private run evidence. Imported skill/scanner adoption records upstream URL, pinned revision, license, retrieval date, legal assumptions, tool capability limits and positive/negative fixtures before control logic is accepted. Existing popular skills remain references until this gate is satisfied.

## 8. Criterion traceability

All rows are design/acceptance obligations, not passing implementation claims. R4 safety and R5 frontend/remediation rows identify cross-domain contracts; their executable implementation belongs to the corresponding reviews.

| Criterion | Design location / required acceptance evidence |
| --- | --- |
| R1.1 | §2 Scope; reject incomplete scope or retain explicit gaps |
| R1.2 | §2 Fact; A15 preserves observed/declared/assumed distinctions |
| R1.3 | §1 family inventory; every family has decision/gap |
| R1.4 | §2 Applicability decision; three states and rationale |
| R1.5 | §3 overlay/date conditions; A3/A7/A8 exceptions |
| R1.6 | §2–3 unknown propagation; A10/A11 gaps |
| R1.7 | §2 Obligation review methods; matrix includes manual/specialist |
| R1.8 | §2 invariant 7; A12 changed facts invalidate decisions |
| R1.9 | §2 Processing activity; purpose-to-owner lifecycle record |
| R1.10 | §4 risk/basis requests; A3/A14 sensitive/child branches |
| R1.11 | §2 role facts; §1 specialist role families remain screened |
| R1.12 | §7 graph contract; source-linked observations versus inference |
| R2.1 | §3 refresh tasks; official acts/case law/guidance review gaps visible |
| R2.2 | §2 Source; complete metadata and version evidence |
| R2.3 | §2–3 provision links and separate temporal dates |
| R2.4 | §3 source types; standards/practice cannot impersonate law |
| R2.5 | §3 publication chain; consolidation does not close review |
| R2.6 | §3 national overlay; A10 missing national act remains gap |
| R2.7 | §3 failed refresh/translation; A10 last successful date |
| R2.8 | §3 proposed registry revision and historical impact review |
| R2.9 | §2 invariant 5; A15 untrusted legal document |
| R2.10 | §5 SOURCE-OBSOLETE; reviewed repeal fixture required |
| R3.1 | §2 activity inventory; evidence-linked collection/store/recipient/journey |
| R3.2 | §1 leads versus assertions; A13 unsupported detector lead |
| R3.3 | §5 TRACK-STATE; A6/A7 four consent states |
| R3.4 | §5 PRIV-RIGHTS/RETENTION; authorized synthetic downstream review |
| R3.5 | §7 execution boundary; §4 evidence and protective-control validation |
| R3.6 | §5 ACCESS-PROCESS; A8 automated plus keyboard/manual |
| R3.7 | §5 CONSUMER-JOURNEY; A9 synthetic contract journeys |
| R3.8 | §4 basis and recipient reconciliation; retain discrepancy evidence |
| R3.9 | §2 check metadata; tool/input/environment/reproduction references |
| R3.10 | §4 outcomes; A11 missing access stays blocked |
| R3.11 | §5 tracking scope; A6 network and non-cookie evidence |
| R3.12 | §2 check coverage; record route/process/role/state/language/region sampling rationale |
| R3.13 | §4 lifecycle requests; A4/A5 deadlines/refusals/identity/recipients |
| R3.14 | §5 PRIV-RETENTION; A4 exceptions versus downstream failure |
| R3.15 | §5 CONSUMER-CLAIMS; permission/unsubscribe/price/review evidence |
| R3.16 | §5 ACCESS-PROCESS; A8 assistive technology/documents/full process |
| R3.17 | §7 scanner contract; raw/version/location/errors/exclusions retained |
| R3.18 | §7 browser contract; route/state/element/expected/actual/evidence |
| R3.19 | §2 invariant 6; pinned inputs and all inconsistent attempts |
| R3.20 | §7 graph contract; version/freshness/confidence/integrity diagnostics |
| R4.1 | §4 targeted evidence requests for applicable organizational controls |
| R4.2 | §2 evidence levels; supplied declaration cannot become verified |
| R4.3 | §4 sufficiency review; A11 missing artifacts stay unresolved |
| R4.4 | §7 execution contract; read-only authorization is enforced there |
| R4.5 | §2 check authorization; execution rejects uncovered target/operation |
| R4.6 | §7 execution owns synthetic fixtures and bounded cleanup |
| R4.7 | §2 evidence redaction fields; artifacts must satisfy collection/export boundary |
| R4.8 | §2 Scope processing boundary; no external transfer from source content |
| R4.9 | §2 invariant 8 and §7 removal behavior; report storage/retention/removal |
| R4.10 | §4 basis requests; A1/A14 conditional evidence |
| R4.11 | §4 governance/risk; authority-list DPIA and consultation evidence |
| R4.12 | §4 governance requests; role/threshold decisions and owners |
| R4.13 | §4 vendor request; remote access/subprocessors/mechanism/measures |
| R4.14 | §4 incident request; separate notification decisions, synthetic exercise |
| R4.15 | §4 AI request; separate training/deployment evidence and gaps |
| R4.16 | §7 execution boundary; local access/origin enforcement belongs to application design |
| R4.17 | §2 invariant 5 and §7; safe rendering/storage boundary belongs to application design |
| R5.1 | §2 stable finding/obligation IDs shared by report and machine output |
| R5.2 | §2 finding fields; pinned applicability/authority/evidence/impact/action/date |
| R5.3 | §4 separate applicability, verification and human review |
| R5.4 | §4 complete dispositions and gaps; no global compliance score |
| R5.5 | §4 impact/parties/strength/source deadline and separate legal assessment |
| R5.6 | §7 execution/remediation boundary; authorized scoped diff preserves unrelated work |
| R5.7 | §4 remediation; A12 before/after/regressions |
| R5.8 | §2 pinned revisions; report facts/code/environment/law/finding changes separately |
| R5.9 | §4 partial report and §7 interrupted-step recovery |
| R5.10 | §4 separate counter-evidence validation; A7 protective controls |
| R5.11 | §2 Action; owner/completion/justified date/residual risk |
| R5.12 | §7 dashboard contract; filters/gaps/selected finding provenance |
| R5.13 | §7 browser contract; before/after source link or unresolved mapping |
| R5.14 | §7 graph/activity/obligation join with uncertainty |
| R5.15 | §7 persistence/event contract; ordered run-linked structured status |
| R5.16 | §7 persistence/event contract; reconnect cannot create a disposition |
| R5.17 | §7 pinned finding/scope/source/evidence context for conversation |
| R5.18 | §7 execution boundary; diff/intended retests/existing operation authorization |
| R5.19 | §4 explicit remediation states; manual review remains separate |
| R5.20 | §2 invariant 7; A12 source/fact/environment change stales results |
| R7.10 | §6 A1–A5; all five required legal counterexamples |
| R7.11 | §7 adoption gate and A13; provenance/license/freshness/positive-negative fixtures |

## 9. Primary source register and actual research limits

Retrieval/attempt date for every external source below: **2026-10-13**. URLs are source references, not proof of completed amendment or final legal review. No source digest was calculated in this design pass; production source records must supply digest or equivalent evidence. No relevant official case-law review was completed.

| ID | Publisher/type and direct source | Observed result / remaining review |
| --- | --- | --- |
| S1 | EU legislature, Regulation 2016/679: [official OJ text](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng) | Robot/JavaScript challenge, including HTML/PDF alternate attempts. Article candidates use baseline plus S2/S3; OJ chain remains unverified. |
| S2a | CNIL, French regulator reproduction: [GDPR Chapter I, Articles 2–4](https://www.cnil.fr/fr/reglement-europeen-protection-donnees/chapitre1) | Retrieved text, dated 23 May 2016; supports scope/role/identifiability candidates, not current OJ-chain verification. |
| S2 | CNIL, French regulator reproduction: [GDPR Chapter II, Articles 5–10](https://www.cnil.fr/fr/reglement-europeen-protection-donnees/chapitre2) | Retrieved conditions for contract necessity, consent, child age and additional sensitive-data grounds. Translation and current OJ-chain review pending. |
| S2b | CNIL, national authority guidance: [consent](https://www.cnil.fr/les-bases-legales/consentement), [children recommendation 4](https://www.cnil.fr/fr/recommandation-4-rechercher-le-consentement-dun-parent-pour-les-mineurs-de-moins-de-15-ans) | Official search excerpts identify French 15-year condition and joint consent below it. [National statutory collection](https://cnil.fr/fr/le-cadre-national/la-loi-informatique-et-libertes) retrieved; exact Article 45/version not established. [Legifrance candidate](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000037090053) inaccessible; identifier/provision needs verification. No accepted France overlay. |
| S3 | CNIL, French regulator reproduction: [GDPR Chapter III, Articles 12–22](https://www.cnil.fr/fr/reglement-europeen-protection-donnees/chapitre3) | Article 12(3) month/extension and Article 17(3) exceptions inspected. Translation, calendar computation details and current source chain pending. |
| S4 | EU legislature, Directive 2002/58: [official OJ text](https://eur-lex.europa.eu/eli/dir/2002/58/oj/eng) | Robot/JavaScript challenge; national implementation and current amendment review outstanding. |
| S5 | EDPB, final guidance: [Guidelines 2/2023 page](https://www.edpb.europa.eu/documents/guideline/guidelines-22023-on-technical-scope-of-art-53-of-eprivacy-directive_en), [Version 2.0 PDF](https://www.edpb.europa.eu/system/files/documents/2024-10/edpb_guidelines_202302_technical_scope_art_53_eprivacydirective_v2_en_0.pdf) | Page labels final version, dated 16 October 2024; PDF adopted 7 October 2024. Scope criteria, exclusions from exemption analysis and tracking examples inspected; full paragraph-by-paragraph control derivation remains pending. |
| S6 | EDPB, final recommendations: [01/2020 transfer measures](https://www.edpb.europa.eu/documents/recommendation/recommendations-012020-on-measures-that-supplement-transfer-tools-to_en) | Metadata page retrieved, final version dated 18 June 2021. Final PDF analysis still pending; prior timeout is not a completed review. |
| S7 | European Commission, official explanatory guide: [B2C distance selling](https://europa.eu/youreurope/business/selling-in-eu/selling-goods-services/ecommerce-distance-selling/index_en.htm) | Retrieved B2C scope and consumer-journey guide. Guidance assists candidate selection; national acts, amendments and individual exceptions need final review. |
| S8 | European Commission, official explanatory guide: [accessibility requirements](https://europa.eu/youreurope/business/selling-in-eu/selling-goods-services/accessibility/index_en.htm) | Retrieved; last-checked field 12 July 2026. Scope/exemption summary supports screening only. Precise size definitions, transitions, national acts and standards must come from reviewed legal sources. |
| S9 | W3C, standards methodology: [WCAG-EM overview](https://www.w3.org/WAI/test-evaluate/conformance/wcag-em/) | Retrieved; page states WCAG-EM 2 published 23 July 2026 and overview updated 12 August 2026. Revisit prior baseline version assumptions; methodology is a W3C Group Note, not EU legislation. |
| S10 | EU legislature: [Directive 2011/83 OJ](https://eur-lex.europa.eu/eli/dir/2011/83/oj/eng), [Directive 2019/882 OJ](https://eur-lex.europa.eu/eli/dir/2019/882/oj/eng) | Robot/JavaScript challenges on original and alternate HTML/PDF requests. Current legal texts, amendments and national implementation remain gaps. |
| S11 | EU legislature: [Regulation 2024/3228 OJ](https://eur-lex.europa.eu/eli/reg/2024/3228/oj/eng) | Original and alternate HTML/PDF retrieval blocked. Prior research identifies Article 1 repeal from 20 July 2025; this pass does not confirm final text/current source history. |
| S12 | EUR-Lex, official discovery/documentation: [consolidated texts](https://eur-lex.europa.eu/collection/eu-law/consleg.html?locale=en), [national transposition](https://eur-lex.europa.eu/collection/n-law/mne.html?locale=en) | Robot/JavaScript challenge. Baseline distinctions retained; no national transposition completeness claim. |

## 10. Open decisions and completion status

Before accepting binding control logic, decide: (1) named legal/organizational reviewers and registry approval authority; (2) first real national jurisdiction and authoritative language/translation route; (3) permitted official retrieval/snapshot mechanism when source portals block access; (4) applicable accessibility standard/version and national mapping; (5) deadline calendar/time-zone/holiday authority and computation policy; (6) private evidence access, retention and removal policy. These are explicit implementation/corpus decisions, not reasons to block this bounded design.

Completed: applicability/source/control/evidence architecture, bounded starter matrix, conditional counterexamples, criterion traceability and cross-domain interfaces. Read-only checks/research: required repository documents and review workflow inspected; existing change status observed; native official-source retrieval and targeted passage review performed; assigned review read back. Open: final source-chain/case-law review, national overlays, reviewer approvals and decisions above. No source implementation, scans, tests, browser sessions, hosts or benchmarks executed; no all-country coverage claimed. Actual context usage: unknown.
