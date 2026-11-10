# Rust in the project graph (2.4, 2026-11-07)

## Decision

The Owner's projects use Python and Rust, so 2.4 teaches the project graph Rust (instead of
JavaScript/TypeScript). Of three options, the Owner chose a small reader written in Python:
no new dependency and no Rust toolchain, deterministic, at the cost of missing what only a
compiler sees (macro expansion, types). A tree-sitter parser (a native dependency) and a
`syn`-based helper (needs a Rust toolchain) were not adopted.

## How it reads Rust

- A tokenizer drops comments (nested `/* */` too) and keeps strings, raw strings, byte strings,
  char literals and lifetimes apart, so code inside a string or comment is never read as code.
- Items: `fn` (functions; `Type.method` inside `impl` and `trait`), `struct`, `enum`, `union`,
  `trait` (classes). `impl Trait for Type<T> where …` names the methods after `Type`.
- `use` trees (`crate::`, `super::`, `self::`, groups, `as`, globs) and `mod` declarations
  (`a.rs`, `a/mod.rs`, `lib.rs`, `main.rs`, `bin/`) link files of one crate.
- Calls: `f()`, `path::f()`, `Type::f()`, `Self::f()`, `f::<T>()` and `.method()`. Macros and
  standard-library constructors (`Ok`, `Some`, `Box` …) are not calls; common standard-library
  methods (`.clone()`, `.into()`, `.iter()` …) are never linked to project code. A method call
  reaches only methods.
- Test code (`#[cfg(test)]`, `#[test]`, `#[tokio::test]`-style attributes, `tests/`, `benches/`)
  and `macro_rules!` bodies are left out; `#[cfg(not(test))]` code is kept. An imported external crate's name counts for the functions that use it, so
  `use reqwest::Client` makes `Client::new().post(…)` a third-party call.
- Python and Rust names are never linked to each other.

## Measurements

Three crates were downloaded from crates.io (published more than 14 days earlier), parsed and
never built: lettre 0.11.23 (email), async-openai 0.42.2 (AI client), sentry-core 0.49.3 (error
tracking).

| Crate | Lines | Files parsed | Time | Function nodes / `fn` keywords | Call edges (extracted / ambiguous) |
|---|---|---|---|---|---|
| lettre | 16,918 | 73 / 73 | 0.4 s | 678 / 895 | 440 / 1,138 |
| async-openai | 37,643 | 260 / 260 | 1.1 s | 730 / 987 | 562 / 1,324 |
| sentry-core | 9,920 | 37 / 37 | 0.2 s | 417 / 494 | 235 / 441 |

In lettre, 178 of the 217 `fn` keywords without a node are test code (left out on purpose).
Of the rest, the 23 checked are functions generated inside `macro_rules!` bodies, which only
macro expansion would show, and tests carrying a second attribute; the remaining difference
was not traced one by one. Skipping common standard-library methods cut
ambiguous edges by about 40% (lettre 1,837 to 1,138) while keeping the extracted ones. The
remaining ambiguous calls are methods such as `new` or `send` defined on several types;
telling them apart needs type inference. Flows follow at most one ambiguous call.

The three crates are libraries, so they have no data-to-sink flow of their own (sentry-core
had three, all false, from the string `"release-health"`, which led to the "health" change
below). The fictional crate in `fixtures/eval/graph-project-rust` shows the flows: a member's
weight sent to a model client and an email sent through `reqwest`, both extracted.

## Changed for Python too

"health" alone no longer marks special-category data: `release-health` (sentry) and health
checks were tagged as health data. It now needs a data word next to it (`health_data`,
`health_record`, `health_condition`). On django-allauth this also drops the one true positive
(the Exist provider, a health-tracking app), a deliberate precision-over-recall trade-off; the
search evaluation is unchanged.

## Limits

No macro expansion, no type inference, no trait resolution beyond names, no `#[path]`
attributes, no `include!`. Every path is a possible path for a reviewer to read, never a
finding.
