---
id: 003-official-source-retrieval
unit: 001-legal-revalidation-cli
intent: 001-read-only-legal-revalidation
status: draft
priority: must
created: 2026-10-18T19:01:39Z
assigned_bolt: 002-legal-revalidation-cli
implemented: false
---

# Story: 003-official-source-retrieval

## User Story

As a project owner, I want to retrieve selected official sources safely, so that my local legal review is traceable and explicit about its limits.

## Acceptance Criteria

- [ ] **AC-1**: Given selected URLs and fake DNS/HTTP responses, when issuing bounded GETs, then HTTPS official hosts, destinations and every redirect are validated; credentials, nonstandard ports, nonofficial hosts and private/local destinations are refused, including public-to-private redirects.
- [ ] **AC-2**: Given a request, when issuing or redirecting, then no project evidence or provider/session credentials are sent; documented finite download, request-duration, redirect and attempt/collection bounds are tested and enforced.
- [ ] **AC-3**: Given accepted responses, when retaining versions, then exact bytes/digest, requested/final URL, full retrieval timestamp, language, publisher, identifier and classification are recorded without altering prior source versions.
- [ ] **AC-4**: Given timeouts, unsafe destinations, oversized responses or other failures, when reporting attempts, then each has a safe failure record without invented content or old bytes represented as fresh success.
- [ ] **AC-5**: Given binding acts/judgments, guidance, proposals, standards, engineering practice and fictional fixtures, when classifying/reporting, then distinctions remain visible; official hosting alone establishes neither binding status, completeness, applicability nor assessment-date currency. Login/challenge/error pages are rejected; uncertain text requires review.

## Technical Notes

Primary requirement ownership: FR-2. See [unit traceability](../unit-brief.md) and the canonical requirements/context/design linked there. All fixtures are synthetic. Retrieval requires `--fetch-official`; default mode performs no network operations, and combining `--offline` with `--fetch-official` fails argument validation. Test both the default and conflicting flags with fake transport.

## Dependencies

### Requires
- [002-accountable-mapping-and-report](002-accountable-mapping-and-report.md)

### Enables
- [004-revalidation](004-revalidation.md)

## Edge Cases

Failure/ambiguity cases in the criteria remain safe failures or explicit gaps.

## Out of Scope

Deferred scanners, providers, remediation, dashboard, global installation and automated compliance verdicts.
