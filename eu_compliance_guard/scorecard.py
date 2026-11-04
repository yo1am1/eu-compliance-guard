"""Review progress of one verified run: separate meters, each points out of 10. Never a compliance score.

Pure: reads only the verified bundle (and an optional predecessor bundle for a display-only
trend). No clock, file, network or environment access, so the same run always gives a
byte-identical scorecard. There is no total, sum or average of the meters anywhere; see
docs/decisions/dashboard-review-progress.md.

Recorded gap lines are read only through the phrase constants assemble and history write
them with, never by matching free text.
"""
from __future__ import annotations

from datetime import date
import json

from . import history, models as m, nextstep, revalidation as r
from .grounding import not_observable

NOTICE = m.SCORE_NOTICE
# Gap areas the report groups by; any other recorded gap is a note outside the meters.
AREA_PREFIXES = ("Requirement ", "Obligation ", "Historical ", "Source target ", "Source ", "Evidence ", "Fact ", "Family ")
# Source problems that only a successful official retrieval can close: a limit of this run.
UNCONFIRMED_SOURCE_GAPS = frozenset({r.OFFLINE_FRESHNESS_GAP, r.FETCH_UNCONFIRMED_GAP})
REQUIREMENT_BLOCKERS = {
    r.NO_MAPPING_GAP: "no_mapping",
    r.FACT_PINS_MISSING_GAP: "fact_open",
    r.FACT_OPEN_GAP: "fact_open",
    r.FACT_EVIDENCE_GAP: "fact_evidence_changed",
    r.REQUIREMENT_EVIDENCE_GAP: "requirement_evidence",
    r.REQUIREMENT_ORIGIN_GAP: "origin_changed",
    r.METHODS_OPEN_GAP: "methods_open",
    r.MAPPED_NOT_APPLICABLE_GAP: "mapped_not_applicable",
    history.RENEW_REQUIREMENT_GAP: "renew_after_change",
}

LABELS = {"alignment": "Alignment", "law_text": "Law text", "facts": "Facts", "decisions": "Decisions",
          "mapping": "Mapping", "reviews": "Reviews"}
UNITS = {"alignment": "requirements supported", "law_text": "obligations with reviewed pinned text",
         "facts": "facts declared or observed", "decisions": "obligations decided",
         "mapping": "requirements mapped", "reviews": "review methods complete"}
HOW_TO_RAISE = {
    "alignment": "Close each requirement's blockers: map it, settle its facts and evidence, keep its origin "
                 "unchanged, and decide every mapped duty with every review method complete.",
    "law_text": "Retrieve or download the official text, select it as a source with a source review covering "
                "all seven topics, and pin each duty to a listed locator. Duties need a binding source.",
    "facts": "Run eu-compliance-guard ground, then ground --apply fact=path:line for technical facts; the owner "
             "confirms organisational facts.",
    "decisions": "Record an accountable applicability decision per obligation: reviewer, date, rationale, "
                 "jurisdictions, condition and exception answers, fact refs and every obligation pin. "
                 "Not applicable also counts as decided.",
    "mapping": "Add obligation_refs (id and revision) to each requirement.",
    "reviews": "Record one reviewed evidence review per obligation and method: reviewer, date, period, owner, "
               "rationale and admitted evidence, with no missing or contrary items.",
}
TAG_LABELS = {
    "supported": "supported", "conflicting": "reviewer recorded insufficient evidence", "unresolved": "unresolved",
    "no_mapping": "no mapping", "fact_open": "relied-on fact open", "fact_evidence_changed": "fact evidence changed",
    "requirement_evidence": "requirement evidence unavailable", "origin_changed": "origin changed",
    "methods_open": "mapped review methods open", "no_methods": "mapped duty declares no methods",
    "mapped_not_applicable": "mapped duty does not apply: remap or exclude",
    "renew_after_change": "renew review after a change", "other": "other recorded gap",
    "no_pin": "no provision pin", "target_only": "pinned to a target, not a selected source",
    "source_review_open": "source review open", "locator_not_listed": "locator not listed by the source",
    "non_binding_for_duty": "non-binding source for a duty", "overlay_open": "national overlay open",
    "sources_confirmable_by_fetch": "sources an official retrieval could confirm",
    "observed": "observed", "declared": "declared", "assumed": "assumed", "unknown": "unknown",
    "fact_conflict": "conflicting declarations",
    "evidence_changed": "evidence changed", "ask_owner": "ask the owner", "ground_in_code": "ground in code",
    "applicable": "decided: applies", "not_applicable": "decided: does not apply", "missing": "no decision recorded",
    "declared_unresolved": "recorded as unresolved", "declared_not_accepted": "recorded decision not accepted",
    "unclaimed_obligations": "obligations no requirement maps to",
    "review_complete": "review complete", "reviewer_recorded_insufficient": "reviewer recorded insufficient evidence",
    "not_started": "not started", "incomplete": "incomplete", "technical_not_run": "technical checks not run by this tool",
    "evidence_ready": "evidence items admitted", "evidence_declared": "evidence items declared",
}
STATUS_LABELS = {"declarations_incomplete": "Declarations incomplete", "needs_attention": "Needs attention",
                 "in_review": "In review", "steps_closed": "Recorded steps closed"}
