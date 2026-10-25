---
stage: implement
bolt: 002-legal-revalidation-cli
created: 2026-10-25T02:30:00Z
status: awaiting-owner-validation
---

# Implementation walkthrough: official-source retrieval

The Owner directed this session to implement the next task. Stage 2 is done on the
branch `claude/bolt-002-official-retrieval`. Owner validation of Plan and Implement
is still pending, and no story or bolt completion is claimed.

## What changed

| Commit | Files | Change |
| --- | --- | --- |
| `docs: plan official-source retrieval bolt` | this bolt's `bolt.md`, `implementation-plan.md` | Plan and decisions |
| `feat: add official retrieval provenance contracts` | `models.py`, generated schema/TypeScript, `tests/test_retrieval_models.py` | `RetrievalProvenance`, `SourceAttempt.retrieval`, `SourceTarget.redirect_hosts`, bundle `source_attempts`/`retrieved_sources`, marker limit 36 |
| `feat: add bounded official-source retrieval policy` | `sources.py` | Registry, URL/DNS checks, pinned TLS connection, redirects, bounds, spawned worker |
| `test: cover official retrieval policy with fake transport` | `tests/test_sources.py` | Fake DNS/HTTP, a local wire check and real worker cleanup |
| `feat: add opt-in official-source retrieval to revalidate` | `revalidation.py`, `report.py`, `__main__.py`, CLI test, `tests/test_retrieval_workflow.py` | Assembly, retention, report section, `--fetch-official` |

## Behaviour

- **Opt-in only.** Without `--fetch-official`, no network code runs.
  `--offline --fetch-official` is an argparse conflict and exits 2.
  `--previous` is still rejected before any read.
- **One attempt per declared target.** `synthetic_fixture` targets are never
  contacted. Unsafe targets and exhausted budgets are refused without starting a
  worker.
- **Network policy (`sources.py`).** Only the five registry hosts are allowed,
  with HTTPS on port 443 and no userinfo, fragment, IP literal, `%` or control
  characters. If any DNS address is non-global, the whole answer set is
  rejected; more than 16 addresses are also refused. The connection goes to the
  checked address, and the peer is verified. TLS uses the default context with
  SNI set to the original host. `http.client` ignores proxy, cookie and
  `.netrc` settings. The request headers are fixed. At most three redirects are
  followed, and each one is re-validated and re-resolved. Header, body and time
  limits match the design table.
- **Worker.** Each target runs in a `spawn` process that stages the body in a
  0700 temporary directory. The parent waits only until the target deadline. It
  then stops the worker with terminate, then kill. If the worker survives, the
  run fails with `retrieval-failed`.
- **Assembly.** Login, challenge and error pages give `retrieval_failed` with
  `content-rejected`, and their body is not retained. PDFs, uncertain HTML and
  a missing intended identifier stay retrieved candidates with review gaps. A
  page `lang` that differs from the target gives `translation_unverified`. Every
  retained candidate is a separate `LegalSource` with no provisions, plus the gap
  "requires accountable source review".
- **Effect on declared sources.** Different bytes withdraw the declared source's
  support. A failed or unconfirmed retrieval leaves a real source's freshness
  unknown. Only admitted, byte-identical bytes clear the offline freshness gap,
  and that confirms unchanged content only.
- **Retention.** Accepted bytes go to `sources/<digest>.bin` (0600) and are listed
  in `complete.json`. Declared sources and input files are never modified.
- **Report.** A new "Official-source retrieval attempts" section lists each
  attempt's provenance and failure code. It states that hosting establishes
  neither binding status, completeness, applicability nor currency. URLs remain
  escaped text.

## Limits

- No live official-source request was made. All network tests use fakes, a
  local listener or a spawned fake transport.
- Rejected bodies are hashed and counted, not quarantined on disk.
- Identifier and language signals are heuristics. Reviewer acceptance of
  document identity is still required.
- In this container `tests/test_execution.py` fails and hangs: the existing
  executor tests expect a sandbox binary that is not installed. That module is
  unchanged and outside this bolt, so `make check` cannot finish here. Its
  components were run separately (see the test walkthrough).
