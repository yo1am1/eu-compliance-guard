# Changelog

## Unreleased

### Added

- `scope.technical`: a place in the declarations for facts about what the software does ("sets
  analytics cookies"). Until now such a fact had no obvious slot: under `size_and_sector` it
  was treated as organisational and never searched for in code, and it only worked under
  `roles`. `ground` now says so when a fact under `size_and_sector` cannot be searched. Existing
  declarations stay valid (the list defaults to empty); a file that uses it needs 2.6.1 or later.

### Fixed

Found by a seven-agent audit of the whole code base (six owners, one reviewer).

- Runs: a run compared with its predecessor now sees a change to the source review for the
  assessment date even when a review for another date is listed after it; before, the change
  was missed and support was not withdrawn. With `--fetch-official`, the consolidation queries
  share the run's single 300-second network budget instead of getting a second one. A retrieval
  helper that cannot start is recorded as `worker-failed` instead of crashing the run.
- Citation guard: citations in brackets or Markdown ("(Article 5 GDPR)", "**Article 5**"),
  without a space ("Art.5") and both ends of a range ("Articles 5–7") are checked; before, such
  a citation of a missing article passed.
- Law text: inserted UK provisions keep their full number (Data Protection Act 2018 sections
  74AA and 74AB are parsed; UK GDPR Article 8ZA is no longer shown as 8Z). Footnotes of a
  consolidated EUR-Lex page, UK signature blocks and the "SCHEDULES" heading are no longer text
  of the last provision. **A law lock made earlier over these texts shows these provisions as
  changed once.** The timeline reads UK dates with an ordinal day ("11th December 2003").
- Rust graph: an item after a test-only `use` or under `#[cfg(not(test))]` is no longer left
  out; test code behind `pub(crate)` or `#[tokio::test]` is. Calls by full path
  (`crate::net::send()`) resolve without a `use`; `Vec::<u8>::new()` no longer links to project
  code; a char literal `'\''` no longer hides the code after it.
- Python graph: `import module` then `module.f()`, dotted `pkg.module.f()` and a `src/` layout
  resolve to the right file; `self.store.save()` is no longer linked to a same-named function
  of the calling file; a form feed no longer shifts the lines concepts are read from; a data
  flow is no longer dropped when a guessed call reaches one of its functions first.
- Next step: `next`, the report and the dashboard no longer ask to review evidence for a duty
  reviewed as not applicable; they ask to remap the requirement. A step for a fact with
  conflicting declarations says so.
- Exports: `export ropa` lists a missing establishment and assumed or unknown controller roles
  as gaps; Markdown exports render declared links and images as plain text.
- `seal --check` reported a changed run as intact when an untouched copy of it lay in another
  run folder. `accept` never returned when a long source-target id filled the obligation id.
  `verify` failed whole on one malformed signature file; it is now listed as invalid.
  `import-evidence --kind sarif` failed on a rule id that is not a string.
- A project id, media type or hook value ending in a newline is no longer accepted.
- Plugin: the side panel lists open `scope.technical` facts; the session hook summarizes the
  run completed last (as `next` and the band do) and keeps its context on a wrong-shaped
  bundle; `/eucg-audit` names the admitted legislation.gov.uk URL form (`/data.htm`);
  `/eucg-next` handles `review` and remap steps.

### Changed

- `seal --check --allowed-signers` marks entries without a signature as `NOT signed` (JSON:
  `signatures_checked`), and a signer's name is printed only once verified.
- A project file the tool rewrites (exports, `eu-law.lock`, `runs.log`, packs, signatures) never
  gains permission bits: a file made private stays private.
- `verify` says `file holds another decision`, and the MCP server says `Unknown tool.`, instead
  of echoing text they were given.
- Faster: `graph`, `ground` and `pr-check` build the project graph in about half the time. The
  optional semantic search keeps its newest 32 cache files, and with the extra installed but
  turned off the 67 MB model file is no longer hashed on every run.
- Docs: the command reference lists every option; the help card names all six MCP tools;
  contributor docs say what `make check` and CI run.

### Changed (internal; no behaviour change)

- Review rules shared by assembling a run and validating a bundle (accountable review, open
  fact, admitted evidence, binding source types) are defined once.

- The three longest functions are split into named steps: assembling a run (379 lines), the
  bundle validator (318) and the report renderer (285). No function they contained is longer
  than 68 lines now. Verified byte for byte on 17 reference bundles and reports, and by 20,000
  deliberately broken bundles that the old and the new validator reject with the same errors.

## 2.6.0 — 2026-11-10

Better suggestions, tamper evidence, and a smaller code base. Article suggestions can use an
optional local embedding model (off by default); runs can be sealed in a hash-chained log so a
rewritten report is detected; code no command used is removed and duplication cut. A new
end-to-end test (`make e2e`, 109 checks) runs every command as a user would, and the README
is rebuilt from real output.

### Changed (presentation)

- A new README in one deliberate look: a centred header with badges and section links, a
  table of what the tool does, an architecture diagram, and an animated tour with nine
  stills. Every image is real output for the fictional FitBox project, rebuilt by
  `make readme-images` in the report's own palette, as WebP with rounded corners baked in.
  `tests/test_docs_style.py` keeps it that way (one image format, alt text, no dead links).
  `CITATION.cff` added.

### Added (tests)

- `make e2e` (`scripts/e2e.py`, also in CI): every command driven from outside on a fresh
  fictional project with the real GDPR and ePrivacy texts as declared sources, 109 checks of
  exit codes, output, files, determinism and the legal notice, including the MCP server over
  stdio and a tampered run. `--live` also expects both acts confirmed as current by the
  Publications Office.

### Removed

- Code no command used (Owner decision, YAGNI): the offline Linux executor helper
  (`execution.py`), the agent-protocol inspection (`agent.py`) and about 60 record types for
  commands, conversations, patches and snapshots from the original design. `models.py` is 530
  lines shorter and the generated JSON Schema 4,500 lines shorter; it now holds records only,
  with no command union at its root. Git history keeps the removed code for when scanners of
  our own are built.

### Changed (internal; no behaviour change)

- The command line has one error path, one run lookup and a dispatch table instead of 21 copied
  `try`/`except` blocks and a 22-branch `if` chain (94 lines shorter, same output).
- Nine identical error classes share `errors.CodedError`; two near-identical atomic-write
  functions share `files.py`; the evaluation scores every set with one function; dead code
  (`articles._query`) is gone. `tests/test_hygiene.py` keeps these from coming back, and
  CONTRIBUTING has a map of the modules.

### Added

- Optional semantic ranking of article suggestions. Word search stays the default and the only
  thing a default install has. With the `semantic` extra installed, turned on
  (`EUCG_SEMANTIC=on` or `"semantic": true` in the config file) and set up once
  (`semantic setup`), suggestions merge the word ranking with a small local embedding model
  (BAAI/bge-small-en-v1.5, MIT, about 67 MB, pinned by SHA-256) and label each hit "word
  match" or "semantic match". It only orders articles to read; nothing is mapped or decided.
  Using the model is offline; only `semantic setup` downloads, from huggingface.co.
- Measured on a new test set of 40 plain-language requirements against the real GDPR text
  (`fixtures/eval/gdpr-v1.json`): a right article in the top 3 for 28 of 40 with word search
  and 34 of 40 with the hybrid; top 1 for 23 and 26. The model alone (30 of 40) is worse than
  the hybrid, and it misses cases word search finds. The cases were written by the project,
  so the numbers show direction, not precision. `make eval` reports both, and
  `fixtures/eval/baseline.json` holds the floors.
- `semantic status|setup`, `make semantic-check`, and a CI job that runs the real model.
- Tamper evidence for runs. `seal` appends a run to `.eu-compliance-guard/runs.log`: its id, the
  digest of its completion marker and the digest of the previous line, optionally signed with
  an SSH key. `seal --check` verifies the chain, every sealed run still on the machine and the
  signatures. A report rewritten together with its own checksums, which a run alone cannot
  detect, is reported as changed (tested). The log is evidence when committed to Git or
  signed; the docs say what it does not prove.

## 2.5.1 — 2026-11-10

Fixes from a full audit of 2.5.0 (nine auditors, one verifier, findings re-checked against the
code and sources). No new features: the tool now does what its documentation says, and the
documentation says only what the tool does. Checked live: GDPR, ePrivacy and CRA fetched from
the Publications Office match the shipped test texts byte for byte and are confirmed current.

### Fixed

- `revalidate --fetch-official` could never confirm an EU act as current: the identity check
  looked for the CELEX number, which Publications Office pages do not print. It now also
  accepts the act's own "2016/679" form, and a fetch byte-identical to the declared source
  needs no second identity signal. Checked against all six EU texts in `fixtures/official/`.
- `timeline` took the date of a cited act for an application date (ePrivacy Article 2:
  "Directive 2002/21/EC … of 7 March 2002 … shall apply") and missed transposition deadlines
  worded "shall bring into force" (ePrivacy Article 17, 31 October 2003). A superscript digit
  next to a month no longer crashes it, and a long clause with many dates is no longer quadratic.
- `timeline` now says its dates come from the retained version of each act and that a later
  amending act, such as Regulation (EU) 2026/1744 for the AI Act's high-risk dates, is not
  reflected unless that version includes it.
- `accept` mapped a requirement to an article the act does not have ("Article 999"), and
  `pack build` packaged it, dropping it from the pack's law digests without a word. Both now
  check the article against the locked and declared text and fail with `unknown-article`;
  with no text to check against, `accept` says so.
- The citation guard checked "Article 9 of the Product Liability Directive" against whatever
  act was declared, and passed it when that act had an Article 9. A citation naming an act it
  does not recognise (a Regulation, Directive, Act, ... that is neither declared nor known) is
  now reported as not checked.
- `verify` reported a decision signed without `eu-law.lock` as "decision, law and evidence
  unchanged", although that signature pins no article text. It now says the law is not pinned
  and to lock and sign again. Tests now cover a changed law digest, changed evidence and a
  removed decision.
- The project graph was still quadratic per file, so 2.5.0's "linear now" covered only part of
  the problem: the Rust reader rescanned to the end of the file for every item (a 64 KB file
  held `pr-check` for 71 s), and the Python reader re-split the file for every definition (a
  340 KB file took 131 s). Both are linear now; 30,000 items read in under a second, with tests.
- A project larger than the graph's limits (50,000 definitions, 200,000 links) made `graph`,
  `ground` and `pr-check` fail with a bare exit 2. The graph now keeps every extracted link
  first, leaves out ambiguous calls, and says how much was left out (`omitted_nodes`,
  `omitted_edges`).
- The plugin's session hook crashed at import on Python 3.9, the `python3` of stock macOS, so
  the plugin's context never loaded there. It now runs on Python 3.8 and later.
- `pr-check` let `--strict` pass a line posting a user's email and weight to a third-party URL:
  "weight" needed a second health word, and a web address did not count as a third party.
  Next to personal data, one special-category word or a web address is now enough. "weight",
  "height" and "heart" no longer count without a person, so CSS such as `font-weight` and
  `height` is no longer flagged as health data. `graph` uses the same rule.
- `ground` offered lines of the declared law texts as code evidence, and `ground --apply`
  pinned a fact as "observed source code" to a table-of-contents line of the ePrivacy
  Directive on one shared word ("page"). Declared source copies are no longer indexed or
  pinnable, and `--apply` needs a concept term or two shared words.
- `import-evidence` summarised a SARIF log passed as `--kind wec` (and the reverse) as an empty
  result. The wrong format is now refused. Imported copies and summaries are written readable
  by their owner only (0600), since another tool's output can name a site's users or internals.
- The Markdown report had the legal notice only near the top, although the README says every
  output ends with it. It now ends with it too.

### Changed (documentation)

- Claims the code does not support are corrected: runs are checksummed, not tamper-evident
  (anyone who can write the run folder can rewrite a report and its checksums); the dependency
  notices and the `eucg` skill said MIT, but the project is AGPL-3.0-only from 1.2.0; licence
  files of removed dependencies are gone and every runtime package is listed. The package no
  longer claims "OS Independent": Linux and macOS are supported, Windows is not, and the
  README and plugin guide say so. "Read-only" is defined: the tool writes only its own records.
- The plugin guide recommended allowing `uv run --project * …`, which would let uv run any
  other project's code. It now gives the plugin's own path, and says what allowing it means for
  network consent. The guide's band paragraph, cut off in 2.x, is whole again.
- Stale help: `mcp` lists all six tools, `graph` says Python and Rust, the command table lists
  `pack starters`, the example PR workflow no longer calls its pin 1.1.0 and says its
  dependencies are not locked, and CONTRIBUTING no longer says the band's types are generated.
- The UK GDPR test text now also credits EUR-Lex, since it derives from Regulation (EU) 2016/679.

### Tests

- New tests pin behaviour that mutations of 2.5.0 showed nothing covered: `impact` on a removed
  article and on a version-only change (now shown as "version not recorded → v2"), the DPIA
  screening's count of guidance criteria with signals, signed-decision staleness, the timeline's
  reached/upcoming boundary and its text output.

## 2.5.0 — 2026-11-07

Stabilisation before 3.0: an audit of everything 2.2 to 2.4 added, and the open choices
settled. The Owner chose to remove the unused React page and the `api` extra; the plugin's
dashboard (band, side panel, Dashboard button, the static HTML view) is unchanged. The live
check of the band and panel in a real Claude Code session is still the Owner's to run.

### Removed

- The unused React page in `frontend/`, with its npm build, Node.js CI steps and Dependabot
  entry. The plugin's dashboard is the static HTML view; `view` still writes
  `views/<run>.scorecard.json` as data.
- The optional `api` extra (FastAPI, Uvicorn) and the dev dependency group. Nothing used them;
  the CLI and plugin need only Pydantic.

### Fixed

From the 2.5 audit of what 2.2 to 2.4 added:

- Three parsers were quadratic on hostile input, so a crafted file or text could stall
  `pr-check` in CI or the MCP server: the UK parser on unmatched end tags (20,000 took 15 s),
  the citation guard on many citations and quotations (20,000 took 10 s), and the Rust reader on
  unclosed generic arguments (8,000 took 11 s). All three are linear now, with tests that fail
  if they regress.
- CSV exports keep a cell starting with a tab or carriage return as text, as they already did
  for `=`, `+`, `-` and `@` (spreadsheet formula injection).
- A function defined twice in one file (`#[cfg(unix)]` and `#[cfg(windows)]` in Rust, or an
  `if`/`else` in Python) made its unique calls look ambiguous; a name now resolves to its one node.

## 2.4.0 — 2026-11-07

The project graph reads Rust, next to Python, because the Owner's projects use both. A small
reader of its own, with no new dependency and no Rust toolchain.

Acceptance: a fictional crate yields the expected calls and flows, all extracted; three real
crates (lettre, async-openai, sentry-core) parse completely in 0.2–1.1 s, with the gaps
measured and explained (test code left out on purpose, functions generated by macros missed);
fuzzing found and fixed an infinite loop on malformed `use` groups. See
`docs/decisions/rust-graph.md`.

### Added

- Rust in the project graph (2.4): a small reader of its own (no Rust toolchain, no new
  dependency) finds functions, methods, structs, enums and traits, `use` imports, `mod`
  declarations and calls, with the same data tags and flows as Python. Test code
  (`#[cfg(test)]`, `#[test]`, `tests/`, `benches/`) is left out; macros are not expanded.
  Measured on three real crates (see `docs/decisions/rust-graph.md`). `reqwest` and `ureq` are
  third-party words.

### Changed

- "health" alone no longer marks special-category data in the graph; it needs a data word
  next to it ("health_data", "health_record"): `release-health` and health checks were
  tagged as health data on real projects.

## 2.3.0 — 2026-11-07

The laws software teams meet now: application dates quoted from the text, draft starter packs
for the GDPR, ePrivacy cookies, the Accessibility Act and the Cyber Resilience Act, and drafts
for record keeping. The US is not added (Owner decision); 2.4 is left to be decided.

Acceptance: the timeline was checked on the real final provisions of the AI Act, the CRA, the
EAA, NIS2 and the GDPR, every quotation verbatim. Every starter-pack pin was checked against
the official text; the GDPR pack was imported into a project, the GDPR fetched live and locked,
and a second import reported no text difference. The exports were tested on synthetic
activities, with hostile text kept out of Markdown and CSV formulas.

### Added

- Exports (2.3): `export ropa` drafts a record of processing activities in the shape of GDPR
  Article 30(1), with each fact's basis and every gap listed; `export dpia` drafts DPIA
  screening inputs (Article 35(3) and the WP248 criteria) with the signals the declarations
  show and no answers. Markdown, JSON, and CSV for the record.

- Application-date timeline (2.3): `timeline` lists the dated application, entry-into-force
  and transposition clauses of the retained text, word for word, reached or upcoming against
  the assessment date; also an MCP tool.
- The Cyber Resilience Act, the European Accessibility Act and NIS2 are part of the real-text
  test set (71, 35 and 46 articles).
- Draft starter packs: GDPR core (13 obligations), ePrivacy cookies and electronic marketing
  (2), European Accessibility Act services (2) and Cyber Resilience Act manufacturers (3),
  shipped in the package and listed by `pack starters`. Every pin is checked against the
  official text and every pinned article's digest is recorded. AI-assisted, reviewed by no
  one, no guarantee; imported with `--unsigned`, never as decisions.

## 2.2.0 — 2026-11-06

Jurisdictions become modules, and the United Kingdom is the second one, through
legislation.gov.uk. The EU behaves as before; the record formats do not change.

Acceptance: the UK GDPR, PECR and the Data Protection Act 2018 were fetched with the tool's own
retrieval and parse into 120 articles, 50 regulations and 259 sections, with titles checked
against the source (now a committed test set). A project with a PECR target ran
`revalidate --fetch-official` against the live site, locked 50 regulations, showed Regulation 6
with the UK version note in the report, and `cite-check` confirmed a verbatim quotation. See
`docs/decisions/jurisdictions.md`.

### Added

- Jurisdictions as modules (2.2): each jurisdiction registers its official hosts, its act
  identifiers and its well-known acts (`jurisdictions.py`). The EU is the first.
- The United Kingdom: `www.legislation.gov.uk` (The National Archives) is a registered host;
  UK identifiers (`ukpga/2018/12`, `uksi/2003/2426`, `eur/2016/679`, with an optional date)
  are read for `check`, the report's version note and the law lockfile; legislation.gov.uk
  XHTML is parsed into sections, regulations and articles, with amendment notes left out;
  the citation guard reads "section 170", "s. 170", "regulation 6" and "reg. 6" and knows
  the UK GDPR, the Data Protection Act 2018, PECR and other UK acts by name. The audit skill
  shows how to declare UK targets.
- A test set of UK texts (UK GDPR, PECR, Data Protection Act 2018) under the Open Government
  Licence, next to the EU texts.

### Fixed

- legislation.gov.uk may take over ten seconds to build a large act; its host gets a 30-second
  first-byte allowance, while an explicit retrieval budget always wins.
- `lock` counts provisions, not articles.

## 2.1.0 — 2026-11-06

Precision: the 2.0 base tested on hostile input, real law and real code, and fixed where it
fell short. No new jurisdiction yet; that is 2.2.

How it was tested:

- Every parser of untrusted input was fuzzed (12,000 random and mutated rounds plus targeted
  edge cases); a seeded version now runs in CI.
- The article parser and citation guard ran on real official texts (GDPR, AI Act, consolidated
  ePrivacy Directive), now a committed test set with digests.
- The project graph was measured on three real projects (django-allauth, sentry-sdk, Django),
  parsed only, with hand-judged samples; see `docs/decisions/graph-precision.md`.
- The WEC importer's field names were checked against the EDPS collector's source code.
- Signing, packs, the lockfile, the reports and the plugin were read adversarially; HTML views
  were checked with injection payloads in every free-text field (all escaped).

### Fixed

- The MCP server no longer stops on one deeply nested JSON message, limits nesting to 64
  levels on every Python, and rejects invalid request ids and NaN.
- SARIF imports no longer print a boolean line number.
- WEC imports read the site from `targetUrl`, as current collector versions write it (field
  names checked against the collector's source); older `uri_ins` files still work.
- `verify` binds each signature file to the decision it is named after and lists reviewed
  decisions left unsigned; signature files are read without following links, size-limited.
- `pack import` imports exactly the bytes whose signature it verified.
- `impact` reports law text the newer run did not retain as not compared, never as removed,
  and refuses another project's lock.
- The project graph tags data from identifiers, not prose or generic words, starts no flow in
  test code, and follows at most one ambiguous call per flow. On three real projects the
  false children's-data tags fell from hundreds to none (see
  `docs/decisions/graph-precision.md`).

### Added

- Citations are checked in the act they name ("Article 17 GDPR", "Article 5(3) of the
  ePrivacy Directive", "Article 99 of Regulation (EU) 2016/679"); well-known acts the run
  did not retain are reported as not checked.
- Tests: seeded fuzzing of every parser of untrusted input, and a test set of real official
  texts (GDPR, AI Act, consolidated ePrivacy Directive) in `fixtures/official/`.

## 2.0.0 — 2026-11-06

From a review tool to a compliance workspace: the law a review read is pinned, a law
change reopens exactly the decisions that cite it, decisions are signed by their
reviewer, agent-written citations are checked against the official text, and other
tools' results come in as untrusted evidence. This completes the 2.0 intent as the
Owner adopted it; GRC exports and the graph side of change impact move to 2.1.

Acceptance, recorded honestly:

- Every new command ran end to end on a synthetic project, by script: `revalidate`,
  `lock`, `sign` and `verify` with a real ed25519 key (unchanged, then reported as
  changed after an edit), `cite-check` (a pass, then a missing article and a misattributed
  quotation), `pack build`, `sign`, `verify` and `import`, `import-evidence` and `impact`.
- `mcp` ran as a separate process driven over stdio through the MCP handshake
  (`initialize`, `tools/list`, every tool, and an invalid call). The official MCP
  Inspector could not be run in this environment; no Claude client was connected.
- The check found three defects, fixed before release (see Fixed).
- Signing with the Owner's own key and a live band and panel check in a session were
  not done.

### Added

- Law lockfile and change impact (2.0 bolt 017): `lock` writes `eu-law.lock` (each act's
  version, source digest and per-article digests, from a verified run). `impact` lists
  the articles changed since the lock and the obligations, decisions and requirements
  citing them, with `--strict` for CI. The contract is generated from `models.py`
  (`LawLock`).
- Signed decisions (2.0 bolt 018): `sign` signs a reviewed applicability decision with
  the reviewer's SSH key (`ssh-keygen -Y sign`), covering the decision, its obligation, the
  locked article digests, the evidence digests and the commit. `verify` checks each
  signature against an allowed-signers file and names what changed since signing.
- Citation guard: `cite-check` checks that cited articles exist in the retained text and
  quotations appear verbatim in the cited article. `mcp` serves it, `article_search` and
  `next_steps` as read-only MCP tools over stdio.
- Imports (2.0 bolt 019): `import-evidence --kind wec|sarif` keeps an EDPS Website
  Evidence Collector inspection or a SARIF log as untrusted evidence under
  `.eu-compliance-guard/imports/`, with a summary by concept. Declarations are never
  changed. Synthetic fixtures only.
- Obligation packs (2.0 bolt 020), format only: `pack build` drafts a pack of portable
  obligations with their article pins and the locked article digests; `pack sign` and
  `pack verify` use the reviewer's SSH key; `pack import` adds candidate obligations
  and targets, never overwrites a different record, and never maps or decides. The
  contract is generated from `models.py` (`ObligationPack`).
- MCP review tools (2.0 bolt 021): the `mcp` server also serves `ground` (read-only
  proposals) and `pr_check` (given a unified diff).
- `--version` prints the installed version.

### Changed

- The README is a short overview; the full command reference moved to `docs/cli.md`
  and the plugin's band, panel, dashboard and hook to `docs/plugin.md`.
- Package metadata (authors, classifiers, keywords, project links), a contributing
  guide, a security policy, and issue and pull-request templates.

### Fixed

- Grounding and the project graph no longer read the tool's own outputs (`imports/`,
  `signatures/`, `eu-law.lock`) as project code when the files root is the declarations
  folder: imported tool output is untrusted and was proposed as code evidence.
- Importing a pack into the project it came from no longer reports a conflict.
- `sign` says when no `eu-law.lock` exists, so the signature pins no article text.

## 1.5.0 — 2026-11-06

Trustworthy guidance: suggestions explain themselves, a suggestion becomes a mapping in
one step, and the law shown is the version in force, with a notice when a newer
consolidation exists. This completes the 1.5 intent.

Acceptance, recorded honestly:

- The plugin loaded in a real Claude Code session, its commands were listed, and
  `/eucg-audit` started (initialising a fictional project with `--synthetic`).
- The accept flow was verified on real runs, with screenshots. Before, Mapping was
  5/10 and the next step was to map the requirement. After `accept` and a new run,
  Mapping was 10/10, `check` stayed valid, and the next step was a reviewer's
  applicability decision. Nothing was decided automatically.
- Not verified live: the band and side panel updating inside an interactive
  session. This environment does not allow driving a second Claude agent; the
  automated band tests (33) cover them.

### Added

- Newer-consolidation notice (1.5 bolt 008, part two). With `revalidate --fetch-official`,
  each act target with a CELEX number gets one fixed query to the Publications Office's
  SPARQL endpoint, through the same registry-checked, bounded retrieval as act text. CSV
  answers are admitted for these requests only. A newer consolidation, a base CELEX with
  a consolidation in force, or an unreadable answer becomes a review gap; declarations
  are never changed.

## 1.4.0 — 2026-11-05

Act on suggestions in one step, see which version of the law you are reading, and use
the plugin on real repositories: faster grounding, monorepos, the newest run by
completion, CI on every pull request, and code evidence in the side panel.

### Added

- Panel grounding (1.5 bolt 010): each fact the owner still has to confirm shows its top
  code line (`code app/roles.py:12`), and a **Confirm code evidence** button opens
  `/eucg-next`, which asks the owner before pinning anything. Locations are validated
  (plain path segments, no `..`, a line number), and no run text is shown.
- Real repositories (1.5 bolt 009):
  - `ground` searches through an inverted index. 300 facts over about 60,000 lines of
    real Python now take 0.6 s instead of 33 s, with identical results (checked on 400
    queries and pinned by a full-scan test).
  - The newest run is the one completed last (its completion marker), not the last
    name, in the CLI and the band.
  - `pr-check` in a monorepo matches diff paths below the project folder: run it from
    the repository top with `--input services/api/.eu-compliance-guard/declarations.json`.
- `accept REQ=TARGET:ARTICLE` (1.5 bolt 007) maps a requirement to a candidate
  obligation citing that article, reused or created, with revisions and pins updated
  atomically. It never records an applicability decision. `/eucg-next` offers it for
  mapping steps.
- Law in force (1.5 bolt 008, part one): CELEX numbers are read from target identifiers
  and Cellar or EUR-Lex URLs without a regular expression. `check` warns when an act
  target uses a base CELEX (the act as first published) and lists each target's
  version. Each article excerpt in the report names the consolidation date or says the
  text is as first published.

## 1.3.0 — 2026-11-05

Review progress at a glance, a project graph that follows data through the code,
measured search, and hardening: a 14-day version cooldown, verified official hosts,
fewer regular expressions, a legal notice on every output and a determinism test.

### Added

- Review progress: `score` shows separate meters for one run (Alignment, Law text,
  Facts, Decisions, Mapping, Reviews), each points out of 10 for recorded review
  steps, with a family screening line and unscored record hygiene. There is no total
  and no verdict; see `docs/decisions/dashboard-review-progress.md`.
- The HTML view leads with a Review progress section, and `view` also writes
  `views/<run>.scorecard.json` (0600).
- The band and panel show the meters in fixed format (one `score --json` call per run
  replaces the `next` call).
- `frontend/` has a local, offline dashboard page that renders a scorecard file.
- **Dashboard** button (band hotkey `d`, also in the panel): `view --dashboard --open`
  opens `views/<run>.dashboard.html`. It is one static, at-a-glance page with no build,
  no server and no script.
- `make verify-hosts` checks, with consent, that each official host answers over
  HTTPS. `docs/official-hosts.md` names each host's operator and purpose, and a test
  keeps it in step with the code.
- `make eval`: a versioned synthetic evaluation set (1.5 bolt 005) for article search
  and grounding, with a baseline floor enforced by a test. Baseline: articles top-1
  15/20 and top-3 18/20 on tuning, 14/20 and 17/20 held out; grounding top-1 7/10 and
  top-3 8/10.
- Graph view (2.0 bolt 016): `graph --view [--open]` and the panel's **Graph** button
  open a static, script-free page. It shows a fixed-layout picture of the functions on
  data flows or touching a concept, with flows highlighted and ambiguous calls dashed.
  It also lists each flow with its pinned facts, and law to code: fact, then the
  requirements and obligations relying on it.
- Graph-aware `pr-check` (2.0 bolt 015): with declarations, a diff that adds lines inside
  a function on a data flow lists that flow and the facts pinned on it, or says no
  fact covers it. The graph comes from the checked-out code; `revalidate` still reads
  only selected files, so runs do not record a graph.
- Hybrid search (2.0 bolt 014) was measured and not adopted. Re-ranking code
  candidates by graph closeness gave no gain on either grounding set (7/10 and 5/6
  top-1 with or without it); see `docs/decisions/hybrid-search.md`. Six multi-file
  grounding cases now join `make eval`.
- Path evidence (2.0 bolt 013): `ground` follows data through the project graph.
  Candidates inside a flow show the call path, for example `plan_meals → ask_model`,
  with each hop's `file:line`. Flows from personal, health or children's data to AI,
  tracking, third parties or marketing that no pinned evidence covers are listed for
  review. `make eval` now reports flows found (1/1) and unexpected flows (0).
- `graph` (2.0 bolt 012) builds a deterministic project graph by static parsing only:
  Python files, classes and functions, imports and calls (resolved like Python, with
  `ambiguous` labels instead of guesses), and the concepts each function touches. The
  contract is generated from `models.py` (`ProjectGraph`). It maps 60k lines in about
  3 s.
- Explained suggestions (1.5 bolt 006): each article suggestion and grounding
  candidate lists the terms that matched. Each term is marked as coming from the
  statement or fact, or bridged through the legal or concept vocabulary (with the word
  it came from). This appears in the view, in `ground` text and in JSON. The search
  also improved:

  | Set | Before (top-1, top-3) | After |
  |---|---|---|
  | Articles, tuning | 15, 18 | 17, 20 |
  | Articles, held out | 14, 17 | 14, 17 |
  | Grounding | 7, 8 | 7, 10 |

  The changes are rectification and parental-consent bridge terms, and base word
  forms ("renews" finds `auto_renew`) in grounding. Only tuning misses were used.
- Every text, markdown and HTML output ends with one legal notice: not legal advice,
  the named reviewer decides and is responsible, no warranty.

### Changed

- Hardening (1.5 bolt 011):
  - Dependency resolution waits 14 days for new releases (`[tool.uv] exclude-newer`).
    Dependabot updates uv, npm and GitHub Actions with a 14-day cooldown, while
    security updates go through without the wait.
  - The pull-request check example pins its actions to commit SHAs.
  - Parsing regular expressions are replaced by explicit parsers, and tests compare
    each parser with the old pattern on random inputs. Only short, anchored validators
    remain, and a lint test blocks any new regular expression in Python or in the band.
  - A test runs the pipeline under different hash seeds, time zones and locales and
    requires byte-identical outputs.
- Gap phrases that other modules read back and the provision pin checks are shared
  constants and one helper in `revalidation.py`; recorded output is unchanged.

## 1.2.0 — 2026-11-05

Licence change and the Great Auditor fixes: 83 confirmed defects found by an agent
audit that tested every command, option and flow, each fixed with a regression test.

### Changed

- Licence changed from MIT to GNU AGPL-3.0-only, with an attribution notice
  (`NOTICE`, section 7(b)). Releases 1.0.0 and 1.1.0 remain MIT.
- `init` keeps file paths inside the project: outside `.eu-compliance-guard/` it sets
  `"files_root": "declarations_dir"`. It refuses symlinked folders and an empty date.
- A missing declarations file is reported as `io-failed`; an unreadable or linked path
  as `unsafe-path`. A named `pr-check --input` must exist.
- Commits are unsigned and carry only the Owner's identity. Some earlier commits on
  `main` (up to 1.1.0) carry co-author trailers, one carries an agent identity, and
  some show as Unverified on GitHub; history was not rewritten.

### Fixed

- `next` gives every open requirement a step (new `review` kind), asks to ground a
  fact again when its pinned file changed, names what blocks a recorded decision, and
  never offers to fetch a target the fetch policy refuses.
- `ground` never grounds legal facts (lawful basis, roles, size) in code, lists facts
  whose pinned file changed, re-pins them cleanly, keeps uncited touchpoints visible,
  checks every `--apply` before writing any, accepts only plain line numbers, keeps the
  file mode and reports unreadable folders as skipped. `--json` works with `--apply`.
- `check` reports every problem in one pass with its JSON location (including stale
  pins and the revision cascade), encoding problems, oversized files and truncation,
  and never prints unknown keys. A changed grounded code file is a warning to ground
  again, not a digest to copy.
- Run history never restores withdrawn support because a file was briefly missing;
  same-run renewals are explained; unreadable runs report `unsafe-path`.
- Article text: chapter and section headings, scripts, tables of contents, correlation
  tables and annex suffixes no longer leak into or split articles; BOM and upper-case
  media types are handled.
- `pr-check` rejects coloured or non-diff input, strips mnemonic prefixes, counts
  renames once and keeps added lines of combined merge diffs.
- Output that cannot be written is `io-failed` (never a traceback or exit 1); text the
  console cannot encode is escaped. A relative `XDG_STATE_HOME` is ignored.
- The view and report name removed historical obligations, show each source's type and
  style only admitted retrievals as confirmed. The band shows the run state and says
  when the default level is off.
- `revalidate` handles up to the bundle's gap limit, and its requirement gaps name the
  real blocker.

## 1.1.0 — 2026-11-04

Grounded assumptions, article text and guidance on what to do next.

### Added

- **Grounding (`ground`):** a local, explainable index of the project's code (Okapi
  BM25 over identifier-split tokens with a legal-concept lexicon; no network, model
  or embeddings). It ranks `file:line` candidates for each assumed or unknown fact and
  lists touchpoints no fact covers. `ground --apply FACT=PATH:LINE` pins a confirmed
  technical fact as `observed`, with the file's digest as evidence; organisational
  facts are refused. A later change to the file reopens the gap.
