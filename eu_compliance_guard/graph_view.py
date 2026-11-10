"""A static graph view (2.0 bolt 016): one self-contained HTML file, no script, no request.

It focuses on what a reviewer needs: functions on data flows or touching a concept, and their
direct neighbours. The layout is fixed (one column per file, functions in line order), so the
same graph always draws the same picture. Links between the picture and the lists are plain
anchors. Every count says what was left out; nothing is dropped silently.
"""
from __future__ import annotations

from html import escape
from pathlib import Path

from . import authoring, graph as graphs, grounding, models as m
from .notice import LEGAL_NOTICE
from .view import DASH_CSS, publish_views

MAX_SHOWN = 150
COLUMNS = 4
COLUMN_WIDTH, BOX_WIDTH, ROW, HEADER = 270, 230, 44, 40

GRAPH_CSS = """
svg{width:100%;height:auto;background:var(--card);border:1px solid var(--line);border-radius:18px}
svg text{font:12px system-ui,-apple-system,"Segoe UI",sans-serif;fill:var(--fg)}
svg .file{fill:var(--muted);font-weight:600}svg .tags{fill:var(--muted);font-size:11px}
svg rect{fill:var(--bg);stroke:var(--line)}svg .flow rect{stroke:var(--accent);stroke-width:2}
svg line{stroke:var(--faint);stroke-width:1.2}svg line.flow{stroke:var(--accent);stroke-width:2.5}
svg line.ambiguous{stroke-dasharray:4 4}
.legend{color:var(--muted);font-size:13px;margin:8px 0 14px}
section.card{margin-bottom:14px}code{font-size:13px}
td,th{text-align:left;vertical-align:top;padding:8px 10px;border-bottom:1px solid var(--line);font-size:14px}
table{width:100%;border-collapse:collapse}th{color:var(--muted);font-weight:600}
"""


def _anchor(node_id: str) -> str:
    return "n-" + node_id.removeprefix("node-")


def _law_links(declared: m.RevalidationInput) -> dict[str, list[str]]:
    """Fact id -> requirements and obligations that rely on it, with the provisions those obligations pin."""
    obligations = {item.id: item for item in declared.obligations}
    links: dict[str, set[str]] = {}
    for requirement in declared.requirements:
        for ref in requirement.fact_refs:
            links.setdefault(ref.id, set()).add(f"requirement {requirement.id}")
    for decision in declared.applicability_decisions:
        obligation = obligations.get(decision.obligation.id)
        where = ", ".join(pin.locator for pin in obligation.source_provisions[:3]) if obligation else ""
        for ref in decision.fact_refs:
            links.setdefault(ref.id, set()).add(f"obligation {decision.obligation.id}" + (f" ({where})" if where else ""))
    return {fact: sorted(items) for fact, items in links.items()}


