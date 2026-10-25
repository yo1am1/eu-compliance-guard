---
stage: plan
bolt: 002-legal-revalidation-cli
created: 2026-10-25T01:30:00Z
status: recorded
---

# Implementation Plan: official-source retrieval

**Stage 1 Plan: recorded 2026-10-25.** The Owner directed this session to find
the next task and proceed with implementation. This plan covers story 003 and
records the decisions taken. Human validation of Plan, Implement and Test remains
the Owner's checkpoint; no story, bolt or MVP is marked complete here.

## Objective and scope

1. **Deliver bounded opt-in retrieval:** `--fetch-official` fetches each declared
   `SourceTarget` through a fixed host registry, pinned DNS, verified TLS and
   validated redirects. Each target yields exactly one `SourceAttempt` with
   safe provenance. Accepted bytes are retained in the run directory as an
   unreviewed candidate `LegalSource`. Covers story 003 AC-1 to AC-5.
2. **Reuse the foundation:** `SourceAttempt`, `LegalSource`, `SafeError`,
   `admit_source_content`, private run publication, the completion marker and the
   escaped report. Standard library only (`urllib.parse`, `ipaddress`, `socket`,
   `ssl`, `http.client`, `multiprocessing`). No dependency or lockfile change.
3. **Defer:** `--previous`, predecessor comparison, freshness overlays, the
   portable skill and release checks stay in Bolt 003. `--previous` still fails
   with exit 2 before reads. Rejected bodies are counted and hashed, but not
   retained; the design makes their quarantine optional.

## Contracts (`models.py`, then `make contracts`)

1. `SourceTarget.redirect_hosts: list[HostName]` (max 4, default empty). These are
   explicitly approved redirect hosts. Retrieval also requires the code registry.
   The default keeps existing declarations valid.
2. New `RetrievalProvenance`: requested/final URL, redirect chain (max 3),
   UTC start/end, HTTP status, media type/charset, bytes read, digest, retained
   artifact path, content admission state/reason and comparison against the
   declared source for the same target (`same_bytes`, `different_bytes`,
   `no_prior_source`, `not_compared`). No headers or cookies are retained.
3. `SourceAttempt.retrieval: RetrievalProvenance | None = None`. This field is
   optional, so existing fixtures and legal-contract tests keep their meaning.
4. `RevalidationBundle.source_attempts` and `retrieved_sources` (max 16 each,
   default empty). The validators require one attempt per target at most, attempt
   and target membership, resolvable retrieved/last-successful pins, and retrieved
   records that match their target's identity/classification and final URL with
   empty provisions. They also require provenance consistency with retained
   artifacts. A run with any attempt or retrieved candidate can never be
   `completed`.
5. `RunCompletion.files` max raised to 36. That covers four artifacts plus up to
   16 declared and 16 retrieved source files under the existing `sources/` scheme.

## Network policy (`sources.py`, new)

- Registry: `eur-lex.europa.eu`, `curia.europa.eu`, `commission.europa.eu`,
  `digital-strategy.ec.europa.eu`, `www.edpb.europa.eu`. Matching is exact; there
  are no wildcards or input-added hosts.
- URL checks run for the target and every redirect: length ≤ 4,096, HTTPS only,
  netloc exactly `host` or `host:443`, and a lowercase ASCII registered host.
  Userinfo, fragments, whitespace, control characters, backslashes, `%` in the
  authority and IP literals are refused. Redirect hosts must be the target host,
  or in `redirect_hosts`, and also in the registry.
- DNS uses `getaddrinfo` A/AAAA. If any address is not global, or is an
  IPv4-mapped/multicast address, the whole answer set is rejected. More than 16
  addresses are refused. The connection goes to the checked numeric address;
  the connected peer is verified and the name is never resolved again.
- TLS uses `ssl.create_default_context()` with the original host as SNI/Host.
  `http.client` never reads proxy settings, cookies or `.netrc`. Headers are
  fixed: User-Agent, Accept, `Accept-Encoding: identity` and `Connection: close`.
- Redirects: 301/302/303/307/308 with one `Location`. At most three redirects
  (four GETs per target) are followed. Loops and overlong locations are rejected.
- Responses must be status 200 with an allowed media type, no content encoding,
  ≤ 100 headers, ≤ 8 KiB per header line and ≤ 64 KiB of headers in total.
  Bodies are limited to 8 MiB each, with an early `Content-Length` refusal, and
  are read in 64 KiB chunks. The run total is 64 MiB, counting rejected bodies.
- Time limits: 5 s per socket operation, 20 s wall time per target and 300 s of
  network budget per run. Each target runs in a disposable `spawn` worker that
  writes the body to a private staging directory (0700/0600). The parent
  terminates/kills the worker at the deadline. If the worker cannot be stopped,
  the run fails (`retrieval-failed`). Targets after budget exhaustion receive
  explicit `network-budget-exhausted` attempts.
- `synthetic_fixture` targets are never contacted (`synthetic-target-not-fetched`).

## Assembly, report and CLI

- `run(..., fetch_official=True)` preflights the output parent before any network
  call. It then fetches, assembles and publishes. Offline mode is unchanged.
- Content admission reuses `admit_source_content`. Login, challenge and error
  pages become `retrieval_failed` (`content-rejected`). Uncertain formats, PDFs,
  a missing intended identifier, or an HTML `lang` that disagrees with the target
  stay retrieved candidates with review gaps. A language mismatch uses the
  existing `translation_unverified` state.
- Every retrieved candidate records the gap "candidate requires accountable source
  review". If the bytes differ from a declared source for the same target, that
  declared source loses support. A failed or unconfirmed retrieval keeps a real
  declared source's freshness unknown. Only a retrieved, admitted, byte-identical
  response replaces the offline freshness gap. That still establishes unchanged
  content only, never binding status, applicability or currency.
- The report adds a retrieval section listing each attempt's provenance and
  failure code, the candidate's classification and the statement that official
  hosting does not establish authority. Imported URLs remain escaped text.
- CLI: `--offline` and `--fetch-official` form an argparse mutually exclusive
  group (exit 2). `--previous` is still rejected before reads. The new safe code
  is `retrieval-failed`.

## Acceptance checks (synthetic and fake; no live source contact)

| AC | Tests |
| --- | --- |
| AC-1 | URL policy table (scheme, credentials, ports, hosts, IP literals, encodings, fragments, length); DNS mixed public/private, mapped IPv6, >16, empty; public→private and disallowed-host redirects; loops; redirect limit |
| AC-2 | Exact request headers on a local plain-TCP listener with a fake TLS context, including proxy variables being ignored; header/body/Content-Length/total bounds at the limit and one over; per-target deadline with a real spawned worker that hangs and is cleaned up; budget exhaustion |
| AC-3 | Retained bytes/digest, requested/final URL, timestamps and classification in the bundle; declared source unchanged; marker digests |
| AC-4 | Timeout, DNS/TLS/connect errors, unsafe destination, oversize and status errors become safe failure attempts without content; declared bytes are only `last_successful_source` |
| AC-5 | Login/challenge pages rejected; PDF/uncertain/identifier/language gaps; retrieved candidates never support duties; synthetic targets not fetched; offline default performs no network; `--offline --fetch-official` conflict |

Verification: `make contracts`, `make check`. In this container the executor
module's existing tests require an unavailable sandbox binary and are reported
separately. No live official-source smoke run is part of this plan.
