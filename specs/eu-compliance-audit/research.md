# EU compliance audit — external coverage review

Date: 2026-10-11. Scope: compare the requirements draft with regulator guidance, audit methodology and publicly available agent skills. This is specification research, not an audit of a live service or validation of every EU country's law.

## Conclusion

The initial draft covered the principal digital-service legal families, but its broad categories did not make every necessary audit control explicit. The changes below turn identified gaps into acceptance criteria. Coverage still requires a sourced obligation/control matrix, country verification and executable/manual evidence in the later implementation; a larger requirement count alone establishes none of those.

## Coverage changes

| Gap or under-specified control | Requirements affected | Research basis |
| --- | --- | --- |
| Processing activity ownership, full data lifecycle, role distinctions | 1.9, 1.11 | EDPB accountability guidance; CNIL developer guide; Commission AI classification workflow. |
| Children, special-category/criminal-offence data, profiling and vulnerable individuals | 1.10, 7.10 | GDPR Articles 8–10 and 22; context-dependent safeguards must replace blanket rules. |
| Current case law and removal of obsolete requirements | 2.1, 2.10 | Official legal text/status review; the ODR repeal is a concrete dated regression case. |
| Tracking beyond cookies and explicit sampling boundaries | 3.11–3.12 | EDPB technical ePrivacy guidance; W3C evaluation methodology. |
| Rights-request procedures and retention exceptions | 3.13–3.14 | GDPR Articles 12–22; CNIL data-lifecycle guidance. |
| Detailed commercial claims and whole-process accessibility | 3.15–3.16 | Your Europe consumer guide; W3C WCAG-EM. |
| Lawful-basis evidence, DPIA screening and governance roles | 4.10–4.12 | GDPR Articles 6, 9, 27, 30 and 35–39; EDPB guidance. |
| Actual transfers/remote access, vendor arrangements and incident procedures | 4.13–4.14 | EDPB transfer recommendations; GDPR Articles 28 and 33–34; ICO methodology. |
| AI development versus operational processing | 4.15 | CNIL AI development recommendations; separate AI Act classification workflow. |
| Validation against counter-evidence and accountable remediation | 5.10–5.11 | Cloudflare's audit workflow; regulator accountability frameworks. |
| Tests against legally incorrect simplifications and unvetted imported rules | 7.10–7.11 | Inspection of community GDPR guidance and Meta's experimental privacy review heuristics. |

The 2026-10-11 coverage review increased the draft from 63 to 83 acceptance criteria while retaining seven requirement groups and six goals. The local-application extension below adds further criteria without turning requirement counts into a coverage measure.

## Articles and official guidance to use

### Core privacy and governance