def render(project: m.ProjectGraph, declared: m.RevalidationInput | None = None, project_id: str = "") -> str:
    nodes = {node.id: node for node in project.nodes}
    flows = graphs.flows(project)
    refs = {ref for item in (declared.evidence if declared else []) for ref in item.evidence.source_refs}
    facts_by_evidence: dict[str, set[str]] = {}
    for fact in (m.scope_facts(declared.scope) if declared else []):
        for evidence in fact.evidence_ids:
            facts_by_evidence.setdefault(evidence, set()).add(fact.id)
    flow_nodes = {graphs.node_id(hop["location"].rpartition(":")[0], hop["name"]) for flow in flows for hop in flow["hops"]}
    calls = [edge for edge in project.edges if edge.kind == "calls"]
    interesting = flow_nodes | {node.id for node in project.nodes if node.kind == "function" and (node.concepts or node.data)}
    neighbours = {edge.target for edge in calls if edge.source in flow_nodes} | {edge.source for edge in calls if edge.target in flow_nodes}
    candidates = sorted(interesting | neighbours, key=lambda key: (key not in flow_nodes, -len(nodes[key].concepts),
                                                                   nodes[key].path, nodes[key].line))
    shown = set(candidates[:MAX_SHOWN])
    flow_edges = set()
    for flow in flows:
        hops = [graphs.node_id(hop["location"].rpartition(":")[0], hop["name"]) for hop in flow["hops"]]
        flow_edges.update(zip(hops, hops[1:]))

    # Fixed layout: files in path order, COLUMNS per band; functions in line order inside a file.
    files = sorted({nodes[key].path for key in shown})
    position: dict[str, tuple[int, int]] = {}
    bands, band_height, y = [], 0, 20
    for index, path in enumerate(files):
        if index and index % COLUMNS == 0:
            y += band_height + 30
            band_height = 0
        members = sorted((key for key in shown if nodes[key].path == path), key=lambda key: nodes[key].line)
        x = 20 + (index % COLUMNS) * COLUMN_WIDTH
        bands.append((path, x, y))
        for row, key in enumerate(members):
            position[key] = (x, y + HEADER + row * ROW)
        band_height = max(band_height, HEADER + len(members) * ROW)
    height = y + band_height + 20
    width = 20 + min(COLUMNS, max(1, len(files))) * COLUMN_WIDTH
    svg = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Project graph: files, functions and calls">']
    for edge in sorted(calls, key=lambda item: (item.source, item.target)):
        if edge.source in position and edge.target in position:
            (x1, y1), (x2, y2) = position[edge.source], position[edge.target]
            kind = "flow" if (edge.source, edge.target) in flow_edges else ""
            kind += " ambiguous" if edge.provenance == "ambiguous" else ""
            if x1 == x2:  # same file: from the bottom of one box to the top of the other
                down = y2 > y1
                svg.append(f'<line class="{kind.strip()}" x1="{x1 + 30}" y1="{y1 + (34 if down else 0)}" '
                           f'x2="{x2 + 30}" y2="{y2 + (0 if down else 34)}"/>')
            else:
                svg.append(f'<line class="{kind.strip()}" x1="{x1 + BOX_WIDTH}" y1="{y1 + 16}" x2="{x2}" y2="{y2 + 16}"/>')
    for path, x, top in bands:
        svg.append(f'<text class="file" x="{x}" y="{top + 20}">{escape(path[-34:])}</text>')
    for key, (x, top) in sorted(position.items()):
        node = nodes[key]
        extra = [item.replace("_", " ") for item in node.data if item not in node.concepts]
        tags = ", ".join(item.replace("_", " ") for item in node.concepts) + (("; data: " if node.concepts else "data: ")
                                                                             + ", ".join(extra) if extra else "")
        svg.append(f'<a href="#{_anchor(key)}"><g class="{"flow" if key in flow_nodes else ""}">'
                   f'<rect x="{x}" y="{top}" width="{BOX_WIDTH}" height="34" rx="8"/>'
                   f'<text x="{x + 10}" y="{top + 15}">{escape(node.name[-30:])}</text>'
                   f'<text class="tags" x="{x + 10}" y="{top + 28}">{escape(tags[:40])}</text></g></a>')
    svg.append("</svg>")

    flow_rows = []
    for flow in flows:
        facts = sorted({fact for item in (declared.evidence if declared else [])
                        if graphs.covers(flow, set(item.evidence.source_refs))
                        for fact in facts_by_evidence.get(item.evidence.id, ())})
        route = " → ".join(f'<a href="#{_anchor(graphs.node_id(hop["location"].rpartition(":")[0], hop["name"]))}">'
                           f'{escape(hop["name"])}</a> <code>{escape(hop["location"])}</code>' for hop in flow["hops"])
        flow_rows.append(f"<tr><td>{escape(', '.join(flow['data']))} → {escape(', '.join(flow['sinks']))}</td><td>{route}</td>"
                         f"<td>{escape(flow['provenance'])}</td><td>{escape(', '.join(facts)) if facts else 'no fact covers it'}</td></tr>")
    law = _law_links(declared) if declared else {}
    fact_rows = [f"<tr><td><code>{escape(fact)}</code></td><td>{escape('; '.join(items))}</td></tr>" for fact, items in sorted(law.items())]
    function_rows = []
    for key in sorted(shown, key=lambda item: (nodes[item].path, nodes[item].line)):
        node = nodes[key]
        out = sorted(nodes[edge.target].name for edge in calls if edge.source == key)
        into = sorted(nodes[edge.source].name for edge in calls if edge.target == key)
        function_rows.append(f'<tr id="{_anchor(key)}"><td><code>{escape(node.path)}:{node.line}</code></td><td>{escape(node.name)}</td>'
                             f"<td>{escape(', '.join(node.concepts) or '—')}</td><td>{escape(', '.join(node.data) or '—')}</td>"
                             f"<td>{escape(', '.join(into) or '—')}</td><td>{escape(', '.join(out) or '—')}</td></tr>")
    left_out = len(interesting | neighbours) - len(shown)
    functions = sum(node.kind == "function" for node in project.nodes)
    title = escape(project_id) if project_id else "this project"
    parts = [
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
        "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\">",
        f"<title>EU Compliance Guard graph</title><style>{DASH_CSS}{GRAPH_CSS}</style></head><body><main>",
        f'<div class="top"><div><h1>Project graph</h1><p class="sub">{title} · {project.parsed} of {project.files} Python and Rust files · '
        f'{functions} functions · {len(flows)} data flow{"s" if len(flows) != 1 else ""}</p></div>'
        f'<div><span class="pill">digest {escape(project.digest[7:19])}</span></div></div>',
        f'<p class="legend">Showing {len(shown)} functions on data flows or touching a concept, and their neighbours'
        + (f"; {left_out} more are listed by <code>graph --json</code>" if left_out else "")
        + ". Highlighted: data flows. Dashed: ambiguous calls. Select a box to jump to its details.</p>",
        "".join(svg),
        '<section class="card" style="margin-top:14px"><h2>Data flows</h2>'
        + ("<table><tr><th>From → to</th><th>Path</th><th>Parsing</th><th>Facts on it</th></tr>" + "".join(flow_rows) + "</table>"
           if flow_rows else '<p class="hint">No flow from personal data to AI, tracking, third parties or marketing was found by parsing. '
           "That is not evidence that none exists.</p>") + "</section>",
        ('<section class="card"><h2>From law to code</h2><table><tr><th>Fact</th><th>Relied on by</th></tr>'
         + "".join(fact_rows) + "</table></section>") if fact_rows else "",
        '<section class="card"><h2>Functions shown</h2><table><tr><th>Where</th><th>Name</th><th>Concepts</th><th>Data</th>'
        "<th>Called by</th><th>Calls</th></tr>" + "".join(function_rows) + "</table></section>",
        f"<footer>{escape(project.notice)}<br>{escape(LEGAL_NOTICE)}</footer>",
        "</main></body></html>",
    ]
    return "\n".join(parts)


def write(declarations: str | Path) -> Path:
    """Write `<state-dir>/views/graph.html` for the project the declarations describe."""
    path = Path(declarations)
    declared, root = grounding._declarations(path)
    project = graphs.build_graph(root, grounding._own_files(path, root))
    state = authoring.state_dir(path)
    publish_views(state / "graph", [("graph.html", render(project, declared, declared.project_id).encode("utf-8"))])
    return state / "views" / "graph.html"
