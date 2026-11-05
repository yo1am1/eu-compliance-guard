"""Project graph (2.0 bolt 012): files, classes and functions of a Python project, with the
imports and calls between them and the concepts each touches.

Built only by parsing (the standard library `ast`): no project code is imported or run. Files are
read like `ground` reads them (no symlinks, bounded, dependency folders skipped). The same files
always give a byte-identical graph. Static parsing misses dynamic calls, so every path through the
graph is a possible path, and an empty graph never shows compliance.
"""
from __future__ import annotations

import ast
from collections import Counter
import hashlib
import json
from pathlib import Path

from . import grounding, models as m, prcheck

MAX_AMBIGUOUS = 5


def node_id(path: str, name: str = "") -> str:
    return "node-" + hashlib.sha256(f"{path}::{name}".encode("utf-8")).hexdigest()[:24]


def _module(path: str) -> str:
    parts = path[:-3].split("/")
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _concepts(text: str) -> list[str]:
    """pr-check's rule: a strong term counts alone, otherwise two of a concept's terms must appear."""
    return prcheck.concepts_in(text)


def _called(call: ast.Call) -> tuple[str | None, str] | None:
    """(qualifier, name): `f()` -> (None, "f"); `module.f()` -> ("module", "f"); `a.b.f()` -> (None, "f")."""
    if isinstance(call.func, ast.Name):
        return None, call.func.id
    if isinstance(call.func, ast.Attribute):
        owner = call.func.value
        return (owner.id if isinstance(owner, ast.Name) else None), call.func.attr
    return None


class _FileVisitor(ast.NodeVisitor):
    """Definitions, calls and imports of one file; qualified names follow nesting."""

    def __init__(self, path: str, text: str):
        self.path, self.text = path, text
        self.scope = [(node_id(path), "")]
        self.definitions: list[tuple[str, str, str, int, list[str], str]] = []  # id, kind, qualname, line, concepts, parent
        self.calls: list[tuple[str, str | None, str, int]] = []  # caller id, qualifier, called name, line
        self.imports: list[tuple[str, int, int]] = []  # module, level, line
        self.symbols: list[tuple[str, str, str, int]] = []  # local name, module, imported name, level
        self.aliases: list[tuple[str, str, int]] = []  # local name, module, level

    def _define(self, node, kind: str) -> None:
        parent, prefix = self.scope[-1]
        qualname = f"{prefix}.{node.name}" if prefix else node.name
        identity = node_id(self.path, qualname)
        segment = ast.get_source_segment(self.text, node) or node.name
        self.definitions.append((identity, kind, qualname, node.lineno, _concepts(segment), parent))
        self.scope.append((identity, qualname))
        self.generic_visit(node)
        self.scope.pop()

    def visit_ClassDef(self, node):
        self._define(node, "class")

    def visit_FunctionDef(self, node):
        self._define(node, "function")

    def visit_AsyncFunctionDef(self, node):
        self._define(node, "function")

    def visit_Call(self, node):
        called = _called(node)
        if called is not None:
            self.calls.append((self.scope[-1][0], *called, node.lineno))
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append((alias.name, 0, node.lineno))
            if alias.asname:
                self.aliases.append((alias.asname, alias.name, 0))

    def visit_ImportFrom(self, node):
        base = node.module or ""
        self.imports.append((base, node.level, node.lineno))
        for alias in node.names:
            local = alias.asname or alias.name
            # `from package import name` names a submodule or a symbol; both readings are kept.
            submodule = f"{base}.{alias.name}" if base else alias.name
            self.imports.append((submodule, node.level, node.lineno))
            self.aliases.append((local, submodule, node.level))
            self.symbols.append((local, base, alias.name, node.level))


def _resolve(path: str, module: str, level: int, modules: dict[str, str]) -> str | None:
    if level:
        package = _module(path).split(".")
        package = package[:len(package) - level + (1 if path.endswith("__init__.py") else 0)]
        module = ".".join([*package, module] if module else package)
    return modules.get(module)