ATTENTION_LABELS = {"reviewer_recorded_insufficient": "a reviewer recorded insufficient evidence",
                    "re_review_after_change": "re-review after a change", "evidence_changed": "evidence changed",
                    "origin_changed": "requirement origin changed"}
HYGIENE_LABELS = {"requirements_located": "requirements located in project files",
                  "evidence_referenced": "requirements with evidence referenced",
                  "origins_unchanged": "requirement origins unchanged"}


def _tally(tags) -> list[m.ScoreCount]:
    found: dict[str, int] = {}
    for tag in tags:
        found[tag] = found.get(tag, 0) + 1
    return [m.ScoreCount(key=tag, count=found[tag]) for tag in m.SCORE_TAGS if tag in found]


def _ordered(tags) -> list[str]:
    tags = set(tags)
    return [tag for tag in m.SCORE_TAGS if tag in tags]


def _dimension(key: str, done: int, total: int, counts, open_items: list[tuple[str, str | None, list[str]]],
               ceiling: m.ScoreCeiling | None = None) -> m.ScoreDimension:
    open_items = sorted(open_items, key=lambda item: (item[0], item[1] or ""))
    raise_points, raise_by = m.raise_hint(done, total)
    return m.ScoreDimension(
        key=key, points=m.review_points(done, total), done=done, total=total,
        raise_points=raise_points, raise_by=raise_by, counts=_tally(counts),
        reasons=_tally(tag for _, _, reasons in open_items for tag in reasons),
        open_items=[m.ScoreOpenItem(id=identity, method=method, reasons=_ordered(reasons))
                    for identity, method, reasons in open_items[:m.MAX_OPEN_ITEMS]],
        open_total=len(open_items), ceiling=ceiling)


class _Run:
    """Indexes of one bundle, built once; all lookups are by recorded id or shared phrase."""

    def __init__(self, bundle: m.RevalidationBundle):
        self.bundle = bundle
        self.declared = declared = bundle.declarations
        self.gaps = set(bundle.gaps)
        self.obligations = {item.id: item for item in declared.obligations}
        self.sources = {item.source.id: item for item in declared.sources}
        self.source_gaps = {}
        for identity in self.sources:
            prefix = f"Source {identity}: "
            self.source_gaps[identity] = [gap.removeprefix(prefix) for gap in bundle.gaps if gap.startswith(prefix)]
        self.bad_evidence = {item.evidence.id for item in declared.evidence
                             if f"Evidence {item.evidence.id}: {r.EVIDENCE_UNREADY_GAP}" in self.gaps}
        self.assessments = [item for item in bundle.requirement_assessments if item.state != "outside_declared_assessment"]
        self.requirements = {item.id: item for item in declared.requirements}