- **Act text from the Publications Office:** `publications.europa.eu` (Cellar) joins
  the fixed host registry as the sixth host, with the target's language tag sent as
  `Accept-Language` and a same-host http→https redirect upgrade only for that host.
- **Article text in the report:** each declared "Article N" reference expands to the
  article's title and text from the act bytes the run retained. Each requirement
  lists up to three articles to read, ranked by a local text search that bridges
  everyday words to legal vocabulary. Both are labelled unreviewed candidates.
- **Next best step (`next`, `/eucg-next`):** open steps ranked by how many open
  requirements each one unblocks (retrieve text, confirm a fact, review a source,
  decide applicability, map a requirement, screen families), in the CLI, the report,
  the band and a skill that walks through step 1 without filling in review data.
- **Pull-request check (`pr-check`, `/eucg-pr`):** deterministic screening of a
  diff's added lines for legal concepts with candidate families, whether the
  declarations mention each one, and evidence or requirements in changed files.
  Markdown for a PR comment, JSON, and `--strict`. A GitHub Actions example keeps one
  marked comment updated.
- **Side panel (`/eucg-panel`, band Panel button):** a pane beside the chat with the
  top three steps, the facts the owner still has to confirm and open gaps by area.

### Changed

- The band shows the next best step and has Next step and Panel buttons.
- Report IDs wrap at hyphens.

