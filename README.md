# EU Compliance Guard

[![CI](https://github.com/yo1am1/eu-compliance-guard/actions/workflows/ci.yml/badge.svg)](https://github.com/yo1am1/eu-compliance-guard/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/yo1am1/eu-compliance-guard)](https://github.com/yo1am1/eu-compliance-guard/releases)
[![License: AGPL-3.0-only](https://img.shields.io/badge/license-AGPL--3.0--only-blue)](LICENSE)

A Claude Code plugin and command-line tool that keeps a project's EU and UK legal review
traceable. It maps declared project requirements to candidate obligations and
official sources, then keeps every unanswered question visible as a review gap. It
writes private, tamper-evident reports and revalidates them when the project or the
law changes.

It is read-only and never gives a compliance verdict. A named human reviewer makes
every legal decision, and the tool records who decided what, against which text and
evidence. No output, test or example implies a real compliance audit.

**Version 2.2.0.** See the [changelog](CHANGELOG.md) and the [roadmap](docs/roadmap.md).

![Walkthrough: the band and side panel in Claude Code, then article text and articles to read in the report](docs/images/walkthrough.gif)

<details>
<summary>Screenshots</summary>

**In Claude Code:** the band above the prompt names the next step and shows progress;
the side panel lists the top steps, the questions for the owner and open items by area.

![The band and the side panel in Claude Code](docs/images/plugin-band-panel.png)

**In the report:** each declared article opens to its text, retrieved from the
Publications Office and labelled as an unreviewed candidate.

![Article text beside each declared legal reference](docs/images/report-article-text.png)

**Articles to read:** each requirement lists the articles a local text search ranks
highest. A suggestion, not a mapping.

![Articles to read under each requirement](docs/images/report-articles-to-read.png)

All screenshots show the fictional FitBox example project.

</details>

## Features

**Review workflow**

- Declarations of requirements, facts, sources and obligations, validated with located
  diagnostics (`init`, `check`).
- Official text from verified hosts, fetched only with consent: EU law from EUR-Lex and the
  Publications Office, with a notice when a newer consolidation exists, and UK law from
  legislation.gov.uk, by section, regulation or article (`revalidate --fetch-official`).
- Private, digest-verified runs that revalidate against their predecessor, so stale
  reviews never carry over silently.
- The next best step, review-progress meters, article suggestions with their reasons,
  and one-step mapping (`next`, `score`, `accept`).

**Code awareness**

- Facts grounded in code lines, and a static project graph that follows data from
  fields to network, storage and model calls (`ground`, `graph`).
- A pull-request screen for legal touchpoints, with a GitHub Action (`pr-check`).

**Law that stays current, decisions that stay accountable**

- A law lockfile with per-article digests, and the decisions a law change reopens
  (`lock`, `impact`).
- Decisions signed with the reviewer's SSH key, bound to the locked text and the
  evidence (`sign`, `verify`).
- A citation guard for agent-written text: cited articles must exist and quotations
  must be verbatim (`cite-check`).
- Drafts for record keeping: a record of processing activities (Article 30) and DPIA
  screening inputs (Article 35), as Markdown, JSON or CSV, with every gap listed (`export`).
- An application-date timeline: when each act, or each part of it, applies, quoted from the
  text and marked reached or upcoming against the assessment date (`timeline`).
- Signed, reusable obligation packs, as a format (`pack`).
- Imports of EDPS Website Evidence Collector and SARIF results as untrusted evidence
  (`import-evidence`).
- An MCP server for any agent, with read-only `cite_check`, `article_search`, `ground`,
  `pr_check`, `timeline` and `next_steps` tools (`mcp`).

## Quick start (Claude Code)

```text
/plugin install eu-compliance-guard --marketplace yo1am1/eu-compliance-guard
```

On older Claude Code versions, run `/plugin marketplace add yo1am1/eu-compliance-guard`,
then `/plugin install eu-compliance-guard@eu-compliance-guard`. The plugin runs its CLI
with [uv](https://docs.astral.sh/uv/), which downloads Pydantic on first use.
Without uv it needs a `python3` (3.12 or later) that has Pydantic installed. The
session hook says so when neither is available.

In your project:

1. Run `/eucg-audit`. It creates `.eu-compliance-guard/declarations.json` with
   `init`, drafts requirements and facts from the code (marked `assumed` or `unknown`),
   and runs `check` until the file is valid. It then writes a private report and
   ranks what needs attention.
2. Answer the open questions and add reviews as the named reviewer. The agent never
   fills in a reviewer, a review time or a legal decision.
3. Run `/eucg-audit` again later. It offers the previous run as `--previous`, so
   changed dependencies make earlier reviews stale instead of silently carrying over.

| Command | What it does |
| --- | --- |
| `/eucg [lite\|full\|strict\|off]` | Mode: notices EU legal touchpoints while coding and keeps declarations and gaps explicit |
| `/eucg-review [target]` | Maps a diff to the eleven candidate legal families and the facts to declare |
| `/eucg-audit [--fetch-official] [--previous <run>]` | Prepares declarations, runs the private report and ranks what needs attention |
| `/eucg-next` | Walks through the step that unblocks the most open requirements |
| `/eucg-pr [target]` | Screens a branch or PR diff for legal touchpoints; can set up the GitHub Action |
| `/eucg-gaps` | Ledger of open review gaps from the latest run |
| `/eucg-status` | The latest run at a glance |
| `/eucg-panel` | Opens the side panel with the latest run's next steps, owner questions and gaps by area |
| `/eucg-help` | Reference card |

The band, side panel, dashboard, report view, session hook and permission settings are
described in the [plugin guide](docs/plugin.md).

## Command-line tool

```sh
uv tool install git+https://github.com/yo1am1/eu-compliance-guard   # or: pip install <checkout>

eu-compliance-guard init --project-id shop --jurisdiction EU
eu-compliance-guard check
runs=$(eu-compliance-guard state-dir)          # private, symlink-free run storage
eu-compliance-guard revalidate --input .eu-compliance-guard/declarations.json --output "$runs/run-001"
eu-compliance-guard next                       # the step that unblocks the most open requirements
eu-compliance-guard lock                       # pin the law this review read
eu-compliance-guard view --run "$runs/run-001" --open
```

Every command, its options and exit codes are in the
[command-line reference](docs/cli.md). To give other agents the read-only tools, run
`claude mcp add eucg -- eu-compliance-guard mcp`.

## Limits

- No output is a compliance verdict, legal advice or an exhaustive search of EU
  law. The eleven candidate families are screening keys, not a corpus. Every text,
  markdown and HTML output ends with the same notice: the named reviewer decides and
  is responsible, and the tool comes without warranty (see `LICENSE` and `NOTICE`).
- Reviewer names are self-attested unless a decision is signed with `sign`; a signature
  shows who recorded a decision against which text, not that it is right.
- Retrieval checks cannot prove a document's identity or currency; a reviewer must.
  National hosts and PDFs need manual review.
- Processing budgets are cooperative, not a hard CPU or filesystem deadline. The
  bounded Linux execution helper is not an enabled scanner, and its real
  containment is unverified.
- Scanners of our own, a Graphify import, the API (optional `api` extra) and remediation
  automation are later work. Obligation packs ship as a format only. No lawyer reviews packs or outputs, and nothing is guaranteed. The dashboard shows one run's review progress from a local file; it
  manages nothing.

## Documentation

| Document | Contents |
| --- | --- |
| [Plugin guide](docs/plugin.md) | Slash commands, band, side panel, dashboard, session hook, permissions |
| [Command-line reference](docs/cli.md) | Every command; declarations, runs, official sources and the 2.0 features |
| [Official hosts](docs/official-hosts.md) | The verified EU hosts and how they are checked |
| [Implementation status](docs/implementation-status.md) | What exists, what was verified and how |
| [Roadmap](docs/roadmap.md) | Released versions and what comes next |
| [Decisions](docs/decisions/) | Recorded design decisions and measurements |
| [Specifications v2](specs_v2/README.md) and the [memory bank](memory-bank/) | Requirements, plans and bolt records |
| [Historical specifications](specs/eu-compliance-audit/requirements.md) | Preserved snapshots from [agentic-setup](https://github.com/yo1am1/agentic-setup); paths and draft labels describe their original home |

## Contributing, security and licence

- [Contributing](CONTRIBUTING.md): setup, checks, conventions and the release steps.
- [Security policy](SECURITY.md): how to report a vulnerability privately.
- [Licence](LICENSE): GNU AGPL-3.0-only from 1.2.0 (1.0.0 and 1.1.0 stay MIT). If you
  modify it or run it as a service, publish your source under the AGPL and credit
  EU Compliance Guard as [NOTICE](NOTICE) requires. Contributions need the author's
  agreement to relicense, so the project can also offer a paid service.
- [Dependency notices](THIRD_PARTY_NOTICES.md).