def _alignment(run: _Run) -> m.ScoreDimension:
    technical, unconfirmed, open_items = set(), set(), []
    for assessment in run.assessments:
        identity = assessment.requirement.id
        mapped = [run.obligations[ref.id] for ref in run.requirements[identity].obligation_refs if ref.id in run.obligations]
        if any("technical" in obligation.required_methods for obligation in mapped):
            technical.add(identity)
        if any(UNCONFIRMED_SOURCE_GAPS & set(run.source_gaps.get(pin.source_id, ()))
               for obligation in mapped for pin in obligation.source_provisions):
            unconfirmed.add(identity)
        if assessment.state == "supported":
            continue
        reasons = [REQUIREMENT_BLOCKERS.get(gap, "other") for gap in assessment.gaps]
        if any(not obligation.required_methods for obligation in mapped):
            reasons.append("no_methods")
        open_items.append((identity, None, reasons or ["other"]))
    total = len(run.assessments)
    done = sum(item.state == "supported" for item in run.assessments)
    ceiling = None
    reachable = m.review_points(total - len(technical | unconfirmed), total)
    if reachable is not None and reachable < 10:
        ceiling = m.ScoreCeiling(points=reachable, technical=len(technical), unconfirmed_sources=len(unconfirmed))
    return _dimension("alignment", done, total, [item.state for item in run.assessments], open_items, ceiling)


def _law_text(run: _Run) -> m.ScoreDimension:
    open_items, done = [], 0
    for obligation in run.declared.obligations:
        codes = r.pin_problems(obligation.source_provisions, run.sources, run.source_gaps, obligation.classification == "duty")
        if any(run.source_gaps.get(identity) for identity in obligation.overlay_ids):
            codes.append("overlay_open")
        if codes:
            open_items.append((obligation.id, None, codes))
        else:
            done += 1
    confirmable = sum(1 for problems in run.source_gaps.values() if problems and set(problems) <= UNCONFIRMED_SOURCE_GAPS)
    return _dimension("law_text", done, len(run.declared.obligations), ["sources_confirmable_by_fetch"] * confirmable,
                      open_items)


def _facts(run: _Run) -> m.ScoreDimension:
    facts = {item.id: item for item in m.scope_facts(run.declared.scope)}
    unobservable = not_observable(run.declared.scope)
    counts, open_items, done = [], [], 0
    for fact in facts.values():
        changed = any(identity in run.bad_evidence for identity in fact.evidence_ids)
        counts.append(fact.basis)
        counts.extend(["fact_conflict"] * bool(fact.conflicts) + ["evidence_changed"] * changed)
        if fact.basis in ("declared", "observed") and not fact.conflicts and not changed:
            done += 1
            continue
        reasons = [fact.basis] if fact.basis in ("assumed", "unknown") else []
        reasons += ["fact_conflict"] * bool(fact.conflicts) + ["evidence_changed"] * changed
        reasons.append("ask_owner" if fact.id in unobservable else "ground_in_code")
        open_items.append((fact.id, None, reasons))
    return _dimension("facts", done, len(facts), counts, open_items)


def _decisions(run: _Run) -> m.ScoreDimension:
    effective = {item.obligation.id: item for item in run.bundle.effective_applicability_decisions}
    recorded = {item.obligation.id: item for item in run.declared.applicability_decisions}
    counts, open_items, done = [], [], 0
    for obligation in run.declared.obligations:
        decision = effective.get(obligation.id)
        if decision is not None and decision.applicability != "unresolved":
            done += 1
            counts.append(decision.applicability)
            continue
        own = recorded.get(obligation.id)
        reason = ("renew_after_change" if decision is not None and history.INVALIDATED_GAP in decision.gaps
                  else "missing" if own is None else "declared_unresolved" if own.applicability == "unresolved"
                  else "declared_not_accepted")
        counts.append(reason)
        open_items.append((obligation.id, None, [reason]))
    return _dimension("decisions", done, len(run.declared.obligations), counts, open_items)