### Fixed (release review)

- `ground --apply` never follows a planted temp-file symlink and reads declarations
  without following links; a bare relative `--input` resolves the project root.
- Oversized project files are skipped without being read whole.
- Plain-text acts no longer open an article at a reference such as "Article 6(1)".
- Source targets with an invalid language tag fail as `invalid-language` instead of
  being fetched in English.
- Diff paths can no longer break out of PR comment code spans; broad words alone no
  longer count as a concept being mentioned.
- The band ranks each run once, keeps a failed ranking instead of retrying every turn,
  and never lets an older run's ranking replace the newest.
- Skills never pin evidence or record review fields the owner did not give.

## 1.0.0 — 2026-11-03

First stable MVP of the read-only requirements-to-law revalidation workflow.

### Added

- **Declarations and reports (Bolt 001):** versioned declarations with accountable
  review attestations. Private, immutable run directories with completion-marker
  digests. JSON and escaped Markdown reports that put each issue beside its declared
  legal provision.
- **Official-source retrieval (Bolt 002):** `--fetch-official` with a fixed
  five-host registry, pinned DNS and verified TLS, validated redirects, byte and time
  bounds, and a disposable helper process. Retrieved bytes become unreviewed
  candidates; every failure is a safe recorded attempt.
- **Revalidation (Bolt 003):** `--previous` verifies one retained run, records
  `comparison.json` and freshness overlays, and makes changed dependencies stale.
