"""Static, escaped HTML view of one verified run; a derived file, never part of the run.

The view is written beside the run directory (``<parent>/views/<run>.html``) so the
immutable run and its completion marker stay untouched. It holds no scripts, loads
nothing, and renders recorded metadata only; it is not a compliance verdict.
"""
from __future__ import annotations

from collections import Counter
from html import escape
import json
import os
from pathlib import Path
import stat

from urllib.parse import quote

from .notice import LEGAL_NOTICE
from .errors import CodedError
from . import articles, grounding, jurisdictions, models as m, nextstep, revalidation as r, scorecard

CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1b;--muted:#6b6a65;--line:#e4e1d8;--card:#fff;--warn:#9a5b00;--warnbg:#fff4df;--bad:#a1271b;--badbg:#fde9e6;--ok:#2d6a3e;--okbg:#e6f3e9}
@media (prefers-color-scheme:dark){:root{--bg:#161614;--fg:#ecebe6;--muted:#a3a29b;--line:#34332f;--card:#1f1e1c;--warn:#f0b35a;--warnbg:#3a2a12;--bad:#f08a7e;--badbg:#3d1915;--ok:#8fd19e;--okbg:#17301e}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1080px;margin:0 auto;padding:24px 16px 64px}h1{font-size:24px;margin:0 0 4px}h2{font-size:18px;margin:32px 0 8px}
.muted{color:var(--muted)}.banner{padding:12px 14px;border-radius:8px;background:var(--warnbg);color:var(--warn);margin:16px 0;font-weight:600}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:16px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}.card b{display:block;font-size:22px}
.scroll{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:8px}table{width:100%;border-collapse:collapse}tr:last-child td{border-bottom:0}
th,td{text-align:left;vertical-align:top;padding:8px 10px;border-bottom:1px solid var(--line);font-size:14px}th{color:var(--muted);font-weight:600}
.tag{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:600;background:var(--warnbg);color:var(--warn)}
.law{margin:4px 0 0}.law summary{font-weight:500;padding:2px 0}.law p{margin:4px 0;font-size:13px;color:var(--muted);white-space:pre-line}
.suggest{font-size:13px;margin-top:4px}.next{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 12px 12px 34px}.next li{margin:4px 0}.next b{font-weight:600}.tag.ok{background:var(--okbg);color:var(--ok)}.tag.bad{background:var(--badbg);color:var(--bad)}
details{margin:10px 0}summary{cursor:pointer;font-weight:600;padding:6px 0}summary .count{display:inline-block;min-width:1.6em;padding:0 7px;margin-left:6px;border-radius:999px;background:var(--line);text-align:center;font-size:13px}
details>.scroll{margin-top:6px}
.progress{--accent:#3d5a80;--cell:#e4e1d8;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin:16px 0}
@media (prefers-color-scheme:dark){.progress{--accent:#9fb7d9;--cell:#3a3935}}
.progress h2{margin:0;font-size:18px}.progress .head{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:baseline}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}.chip{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:600;border:1px solid var(--line);color:var(--muted)}
.chip.status{color:var(--fg);border-color:var(--accent)}.chip.bad{background:var(--badbg);color:var(--bad);border-color:transparent}.chip.fiction{background:var(--warnbg);color:var(--warn);border-color:transparent}
.bar{display:inline-flex;gap:2px;vertical-align:middle}.bar i{display:inline-block;width:12px;height:12px;border-radius:2px;background:var(--cell)}
.bar i.on{background:var(--accent)}.bar i.cap{background:repeating-linear-gradient(45deg,var(--cell) 0 2px,transparent 2px 4px);outline:1px solid var(--cell)}
.hero{border:1px solid var(--line);border-radius:8px;padding:12px;margin:8px 0}.hero .pts{font-size:28px;font-weight:700;margin:0 8px}
.cta{border-left:3px solid var(--accent);padding:6px 10px;margin:10px 0}.cta b{font-weight:700}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin:10px 0}
.tile{border:1px solid var(--line);border-radius:8px;padding:10px}.tile.focus{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}
.tile h3{font-size:14px;margin:0;display:flex;justify-content:space-between;gap:8px}.tile p{margin:4px 0;font-size:13px}.tile details{margin:4px 0}.tile summary{font-size:13px;font-weight:500}
.tile li{font-size:13px}.notice{font-size:13px;color:var(--muted);margin:8px 0 0}
ul{margin:0;padding-left:20px}code{font-size:13px;overflow-wrap:anywhere}td:first-child code{overflow-wrap:normal;word-break:normal}
"""


class ViewError(CodedError):
    pass


def _tag(value: str, confirmed: bool = True) -> str:
    """``confirmed=False`` never styles a value as ok, e.g. fetched bytes that still need review."""
    kind = "ok" if confirmed and value in ("supported", "applicable", "passed", "retrieved", "completed", "same_bytes") else (
        "bad" if value in ("conflicting", "observed_failure", "retrieval_failed", "different_bytes") else "")
    return f'<span class="tag {kind}">{escape(value)}</span>'


def _table(headers: list[str], rows: list[list[str]], empty: str) -> str:
    if not rows:
        return f'<p class="muted">{escape(empty)}</p>'
    head = "".join(f'<th scope="col">{escape(item)}</th>' for item in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    name = escape(", ".join(headers), quote=True)
    return f'<div class="scroll" tabindex="0" role="region" aria-label="{name}"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _list(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>" if items else '<span class="muted">none</span>'


def _gap_area(gap: str) -> str:
    subject, _, detail = gap.partition(": ")
    if not detail:
        return "coverage"
    return "source target" if subject.startswith("Source target ") else subject.split(" ", 1)[0].lower()


def _gap_row(gap: str) -> list[str]:
    subject, _, detail = gap.partition(": ")
    if not detail:
        return [_tag("coverage"), "", escape(gap)]
    area = _gap_area(gap)
    return [_tag(area), f"<code>{escape(subject.split(' ', 2 if area == 'source target' else 1)[-1])}</code>", escape(detail)]


# Most actionable areas first; long, low-signal groups start collapsed.
AREAS = [("requirement", "Requirements", True), ("obligation", "Candidate obligations", True),
         ("historical", "Changed since the previous run", True), ("source target", "Source targets", True),
         ("source", "Selected sources", True), ("evidence", "Evidence", True), ("fact", "Facts to confirm", False),
         ("family", "Legal families to screen", False)]


def _attention(gaps: list[str]) -> str:
    groups: dict[str, list] = {}
    for gap in gaps:
        area = _gap_area(gap)
        groups.setdefault(area if area in {key for key, _, _ in AREAS} else "coverage", []).append(_gap_row(gap))
    if not groups:
        return '<p class="muted">No open gaps recorded. That is not a compliance conclusion.</p>'
    parts = []
    for key, label, is_open in [*AREAS, ("coverage", "Coverage and scope", True)]:
        rows = groups.get(key)
        if rows:
            parts.append(f'<details{" open" if is_open else ""}><summary>{escape(label)} <span class="count">{len(rows)}</span>'
                         f"</summary>{_table(['Area', 'Item', 'What is open'], rows, '')}</details>")
    return "".join(parts)


def _value(value) -> str:
    return "not known" if value in (None, "", [], {}) else value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def _open_facts(bundle: m.RevalidationBundle) -> list[m.Fact]:
    """Assumed, unknown or conflicting facts, each once: the questions for the owner."""
    return list({item.id: item for item in m.scope_facts(bundle.declarations.scope)
                 if m.open_fact(item)}.values())


def _owner_questions(bundle: m.RevalidationBundle) -> str:
    """The open facts as questions, with the requirements that rely on them."""
    relied: dict[str, list[str]] = {}
    for requirement in bundle.declarations.requirements:
        for pin in requirement.fact_refs:
            relied.setdefault(pin.id, []).append(requirement.id)
    facts = _open_facts(bundle)
    if not facts:
        return '<p class="muted">Every declared fact is marked declared or observed.</p>'
    rows = [[escape(fact.key), escape(_value(fact.value)), _tag(fact.basis), escape(fact.owner or "—"),
             _list(relied.get(fact.id, []))] for fact in facts]
    return _table(["Question", "Current answer", "Basis", "Owner", "Requirements relying on it"], rows, "")


def _next_steps(bundle: m.RevalidationBundle) -> str:
    steps = nextstep.next_steps(bundle, 3)
    if not steps:
        return '<p class="muted">No recorded step is open. That is not a compliance conclusion.</p>'
    items = "".join(f"<li><b>{escape(step['action'])}</b> <span class=\"muted\">Unblocks {step['unblocks']} open "
                    f"requirement(s).</span>" + (f"<br><code>{escape(step['command'])}</code>" if step["command"] else "")
                    + "</li>" for step in steps)
    return f'<ol class="next">{items}</ol>'


def _cells(item: m.ScoreDimension) -> str:
    """Ten CSS cells; hatched above a ceiling. The label carries the number for screen readers."""
    if item.points is None:
        return '<span class="bar" role="img" aria-label="not scored">' + "<i></i>" * 10 + "</span>"
    reachable = item.ceiling.points if item.ceiling else 10
    cells = '<i class="on"></i>' * item.points + "<i></i>" * (reachable - item.points) + '<i class="cap"></i>' * (10 - reachable)
    return f'<span class="bar" role="img" aria-label="{item.points} of 10 points">{cells}</span>'


def _open_items(item: m.ScoreDimension) -> str:
    rows = "".join(f"<li><code>{escape(entry.id)}</code>" + (f" · {escape(entry.method)}" if entry.method else "")
                   + f' <span class="muted">{escape(", ".join(scorecard.TAG_LABELS[tag] for tag in entry.reasons))}</span></li>'
                   for entry in item.open_items)
    more = f'<li class="muted">and {item.open_total - len(item.open_items)} more</li>' if item.open_total > len(item.open_items) else ""
    return (f'<details><summary>open items ({item.open_total})</summary><ul>{rows}{more}</ul></details>'
            if item.open_total else "")


def _counted(counts: list[m.ScoreCount]) -> str:
    return " · ".join(escape(scorecard.tag_text(item)) for item in counts)


def _review_progress(card: m.Scorecard) -> str:
    """Top section: one status, the Alignment meter, the next step, then one tile per meter. No total."""
    fiction = '<span class="chip fiction">fictional data</span>' if card.synthetic else ""
    chips = [f'<span class="chip status">● {escape(scorecard.STATUS_LABELS[card.status])}</span>',
             f'<span class="chip">assembly: {escape(card.run_state)} (processing state)</span>',
             f'<span class="chip">{"offline" if card.offline else "official retrieval"}</span>']
    if card.assessed_days_before_run is not None:
        chips.append(f'<span class="chip">assessed {card.assessed_days_before_run} days before run</span>')
    chips.append(f'<span class="chip">notes outside the meters: {card.notes_outside}</span>')
    chips += [f'<span class="chip{" bad" if item.key == "reviewer_recorded_insufficient" else ""}">'
              f"{escape(scorecard.ATTENTION_LABELS[item.key])} ×{item.count}</span>" for item in card.attention]
    focus = card.next_step.focus if card.next_step else None
    hero = card.dimensions[0]
    hint = scorecard.raise_text(hero)
    hero_html = (
        f'<div class="hero{" focus" if focus == "alignment" else ""}"><b>{scorecard.LABELS[hero.key].upper()}</b>'
        f'<span class="pts">{escape(scorecard.points_text(hero.points))}</span>{_cells(hero)} {fiction}'
        f"<p>{hero.done} of {hero.total} {escape(scorecard.UNITS[hero.key])}"
        + (f' · <span class="muted">{escape(hint)}</span>' if hint else "") + "</p>"
        + (f'<p class="muted">blockers: {_counted(hero.reasons)}</p>' if hero.reasons else "")
        + (f'<p class="muted">{escape(scorecard.ceiling_text(hero.ceiling, card.offline))}</p>' if hero.ceiling else "")
        + (f"<p>{_counted(hero.counts)}</p>" if hero.counts else "") + _open_items(hero) + "</div>")
    step = card.next_step
    cta = (f'<div class="cta"><b>▶ NEXT</b> {escape(scorecard.describe_step(step))}<br>'
           '<span class="muted">CLI: <code>eu-compliance-guard next</code> lists the ranked steps.</span></div>'
           if step else '<div class="cta">No recorded step is open. That is not a compliance conclusion.</div>')
    tiles = []
    for item in card.dimensions[1:]:
        hint = scorecard.raise_text(item)
        tiles.append(
            f'<div class="tile{" focus" if focus == item.key else ""}"><h3><span>{escape(scorecard.LABELS[item.key])}</span>'
            f"<span>{escape(scorecard.points_text(item.points))}</span></h3>{_cells(item)} {fiction}"
            f"<p>{item.done} of {item.total} {escape(scorecard.UNITS[item.key])}</p>"
            + (f'<p class="muted">{_counted(item.counts)}</p>' if item.counts else "")
            + (f'<p class="muted">open: {_counted(item.reasons)}</p>' if item.reasons else "")
            + (f"<p>{escape(hint)}</p>" if hint else "")
            + ('<p class="muted">focus of the next step</p>' if focus == item.key else "") + _open_items(item) + "</div>")
    screening = card.screening
    tiles.append(f'<div class="tile{" focus" if step and step.kind == "family" else ""}"><h3><span>Screening</span>'
                 f'<span class="muted">not scored</span></h3> {fiction}'
                 f"<p>{screening.screened} of {screening.total} families screened</p>"
                 f'<p class="muted">applies {screening.applicable} · does not apply {screening.not_applicable}'
                 f" · withdrawn {screening.withdrawn}</p></div>")
    tiles.append('<div class="tile"><h3><span>Record hygiene</span><span class="muted">not scored</span></h3> ' + fiction
                 + "".join(f"<p>{escape(scorecard.HYGIENE_LABELS[item.key])}: {item.done} of {item.total}</p>"
                           for item in card.hygiene) + "</div>")
    trend = ""
    if card.trend is not None and card.trend.comparable:
        trend = ('<p class="muted">Since the parent run: ' + " · ".join(
            f"{escape(scorecard.LABELS[item.key])} {escape(scorecard.points_text(item.points_before))} → "
            f"{escape(scorecard.points_text(item.points_after))}" for item in card.trend.deltas) + "</p>")
    how = "".join(f"<li><b>{escape(scorecard.LABELS[key])}</b>: {escape(scorecard.UNITS[key])}. {escape(scorecard.HOW_TO_RAISE[key])}</li>"
                  for key in m.SCORE_KEYS)
    return (
        '<section class="progress" aria-labelledby="review-progress">'
        '<div class="head"><h2 id="review-progress">Review progress</h2>'
        "<span class=\"muted\">points out of 10 · from this run's records</span></div>"
        f'<div class="chips">{"".join(chips)}</div>{hero_html}{cta}'
        f'<p class="notice">{escape(card.notice)}</p>'
        f'<div class="tiles">{"".join(tiles)}</div>{trend}'
        "<details><summary>How points work</summary><p>Each meter counts closed items of one kind: none closed is 0, all "
        "closed is 10, otherwise ten times the closed share rounded down, kept between 1 and 9. A meter with nothing "
        "declared is not scored. Meters are never added or averaged; no total exists.</p>"
        f"<ul>{how}</ul></details></section>")


def _digest(value: str | None) -> str:
    if value is None:
        return '<span class="muted">—</span>'
    return f'<code title="{escape(value, quote=True)}">{escape(value.removeprefix("sha256:")[:12])}…</code>'


EXCERPT_CHARS = 700


def catalogue(bundle: m.RevalidationBundle, contents: dict[str, bytes]) -> dict[str, dict[str, dict]]:
    """Articles per source target: this run's retrieved bytes first, else the declared retained file."""
    found: dict[str, dict[str, dict]] = {}
    for attempt in bundle.source_attempts:
        retrieval = attempt.retrieval
        if attempt.retrieved_source and retrieval.artifact_path in contents and retrieval.media_type:
            parsed = articles.parse(contents[retrieval.artifact_path], retrieval.media_type)
            if parsed:
                found[attempt.source_target_id] = parsed
    for selected in bundle.declarations.sources:
        path = "sources/" + selected.source.content_digest.removeprefix("sha256:") + ".bin"
        if selected.target_id not in found and path in contents:
            parsed = articles.parse(contents[path], selected.media_type)
            if parsed:
                found[selected.target_id] = parsed
    return found


def source_catalogue(bundle: m.RevalidationBundle, contents: dict[str, bytes]) -> dict[str, dict[str, dict]]:
    """Articles per declared source id, from that source's own retained bytes."""
    found: dict[str, dict[str, dict]] = {}
    for selected in bundle.declarations.sources:
        path = "sources/" + selected.source.content_digest.removeprefix("sha256:") + ".bin"
        if path in contents:
            parsed = articles.parse(contents[path], selected.media_type)
            if parsed:
                found[selected.source.id] = parsed
    return found


def _article(pin: m.ProvisionRef, acts: dict[str, dict[str, dict]], by_source: dict[str, dict[str, dict]],
             versions: dict[str, dict | None] | None = None) -> str:
    """A pin naming a source shows that source's text; only an unpinned target falls back to the target's."""
    key = articles.article_key(pin.locator)
    target = pin.source_id or pin.source_target_id
    pool = by_source.get(pin.source_id, {}) if pin.source_id else acts.get(pin.source_target_id, {})
    item = pool.get(key) if key else None
    if item is None:
        return ""
    text = item["text"] if len(item["text"]) <= EXCERPT_CHARS else item["text"][:EXCERPT_CHARS].rsplit(" ", 1)[0] + " …"
    return (f'<details class="law"><summary>{escape(key)} — {escape(item["title"] or "untitled")}</summary>'
            f'<p>{escape(text)}</p><p>Unreviewed candidate text from the retained <code>{escape(target)}</code> bytes; '
            f"{escape(jurisdictions.version_note((versions or {}).get(pin.source_target_id)))}</p></details>")


def _suggestions(statement: str, index: articles.ArticleIndex) -> str:
    found = index.suggest(statement, top=3)
    if not found:
        return ""
    hybrid = index.method != "words"

    def why(item) -> str:
        words = f'matched {grounding.explain(item["matched"])}'
        if not hybrid:
            return words
        return articles.via_text(item) + (f"; {words}" if item["matched"] else "")

    names = " · ".join(f'{escape(item["article"])} <span class="muted">{escape(item["title"][:60])} ({escape(item["source"])}); '
                       f'{escape(why(item))}</span>'
                       for item in found)
    note = ("Word and semantic search suggestion (local model bge-small-en-v1.5), not a mapping." if hybrid
            else "Text search suggestion, not a mapping.")
    return f'<div class="suggest">Articles to read: {names}<br><span class="muted">{note}</span></div>'


def render_html(bundle: m.RevalidationBundle, contents: dict[str, bytes] | None = None,
                card: m.Scorecard | None = None) -> str:
    """Every dynamic value passes through html.escape; nothing executes or loads."""
    card = card or scorecard.score(bundle)
    acts = catalogue(bundle, contents or {})
    by_source = source_catalogue(bundle, contents or {})
    index = articles.ArticleIndex(acts)
    declared = bundle.declarations
    obligations = {item.id: item for item in declared.obligations}
    # Official law, guidance, proposals and engineering practice must not look alike: a pinned
    # reference shows its source's declared type, an unpinned one its target's intended type.
    source_types = {item.source.id: item.source.type for item in declared.sources}
    target_types = {item.id: item.intended_type for item in declared.source_targets}
    versions = {item.id: jurisdictions.version(item.intended_identifier, item.intended_url) for item in declared.source_targets}
    decisions = {item.obligation.id: item for item in bundle.effective_applicability_decisions}
    requirement_states = Counter(item.state for item in bundle.requirement_assessments)
    applicability = Counter(item.applicability for item in bundle.obligation_dispositions)
    attempts = Counter(item.state for item in bundle.source_attempts)
    fetched = bool(bundle.source_attempts)
    cards = [("Processing state", bundle.run.state), ("Open gaps", str(len(bundle.gaps))),
             ("Requirements supported", f"{requirement_states['supported']} of {len(bundle.requirement_assessments)}"),
             ("Obligations unresolved", f"{applicability['unresolved']} of {len(bundle.obligation_dispositions)}"),
             ("Source attempts", f"{attempts['retrieved']} retrieved / {len(bundle.source_attempts)}" if fetched else "offline")]
    requirement_rows = []
    for assessment in bundle.requirement_assessments:
        requirement = next(item for item in declared.requirements if item.id == assessment.requirement.id)
        location = f"{requirement.origin.path} — {requirement.locator}" if requirement.origin else "declared in JSON"
        requirement_rows.append([f"<code>{escape(requirement.id)}</code>", escape(requirement.statement) + _suggestions(requirement.statement, index),
                                 escape(location),
                                 _tag(assessment.state), _list(assessment.gaps)])
    obligation_rows = []
    for disposition in bundle.obligation_dispositions:
        obligation = obligations[disposition.obligation_id]
        decision = decisions[disposition.obligation_id]
        references = "".join(f"<li>{escape(f'{pin.source_id or pin.source_target_id} — {pin.locator}')} "
                             f"({escape(source_types.get(pin.source_id) or target_types.get(pin.source_target_id) or 'type not declared')})"
                             f"{_article(pin, acts, by_source, versions)}</li>" for pin in obligation.source_provisions)
        methods = " ".join(_tag(f"{item.method}: {item.outcome}") for item in disposition.required_method_dispositions)
        obligation_rows.append([f"<code>{escape(obligation.id)}</code>", escape(f"{obligation.family} · {obligation.classification}"),
                                f"<ul>{references}</ul>" if references else "—", _tag(decision.applicability) + f'<br><span class="muted">{escape(decision.reviewer or "no reviewer")}</span>',
                                methods or '<span class="muted">none declared</span>'])
    attempt_rows = [[f"<code>{escape(item.source_target_id)}</code>", escape(item.intended_type),
                     _tag(item.state, item.retrieval.admission == "accepted"),
                     f"<code>{escape(item.retrieval.final_url or item.retrieval.requested_url)}</code>",
                     escape(str(item.retrieval.status or "—")), _tag(item.retrieval.comparison, item.retrieval.admission == "accepted"),
                     escape(f"{item.failure.code}: {item.failure.safe_message}" if item.failure else "—")]
                    for item in bundle.source_attempts]
    family_rows = [[escape(item.family), _tag(item.applicability), escape(item.reviewer or "—"), _list(item.gaps)]
                   for item in bundle.family_screenings]
    # Older runs did not record the historical obligation; fall back to the current run's dispositions.
    by_disposition = {item.id: item.obligation_id for item in bundle.obligation_dispositions}
    comparison_html = ""
    if bundle.comparison is not None:
        comparison_html = (
            "<h2>Predecessor comparison</h2>"
            f'<p>Historical run <code>{escape(bundle.comparison.previous_run_id)}</code>. '
            "Matching recorded inputs renew neither legal currency nor reviewer approval.</p>"
            + _table(["Change", "Dependency", "ID or path", "Before", "After"],
                [[_tag("added" if item.before is None else "removed" if item.after is None else "changed"),
                  escape(item.kind), escape(item.identity), _digest(item.before), _digest(item.after)]
                 for item in bundle.comparison.changes],
                "Recorded dependencies unchanged.")
            + _table(["Historical obligation", "Freshness", "Changed dependencies", "Review actions and uncertainty"],
                [[f"<code>{escape(item.obligation_id or by_disposition.get(item.obligation_disposition_id, item.obligation_disposition_id))}</code>",
                  _tag(item.freshness), _list(item.changed_dependencies), _list(item.reasons)]
                 for item in bundle.current_assessments], "No historical dispositions."))
    banner = ("FICTIONAL / SYNTHETIC DATA. Every conclusion below is fictional and establishes no real EU duty."
              if bundle.synthetic else "Recorded declarations and self-attested reviews. Not a compliance verdict.")
    parts = [
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
        "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\">",
        f"<title>EU Compliance Guard run</title><style>{CSS}</style></head><body><main>",
        "<h1>EU Compliance Guard</h1>",
        f'<p class="muted">Project <code>{escape(bundle.project_id)}</code> · run <code>{escape(bundle.run.id)}</code> · '
        f'assessment date {escape(declared.scope.assessment_date)} · ended {escape(bundle.run.ended_at or "—")}</p>',
        f'<div class="banner">{escape(banner)}</div>',
        _review_progress(card),
        '<div class="cards">' + "".join(f'<div class="card"><span class="muted">{escape(label)}</span><b>{escape(value)}</b></div>'
                                        for label, value in cards) + "</div>",
        "<h2>Next best steps</h2>",
        "<p class=\"muted\">Ranked by how many open requirements each step unblocks. Workflow guidance, not a verdict.</p>",
        _next_steps(bundle),
        "<h2>Questions for the project owner</h2>",
        "<p class=\"muted\">Assumed or unknown facts stay review gaps until the owner confirms them.</p>",
        _owner_questions(bundle),
        "<h2>What needs attention</h2>",
        "<p class=\"muted\">Review gaps are open questions, not established violations. Reviewed deficiencies record a named reviewer's assessment.</p>",
        _attention(bundle.gaps),
        "<h2>Requirements</h2>",
        _table(["ID", "Statement", "Location", "State", "Gaps"], requirement_rows, "No requirements declared: a coverage gap."),
        "<h2>Candidate obligations</h2>",
        _table(["ID", "Family", "Declared legal references", "Applicability", "Methods"], obligation_rows,
               "No candidate obligations declared: a coverage gap."),
        "<h2>Official-source retrieval</h2>",
        "<p class=\"muted\">Official hosting establishes neither binding status, completeness, applicability nor currency.</p>",
        _table(["Target", "Type", "State", "URL", "HTTP", "Compared", "Failure"], attempt_rows, "No retrieval was requested for this run."),
        comparison_html,
        "<h2>Eleven candidate legal families</h2>",
        _table(["Family", "Applicability", "Reviewer", "Gaps"], family_rows, ""),
        '<p class="muted">Generated from the verified run bundle. Processing state describes report assembly only; '
        "no compliance verdict, legal approval or exhaustive law search is established.</p>",
        f'<p class="muted">{escape(LEGAL_NOTICE)}</p>',
        "</main></body></html>",
    ]
    return "\n".join(parts)


DASH_CSS = """
:root{--bg:#f7f6f2;--fg:#1b1b19;--muted:#6e6c66;--faint:#9a978f;--line:#e6e3da;--card:#fff;--track:#ece9e1;--accent:#3d5a80;--warn:#8a5a00;--warnbg:#fff3d9}
@media (prefers-color-scheme:dark){:root{--bg:#0d0d0c;--fg:#f1f0eb;--muted:#9b9890;--faint:#6d6b64;--line:#24231f;--card:#151513;--track:#22211e;--accent:#9fb7d9;--warn:#f0c46a;--warnbg:#2a2312}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1040px;margin:0 auto;padding:32px 20px 56px}
.num{font-variant-numeric:tabular-nums}
.top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;margin-bottom:24px}
h1{margin:0;font-size:26px;font-weight:650;text-wrap:balance}.sub{margin:4px 0 0;color:var(--muted);font-size:14px}.sub a{color:inherit}
.pill{display:inline-block;padding:4px 12px;border-radius:999px;border:1px solid var(--line);background:var(--card);font-size:13px;font-weight:600}
.pill.warn{background:var(--warnbg);color:var(--warn);border-color:transparent}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:22px 24px}
.label{color:var(--muted);font-size:13px}
.track{height:8px;border-radius:999px;background:var(--track);overflow:hidden;margin:12px 0 0}.track span{display:block;height:100%;background:var(--accent);border-radius:999px}
.hero{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.2fr);gap:28px;align-items:center;margin-bottom:14px}
.big{font-size:56px;font-weight:700;line-height:1.05}.big small{font-size:22px;color:var(--faint);font-weight:600}
.step{border-radius:14px;background:var(--bg);padding:16px 18px}.step b{display:block;font-size:16px;margin:2px 0 4px;text-wrap:pretty}
.kpis{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin-bottom:14px}
.kpi{padding:16px 18px}.kpi .v{font-size:30px;font-weight:700;margin-top:2px}.kpi .v small{font-size:15px;color:var(--faint)}.kpi .note{color:var(--muted);font-size:13px;margin-top:8px}
.grid2{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:14px;margin-bottom:14px}
h2{margin:0 0 12px;font-size:16px}ol,ul{margin:0;padding:0;list-style:none}
li{display:flex;justify-content:space-between;gap:12px;padding:10px 0;border-top:1px solid var(--line);font-size:14px}li:first-child{border-top:0;padding-top:0}
.n{color:var(--muted);white-space:nowrap}.hint{color:var(--muted);font-size:13px;margin:10px 0 0}
footer{color:var(--faint);font-size:12px;margin-top:24px}
@media (max-width:760px){.hero,.grid2{grid-template-columns:1fr}.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}}
"""


def _ended(value: str | None) -> str:
    """'2026-11-05T08:19:01.4Z' -> '2026-11-05 08:19 UTC': the same date form as the assessment date."""
    return f"{value[:10]} {value[11:16]} UTC" if value and len(value) >= 16 else "not ended"


def _track(points: int | None) -> str:
    return f'<div class="track"><span style="width:{(points or 0) * 10}%"></span></div>'


def _fraction(points: int | None) -> str:
    return "—" if points is None else f'{points}<small>/10</small>'


def render_dashboard(bundle: m.RevalidationBundle, card: m.Scorecard | None = None, report: str | None = None) -> str:
    """One self-contained page that reads at a glance: status, one big number, the next step, five
    meters, a short to-do list and owner questions. Details stay in the full report. No script, no request."""
    card = card or scorecard.score(bundle)
    hero, *meters = card.dimensions
    status = escape(scorecard.STATUS_LABELS[card.status])
    link = f' · <a href="{escape(quote(report))}">full report</a>' if report else ""
    fiction = '<span class="pill warn">Fictional sample data</span> ' if bundle.synthetic else ""
    step = card.next_step
    step_html = (f'<div class="step"><span class="label">Next step</span><b>{escape(scorecard.step_title(step))}</b>'
                 f'<span class="label num">{scorecard.step_unblocks(step)}</span></div>'
                 if step else '<div class="step"><span class="label">Next step</span><b>No recorded step is open</b>'
                 '<span class="label">That is not a compliance conclusion.</span></div>')
    kpis = "".join(
        f'<div class="card kpi"><div class="label">{escape(scorecard.LABELS[item.key])}</div>'
        f'<div class="v num">{_fraction(item.points)}</div>{_track(item.points)}'
        f'<div class="note num">{item.done} of {item.total} {escape(scorecard.UNITS[item.key])}</div></div>'
        for item in meters)
    todo = "".join(f'<li><span>{escape(item["action"])}</span><span class="n num">unblocks {item["unblocks"]}</span></li>'
                   for item in nextstep.next_steps(bundle, top=3)) or "<li><span>No recorded step is open.</span></li>"
    screening = card.screening
    coverage = [f'<li><span>Legal families screened</span><span class="n num">{screening.screened} of {screening.total}</span></li>']
    coverage += [f'<li><span>{escape(scorecard.HYGIENE_LABELS[item.key]).capitalize()}</span><span class="n num">{item.done} of {item.total}</span></li>'
                 for item in card.hygiene if item.total]
    coverage_hint = ('<p class="hint">Next: screen the eleven legal families with /eucg-audit.</p>'
                     if screening.screened < screening.total else "")
    questions = _open_facts(bundle)
    questions_html = ("" if not questions else
        '<section class="card"><h2>Questions for the owner</h2><ul>'
        + "".join(f'<li><span>{escape(fact.key)}</span><span class="n">{escape(fact.basis)} · ask {escape(fact.owner or "the project owner")}</span></li>'
                  for fact in questions)
        + "</ul></section>")
    parts = [
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
        "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\">",
        f"<title>EU Compliance Guard dashboard</title><style>{DASH_CSS}</style></head><body><main>",
        f'<div class="top"><div><h1>Review progress</h1><p class="sub">{escape(bundle.project_id)} · run ended '
        f'<span class="num">{escape(_ended(bundle.run.ended_at))}</span>{link}</p></div>'
        f'<div>{fiction}<span class="pill">{status}</span></div></div>',
        f'<section class="card hero"><div><div class="label">{escape(scorecard.LABELS[hero.key])} · requirements supported</div>'
        f'<div class="big num">{_fraction(hero.points)}</div>{_track(hero.points)}'
        f'<div class="label num" style="margin-top:8px">{hero.done} of {hero.total} requirements</div></div>{step_html}</section>',
        f'<section class="kpis">{kpis}</section>',
        f'<div class="grid2"><section class="card"><h2>To do</h2><ol>{todo}</ol></section>'
        f'<section class="card"><h2>Coverage</h2><ul>{"".join(coverage)}</ul>{coverage_hint}</section></div>',
        questions_html,
        f"<footer>{escape(scorecard.NOTICE)} Details are in the full report.<br>{escape(LEGAL_NOTICE)}</footer>",
        "</main></body></html>",
    ]
    return "\n".join(parts)


def verify_run(run_dir: str | os.PathLike, contents: dict[str, bytes] | None = None) -> m.RevalidationBundle:
    """Accept a run only when its marker and every listed artifact digest match."""
    from .history import load_run
    try:
        return load_run(run_dir, sources_out=contents)[0]
    except r.RevalidationError as error:
        raise ViewError(error.code) from None


def publish_views(anchor: Path, files: list[tuple[str, bytes]]) -> None:
    """Write files into `<anchor's parent>/views/` (0700 folder, 0600 files).

    Each file goes to a temporary name and is renamed into place, never through a symlink;
    the parent must be private. Failures surface as ViewError codes.
    """
    try:
        with r._parent(anchor) as (parent_fd, _):
            r._private_parent(parent_fd)
            try:
                os.mkdir("views", 0o700, dir_fd=parent_fd)
            except FileExistsError:
                pass
            views_fd = os.open("views", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent_fd)
            try:
                info = os.fstat(views_fd)
                if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
                    raise ViewError("privacy-unavailable")
                for name, content in files:
                    temporary = "." + name + ".tmp"
                    try:
                        os.unlink(temporary, dir_fd=views_fd)
                    except FileNotFoundError:
                        pass
                    r._write(views_fd, temporary, content, float("inf"))
                    os.replace(temporary, name, src_dir_fd=views_fd, dst_dir_fd=views_fd)
                os.fsync(views_fd)
            finally:
                os.close(views_fd)
    except r.RevalidationError as error:
        raise ViewError(error.code) from None
    except OSError:
        raise ViewError("io-failed") from None


def write_view(run_dir: str | os.PathLike, dashboard: bool = False) -> Path:
    """Write ``<parent>/views/<run>.html`` and ``<run>.scorecard.json`` (0700 directory, 0600 files).

    Each file is written to a temporary name and renamed into place, never through a symlink;
    an older view of the same run is replaced. Returns the HTML path.
    """
    if not os.fspath(run_dir):
        raise ViewError("unsafe-path")  # Path("") is ".": never fall back to the working directory.
    run_dir = Path(run_dir)
    contents: dict[str, bytes] = {}
    bundle = verify_run(run_dir, contents)
    card = scorecard.score(bundle)
    html = render_html(bundle, contents, card).encode("utf-8")
    files = [(run_dir.name + ".scorecard.json", scorecard.to_json(card)),
             (run_dir.name + ".dashboard.html", render_dashboard(bundle, card, run_dir.name + ".html").encode("utf-8")),
             (run_dir.name + ".html", html)]
    publish_views(run_dir, files)
    return run_dir.parent / "views" / (run_dir.name + (".dashboard.html" if dashboard else ".html"))
