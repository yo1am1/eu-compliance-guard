---
bolt: 003-legal-revalidation-cli
created: 2026-11-04T05:10:00Z
status: recorded
---

# Live interactive end-to-end check — 2026-11-04

The Owner asked for end-to-end tests with real clicks and screenshots of the plugin,
its outputs, skills and documentation. The plugin was installed from GitHub through
the marketplace flow. Real interactive Claude Code 2.1.318 ran inside a terminal
(tmux, 150×48), and the band was driven with real key presses: ctrl+x Tab focuses it,
then the hotkeys. The project was a new fictional subscription app ("FitBox": sign-up
with weight and birth year, monthly auto-renewal with email-only cancellation, an
analytics cookie set before any banner, and an LLM "Coach Anna" chat). No real project
or live legal source was involved.

| Step | Result |
| --- | --- |
| First start, no `.eu-compliance-guard/` | No band; skills listed in the typeahead under `eu-compliance-guard:` |
| `/eucg-audit` typed in the session | `init` → drafted 9 requirements, GDPR/ePrivacy/CRD/AI Act candidate obligations, every fact `assumed`/`unknown`, no invented review → `check` → private run (`partial`, 81 gaps) → 11 ranked attention items |
| Band after the turn | Rendered live: state, gaps, `0/9 requirements supported`, assessment age, fictional label, five buttons |
| Band **Open report** (`o`) | Verified view written (0600) and a clickable `Report view:` link shown |
| Band **Gaps** (`g`) | `/eucg-gaps` ledger, 81 gaps in 6 groups |
| Code change, then band **Review diff** (`r`) | Flagged weight sent to the LLM as possible Article 9 health data, profiling, a missing minimum age (DE/FR/PL), and the existing AI-disclosure requirement now covering the new path. Asked before writing |
| Accept → declarations updated → asked before using the predecessor → revalidation | Revisions raised; run 2 compared with run 1; band refreshed to `101 gaps · 0/12` |
| Band **Help** (`h`) and **Audit** (Enter on default focus) | Help card shown. Audit noticed the declarations were byte-identical to the latest run and offered to skip a redundant run |
| Report page in Chromium (desktop, dark, 390 px mobile, keyboard) | No scripts, no external links, no horizontal page scroll; keyboard focus reaches the scrollable tables |
| README CLI example, verbatim, via `uv tool install` | All seven commands exit 0 |

## Defects found and fixed

- **Stale band link:** after a new run, the band's `Report view:` link still opened
  the previous run's page. It is now shown only for the run the band summarizes.
  Verified live after reinstalling: a newer run plus one turn hid the old link.
  (`8a01651`)
- **Report page value:** the page opened with a flat list of 101 gaps, starting with
  23 identical "assumed, unknown or conflicting declaration needs review" rows, while
  the important items sat far down the page.
  - The page now leads with **Questions for the project owner**: each fact's question,
    current answer, basis, owner and the requirements relying on it.
  - Gaps are grouped by area with counts, and the long fact and family groups start
    collapsed (native `<details>`, no scripts).
  - The comparison says added, removed or changed with short digests (full digest on
    hover), and names the historical obligation instead of a hashed disposition id.

  (`c6ba9de`)

## Not covered

- Opening a real browser: the container has none, so `view --open` reported
  `no-browser` as designed.
- The VS Code and desktop-app surfaces; the band tests cover them through
  `claude plugin test`.

`make check` passes 219 tests; `claude plugin test .` passes 7 band tests.