1. [EDPB — Be compliant](https://www.edpb.europa.eu/sme/be-compliant/be-compliant_en). Official EU regulator guidance linking privacy by design, processing records and DPIA decisions. Its emphasis on documented assessments supports explicit governance controls rather than source-code-only conclusions.
2. [CNIL — GDPR developer's guide](https://www.cnil.fr/en/gdpr-developers-guide). Practical regulator material covering architecture, development, SDKs, lifecycle controls and deployment. Use it as an engineering research baseline, with national scope retained where relevant.
3. [CNIL — Personal-data security guide](https://www.cnil.fr/fr/guide-de-la-securite-des-donnees-personnelles). Current collection of organizational and technical security guidance. The [2024 English edition](https://www.cnil.fr/sites/cnil/files/2024-03/cnil_guide_securite_personnelle_ven_0.pdf) is a dated supporting reference, not automatically the latest edition.
4. [GDPR — official legal text](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng). Article-level basis for role, lawful-basis, rights and governance decisions; amendments/current official relationships still require review at audit time. Article 12 uses a month-based rights-response period, not a universal fixed 30-day duration. Article 8 is conditional on the service/legal basis and allows national age variation; Article 9 provides several possible conditions, not only explicit consent.
5. [ICO — Data protection audit framework](https://ico.org.uk/for-organisations/advice-and-services/audits/data-protection-audit-framework/). Useful audit organization and control/evidence methodology. **UK authority, not an EU legal source**; the page also flags guidance under review. Borrow methodology only after mapping to relevant EU/national law.

### Tracking, transfers and AI

6. [EDPB — Cookie Banner Taskforce report](https://www.edpb.europa.eu/system/files/2023-01/edpb_20230118_report_cookie_banner_taskforce_en.pdf). A dated enforcement reference for banner practices. Relevant issues include preselected options, rejection paths and misleading presentation; country-specific positions must remain identifiable.
7. [EDPB — final Guidelines 2/2023 on technical ePrivacy scope](https://www.edpb.europa.eu/documents/guideline/guidelines-22023-on-technical-scope-of-art-53-of-eprivacy-directive_en). The final version is 2.0; avoid the obsolete consultation draft. Its [official PDF](https://www.edpb.europa.eu/system/files/documents/2024-10/edpb_guidelines_202302_technical_scope_art_53_eprivacydirective_v2_en_0.pdf) provides the technical research basis for tracking mechanisms beyond cookies.
8. [EDPB — Recommendations 01/2020 on supplementary transfer measures](https://www.edpb.europa.eu/documents/recommendation/recommendations-012020-on-measures-that-supplement-transfer-tools-to_en). The official record identifies the final 2021 version. Use it to structure transfer review; the page's full retrieval timed out during this pass, so detailed steps require full-text inspection before implementation.
9. [CNIL — AI development recommendations](https://www.cnil.fr/en/ai-system-development-cnils-recommendations-to-comply-gdpr), published 5 January 2026. Addresses personal-data processing during development, including responsibility, purposes and safeguards. Its scope does not establish complete AI Act or deployment compliance. The linked [AI checklist](https://www.cnil.fr/sites/default/files/2026-01/ai_checklist.pdf) explicitly excludes AI Act obligations.
10. [European Commission — EU AI Act Compliance Checker](https://ai-act-service-desk.ec.europa.eu/en/eu-ai-act-compliance-checker). Official role/applicability research aid. The page labels the tool beta; it is not an independent audit or substitute for current legal-text review.

### Consumer journeys, accessibility and obsolete material

11. [Your Europe — B2C e-commerce and distance selling](https://europa.eu/youreurope/business/selling-in-eu/selling-goods-services/ecommerce-distance-selling/index_en.htm). Official guide for investigating contractual disclosures, consumer journeys and relevant exceptions. National application and assessment-date changes remain separate research duties.
12. [W3C WAI — WCAG-EM overview](https://www.w3.org/WAI/test-evaluate/conformance/wcag-em/). Evaluation methodology for defining scope, choosing samples and documenting results. It does not itself determine which EU accessibility law or harmonized standard applies.
13. [Regulation (EU) 2024/3228 — ODR platform discontinuation](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX%3A32024R3228). Article 1 repeals the old ODR regulation from 20 July 2025. This is a useful test that the toolkit rejects stale legal templates instead of reinstalling retired requirements; other applicable consumer-redress duties require their own review.

### Agent workflow article

14. [Cloudflare — Build your own vulnerability harness](https://blog.cloudflare.com/build-your-own-vulnerability-harness/). Primary engineering article explaining an audit harness and the companion skill. Useful for separating candidate discovery from verification and maintaining orchestration across changing models; security methodology does not supply EU legal coverage.

## Comparable skills inspected

Repository counts below are GitHub API snapshots on 2026-10-11, not quality scores or measured audit performance. Registry installs were observed separately and can differ across cached pages.

| Project | Evidence inspected | Useful pattern | Limit / adoption assessment |
| --- | --- | --- | --- |
| [Cloudflare security-audit-skill](https://github.com/cloudflare/security-audit-skill) | README and published skill content; MIT; 28,131 stars; registry installs not checked. | Coverage ledger, adversarial candidate verification, structured findings and validators. | Best workflow reference here; security-focused. Its sandbox/permission requirements and internal subagent mechanics need adaptation to our visible Herdr constraints. |
| [wshobson GDPR data handling](https://github.com/wshobson/agents/tree/main/plugins/hr-legal-compliance/skills/gdpr-data-handling) | Original SKILL.md and detailed examples; MIT; parent repo 40,372 stars; approximately 14K [registry installs](https://skills.sh/wshobson/agents/gdpr-data-handling). | Consent, rights-request and lifecycle implementation examples. | Reference only. It uses blanket sensitive-data/child-consent labels and fixed 30-day request examples; our rules must retain statutory conditions, national variation and month-based deadlines. Examples are not a validated complete runtime. |
| [Meta SecPriv](https://github.com/facebookresearch/secpriv-skill) | README metadata and full SKILL.md; MIT; 9 stars; registry installs unknown. | Combined privacy/security source-flow review with a detector/validator separation. | Experimental benchmark/code-review reference, not an EU compliance engine. Some suppression rules treat hashing, aggregation or encryption as sufficient to drop privacy findings; that must not become proof of anonymization or overall lawful processing. No benchmark reproduced here. |
| [bellu privacy-audit](https://github.com/bellu/privacy-audit) | Metadata, source tree and full SKILL.md; MIT; 7 stars; registry installs unknown. | Compare policy claims with data practices inferred from code. | Low-adoption reference. Code cannot establish all business facts; its automatic UI/API artifact generation and host-specific paths do not fit our portable local toolkit unchanged. |

The inspected skills do not establish complete coverage of our EU scope. Popularity supports discovery, not legal correctness. No third-party skill was installed or executed, and no source instructions were copied into the Canonical_Package.

## Other reusable workflows

- [CNIL PIA methodology and software](https://www.cnil.fr/en/privacy-impact-assessment-pia), with a [current download entry point](https://www.cnil.fr/fr/outil-pia-telechargez-et-installez-le-logiciel-de-la-cnil). A regulator-backed structured DPIA workflow; examine current templates before adapting them.
- ICO's audit toolkits and trackers provide an organizational assessment pattern with the UK-law boundary stated above.
- W3C's evaluation/reporting resources provide a sampling and reporting pattern for accessibility without certifying legal applicability.
- The Commission AI checker provides a role/classification pattern; reproduce grounded reasoning from law rather than scrape or assume the checker is an executable legal oracle.

## Work still needed before a coverage claim

- Build the obligation-to-authority-to-check-to-evidence matrix for the supported project classes; map every task back to those controls.
- Verify selected national laws and authority lists, including unresolved source/language/sector cases; no all-country verification occurred in this research pass.
- Inspect complete final transfer, tracking, accessibility and sector-specific materials when deriving their checks; search results and portal metadata alone are insufficient.
- Verify current DSA, AI Act, NIS2, CRA, Data Act and national consumer-law role/threshold/date branches during design and corpus construction. Existing family names are only discovery entries.
- Validate false positives, false negatives, missing access, outdated source versions and hostile document content with synthetic fixtures.
- Validate all seven initially detected CLI integrations through real host discovery and a controlled audit; no host integration was exercised here.

Requirements remain a review draft. This research authorizes neither implementation nor global installation/publication and introduces no changes to the existing commerce-assistant application.

## Local application, graph and scanner extension — 2026-10-13

The owner now requests a frontend with reproducible findings and evidence-linked agent remediation visible in real time. This expands the requirements beyond skill packaging. No application implementation, dependency installation, graph build or target scan was executed in this research pass.

| Candidate | Primary source reviewed | Intended use and limit |
| --- | --- | --- |
| Graphify | [Current upstream README](https://github.com/Graphify-Labs/graphify), reached through the former safishamsi/graphify URL; installed Graphify skill instructions. | Local AST repository map, query/path/explain and versioned graph output. Preserve explicit versus inferred relationship provenance. Graphs locate related evidence; they do not prove runtime data flow or legal compliance. Documentation/media semantic extraction may use a model and remains subject to authorized processing boundaries. |
| Semgrep | [Official CLI reference](https://docs.semgrep.dev/cli-reference). | Candidate source-code scanner with JSON/SARIF result output. Rule matches require applicability and failure validation. The exact edition, rules, license, network behavior and capability limits need design-time verification; do not assume paid analysis features exist in the local edition. |
| Playwright | [Official Trace Viewer documentation](https://playwright.dev/docs/trace-viewer). | Repeatable browser assertions with action history, DOM snapshots, screenshots and network evidence. Reuse its trace capabilities rather than write a new browser recorder. A captured failure must remain tied to its tested environment, inputs and assertion. |
| axe with Playwright | [Official accessibility testing guide](https://playwright.dev/docs/accessibility-testing), [axe-core README](https://github.com/dequelabs/axe-core). | Detect automatable accessibility problems with affected elements; retain incomplete/manual outcomes. Automated accessibility results do not establish full accessibility conformance or legal applicability. |

Graphify's current upstream repository and README differ from some installed skill details; compatibility must be checked against a pinned version and graph schema. Neither upstream benchmark claims nor model savings were reproduced. The requirements therefore demand recorded producer/schema versions, source freshness, confidence and available integrity diagnostics. A separate graph database or cloud subscription is not required by this scope.

The first product acceptance case is deliberately narrow but complete: audit a synthetic repository/test page, display a demonstrated failure and its source/browser evidence, discuss it with an agent, apply an authorized reviewable patch and rerun the affected assertion while the dashboard updates. A second case must keep an unresolved manual/legal item visible. This validates the product loop, not the entire EU obligation catalog.

Frontend and CLI must use the same result model and check execution. Ordered events and retained run state must survive reconnects without duplicating work or attaching results to another project. Applied patches remain awaiting verification; changed source/environment/legal inputs invalidate affected earlier results. Native Herdr implementation assignments follow approval of requirements, design and tasks.