def _mapping(run: _Run) -> m.ScoreDimension:
    requirements = run.declared.requirements
    claimed = {ref.id for item in requirements for ref in item.obligation_refs}
    unclaimed = sum(identity not in claimed for identity in run.obligations)
    open_items = [(item.id, None, ["no_mapping"]) for item in requirements if not item.obligation_refs]
    return _dimension("mapping", len(requirements) - len(open_items), len(requirements),
                      ["unclaimed_obligations"] * unclaimed, open_items)


def _reviews(run: _Run) -> m.ScoreDimension:
    counts, open_items, done, total = [], [], 0, 0
    for disposition in run.bundle.obligation_dispositions:
        if disposition.applicability == "not_applicable":
            continue
        for method in disposition.required_method_dispositions:
            if method.method == "technical":
                counts.append("technical_not_run")
                continue
            total += 1
            if method.outcome == "passed":
                done += 1
                counts.append("review_complete")
                continue
            reason = ("reviewer_recorded_insufficient" if method.outcome == "observed_failure"
                      else "not_started" if not method.review_ids else "incomplete")
            counts.append(reason)
            open_items.append((disposition.obligation_id, method.method, [reason]))
    declared = [item.evidence.id for item in run.declared.evidence]
    counts += ["evidence_declared"] * len(declared)
    counts += ["evidence_ready"] * sum(identity not in run.bad_evidence for identity in declared)
    return _dimension("reviews", done, total, counts, open_items)


def _screening(bundle: m.RevalidationBundle) -> m.ScoreScreening:
    states = [item.applicability for item in bundle.family_screenings]
    return m.ScoreScreening(screened=sum(state != "unresolved" for state in states), total=11,
                            applicable=states.count("applicable"), not_applicable=states.count("not_applicable"),
                            withdrawn=sum(history.FAMILY_WITHDRAWN_GAP in item.gaps for item in bundle.family_screenings))


def _hygiene(run: _Run) -> list[m.ScoreHygiene]:
    requirements = run.declared.requirements
    located = [item for item in requirements if item.origin is not None]
    by_id = {item.requirement.id: item for item in run.bundle.requirement_assessments}
    unchanged = sum(r.REQUIREMENT_ORIGIN_GAP not in by_id[item.id].gaps for item in located if item.id in by_id)
    return [m.ScoreHygiene(key="requirements_located", done=len(located), total=len(requirements)),
            m.ScoreHygiene(key="evidence_referenced", done=sum(bool(item.evidence_ids) for item in run.assessments),
                           total=len(run.assessments)),
            m.ScoreHygiene(key="origins_unchanged", done=unchanged, total=len(located))]


def _attention(run: _Run) -> list[m.ScoreAttentionCount]:
    bundle = run.bundle
    methods = [method for item in bundle.obligation_dispositions for method in item.required_method_dispositions]
    observed = {item.id: item for item in bundle.evidence}
    found = {
        "reviewer_recorded_insufficient": sum(item.state == "conflicting" for item in run.assessments)
        + sum(method.outcome == "observed_failure" for method in methods),
        "re_review_after_change": sum(history.INVALIDATED_GAP in item.gaps for item in bundle.effective_applicability_decisions)
        + sum(history.FAMILY_WITHDRAWN_GAP in item.gaps for item in bundle.family_screenings)
        + sum(history.RENEW_REQUIREMENT_GAP in item.gaps for item in run.assessments),
        "evidence_changed": sum(item.evidence.availability == "available" and item.evidence.id in observed
                                and observed[item.evidence.id].availability in ("missing", "corrupt")
                                for item in run.declared.evidence),
        "origin_changed": sum(r.REQUIREMENT_ORIGIN_GAP in item.gaps for item in run.assessments),
    }
    return [m.ScoreAttentionCount(key=key, count=count) for key, count in found.items() if count]