- **Claude Code plugin:** the `/eucg` mode (lite, full, strict, off) and the
  `eucg-review`, `eucg-audit`, `eucg-gaps`, `eucg-status` and `eucg-help` skills.
  Also a SessionStart hook, a band above the prompt with Audit, Review, Gaps,
  Open report and Help buttons, and the plugin icon.
- `view` writes a verified, script-free HTML view of a run and can open it in the browser.
- `init` writes a valid starter declarations file. `check` reports each problem with
  its JSON location, the observed digest of every selected file, and whether each
  source target can be fetched. `check --previous` names every record whose content
  changed without a higher revision.
- `state-dir` prints and creates (0700, symlink-free) the private run storage, keyed by
  the declared `project_id`. The hook, band and skills use the same location.
- `eu-compliance-guard` console command and `make plugin-check`.
- The report view opens with "Questions for the project owner": each assumed or
  unknown fact, its current answer and the requirements relying on it. Open gaps are
  grouped by area with counts, collapsing the long fact and family lists. The
  predecessor comparison says added, removed or changed and names obligations instead
  of digests.

### Changed

- Cross-reference errors name their JSON location and identifiers, for example
  `requirements[0].fact_refs[0]: fact-x is pinned at revision 7 but declared at revision 0`.
- Runtime dependencies are Pydantic only. FastAPI and Uvicorn moved to the optional
  `api` extra; the plugin runs the CLI with `uv run --no-dev`.
