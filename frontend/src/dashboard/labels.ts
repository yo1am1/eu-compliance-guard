// Generated from eu_compliance_guard/scorecard.py by tests/test_frontend_dashboard.py
// (EUCG_UPDATE_FIXTURES=1). Do not edit: the CLI, HTML view and dashboard share these words.
export const NOTICE = "Points count recorded review steps in this run. They are not a compliance score or verdict."
export const MAX_OPEN_ITEMS = 50
export const LABELS = {
  alignment: "Alignment",
  law_text: "Law text",
  facts: "Facts",
  decisions: "Decisions",
  mapping: "Mapping",
  reviews: "Reviews",
} as const
export const UNITS = {
  alignment: "requirements supported",
  law_text: "obligations with reviewed pinned text",
  facts: "facts declared or observed",
  decisions: "obligations decided",
  mapping: "requirements mapped",
  reviews: "review methods complete",
} as const
export const HOW_TO_RAISE = {
  alignment: "Close each requirement's blockers: map it, settle its facts and evidence, keep its origin unchanged, and decide every mapped duty with every review method complete.",
  law_text: "Retrieve or download the official text, select it as a source with a source review covering all seven topics, and pin each duty to a listed locator. Duties need a binding source.",
  facts: "Run eu-compliance-guard ground, then ground --apply fact=path:line for technical facts; the owner confirms organisational facts.",
  decisions: "Record an accountable applicability decision per obligation: reviewer, date, rationale, jurisdictions, condition and exception answers, fact refs and every obligation pin. Not applicable also counts as decided.",
  mapping: "Add obligation_refs (id and revision) to each requirement.",
  reviews: "Record one reviewed evidence review per obligation and method: reviewer, date, period, owner, rationale and admitted evidence, with no missing or contrary items.",
} as const
export const TAG_LABELS = {
  supported: "supported",
  conflicting: "reviewer recorded insufficient evidence",
  unresolved: "unresolved",
  no_mapping: "no mapping",
  fact_open: "relied-on fact open",
  fact_evidence_changed: "fact evidence changed",
  requirement_evidence: "requirement evidence unavailable",
  origin_changed: "origin changed",
  methods_open: "mapped review methods open",
  no_methods: "mapped duty declares no methods",
  mapped_not_applicable: "mapped duty does not apply: remap or exclude",
  renew_after_change: "renew review after a change",
  other: "other recorded gap",
  no_pin: "no provision pin",
  target_only: "pinned to a target, not a selected source",
  source_review_open: "source review open",
  locator_not_listed: "locator not listed by the source",
  non_binding_for_duty: "non-binding source for a duty",
  overlay_open: "national overlay open",
  sources_confirmable_by_fetch: "sources an official retrieval could confirm",
  observed: "observed",
  declared: "declared",
  assumed: "assumed",
  unknown: "unknown",
  fact_conflict: "conflicting declarations",
  evidence_changed: "evidence changed",
  ask_owner: "ask the owner",
  ground_in_code: "ground in code",
  applicable: "decided: applies",
  not_applicable: "decided: does not apply",
  missing: "no decision recorded",
  declared_unresolved: "recorded as unresolved",
  declared_not_accepted: "recorded decision not accepted",
  unclaimed_obligations: "obligations no requirement maps to",
  review_complete: "review complete",
  reviewer_recorded_insufficient: "reviewer recorded insufficient evidence",
  not_started: "not started",
  incomplete: "incomplete",
  technical_not_run: "technical checks not run by this tool",
  evidence_ready: "evidence items admitted",
  evidence_declared: "evidence items declared",
} as const
export const STATUS_LABELS = {
  declarations_incomplete: "Declarations incomplete",
  needs_attention: "Needs attention",
  in_review: "In review",
  steps_closed: "Recorded steps closed",
} as const
export const ATTENTION_LABELS = {
  reviewer_recorded_insufficient: "a reviewer recorded insufficient evidence",
  re_review_after_change: "re-review after a change",
  evidence_changed: "evidence changed",
  origin_changed: "requirement origin changed",
} as const
export const HYGIENE_LABELS = {
  requirements_located: "requirements located in project files",
  evidence_referenced: "requirements with evidence referenced",
  origins_unchanged: "requirement origins unchanged",
} as const
export const STEP_TEXT = {
  retrieve: "Retrieve the official law text of the declared source targets",
  fact: "Confirm fact {subject}",
  source: "Read and select the source text of {subject}",
  applicability: "Record whether {subject} applies",
  mapping: "Map {subject} to a candidate obligation",
  review: "Review the evidence for {subject}",
  family: "Screen the eleven legal families",
} as const