def _days_before(ended_at: str | None, assessment_date: str) -> int | None:
    if ended_at is None:
        return None
    days = (date.fromisoformat(ended_at[:10]) - date.fromisoformat(assessment_date)).days
    return days if days >= 0 else None


def _trend(bundle: m.RevalidationBundle, card: m.Scorecard, previous: m.RevalidationBundle) -> m.ScoreTrend:
    reason = ("different_project" if previous.project_id != bundle.project_id
              else "not_parent" if previous.run.id != bundle.run.parent_run_id
              else "different_tool_version" if previous.manifest.tool_versions != bundle.manifest.tool_versions else None)
    deltas = []
    if reason is None:
        before = score(previous)
        deltas = [m.ScoreDelta(key=old.key, points_before=old.points, points_after=new.points,
                               total_before=old.total, total_after=new.total)
                  for old, new in zip(before.dimensions, card.dimensions)]
    return m.ScoreTrend(previous_run_id=previous.run.id, comparable=reason is None, reason=reason, deltas=deltas)


def score(bundle: m.RevalidationBundle, previous: m.RevalidationBundle | None = None) -> m.Scorecard:
    """The scorecard of a verified run; ``previous`` only adds a display-only trend."""
    run = _Run(bundle)
    dimensions = [_alignment(run), _law_text(run), _facts(run), _decisions(run), _mapping(run), _reviews(run)]
    attention = _attention(run)
    steps = nextstep.next_steps(bundle, 1)
    step = None
    if steps:
        first = steps[0]
        step = m.ScoreNextStep(kind=first["kind"], subject=first["subject"] or None, unblocks=first["unblocks"],
                               focus=m.SCORE_FOCUS[first["kind"]])
    scored = [item.points for item in dimensions if item.points is not None]
    status = ("declarations_incomplete" if not run.declared.requirements or not run.declared.obligations
              else "needs_attention" if attention
              else "steps_closed" if dimensions[0].points is not None and all(points == 10 for points in scored) and step is None
              else "in_review")
    card = m.Scorecard(
        schema_version=1, scorer_version=1, project_id=bundle.project_id, run_id=bundle.run.id,
        parent_run_id=bundle.run.parent_run_id, synthetic=bundle.synthetic, run_state=bundle.run.state,
        ended_at=bundle.run.ended_at, assessment_date=run.declared.scope.assessment_date,
        assessed_days_before_run=_days_before(bundle.run.ended_at, run.declared.scope.assessment_date),
        offline=not bundle.source_attempts, status=status, attention=attention, dimensions=dimensions,
        screening=_screening(bundle), hygiene=_hygiene(run), next_step=step,
        notes_outside=sum(not gap.startswith(AREA_PREFIXES) for gap in bundle.gaps), notice=NOTICE)
    if previous is not None:
        card = card.model_copy(update={"trend": _trend(bundle, card, previous)})
        card = m.Scorecard.model_validate(card.model_dump())
    return card


