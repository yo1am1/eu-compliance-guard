---
stage: test
bolt: 003-legal-revalidation-cli
created: 2026-10-27T10:43:53Z
status: recorded
---

# Predecessor and release verification

Implementation commit: `ed11d8f`, pushed to `claude/bolt-003-plugin-ui`.
Owner stage and MVP acceptance remain pending; no bolt/story is marked complete.

## Checks

- `make check`: all 197 tests pass, including executor tests with fake processes;
  JSON Schema drift, generated TypeScript drift and compilation pass. Baseline was
  181 tests. No command contract was replaced or added.
- Sixteen new synthetic tests cover predecessor/CLI behavior: byte-identical
  history and successor chains; changed and unrelated requirements; assessment
  dates; added/removed records and review edits; missing/changed evidence and
  sources; matching bytes, failed refresh and new downloads; semantic revision
  enforcement and rollback; corrupted/incomplete/cross-project/symlinked history;
  mismatched normalized artifacts, omitted source bytes, duplicate JSON and bundle
  byte bounds; comparison proof membership and static escaped rendering.
- `claude plugin validate .`: pass, with the existing missing marketplace-icon
  warning. `claude plugin test .`: all four band tests pass on the supported
  simulated surfaces. No model call or plugin installation was used.
- `uv build --offline --out-dir /tmp/eucg-bolt003-dist`: wheel and source archive
  build successfully. Wheel has 22 entries, including CLI, history module, schema
  and licenses. Source archive has 65 entries, including README, fictional fixture,
  tests, all plugin skills/manifests, band/hooks and type declarations. Inspection
  found no installed dependencies, caches, Git metadata or private runtime data.
- Wheel installed with cached dependencies in a fresh temporary environment.
  From outside the checkout, `python -I -m eu_compliance_guard` executed first-run,
  `--previous` successor and static-view commands using the sdist's fictional
  example. All exit 0 with explicit `partial` state; successor links its parent,
  records no dependency changes and leaves source freshness unknown offline.
  Every completion-marker digest and 0700/0600 mode passes; every predecessor
  file hash remains unchanged. HTML stays outside immutable run directories.
- `specs/**` remains byte-identical to the fetched branch. Exact staged files and
  whitespace were reviewed; effective local author/committer are Yehor Trepalin
  using `110065476+yo1am1@users.noreply.github.com`. This session follows the
  Owner-supplied native Codex co-author instruction; the older branch's
  no-trailers criterion is not asserted as accepted.

## Limits

No current-law conclusion, live-source request, provider/scanner execution,
containment verification, interactive plugin drawing, actual browser opening,
global installation or OS-policy change occurred. The recorded historical smoke
and plugin end-to-end reports remain distinct from these synthetic release checks.
Family-screening invalidation remains conservative where dependency attribution
is incomplete; matching bytes never renew legal currency or reviewer approval.
Native Herdr is unavailable in this session, so no hidden teammates were started.
Two pre-existing planning edits remain preserved in Git stash.
