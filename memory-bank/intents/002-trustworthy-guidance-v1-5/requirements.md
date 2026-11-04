---
intent: 002-trustworthy-guidance-v1-5
phase: inception
status: draft-awaiting-owner-approval
created: 2026-11-04T18:00:00Z
---

# Requirements: Version 1.5, trustworthy guidance

## Destination

By 1.5, a developer can trust why the plugin suggests something, act on a suggestion in
one step, and know the law shown is the version in force. The plugin also behaves
correctly on real repositories: monorepos, renames, many facts and many runs.

1.5 stays read-only toward the law: no verdicts and no invented reviewer data. Every
legal decision is still made by a named person.

## Why now

The 1.1 audits found the same weak spots repeatedly:

- Suggestions are opaque. Nobody can see why an article was proposed.
- Acting on a suggestion means editing JSON by hand.
- Act targets returned the original act text, not the law in force.
- Several real-repository cases were deferred: monorepos, renames, run ordering and
  speed.

## Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-1 | **Explain every suggestion.** Article suggestions and grounding candidates show the terms that matched, and say whether each came from the statement directly or through the legal-vocabulary bridge. The report, `ground` and the panel show them; JSON outputs carry them. | Must |
| FR-2 | **Accept a suggestion.** `accept REQ=TARGET:Article N` adds the provision to a candidate obligation (new or existing), raises the revisions and pins, validates, and writes atomically without following links. Applicability stays `unresolved` until a named reviewer decides. `/eucg-next` offers it for `mapping` steps. | Must |
| FR-3 | **Law in force.** Act targets can name a consolidated CELEX version. `check` warns when a target uses a base CELEX for an amended act. The report shows the version date next to each article excerpt, and a fetch records the consolidation the server returned. | Must |
| FR-4 | **Newer consolidation notice.** With consent, `check --fetch-official` asks the Publications Office whether a newer consolidation exists than the one declared, and records the answer as a review gap. It never auto-updates a declaration. | Should |
| FR-5 | **Real-repository correctness.** The newest run is chosen by recorded end time. The files root comes from the location of `--input` (monorepos). `pr-check` handles renames, copies, binary and mode-only changes. `..` paths are handled the same way in every command. | Must |
| FR-6 | **Speed.** `ground` uses an inverted index, so 300 facts over 60k lines finish within 5 s. `view` stays under 5 s for 16 acts and 200 requirements. | Must |
| FR-7 | **Grounding in the panel.** For each fact still to confirm, the panel shows its top code candidate (`file:line`) and a Confirm button that runs the `/eucg-next` flow. The text stays fixed-format: the location is validated, and no free text from the run is shown. | Should |
| FR-8 | **Search quality you can measure.** A fixed, versioned evaluation set of synthetic requirements with expected articles, plus `make eval`, which reports top-1 and top-3 for article search and grounding. A search change ships only with before/after numbers on that set. | Must |
| FR-9 | **Live testing in CI.** A GitHub Actions workflow runs `make check` and `make plugin-check` on every pull request, and the PR-check example runs against the repository itself. | Should |

## Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-1 | No new runtime dependencies. Stdlib plus Pydantic only, as in 1.x. |
| NFR-2 | Every new write path refuses links, writes atomically and validates before writing, as `ground --apply` does. |
| NFR-3 | Network use only with the existing per-run consent and the fixed host registry. |
| NFR-4 | Every user-visible suggestion is labelled as a candidate, never as a mapping or a conclusion. |
| NFR-5 | Every output says it is not legal advice or a verdict; failures surface as gaps, never as silent success. |
| NFR-6 | Deterministic: identical inputs give byte-identical outputs, proven by a run-twice test. |
| NFR-7 | Regular expressions only as anchored, bounded `fullmatch` validators; parsing is structured. Enforced by lint. |
| NFR-8 | Only verified official hosts; SHA-pinned actions; a 14-day cooldown on new versions, except security hotfixes. |

## Out of scope for 1.5

The dashboard, multi-project views, scanners, signed attestations, national overlays and
law-change monitoring belong to [2.0](../003-compliance-workspace-v2/requirements.md).

## Acceptance

1.5 ships when:
- FR-1, FR-2, FR-3, FR-5, FR-6 and FR-8 pass their stories;
- the end-to-end agent team finds no blocker or major defect;
- a live Claude Code session shows an explained suggestion accepted into the
  declarations and closing its mapping step in the next run.