- The fake-process executor tests no longer depend on host sandbox tools, so
  `make check` completes on hosts without bubblewrap.

### Fixed (release team audit)

- **Withdrawn support persists.** A plain rerun with `--previous` no longer restores
  withdrawn support. Support returns only when the applicability decision and every
  evidence review are new revisions reviewed between the two runs. Family screenings
  follow the same rule, and attestations dated after a run are review gaps. Renaming
  or removing and re-adding an obligation cannot reuse old reviews, and renewing an
  obligation and its family screening together restores both.
- **Freshness per source.** Retrieved bytes confirm only the source with those same
  bytes, even when several sources share one target.
- **Storage per project.** Runs are stored per declared `project_id`, not per folder
  name. Runs of another project are never shown, and the band follows the session's
  project folder (worktrees included).
- **Documented maxima.** 200 requirements and 200 obligations publish and revalidate
  across runs. The bundle limit is 16 MiB.
- **Diagnostics.** `check` never echoes declared values or raw unknown keys. Symlinked
  path components report `unsafe-path`. The CLI runs with `python -P`, so a project's
  own package cannot replace it.
- **Band report link.** The band hides its report link once a newer run exists.
- **Labels and levels.** The session hook labels fictional runs and keeps a level
  chosen earlier in the session. Offline and fetch runs of one version count as the
  same configuration.

See [the audit report](memory-bank/bolts/003-legal-revalidation-cli/v1-team-audit-report.md).

### Known limits

- EUR-Lex answers scripted clients with a bot challenge; declare manually
  downloaded acts as selected sources. Only text and HTML sources can support a
  mapping; a PDF always remains a manual-identity-review gap.
- All input, output and predecessor paths must be free of symbolic links.
- Revalidation compares only against the predecessor you name; naming an older run (or
  none) compares against that state.
- Some official pages change bytes on every request, so exact-byte comparison reports
  them as changed.
- The band draws only in interactive Claude Code (terminal or desktop app).
- No output is a compliance verdict, and reviewer names are self-attested.