def build_graph(root: Path, exclude: frozenset[str] = frozenset()) -> m.ProjectGraph:
    files, skipped = grounding.read_project(Path(root), exclude)
    python = [(path, raw, text) for path, raw, text in files if path.endswith(".py")]
    modules = {_module(path): path for path, _, _ in python}
    nodes: dict[str, m.GraphNode] = {}
    edges: set[tuple[str, str, str, str, int]] = set()  # source, kind, target, provenance, line
    by_name: dict[str, list[str]] = {}
    pending_calls: list[tuple[str, str, str | None, str, int]] = []  # path, caller, qualifier, name, line
    top_level: dict[str, dict[str, str]] = {}  # path -> top-level name -> node id
    scopes: dict[str, tuple[dict[str, str], dict[str, str]]] = {}  # path -> (symbol -> node id, alias -> path)
    parsed = 0
    for path, _, text in python:
        try:
            tree = ast.parse(text, filename=path)
        except (SyntaxError, ValueError, RecursionError, MemoryError):
            skipped += 1
            continue
        parsed += 1
        visitor = _FileVisitor(path, text)
        try:
            visitor.visit(tree)
        except RecursionError:
            skipped += 1
            continue
        nodes[node_id(path)] = m.GraphNode(id=node_id(path), kind="file", path=path, name=path, line=1,
                                           concepts=_concepts(text))
        for identity, kind, qualname, line, concepts, parent in visitor.definitions:
            nodes[identity] = m.GraphNode(id=identity, kind=kind, path=path, name=qualname, line=line, concepts=concepts)
            edges.add((parent, "defines", identity, "extracted", line))
            by_name.setdefault(qualname.rsplit(".", 1)[-1], []).append(identity)
        pending_calls += [(path, *call) for call in visitor.calls]
        top_level[path] = {qualname: identity for identity, _, qualname, _, _, _ in visitor.definitions if "." not in qualname}
        scopes[path] = ({}, {})
        for local, module, level in visitor.aliases:
            target = _resolve(path, module, level, modules)
            if target is not None:
                scopes[path][1][local] = target
        pending_symbols = [(path, local, module, name, level) for local, module, name, level in visitor.symbols]
        for _, local, module, name, level in pending_symbols:
            scopes[path][0].setdefault(local, f"{module}\0{name}\0{level}")
        for module, level, line in visitor.imports:
            target = _resolve(path, module, level, modules)
            if target is not None and target != path:
                edges.add((node_id(path), "imports", node_id(target), "extracted", line))
    def lookup(path: str, qualifier: str | None, name: str) -> str | None:
        """Python's own lookup order: this file's definitions, then imported names and modules."""
        symbols, aliases = scopes.get(path, ({}, {}))
        if qualifier is None:
            if name in top_level.get(path, {}):
                return top_level[path][name]
            if name in symbols:
                module, imported, level = symbols[name].split("\0")
                source = _resolve(path, module, int(level), modules)
                return top_level.get(source, {}).get(imported) if source else None
            return None
        source = aliases.get(qualifier)
        return top_level.get(source, {}).get(name) if source else None

    for path, caller, qualifier, name, line in pending_calls:
        found = lookup(path, qualifier, name)
        if found is not None:
            edges.add((caller, "calls", found, "extracted", line))
            continue
        if qualifier is not None and qualifier in scopes.get(path, ({}, {}))[1]:
            continue  # a project module's attribute that defines nothing by that name: no guess
        targets = sorted(by_name.get(name, []))
        if len(targets) == 1:
            edges.add((caller, "calls", targets[0], "extracted", line))
        else:
            for target in targets[:MAX_AMBIGUOUS]:
                edges.add((caller, "calls", target, "ambiguous", line))
    digest = m.content_digest(json.dumps(sorted((path, m.content_digest(raw)) for path, raw, _ in python)).encode("utf-8"))
    ordered = sorted(edges, key=lambda edge: (edge[0], edge[1], edge[2], edge[4], edge[3]))
    unique: dict[tuple, tuple] = {}
    for edge in ordered:
        # One edge per (source, kind, target, line): an extracted reading wins over an ambiguous one.
        unique.setdefault((edge[0], edge[1], edge[2], edge[4]), edge)
    return m.ProjectGraph(
        schema_version=1, graph_version=1, files=len(python), parsed=parsed, skipped=skipped, digest=digest,
        nodes=[nodes[key] for key in sorted(nodes)],
        edges=[m.GraphEdge(source=s, kind=k, target=t, provenance=p, line=n) for s, k, t, p, n in unique.values()],
        notice=m.GRAPH_NOTICE)


def to_json(graph: m.ProjectGraph) -> bytes:
    return (json.dumps(graph.model_dump(mode="json"), indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def format_graph(graph: m.ProjectGraph, top: int = 10) -> str:
    kinds = Counter(node.kind for node in graph.nodes)
    calls = [edge for edge in graph.edges if edge.kind == "calls"]
    ambiguous = sum(edge.provenance == "ambiguous" for edge in calls)
    lines = [f"{graph.parsed} of {graph.files} Python files parsed ({graph.skipped} skipped) · digest {graph.digest[:19]}…",
             f"{kinds['class']} classes · {kinds['function']} functions · {len(calls)} calls ({ambiguous} ambiguous) · "
             f"{sum(edge.kind == 'imports' for edge in graph.edges)} imports"]
    tagged = Counter(concept for node in graph.nodes if node.kind != "file" for concept in node.concepts)
    if tagged:
        lines.append("concepts in functions and classes: " + ", ".join(f"{name} {count}" for name, count in sorted(tagged.items())))
    sensitive = [node for node in graph.nodes if node.kind == "function" and node.concepts]
    for node in sorted(sensitive, key=lambda item: (-len(item.concepts), item.path, item.line))[:top]:
        lines.append(f"  {node.path}:{node.line}  {node.name}  [{', '.join(node.concepts)}]")
    lines.append(graph.notice)
    return "\n".join(lines)
