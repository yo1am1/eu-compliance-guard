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
import re
import stat

from . import articles, models as m, nextstep, revalidation as r

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
ul{margin:0;padding-left:20px}code{font-size:13px;overflow-wrap:anywhere}td:first-child code{overflow-wrap:normal;word-break:normal}
"""


class ViewError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _tag(value: str) -> str:
    kind = "ok" if value in ("supported", "applicable", "passed", "retrieved", "completed", "same_bytes") else (
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


def _gap_row(gap: str) -> list[str]:
    subject, _, detail = gap.partition(": ")
    if not detail:
        return [_tag("coverage"), "", escape(gap)]
    area = "source target" if subject.startswith("Source target ") else subject.split(" ", 1)[0].lower()
    return [_tag(area), f"<code>{escape(subject.split(' ', 2 if area == 'source target' else 1)[-1])}</code>", escape(detail)]


# Most actionable areas first; long, low-signal groups start collapsed.
AREAS = [("requirement", "Requirements", True), ("obligation", "Candidate obligations", True),
         ("historical", "Changed since the previous run", True), ("source target", "Source targets", True),
         ("source", "Selected sources", True), ("evidence", "Evidence", True), ("fact", "Facts to confirm", False),
         ("family", "Legal families to screen", False)]


def _attention(gaps: list[str]) -> str:
    groups: dict[str, list] = {}
    for gap in gaps:
        row = _gap_row(gap)
        area = re.sub(r"<[^>]+>", "", row[0])
        groups.setdefault(area if area in {key for key, _, _ in AREAS} else "coverage", []).append(row)
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


def _owner_questions(bundle: m.RevalidationBundle) -> str:
    """Assumed, unknown or conflicting facts as questions, with the requirements that rely on them."""
    declared = bundle.declarations
    relied: dict[str, list[str]] = {}
    for requirement in declared.requirements:
        for pin in requirement.fact_refs:
            relied.setdefault(pin.id, []).append(requirement.id)
    facts = {item.id: item for item in m.scope_facts(declared.scope)
             if item.basis in ("assumed", "unknown") or item.conflicts}
    if not facts:
        return '<p class="muted">Every declared fact is marked declared or observed.</p>'
    rows = [[escape(fact.key), escape(_value(fact.value)), _tag(fact.basis), escape(fact.owner or "—"),
             _list(relied.get(fact.id, []))] for fact in facts.values()]
    return _table(["Question", "Current answer", "Basis", "Owner", "Requirements relying on it"], rows, "")


def _next_steps(bundle: m.RevalidationBundle) -> str:
    steps = nextstep.next_steps(bundle, 3)
    if not steps:
        return '<p class="muted">No recorded step is open. That is not a compliance conclusion.</p>'
    items = "".join(f"<li><b>{escape(step['action'])}</b> <span class=\"muted\">Unblocks {step['unblocks']} open "
                    f"requirement(s).</span>" + (f"<br><code>{escape(step['command'])}</code>" if step["command"] else "")
                    + "</li>" for step in steps)
    return f'<ol class="next">{items}</ol>'


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


def _article(pin: m.ProvisionRef, acts: dict[str, dict[str, dict]], by_source: dict[str, dict[str, dict]]) -> str:
    """A pin naming a source shows that source's text; only an unpinned target falls back to the target's."""
    key = articles.article_key(pin.locator)
    origin = pin.source_id if pin.source_id else pin.source_target_id
    pool = by_source.get(pin.source_id, {}) if pin.source_id else acts.get(pin.source_target_id, {})
    item = pool.get(key) if key else None
    target = origin
    if item is None:
        return ""
    text = item["text"] if len(item["text"]) <= EXCERPT_CHARS else item["text"][:EXCERPT_CHARS].rsplit(" ", 1)[0] + " …"
    return (f'<details class="law"><summary>{escape(key)} — {escape(item["title"] or "untitled")}</summary>'
            f'<p>{escape(text)}</p><p>Unreviewed candidate text from the retained <code>{escape(target)}</code> bytes; '
            "check the official consolidated version before relying on it.</p></details>")


def _suggestions(statement: str, index: articles.ArticleIndex) -> str:
    found = index.suggest(statement, top=3)
    if not found:
        return ""
    names = " · ".join(f'{escape(item["article"])} <span class="muted">{escape(item["title"][:60])} ({escape(item["source"])})</span>'
                       for item in found)
    return f'<div class="suggest">Articles to read: {names}<br><span class="muted">Text search suggestion, not a mapping.</span></div>'


def render_html(bundle: m.RevalidationBundle, contents: dict[str, bytes] | None = None) -> str:
    """Every dynamic value passes through html.escape; nothing executes or loads."""
    acts = catalogue(bundle, contents or {})
    by_source = source_catalogue(bundle, contents or {})
    index = articles.ArticleIndex(acts)
    declared = bundle.declarations
    obligations = {item.id: item for item in declared.obligations}
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
        references = "".join(f"<li>{escape(f'{pin.source_id or pin.source_target_id} — {pin.locator}')}"
                             f"{_article(pin, acts, by_source)}</li>" for pin in obligation.source_provisions)
        methods = " ".join(_tag(f"{item.method}: {item.outcome}") for item in disposition.required_method_dispositions)
        obligation_rows.append([f"<code>{escape(obligation.id)}</code>", escape(f"{obligation.family} · {obligation.classification}"),
                                f"<ul>{references}</ul>" if references else "—", _tag(decision.applicability) + f'<br><span class="muted">{escape(decision.reviewer or "no reviewer")}</span>',
                                methods or '<span class="muted">none declared</span>'])
    attempt_rows = [[f"<code>{escape(item.source_target_id)}</code>", _tag(item.state),
                     f"<code>{escape(item.retrieval.final_url or item.retrieval.requested_url)}</code>",
                     escape(str(item.retrieval.status or "—")), _tag(item.retrieval.comparison),
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
        _table(["Target", "State", "URL", "HTTP", "Compared", "Failure"], attempt_rows, "No retrieval was requested for this run."),
        comparison_html,
        "<h2>Eleven candidate legal families</h2>",
        _table(["Family", "Applicability", "Reviewer", "Gaps"], family_rows, ""),
        '<p class="muted">Generated from the verified run bundle. Processing state describes report assembly only; '
        "no compliance verdict, legal approval or exhaustive law search is established.</p>",
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


def write_view(run_dir: str | os.PathLike) -> Path:
    """Write ``<parent>/views/<run>.html`` (0700 directory, 0600 file), replacing an older view."""
    if not os.fspath(run_dir):
        raise ViewError("unsafe-path")  # Path("") is ".": never fall back to the working directory.
    run_dir = Path(run_dir)
    contents: dict[str, bytes] = {}
    html = render_html(verify_run(run_dir, contents), contents).encode("utf-8")
    try:
        with r._parent(run_dir) as (parent_fd, _):
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
                name, temporary = run_dir.name + ".html", "." + run_dir.name + ".html.tmp"
                try:
                    os.unlink(temporary, dir_fd=views_fd)
                except FileNotFoundError:
                    pass
                r._write(views_fd, temporary, html, float("inf"))
                os.replace(temporary, name, src_dir_fd=views_fd, dst_dir_fd=views_fd)
                os.fsync(views_fd)
            finally:
                os.close(views_fd)
    except r.RevalidationError as error:
        raise ViewError(error.code) from None
    except OSError:
        raise ViewError("io-failed") from None
    return run_dir.parent / "views" / (run_dir.name + ".html")
