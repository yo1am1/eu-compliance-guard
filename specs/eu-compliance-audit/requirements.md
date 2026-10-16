# EU compliance audit — requirements

Status: **requirements approved by the user on 2026-10-13; design pending**.  
Prepared: 2026-10-11; strengthened after external coverage research on the same date; expanded for the local audit application on 2026-10-13.  
Research: [source review, gaps and comparable workflows](research.md).  
Destination: [yo1am1/agentic-setup](https://github.com/yo1am1/agentic-setup).

## Introduction

EU_Compliance_Guard is a local audit application with a shared executable engine and portable agent skills, workflows and host integrations. It enables coding agents to investigate a project's applicable EU obligations using current official sources, verify implementation and operational evidence, and produce a traceable audit with prioritized remediation. Its frontend lets the owner inspect failures, source and browser Evidence, discuss Findings with an agent, and follow authorized fixes and retests in real time. Repository scanners and Graphify support discovery; reproducible assertions and retained Evidence establish technical outcomes. The application combines repository, browser, API, configuration, document and organizational checks. It will be maintained in agentic-setup, implemented by a visible Herdr team after specification approval, and installed for global use across the coding-agent CLIs available on this laptop.

## Goals

| Goal | Observable completion evidence |
| --- | --- |
| G1 — Establish scope and applicable obligations | Project facts, jurisdiction decisions and an obligation register with explicit coverage gaps. |
| G2 — Keep legal conclusions current | Dated official sources, article-level references, amendment/application-date review and recorded research failures. |
| G3 — Verify implementation and operations | Reproducible technical checks plus document/manual-review outcomes tied to each applicable obligation. |
| G4 — Inspect findings and verify fixes interactively | A usable local frontend, evidence-linked agent conversation, live execution status and retained before/after check results shared with CLI reports. |
| G5 — Provide global CLI access | One maintained canonical skill/toolkit with verified discovery and a synthetic audit in each inventoried agent CLI. |
| G6 — Implement through a visible team and publish | Reviewed Herdr work, passed acceptance checks, protected existing work and a verified scoped GitHub publication. |

These are product goals, not an implementation task list. Design and owner-assigned tasks follow requirements approval.

## Glossary

- **EU_Compliance_Guard**: The local audit application, shared executable engine and portable agent integrations.
- **Audit_Scope**: Recorded project, environments, activities, organizational roles, jurisdictions, assessment date, authorized operations and excluded areas.
- **Obligation**: A sourced requirement or explicitly classified recommendation with applicability conditions and an evidence/check method.
- **Legal_Source**: An official legal text, amendment, judgment, regulator publication or standard reference, with authority and temporal status recorded.
- **Evidence**: A retained observation or supplied document supporting an applicability decision, technical result or organizational review.
- **Finding**: A traceable assessment linking an Obligation to Evidence, verification status, impact and any remediation.
- **Host_CLI**: An installed coding-agent CLI that can load the skill or invoke its tools through a documented adapter.
- **Canonical_Package**: The maintained application, engine and agent-integration source in agentic-setup; generated host adapters do not independently define audit behavior.
- **Herdr_Team**: Visible native agents in Herdr with named assignments, disjoint writer scopes and a coordinating supervisor.
- **Audit_Run**: An identified execution tied to project inputs, code/environment versions, scope, legal-source versions, check results and ordered progress events.

## Scope and working assumptions

The initial supported project classes are websites, web applications, SaaS, e-commerce, hosting/platform services and AI-enabled software. Assessment includes organizational data processing supporting these services, not only the public frontend. A complete audit means every identified applicable Obligation in the declared Audit_Scope has a disposition and the report exposes unresolved scope or evidence gaps; it does not mean every obligation can be proven by software.

All EU Member States are eligible jurisdictions. Research and national overlays are selected by project facts; an unavailable or unverified national overlay remains an explicit gap. EEA extensions and non-EU regimes such as the UK or Switzerland require separately identified legal bases and must not be silently treated as EU law.

The initial legal-domain register must include the following families as **applicability candidates**, not blanket obligations or an assertion of a vetted rule catalog:

- GDPR: processing roles, lawful bases, transparency, minimization, rights, retention, security, vendors, transfers, accountability and risk assessments.
- ePrivacy and national implementations: device storage/access, tracking and electronic marketing.
- Online-service identity and commercial disclosures.
- Consumer contracts, digital content/services, subscriptions, pricing, withdrawal, refunds, unfair terms and commercial practices.
- Accessibility requirements for covered services/products.
- Intermediary, hosting and platform responsibilities, including the DSA; marketplace or gatekeeper rules where relevant.
- AI Act responsibilities according to activity, role and risk classification.
- Cybersecurity and software-product responsibilities, including NIS2 and the Cyber Resilience Act where relevant.
- Connected-product/data-processing responsibilities, including the Data Act where relevant.
- Copyright, content permissions and software/asset licensing.
- Additional sector or national rules discovered from facts, including financial, health, employment, children and product-safety contexts; unsupported specialist review must be exposed.

The earlier web conversation described an 88-rule reference catalog and one repository probe. Its archive and original screenshot have not been inspected here; their content is not accepted as verified coverage, and the rule count is not an acceptance target.

### Local application and owner journey

The owner selects an authorized repository and, when available, its local/test URL; establishes scope; starts an audit; inspects Findings and their evidence; asks the agent for an explanation or scoped remediation; and watches the affected checks rerun. The frontend must expose the tested page or element, relevant source location when established, legal/control rationale, missing evidence and verified before/after results. A repository map can show relationships among source files, processing activities, controls and Findings, with observed and inferred relationships distinguishable.

Technical determinism means a declared assertion against recorded inputs and versions can be rerun and its expected/actual results inspected. It does not mean every legal interpretation, organizational control or accessibility requirement is automatically decidable. An agent assertion, generated graph edge or successful patch application cannot independently close a Finding.

One shared engine and result model serve the frontend and CLI integrations. The initial application runs locally; audit state and private artifacts remain outside public package exports. Design must identify separate application/engine paths while retaining the existing canonical .agents library and its provenance conventions.

### Initial host inventory

The following executables were found on PATH on 2026-10-11. Presence is not proof of authentication, native skill support or successful global discovery.

| Host_CLI | Executable | Requirement |
| --- | --- | --- |
| Codex | codex | Global discovery and synthetic audit verification. |
| Claude Code | claude | Global discovery and synthetic audit verification. |
| AGY | agy | Verify its actual host conventions; then global discovery and synthetic audit verification. |
| Gemini CLI | gemini | Global discovery and synthetic audit verification. |
| GitHub Copilot CLI | copilot | Global discovery and synthetic audit verification. |
| Cursor Agent | cursor-agent | Global discovery and synthetic audit verification. |
| Pi | pi | Global discovery and synthetic audit verification. |

Implementation discovery must check for additional installed coding-agent CLIs and relevant aliases. Herdr is the team coordinator; Ollama was also detected as a model runner and is not counted as a coding-agent skill host without an identified orchestration mechanism. Missing, blocked or unsupported host verification prevents a claim that installation across all available Host_CLIs is complete.

## Requirements

### Requirement 1 — Project facts, legal applicability and coverage

**User Story:** As a project owner, I want the agent to establish which obligations apply to my real service, so that its audit covers my exposure without assuming every law applies to every application.

#### Acceptance Criteria

1. WHEN an audit starts, THE EU_Compliance_Guard SHALL record an Audit_Scope covering project/environment identity, assessment date, activities, processing roles, markets, establishment, customer types, relevant size/sector facts and permitted operations.
2. WHEN project facts are derived from code or documents, THE EU_Compliance_Guard SHALL distinguish observed facts from owner declarations and unresolved assumptions.
3. WHEN assessing applicability, THE EU_Compliance_Guard SHALL evaluate every legal-domain family listed in the scope register.
4. WHEN evaluating an Obligation, THE EU_Compliance_Guard SHALL record applicability as applicable, not applicable or unresolved with its factual and legal rationale.
5. WHEN an exemption, phased provision or national rule affects an Obligation, THE EU_Compliance_Guard SHALL retain the condition and supporting Legal_Source in its applicability decision.
6. IF a fact, jurisdiction or specialist domain cannot be established, THEN THE EU_Compliance_Guard SHALL expose the missing decision as a coverage gap rather than infer non-applicability.
7. WHEN an applicable Obligation is identified, THE EU_Compliance_Guard SHALL assign a technical, document, organizational or specialist review method.
8. WHEN project facts or Audit_Scope change, THE EU_Compliance_Guard SHALL mark affected applicability decisions for reassessment.
9. WHEN documenting personal-data processing, THE EU_Compliance_Guard SHALL map each activity to its purpose, data subjects/categories, processing roles, declared lawful basis, recipients, locations, retention and Evidence owner.
10. WHERE children, vulnerable individuals, special-category/criminal-offence data, biometrics, location monitoring or profiling are present, THE EU_Compliance_Guard SHALL assess their additional conditions and safeguards against the relevant EU and national sources.
11. WHERE an activity has distinct regulatory roles or thresholds, THE EU_Compliance_Guard SHALL assess its actual provider/deployer, controller/processor, hosting/platform or product/service role before selecting the corresponding control set.
12. WHEN mapping an authorized repository, THE EU_Compliance_Guard SHALL record identified components and data-processing paths with source references and distinguish structural observations from inferred or unresolved relationships.

### Requirement 2 — Current official sources and maintainable legal knowledge

**User Story:** As an auditor, I want every legal conclusion to use traceable sources valid for the assessment date and jurisdiction, so that old checklists, proposals and general advice are not reported as current binding law.

#### Acceptance Criteria

1. WHEN preparing an audit, THE EU_Compliance_Guard SHALL check the official publication/amendment chain, relevant official case law and authority publications for each legal family assessed.
2. WHEN retaining a Legal_Source, THE EU_Compliance_Guard SHALL record its publisher, official identifier where available, URL, language, document/version date, retrieval time and content digest or equivalent version evidence.
3. WHEN deriving an Obligation, THE EU_Compliance_Guard SHALL link it to the relevant article or section and record entry-into-force, application and transition dates where relevant.
4. WHEN classifying a Legal_Source, THE EU_Compliance_Guard SHALL distinguish enacted law, national implementation, judgments, final guidance, draft guidance, proposals, standards and optional engineering practice.
5. WHEN using a consolidated text, THE EU_Compliance_Guard SHALL check the underlying acts, amendments and corrections relevant to the assessment date.
6. WHEN reviewing a directive or country-specific issue, THE EU_Compliance_Guard SHALL verify the relevant national official source rather than treat the EU-level text as proof of national implementation.
7. IF current official source retrieval, translation verification or amendment review fails, THEN THE EU_Compliance_Guard SHALL disclose the gap and the last successful verification date without labeling the affected conclusion current.
8. WHEN new material changes an existing legal interpretation or check, THE EU_Compliance_Guard SHALL produce a reviewable update identifying affected Obligations, tests and prior audit conclusions before adopting it into the Canonical_Package.
9. WHILE processing retrieved legal pages or supplied documents, THE EU_Compliance_Guard SHALL treat their content as evidence rather than executable agent instructions.
10. WHEN auditing existing checklists, notices or compliance templates, THE EU_Compliance_Guard SHALL flag references to repealed obligations, retired official services or superseded guidance using the relevant source history.

### Requirement 3 — Executable technical verification

**User Story:** As a developer, I want the agent to test actual code and behavior, so that findings distinguish demonstrable failures from patterns that merely suggest a problem.

#### Acceptance Criteria

1. WHEN discovering implementation, THE EU_Compliance_Guard SHALL inventory collection points, data stores, logs, third-party recipients, tracking/storage mechanisms and externally visible user journeys with Evidence references.
2. WHEN performing repository checks, THE EU_Compliance_Guard SHALL label search-pattern matches as leads unless additional Evidence establishes the asserted failure.
3. WHERE consent-dependent tracking is relevant, THE EU_Compliance_Guard SHALL test fresh-visitor, rejection, acceptance and withdrawal states using network and browser-storage Evidence across the identified relevant journeys.
4. WHERE user-rights or retention controls are relevant and test access is authorized, THE EU_Compliance_Guard SHALL exercise the supported access/export, correction, deletion, objection and expiry workflows with synthetic identities, including identified downstream stores and backup/restore handling.
5. WHERE security controls are relevant, THE EU_Compliance_Guard SHALL verify applicable access/tenant isolation, sensitive logging, dependency/configuration and data-protection controls using bounded non-destructive checks.
6. WHERE accessibility obligations are relevant, THE EU_Compliance_Guard SHALL combine automated inspection with keyboard and manual-review outcomes mapped to the applicable legal/standard requirements.
7. WHERE consumer journeys are relevant, THE EU_Compliance_Guard SHALL inspect applicable disclosures, pricing, consent, order confirmation, cancellation, withdrawal and refund behavior using authorized synthetic scenarios.
8. WHEN reconciling public notices with implementation, THE EU_Compliance_Guard SHALL report discrepancies between documented practices and observed data flows or controls.
9. WHEN executing a check, THE EU_Compliance_Guard SHALL retain its tool/version, inputs, environment, result and reproducible steps or assertions.
10. IF a required tool, permission, test environment or data source is unavailable, THEN THE EU_Compliance_Guard SHALL record a blocked or not-tested outcome rather than a passed check.
11. WHEN investigating tracking, THE EU_Compliance_Guard SHALL include identified pixels, link identifiers, fingerprinting, browser storage, SDKs and server-side forwarding rather than use cookie presence as the sole tracking indicator.
12. WHEN planning runtime coverage, THE EU_Compliance_Guard SHALL record the included and excluded routes, complete user processes, identities/roles, consent states, languages and regional variants with a risk-based sampling rationale.
13. WHERE rights-request procedures apply, THE EU_Compliance_Guard SHALL assess request receipt, proportionate identity verification, source-based response deadlines/extensions, restriction/objection handling, justified refusals and applicable recipient notification Evidence.
14. WHEN evaluating erasure or expiry, THE EU_Compliance_Guard SHALL distinguish justified retention exceptions from unfinished deletion across primary, derived, cache, index, log and backup/restore paths.
15. WHERE consumer marketing or commerce controls apply, THE EU_Compliance_Guard SHALL inspect the relevant discount/review claims, recurring charges, optional extras, electronic-marketing permissions and withdrawal/unsubscribe routes against sourced rules.
16. WHERE accessibility obligations apply, THE EU_Compliance_Guard SHALL expose manual assistive-technology, downloadable-document and complete-process checks remaining outside automated results.
17. WHEN importing scanner output, THE EU_Compliance_Guard SHALL retain tool/rule versions, source locations, raw result references, execution errors and coverage exclusions before mapping candidates to Obligations or confirmed Findings.
18. WHEN reporting a browser-observed failure, THE EU_Compliance_Guard SHALL retain its route, tested state, locator or affected element, assertion, expected/actual outcome and relevant DOM, screenshot or network Evidence.
19. WHEN claiming a technical check is reproducible, THE EU_Compliance_Guard SHALL record its fixture, configuration, environment and input versions and expose inconsistent reruns or retries rather than silently choose a passing attempt.
20. WHEN using Graphify or another repository graph, THE EU_Compliance_Guard SHALL retain its producer/schema version, input freshness, source locations, confidence classification and available integrity diagnostics without treating inferred edges as proof of runtime behavior or legal compliance.

### Requirement 4 — Organizational evidence and audit safety

**User Story:** As a project owner, I want the audit to include obligations outside source code while protecting data and services, so that technical verification does not create new exposure or misrepresent real operations.

#### Acceptance Criteria

1. WHEN an applicable Obligation requires organizational evidence, THE EU_Compliance_Guard SHALL request the relevant declarations or artifacts for purposes/lawful bases, processing records, vendor agreements, transfer safeguards, retention, incident response and governance as applicable.
2. WHEN assessing owner-supplied Evidence, THE EU_Compliance_Guard SHALL record whether it is declared, documented or independently verified.
3. IF provided operational documents do not establish the required control, THEN THE EU_Compliance_Guard SHALL retain an unresolved review outcome with the missing evidence identified.
4. WHEN an audit runs without mutation authorization, THE EU_Compliance_Guard SHALL limit operations to read-only investigation and non-destructive observation.
5. WHEN a check requires account/data mutation, external messages, real purchases, active security probes or production operations, THE EU_Compliance_Guard SHALL require authorization covering the target and operation before execution.
6. WHEN test-data mutation is authorized, THE EU_Compliance_Guard SHALL use isolated synthetic fixtures with defined cleanup that does not remove pre-existing records.
7. WHEN collecting or exporting Evidence, THE EU_Compliance_Guard SHALL redact credentials, authentication tokens and unnecessary personal data from logs, screenshots, traces and reports.
8. WHEN providing repository data or Evidence to an external model/service, THE EU_Compliance_Guard SHALL honor the recorded processing boundary and avoid transferring data outside that authorization.
9. WHEN an audit ends, THE EU_Compliance_Guard SHALL state Evidence storage, retention and removal behavior so that audit artifacts remain outside public package exports unless explicitly selected for publication.
10. WHEN assessing a declared lawful basis, THE EU_Compliance_Guard SHALL request the corresponding necessity, legitimate-interest balancing, consent proof or additional special-category condition Evidence instead of assuming consent authorizes every processing activity.
11. WHEN screening processing risk, THE EU_Compliance_Guard SHALL record the DPIA decision using applicable authority lists and risk factors, including assessment and prior-consultation review where required.
12. WHEN assessing GDPR governance, THE EU_Compliance_Guard SHALL record applicability and Evidence for processing records, a data protection officer, an EU representative, competent supervisory authority and accountable control owners.
13. WHERE vendor sharing or international transfer occurs, THE EU_Compliance_Guard SHALL assess actual processing/remote-access locations, subprocessor arrangements, transfer mechanisms and any required transfer assessment or supplementary measures.
14. WHERE incident-response duties apply, THE EU_Compliance_Guard SHALL review awareness/decision records, separate authority and individual notification thresholds, applicable deadlines and synthetic exercise Evidence without sending real notifications.
15. WHERE AI systems process personal data, THE EU_Compliance_Guard SHALL assess development/training and operational use separately, including sourced data provenance, reuse, provider retention/training settings and rights-handling Evidence for datasets or derived artifacts.
16. WHEN serving the local application, THE EU_Compliance_Guard SHALL restrict access to the local machine by default, reject unauthorized origins and enforce the authorized repository, test-target and operation boundaries on every executable action.
17. WHEN displaying or serving imported code, documents, scanner output or audit artifacts, THE EU_Compliance_Guard SHALL render untrusted content safely and prevent access outside the authorized project and Evidence storage boundaries.

### Requirement 5 — Findings, visual review, live progress and remediation

**User Story:** As a developer or reviewer, I want to inspect evidence-backed Findings in a frontend, discuss them with an agent and follow verified fixes live, so that I can act on failures and understand what remains uncertain.

#### Acceptance Criteria

1. WHEN producing a report, THE EU_Compliance_Guard SHALL provide a human-readable audit and a machine-readable result with stable Obligation/Finding identifiers.
2. WHEN reporting a Finding, THE EU_Compliance_Guard SHALL include applicability, legal authority/type, Evidence, verification method/status, impact, remediation or review action and the assessment date.
3. WHEN summarizing verification, THE EU_Compliance_Guard SHALL distinguish passed checks, observed failures, unresolved human review, blocked execution and not-tested checks separately from applicability.
4. WHEN closing an audit, THE EU_Compliance_Guard SHALL show the disposition of every registered Obligation and all remaining coverage gaps without replacing them with a global compliance score or legal certification.
5. WHEN prioritizing Findings, THE EU_Compliance_Guard SHALL explain the impact, affected parties, evidence strength and relevant legal deadline without presenting an automated technical lead as a definitive legal ruling.
6. WHEN remediation is authorized, THE EU_Compliance_Guard SHALL produce a scoped reviewable patch while preserving unrelated files, production data and existing user changes.
7. WHEN recording a fix as verified, THE EU_Compliance_Guard SHALL retain before/after Evidence from rerunning the affected checks plus relevant regression checks.
8. WHEN comparing audits, THE EU_Compliance_Guard SHALL identify changes in project facts, code, deployed environment, legal sources and Findings separately.
9. IF an execution/time budget expires or a run is cancelled, THEN THE EU_Compliance_Guard SHALL preserve completed Evidence and identify unfinished checks in a resumable partial report without marking the audit complete.
10. WHEN confirming a material failure, THE EU_Compliance_Guard SHALL retain a separate validation result that challenges the claimed impact against observed protective controls, counter-evidence and the applicable legal condition.
11. WHEN issuing a remediation plan, THE EU_Compliance_Guard SHALL identify the responsible owner, completion condition, target date where justified and unresolved residual risk for each action.
12. WHEN displaying the audit frontend, THE EU_Compliance_Guard SHALL provide a Findings list with status/impact filters, coverage gaps and a selected-Finding view linking its control, Legal_Source, Evidence and remediation history.
13. WHEN a Finding concerns frontend behavior, THE EU_Compliance_Guard SHALL display its captured page/element and before/after Evidence with established source links or an explicit unresolved source mapping.
14. WHEN displaying a repository map, THE EU_Compliance_Guard SHALL allow the owner to trace a Finding to its identified components, processing activity and Obligation while preserving source provenance and relationship uncertainty.
15. WHEN an Audit_Run makes progress, THE EU_Compliance_Guard SHALL expose ordered, run-identified events for check execution, Findings, agent actions, patch application and retest results without using conversational text as the authoritative status.
16. WHEN the frontend reconnects or reloads, THE EU_Compliance_Guard SHALL restore retained progress and Findings without duplicating events or applying updates to the wrong project or Audit_Run.
17. WHEN the owner discusses a Finding with the agent, THE EU_Compliance_Guard SHALL provide that Finding, scope, relevant sources and Evidence as context and link the response and executable actions back to the same Audit_Run.
18. WHEN an agent proposes remediation, THE EU_Compliance_Guard SHALL expose the affected files, reviewable diff and intended retests and execute only within existing authorization or a newly granted target/operation scope.
19. WHEN displaying remediation progress, THE EU_Compliance_Guard SHALL distinguish proposed, running, applied-awaiting-verification, verified, failed and blocked states and retain required manual review separately.
20. WHEN code, deployed state, project facts, relevant graph inputs or Legal_Source versions change, THE EU_Compliance_Guard SHALL mark affected conclusions stale or awaiting reassessment and prevent an earlier passing result from being represented as verification of the changed state.

### Requirement 6 — Shared local application and portable global CLI integration

**User Story:** As the laptop owner, I want the local application and every available coding-agent CLI to use the same maintained EU audit capability, so that I can inspect and act on consistent rules and results across projects.

#### Acceptance Criteria

1. WHEN preparing global installation, THE EU_Compliance_Guard SHALL inventory installed Host_CLIs and record their versions, supported instruction/tool mechanisms and verification state.
2. WHEN packaging the capability, THE EU_Compliance_Guard SHALL retain one Canonical_Package with portable instructions in agentic-setup's canonical .agents layer and separately identified engine/application paths using the repository's provenance, manifest and validation conventions where applicable.
3. WHEN integrating a Host_CLI, THE EU_Compliance_Guard SHALL use its documented skill discovery mechanism or a documented adapter that provides access to the same audit workflow and executable tools.
4. WHEN installing globally, THE EU_Compliance_Guard SHALL make the capability available from repositories outside agentic-setup without copying private audit Evidence into global instructions.
5. WHEN installation is applied or repeated, THE EU_Compliance_Guard SHALL preserve unrelated host settings, skills and authentication without creating duplicate competing audit definitions.
6. WHEN upgrading or removing the installation, THE EU_Compliance_Guard SHALL affect only managed package/adapter paths and preserve user edits or report a conflict.
7. WHEN testing a Host_CLI integration, THE EU_Compliance_Guard SHALL demonstrate actual host discovery and a read-only synthetic audit with sourced Findings or explicit unresolved-source outcomes.
8. IF a detected Host_CLI cannot complete discovery or the synthetic audit, THEN THE EU_Compliance_Guard SHALL report the blocker and withhold the claim that all installed hosts are supported.
9. WHEN selecting audit tools in a Host_CLI, THE EU_Compliance_Guard SHALL expose missing tool capabilities and installation requirements rather than assume that copying SKILL.md installs an executable audit runtime.
10. WHEN the frontend and a Host_CLI operate on the same project, THE EU_Compliance_Guard SHALL use the same executable checks, identifiers, permissions, result model and retained Audit_Run state rather than maintain separate compliance logic.
11. WHEN the owner starts the local application, THE EU_Compliance_Guard SHALL support authorized repository/test-URL selection and audit review without requiring a hosted account or commercial platform subscription.
12. WHEN the local process restarts, THE EU_Compliance_Guard SHALL preserve completed Audit_Run results and resumable metadata while identifying interrupted actions and invalidating obsolete execution claims.
13. IF current legal research or an agent provider is unavailable, THEN THE EU_Compliance_Guard SHALL keep retained Findings and Evidence inspectable while showing the blocked capabilities and source-verification dates.
14. WHEN the owner uses the dashboard, THE EU_Compliance_Guard SHALL support keyboard navigation, visible focus, accessible names and status announcements and provide status meaning independently of color.

### Requirement 7 — Visible implementation team and public repository delivery

**User Story:** As the owner, I want the approved plan implemented by a visible Herdr team and published to my repository, so that I can inspect contributions and use a reviewed, reproducible package.

#### Acceptance Criteria

1. WHEN implementation begins, THE Herdr_Team SHALL work from approved requirements, design and an owner-assigned task plan.
2. WHEN delegating work, THE Herdr_Team SHALL use visible native Herdr agents with named assignments and disjoint writer scopes rather than hidden collaboration workers.
3. WHEN the supervisor integrates worker changes, THE Herdr_Team SHALL review the full relevant diff and the worker's scoped verification evidence before shared acceptance checks.
4. WHEN a Codex team member's actual context usage exceeds 230000 tokens, THE Herdr_Team SHALL save a bounded handoff and use native compaction without clearing or resetting the conversation; unavailable usage counts SHALL remain explicitly unknown rather than estimated.
5. WHEN accepting the toolkit, THE Herdr_Team SHALL verify synthetic cases for an observed control failure, a passing control, unresolved applicability, stale/unavailable law, missing tool/access, an organizational evidence gap and a verified remediation without converting any blocked case into success.
6. WHEN preparing publication, THE Herdr_Team SHALL pass the repository's required packaging checks and the new audit/host acceptance checks, with measured outcomes and explicit omissions.
7. WHEN publishing to yo1am1/agentic-setup, THE Herdr_Team SHALL select only reviewed capability/specification changes while preserving pre-existing unrelated edits and history.
8. WHEN preparing the public package, THE Herdr_Team SHALL exclude secrets, private documents, laptop/session handovers, audit outputs and user-specific provider configuration.
9. WHEN completing publication, THE Herdr_Team SHALL verify the remote revision and provide the resulting GitHub link plus the globally installed package version and host verification results.
10. WHEN validating legal-rule behavior, THE Herdr_Team SHALL include synthetic counterexamples for an applicable non-consent lawful basis, pseudonymized/encrypted personal data, national age variation, justified erasure exceptions and calendar-month rights deadlines.
11. WHEN evaluating an imported skill or scanner, THE Herdr_Team SHALL verify its provenance, license, source freshness and false-positive/false-negative behavior before adopting its control logic or claiming measured coverage.
12. WHEN accepting the first application milestone, THE Herdr_Team SHALL demonstrate a complete synthetic repository/browser audit in the dashboard, an evidence-linked agent conversation, an authorized scoped patch, live progress and a retained before/after retest shared with a CLI integration.
13. WHEN validating application integration, THE Herdr_Team SHALL verify reconnect/reload recovery, duplicate or stale events, interrupted execution, conflicting source edits, stale graph/check results and tool failures without falsely closing Findings.

## Boundaries

- This is a complete audit workflow within an explicit scope, not a guarantee against litigation or a substitute for unresolved specialist/legal judgments.
- Organizational or manual-review checks are part of completeness; they are not automatically passed by technical scanners.
- A local audit frontend, shared engine, repository/scanner integration and evidence-linked agent interaction are now required scope. A hosted service, paid subscription, separate graph database or new agent framework requires a demonstrated design need and corresponding scope approval.
- Requirements creation does not execute an audit, launch implementation agents, alter global host configuration, publish policies or push this draft.
- The existing commerce-assistant app and its separate specification remain outside this toolkit's source ownership.
- Existing agentic-setup modifications are preserved; no replacement of full upstream instructions or licensing is authorized.

## Official source entry points

These are research entry points, not a reviewed corpus of all applicable law. Individual Obligation citations and current status must be verified during corpus construction and each relevant audit refresh.

- [EUR-Lex: EU legal documents and metadata](https://eur-lex.europa.eu/content/welcome/about.html?locale=en).
- [EUR-Lex: consolidated texts and their documentation status](https://eur-lex.europa.eu/collection/eu-law/consleg.html?locale=en).
- [EUR-Lex: national transposition measures](https://eur-lex.europa.eu/collection/n-law/mne.html?locale=en).
- [EDPB: documents and guidance](https://www.edpb.europa.eu/documents_en).
- [EDPB: public consultations](https://www.edpb.europa.eu/public-consultations_en).
- [European Commission: implementing EU law](https://commission.europa.eu/law/application-eu-law/implementing-eu-law_en).

EUR-Lex describes consolidated texts as documentation without legal effect and provides national transposition records. EDPB distinguishes regulator publications and public consultations. These source distinctions motivate Requirement 2; this document does not fix legal deadlines based on the earlier web answer.

## Review points

The draft assumes a local audit application and shared portable engine for the listed digital-service project classes, with all relevant EU jurisdictions researched on demand. Requirements approval confirms these goals and boundaries; design will settle application/engine repository paths, data and event formats, persistence, source retrieval/cache policy, the agent/CLI bridge, frontend layout, Graphify/scanner choices, execution budgets, writer scopes and release mechanics. The first delivery proves the complete scan–inspect–discuss–fix–retest loop on synthetic fixtures; broader legal-domain and host coverage follows as explicitly measured work. No country is considered verified merely because it appears in the jurisdiction inventory.
