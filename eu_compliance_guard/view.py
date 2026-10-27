"""Static, escaped HTML view of one verified run; a derived file, never part of the run.

The view is written beside the run directory (``<parent>/views/<run>.html``) so the
immutable run and its completion marker stay untouched. It holds no scripts, loads
nothing, and renders recorded metadata only; it is not a compliance verdict.
"""
from __future__ import annotations

from collections import Counter
from html import escape
import os
from pathlib import Path
import stat

from . import models as m, revalidation as r

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
.tag.ok{background:var(--okbg);color:var(--ok)}.tag.bad{background:var(--badbg);color:var(--bad)}
ul{margin:0;padding-left:20px}code{font-size:13px;word-break:break-all}
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


def render_html(bundle: m.RevalidationBundle) -> str:
    """Every dynamic value passes through html.escape; nothing executes or loads."""
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
        requirement_rows.append([f"<code>{escape(requirement.id)}</code>", escape(requirement.statement), escape(location),
                                 _tag(assessment.state), _list(assessment.gaps)])
    obligation_rows = []
    for disposition in bundle.obligation_dispositions:
        obligation = obligations[disposition.obligation_id]
        decision = decisions[disposition.obligation_id]
        references = [f"{pin.source_id or pin.source_target_id} — {pin.locator}" for pin in obligation.source_provisions]
        methods = " ".join(_tag(f"{item.method}: {item.outcome}") for item in disposition.required_method_dispositions)
        obligation_rows.append([f"<code>{escape(obligation.id)}</code>", escape(f"{obligation.family} · {obligation.classification}"),
                                _list(references), _tag(decision.applicability) + f'<br><span class="muted">{escape(decision.reviewer or "no reviewer")}</span>',
                                methods or '<span class="muted">none declared</span>'])
    attempt_rows = [[f"<code>{escape(item.source_target_id)}</code>", _tag(item.state),
                     f"<code>{escape(item.retrieval.final_url or item.retrieval.requested_url)}</code>",
                     escape(str(item.retrieval.status or "—")), _tag(item.retrieval.comparison),
                     escape(f"{item.failure.code}: {item.failure.safe_message}" if item.failure else "—")]
                    for item in bundle.source_attempts]
    family_rows = [[escape(item.family), _tag(item.applicability), escape(item.reviewer or "—"), _list(item.gaps)]
                   for item in bundle.family_screenings]
    comparison_html = ""
    if bundle.comparison is not None:
        comparison_html = (
            "<h2>Predecessor comparison</h2>"
            f'<p>Historical run <code>{escape(bundle.comparison.previous_run_id)}</code>. '
            "Matching recorded inputs renew neither legal currency nor reviewer approval.</p>"
            + _table(["Dependency", "ID or path", "Previous digest", "Current digest"],
                [[escape(item.kind), escape(item.identity), escape(item.before or "not present"),
                  escape(item.after or "not present")] for item in bundle.comparison.changes],
                "Recorded dependencies unchanged.")
            + _table(["Historical disposition", "Freshness", "Changed dependencies", "Review actions and uncertainty"],
                [[escape(item.obligation_disposition_id), _tag(item.freshness), _list(item.changed_dependencies),
                  _list(item.reasons)] for item in bundle.current_assessments], "No historical dispositions."))
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
        "<h2>What needs attention</h2>",
        "<p class=\"muted\">Review gaps are open questions, not established violations. Reviewed deficiencies record a named reviewer's assessment.</p>",
        _table(["Area", "Item", "What is open"], [_gap_row(gap) for gap in bundle.gaps],
               "No open gaps recorded. That is not a compliance conclusion."),
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


def verify_run(run_dir: str | os.PathLike) -> m.RevalidationBundle:
    """Accept a run only when its marker and every listed artifact digest match."""
    from .history import load_run
    try:
        return load_run(run_dir)[0]
    except r.RevalidationError as error:
        raise ViewError(error.code) from None


def write_view(run_dir: str | os.PathLike) -> Path:
    """Write ``<parent>/views/<run>.html`` (0700 directory, 0600 file), replacing an older view."""
    run_dir = Path(run_dir)
    html = render_html(verify_run(run_dir)).encode("utf-8")
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
