---
stage: test
bolt: 002-legal-revalidation-cli
created: 2026-10-25T07:20:00Z
status: recorded
---

# Live official-source smoke check — 2026-10-25

The Owner asked for an end-to-end real test. This was the opt-in live check that the
design keeps separate from acceptance tests. It ran from a cloud container with
direct outbound access: DNS answers were public addresses and TLS was verified by
the default context. The declarations used the fictional fixture plus four real
targets. No real project, evidence or legal assessment was involved, and nothing
here establishes legal truth.

## Results

| Target | Outcome |
| --- | --- |
| Fictional fixture (`example.invalid`) | `synthetic-target-not-fetched`; never contacted |
| EUR-Lex GDPR HTML (`CELEX:32016R0679`) | `http-status`: HTTP 202 with an empty body and `x-amzn-waf-action: challenge` (AWS WAF JavaScript challenge) |
| EDPB Guidelines 05/2020 on consent | retrieved: 200, `text/html; utf-8`, 44,711 bytes, one validated same-host redirect, content accepted as an unreviewed `final_guidance` candidate |
| Commission data-protection page | retrieved: 200, `text/html; utf-8`, 166,073 bytes, no redirect, accepted as an unreviewed candidate |
| `example.com` | `host-not-official`; refused before DNS |

A second run declared the EDPB bytes from run 1 and a stale local copy of the
Commission page. The Commission target correctly reported `different_bytes`, and
the declared source lost support. All runs exited 0 with `partial` state, 0700/0600
artifacts, retained candidate bytes under `sources/` and a valid completion marker.
The whole fetch took about three seconds.

## Findings for the Owner

1. **EUR-Lex HTML cannot be fetched automatically.** EUR-Lex answers scripted clients
   with an AWS WAF challenge. The tool correctly records a safe failure and does not
   try to get past the challenge. Options: download the act manually and declare it
   as a local selected source; or review a registry change for an official
   machine endpoint (such as the Publications Office Cellar or the EUR-Lex web
   service). The second needs its own review.
2. **Some official pages change on every request.** The EDPB page embeds a random
   Drupal `js-view-dom-id-…` value, so exact-byte comparison reports
   `different_bytes` on every fetch. That is conservative and safe, but byte equality
   can never confirm freshness for such pages. A reviewed, normalized secondary
   digest is a possible Bolt 003 revalidation decision. The exact-byte rule is unchanged.
3. Identifier and language screening passed on both retrieved pages. That is a
   conservative content check, not proof of document identity.
