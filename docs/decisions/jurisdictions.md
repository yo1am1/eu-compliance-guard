# Jurisdictions as modules (2.2, 2026-11-06)

## Decision

A jurisdiction is a module of fixed data and pure functions in `jurisdictions.py`: its
official hosts and the domain they must sit under, its act identifiers, its well-known acts,
and how long its hosts may take to answer. The records do not change: declarations, runs,
locks, signatures and packs are the same files for every jurisdiction. The eleven legal
families are topics (data protection, ePrivacy, consumer, accessibility and so on), so they
apply to the UK unchanged.

## The UK

- **Host.** Only `www.legislation.gov.uk` (The National Archives). `ico.org.uk`, the UK
  regulator, answered HTTP 403 to automated clients and is not registered.
- **Format.** `/data.htm` returns a whole XHTML document. `/data.xht` returns a fragment
  without `<html>` and `<body>`, which content screening rightly holds for review, so the
  tool and the docs use `/data.htm`.
- **Provisions.** A provision starts at an element whose id names it (`section-170`,
  `regulation-6`, `section-Article-17`); its title is a `LegP1GroupTitle` before or after.
  A title that cannot belong to the current provision ends it, and is dropped if body text
  arrives before the next anchor: in the Data Protection Act 2018 a prospective section
  (164B) has a title but no anchor, and without that rule every later title shifted by one.
- **Timing.** On a cache miss the site took 11 seconds before the first byte of the Data
  Protection Act 2018 (0.4 seconds when cached), so its host gets a 30-second first-byte
  allowance and a 45-second target budget. Other hosts keep 5 and 20 seconds.
- **Versions.** No date means the latest revised text, which may list changes not yet applied;
  a date gives the text on that date; `/enacted` or `/made` the text as first published.

## Results

The UK GDPR parses into 120 articles (99 plus inserted ones such as 22A to 22D), PECR into 50
regulations, the Data Protection Act 2018 into 259 sections, with titles checked against the
source. An end-to-end run fetched PECR with `--fetch-official`, locked 50 regulations, showed
Regulation 6 in the report with the UK version note, and checked a quotation of it.

## Limits

The newer-consolidation notice is EU-only. UK citations recognise a fixed list of acts by
name; others are matched by their declared target id. Schedules are not split into
paragraphs. The US (2.3) adds a third module the same way.
