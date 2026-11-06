---
intent: 004-precision-and-jurisdictions-v2-5
phase: inception
status: direction-approved-2026-11-06
created: 2026-11-06T13:00:00Z
---

# Version 2.5: precise, then wider

2.0 is a strong base. 2.5 first proves it precisely (tests, audit, fixes), then widens it
beyond the EU, then covers the laws software teams meet now and sees more of the code.
3.0 is reserved for a breakthrough once 2.5 is stable.

## Owner decisions (2026-11-06)

1. **Precision first.** 2.1 starts now: a full audit for defects, fuzz tests for every
   parser of untrusted input, a test set of real official law text, and tests on real
   repositories. Defects found are fixed before new jurisdictions are added.
2. **Jurisdictions: the UK first, then the US.** The UK (legislation.gov.uk, official
   point-in-time XML; UK GDPR, the Data Protection Act 2018, PECR) proves a jurisdiction
   design cheaply. Then US **federal law only** (eCFR, the Federal Register, GovInfo);
   state laws come later, one state at a time.
3. **No lawyer, no guarantees.** This is an open-source side project that may become a
   service later. No lawyer reviews packs or outputs, and none will be named. Packs may
   ship as free starter drafts, labelled unreviewed, and like every output they carry
   the no-warranty notice. This replaces the 2026-11-04 decision that a qualified lawyer
   signs each pack version: a pack signature names whoever reviewed it, not a lawyer.

## Constraints carried forward

Read-only toward legal conclusions and never a verdict; official hosts only for law text,
each verified; network only with consent; deterministic outputs; no new regular
expressions; the 14-day version cooldown; synthetic fixtures for project data;
`specs/**` preserved byte for byte; contracts generated from `models.py`; files are the
API. The tool's name stays "EU Compliance Guard" through 2.x; a rename is a 3.0 question.

## Versions

| Version | Destination |
|---|---|
| 2.1 | **Precision.** Audit by area (parsers, file handling, signing, MCP, plugin); fuzz tests for the article, citation, WEC, SARIF, diff and MCP inputs; committed extracts of real EUR-Lex text as a parser and citation test set; grounding and graph measured on real open-source repositories. |
| 2.2 | **Jurisdictions, starting with the UK.** A jurisdiction becomes a module (verified hosts, identifiers, screening families); the EU is the first; the UK the second. |
| 2.3 | **US federal law.** eCFR (point in time), the Federal Register (new and proposed rules, for change impact) and GovInfo (US Code; needs a free api.data.gov key, through the credential flow). First targets: COPPA, HIPAA, GLBA, FTC rules. |
| 2.4 | **Laws software teams meet now.** Cyber Resilience Act, European Accessibility Act, NIS2 screening, the AI Act's phased dates; an application-date timeline quoted from the text; starter packs as unreviewed drafts; exports (a draft Article 30 record, DPIA screening inputs). |
| 2.5 | **More of the code.** A JavaScript/TypeScript graph through a pinned optional parser; graph digests in runs so a code change reopens decisions as a law change does; a Graphify import; stabilisation for 3.0. |

## 3.0 candidates (not approved)

A hosted workspace syncing the same files (the paid tier); a cross-jurisdiction view of
one requirement across GDPR, UK GDPR and US law; a registry of signed packs; links to
SOC 2 and ISO 27001 controls; a name that fits more than the EU.
