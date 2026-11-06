# Graph precision on real projects (2.1, 2026-11-06)

## Question

The project graph (1.3) tags each class and function with the kinds of data it handles, then
lists possible flows from data to AI, tracking, third-party and marketing calls. It was measured
on a synthetic project only. How precise is it on real code?

## Method

Three real Python projects were downloaded as source archives from PyPI (never installed or
run, only parsed): django-allauth 65.20.1 (accounts, email, social login), sentry-sdk 2.73.0
(error and performance tracking) and Django 5.2.18. For each, the graph was built, data tags
were counted, and a seeded random sample of tagged functions was judged by hand: does this code
really handle that kind of data? The archives are not committed.

## Findings before

- Data tags came from a function's whole source, comments and docstrings included, and one
  vocabulary word was enough. Generic words dominated: `user`, `name`, `account`, and for
  children's data `child`, `children`, `kid` and `age`.
- django-allauth: 3,207 of 6,215 nodes tagged personal data; about 9 of 15 sampled were right.
  68 nodes tagged children's data; 0 of 15 sampled were right (`kid` is a JWT key id).
- sentry-sdk: 198 nodes tagged children's data; 0 of 10 were right (child spans).
- All three projects hit the 200-flow cap, mostly with routes through two or more ambiguous
  calls (an unresolved `.get()` links every `get` method), so the reliable flows were cut off.

## Change

- Data kinds are recognised from identifiers and short string keys only (names, attributes,
  parameters, keyword names, `row["email"]`), never prose, as whole word sequences within one
  identifier (`date_of_birth`, `emailAddress`, `parental_consent`, `weight_kg`). Generic words
  alone no longer count. A data word next to a technical word is ignored (`health_check`).
- Flows never start in test code (a tests folder, `test_*.py`, `*_test.py`, `conftest.py`).
- A flow may pass through at most one ambiguous call, and extracted flows are listed first, then
  the shortest, so the cap keeps the most reliable ones.

## Results

| Project | Personal-data nodes | Children's-data nodes | Flows (extracted / ambiguous) | Graph time |
|---|---|---|---|---|
| django-allauth, before | 3,207 | 68 | 200, capped | 3.0 s |
| django-allauth, after | 1,274 (about 10 of 12 sampled right) | 0 | 150 (30 / 120) | 3.2 s |
| sentry-sdk, before | 761 | 198 | 200, capped | 11.1 s |
| sentry-sdk, after | 98 | 0 | 29 (14 / 15) | 11.7 s |
| Django, before | 1,279 | 385 | 200, capped | 18.5 s |
| Django, after | 574 | 0 | 13 (2 / 11) | 20.2 s |

The search evaluation (`make eval`) is unchanged: graph grounding top-1 5/6, top-3 6/6, and the
expected flow is found with no unexpected one. Among sentry-sdk's flows,
`_add_user_to_sentry_scope → Scope` (user data to a third-party tracker) is the kind of route a
reviewer should read.

## Limits

Hand judgement on small samples is an estimate, not a benchmark. Children's data is now
recognised only from explicit identifiers (`parental`, `guardian`, `coppa`, `is_minor`,
`age_verification`); code that names it otherwise is missed, and grounding still searches the
full vocabulary. Every flow remains a possible path for a reviewer to read, never a finding.
