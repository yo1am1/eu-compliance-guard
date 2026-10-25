---
stage: test
bolt: 002-legal-revalidation-cli
created: 2026-10-25T02:30:00Z
status: awaiting-owner-validation
---

# Test report: official-source retrieval

Owner validation is pending. These checks establish software behaviour on synthetic
inputs only. They do not establish legal truth, live-source acceptance or real
containment.

## Results — 2026-10-25

- 151 tests pass across every module except `test_execution.py`: the 114
  baseline tests plus 37 new ones (8 contract, 18 network policy/worker,
  10 workflow and 1 CLI).
- `python -m eu_compliance_guard.schema --check`, `types:check` and `tsc --noEmit`
  pass.
- `tests/test_execution.py` fails before and after this change in this container,
  because the executor's sandbox binary is unavailable (6 failures, 4 hangs).
  The module is untouched. `make check` therefore cannot complete here and should
  be re-run on a host with the executor's prerequisites.
- The CLI example exits 0 with `--offline`. With `--fetch-official` on the
  synthetic fixture it also exits 0, records a `synthetic-target-not-fetched`
  attempt and makes no network contact. `--offline --fetch-official` exits 2.
- `uv build --offline` produces a wheel containing `sources.py` and the schema;
  the sdist contains the new tests.

## Acceptance criteria trace

| AC | Evidence |
| --- | --- |
| AC-1 | `UrlAndAddressPolicyTests` (schemes, credentials, ports, hosts, IP literals, encodings, fragments, length); mixed/mapped/>16 DNS answers; `test_unsafe_targets_never_reach_dns_or_http`; `test_redirects_are_revalidated_and_bounded`; `test_public_to_private_redirect_is_refused_after_fresh_resolution` |
| AC-2 | `test_pinned_connection_sends_only_fixed_headers_and_ignores_proxy_environment`; header/body/`Content-Length` limits at the boundary and one over; `test_at_most_three_redirects_four_gets`; trickle deadline; `test_helper_returns_staged_bytes_and_enforces_wall_deadline` (real spawned worker that hangs and is cleaned up); budget-exhaustion attempts; fatal unstoppable helper |
| AC-3 | `test_same_bytes_record_provenance_without_claiming_authority`; `test_run_fetches_through_helper_and_retains_candidate_bytes` (exact retained bytes, 0600, marker digests, declared source and input unchanged); bundle contract checks in `test_retrieval_models.py` |
| AC-4 | `test_failures_never_invent_content_or_freshness`; safe-failure mapping in `test_slow_trickle_and_errors_become_safe_failures`; `test_unstoppable_helper_fails_the_run_without_output` |
| AC-5 | `test_login_challenge_pages_are_rejected_and_uncertain_text_needs_review`; `test_guidance_candidate_cannot_become_binding_duty`; `test_changed_bytes_withdraw_declared_support_and_attempts_block_completion`; `test_offline_default_and_unusable_output_perform_no_network`; CLI conflict tests |

## Live smoke check

On 2026-10-25 the Owner asked for an end-to-end real test. The opt-in live check and
its findings are in the [live smoke report](live-smoke-report.md). EUR-Lex HTML is
blocked by a WAF challenge, which is recorded as a safe failure. EDPB and
Commission pages were retrieved.