def to_json(card: m.Scorecard) -> bytes:
    """The one serialisation of a scorecard (view file, fixture): stable key order, UTF-8, newline."""
    return (json.dumps(card.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n").encode("utf-8")


# --- Fixed wording shared by the CLI, the HTML view and (mirrored) the band and dashboard. ---

def bar(points: int | None, ceiling: int | None = None) -> str:
    """Ten cells: filled up to the points, hatched above a ceiling; a not-scored meter is blank."""
    if points is None:
        return "·" * 10
    reachable = 10 if ceiling is None else ceiling
    return "■" * points + "□" * (reachable - points) + "▨" * (10 - reachable)


def points_text(points: int | None) -> str:
    return "not scored: nothing declared" if points is None else f"{points}/10"


def raise_text(item: m.ScoreDimension) -> str:
    if item.raise_points is None:
        return ""
    return f"+{item.raise_points} pt{'s' if item.raise_points != 1 else ''}: close {item.raise_by} more"


def ceiling_text(ceiling: m.ScoreCeiling, offline: bool) -> str:
    parts = []
    if ceiling.technical:
        parts.append(f"{ceiling.technical} rest on technical checks this workflow never runs")
    if ceiling.unconfirmed_sources:
        parts.append(f"{ceiling.unconfirmed_sources} rest on real sources "
                     + ("an offline run cannot confirm (run revalidate --fetch-official)" if offline
                        else "the official retrieval did not confirm"))
    return f"max reachable in this run: {ceiling.points}/10; " + "; ".join(parts) + "."


def tag_text(item: m.ScoreCount) -> str:
    return f"{TAG_LABELS[item.key]} ×{item.count}"


def describe_step(step: m.ScoreNextStep) -> str:
    """Fixed words per kind with the step's validated id; never a run's free text."""
    subject = step.subject or ""
    what = {
        "retrieve": "Retrieve the official law text of the declared source targets",
        "fact": f"Confirm fact {subject}",
        "source": f"Read and select the source text of {subject}",
        "applicability": f"Record whether {subject} applies",
        "mapping": f"Map {subject} to a candidate obligation",
        "review": f"Review the evidence for {subject}",
        "family": "Screen the eleven legal families",
    }[step.kind]
    return f"{what} · unblocks {step.unblocks} open requirement{'' if step.unblocks == 1 else 's'}"


def format_text(card: m.Scorecard) -> str:
    lines = []
    if card.synthetic:
        lines.append("FICTIONAL DATA: synthetic run; nothing below concerns a real project.")
    age = "" if card.assessed_days_before_run is None else f" · assessed {card.assessed_days_before_run} days before run"
    lines.append(f"Review progress · run {card.run_id} · {STATUS_LABELS[card.status]} · assembly {card.run_state}"
                 f" · {'offline' if card.offline else 'official retrieval'}{age}")
    if card.attention:
        lines.append("Attention: " + " · ".join(f"{ATTENTION_LABELS[item.key]} ×{item.count}" for item in card.attention))
    for item in card.dimensions:
        ceiling = item.ceiling.points if item.ceiling else None
        line = (f"{LABELS[item.key]:<10} {bar(item.points, ceiling)} {points_text(item.points):>5}  "
                f"{item.done} of {item.total} {UNITS[item.key]}")
        hint = raise_text(item)
        lines.append(line + (f"  {hint}" if hint else ""))
        if item.reasons:
            lines.append(" " * 11 + "open: " + " · ".join(tag_text(reason) for reason in item.reasons))
        if item.ceiling:
            lines.append(" " * 11 + ceiling_text(item.ceiling, card.offline))
    screening = card.screening
    lines.append(f"Screening: {screening.screened} of {screening.total} families screened (not scored)")
    lines.append("Record hygiene (not scored): " + " · ".join(f"{HYGIENE_LABELS[item.key]} {item.done} of {item.total}"
                                                            for item in card.hygiene))
    lines.append(f"Notes outside the meters: {card.notes_outside}")
    if card.trend is not None:
        trend = card.trend
        if trend.comparable:
            lines.append(f"Since {trend.previous_run_id}: " + " · ".join(
                f"{LABELS[item.key]} {points_text(item.points_before)} → {points_text(item.points_after)}"
                + (f" (of {item.total_before} → {item.total_after})" if item.total_before != item.total_after else "")
                for item in trend.deltas))
        else:
            lines.append({"not_parent": "Trend unavailable: that run is not this run's recorded parent.",
                          "different_project": "Trend unavailable: that run belongs to another project.",
                          "different_tool_version": "Trend unavailable: different tool version."}[trend.reason])
    lines.append("Next: " + (describe_step(card.next_step) if card.next_step else "no recorded step is open."))
    lines.append(card.notice)
    return "\n".join(lines)
