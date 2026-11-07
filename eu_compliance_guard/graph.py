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
import functools
import hashlib
import json
from pathlib import Path

from . import grounding, models as m, prcheck

MAX_AMBIGUOUS = 5
DATA = ("personal_data", "special_category", "children")
SINKS = ("ai", "tracking", "third_party", "marketing")
MAX_FLOW_DEPTH = 6
# A call the parser cannot resolve links every function of that name; a route through more than
# one such guess is mostly noise on real projects, so it is not followed.
MAX_AMBIGUOUS_HOPS = 1
MAX_FLOWS = 200


def node_id(path: str, name: str = "") -> str:
    return "node-" + hashlib.sha256(f"{path}::{name}".encode("utf-8")).hexdigest()[:24]


def _module(path: str) -> str:
    parts = path[:-3].split("/")
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _concepts(text: str) -> list[str]:
    """pr-check's rule: a strong term counts alone, otherwise two of a concept's terms must appear."""
    return prcheck.concepts_in(text)


# Kinds of data, recognised from identifiers and short string keys only (never comments or
# docstrings), as whole word sequences within one identifier: `birth_date`, `emailAddress`,
# `row["phone"]`. Generic words such as `user`, `name`, `account`, `child` or `age` are not
# enough on their own: in code they mostly mean something technical (child spans, JWT `kid`,
# `max_age`), which real repositories showed.
DATA_PHRASES = {
    "personal_data": (("email",), ("e", "mail"), ("phone",), ("mobile", "number"), ("first", "name"), ("last", "name"),
                      ("full", "name"), ("given", "name"), ("family", "name"), ("surname",), ("street",),
                      ("postal", "code"), ("zip", "code"), ("postcode",), ("home", "address"), ("postal", "address"),
                      ("billing", "address"), ("shipping", "address"), ("ip", "address"), ("date", "of", "birth"),
                      ("birth", "date"), ("birthdate",), ("birthday",), ("dob",), ("gender",), ("geolocation",),
                      ("latitude",), ("longitude",), ("passport",), ("ssn",), ("national", "id"), ("iban",),
                      ("credit", "card"), ("card", "number"), ("social", "security")),
    "special_category": (("health", "data"), ("health", "record"), ("health", "records"), ("health", "condition"),
                         ("health", "conditions"), ("health", "information"), ("health", "status", "of"), ("medical",), ("diagnosis",), ("biometric",), ("biometrics",), ("pregnancy",),
                         ("religion",), ("religious",), ("ethnicity",), ("ethnic",), ("sexual",), ("disability",),
                         ("bmi",), ("heart", "rate"), ("blood", "pressure"), ("weight", "kg"), ("weight", "lbs"),
                         ("body", "weight"), ("allergy",), ("allergies",), ("medication",)),
    "children": (("parental",), ("guardian",), ("coppa",), ("is", "minor"), ("minor", "user"), ("under", "13"),
                 ("under", "16"), ("age", "verification"), ("age", "gate"), ("age", "check"), ("child", "account"),
                 ("child", "profile"), ("child", "user"), ("kids", "mode")),
}
# Words that make a one-word data phrase technical next to it in the same identifier. "health"
# alone is no longer a data word: in code it is mostly a check or a release-health metric, so it
# counts only with a data word ("health_data", "health_record").
TECHNICAL: dict[str, set[str]] = {}
MAX_KEY = 40  # a string constant this short without spaces reads as a key, not prose


def _identifiers(node: ast.AST) -> list[str]:
    """Names, attributes, parameters, keyword names and short string keys within a definition."""
    found = []
    for item in ast.walk(node):
        if isinstance(item, ast.Name):
            found.append(item.id)
        elif isinstance(item, ast.Attribute):
            found.append(item.attr)
        elif isinstance(item, ast.arg):
            found.append(item.arg)
        elif isinstance(item, ast.keyword) and item.arg:
            found.append(item.arg)
        elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            found.append(item.name)
        elif isinstance(item, ast.Constant) and isinstance(item.value, str) and len(item.value) <= MAX_KEY \
                and item.value and not any(char.isspace() for char in item.value):
            found.append(item.value)
    return found


@functools.lru_cache(maxsize=65536)
def _identifier_data(identifier: str) -> frozenset[str]:
    """The kinds of data one identifier names; cached, since identifiers repeat across a project."""
    words = [word.lower() for word in grounding._words(identifier)]
    kinds = set()
    for kind, phrases in DATA_PHRASES.items():
        for phrase in phrases:
            size = len(phrase)
            for at in range(len(words) - size + 1):
                if tuple(words[at:at + size]) != phrase:
                    continue
                neighbours = set(words[max(at - 1, 0):at]) | set(words[at + size:at + size + 1])
                if size == 1 and TECHNICAL.get(phrase[0], set()) & neighbours:
                    continue
                kinds.add(kind)
                break
            if kind in kinds:
                break
    return frozenset(kinds)


def _data(node: ast.AST) -> list[str]:
    kinds = set()
    for identifier in set(_identifiers(node)):
        kinds |= _identifier_data(identifier)
    return [kind for kind in DATA if kind in kinds]


def is_test_file(path: str) -> bool:
    """Test code: a tests or benches folder, test_*.py, *_test.py, *_test.rs, tests.rs or conftest.py.
    Its data is fixtures, not processing."""
    parts = path.split("/")
    name = parts[-1]
    return any(part in ("tests", "test", "testing", "benches") for part in parts[:-1]) or name.startswith("test_") \
        or name.endswith(("_test.py", "_test.rs")) or name in ("conftest.py", "tests.rs")


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
        self.definitions: list[tuple] = []  # id, kind, qualname, line, end line, concepts, data, parent
        self.calls: list[tuple[str, str | None, str, int]] = []  # caller id, qualifier, called name, line
        self.imports: list[tuple[str, int, int]] = []  # module, level, line
        self.symbols: list[tuple[str, str, str, int]] = []  # local name, module, imported name, level
        self.aliases: list[tuple[str, str, int]] = []  # local name, module, level

    def _define(self, node, kind: str) -> None:
        parent, prefix = self.scope[-1]
        qualname = f"{prefix}.{node.name}" if prefix else node.name
        identity = node_id(self.path, qualname)
        segment = ast.get_source_segment(self.text, node) or node.name
        self.definitions.append((identity, kind, qualname, node.lineno, node.end_lineno or node.lineno,
                                 _concepts(segment), _data(node), parent))
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


def _rust_graph(files) -> tuple[dict, set, int, int, list]:
    """Nodes and edges of the project's Rust files (see rust_graph.py), kept apart from Python's
    names so a Python call never links to a Rust function or the other way round."""
    from . import rust_graph as rg
    rust = [(path, raw, text) for path, raw, text in files if path.endswith(".rs")]
    read, skipped = {}, 0
    for path, _, text in rust:
        try:
            read[path] = (rg.read_file(path, text), text)
        except (ValueError, RecursionError, MemoryError, IndexError):
            skipped += 1
    by_module = {rg.module_path(path): path for path in read}
    nodes: dict[str, m.GraphNode] = {}
    edges: set[tuple[str, str, str, str, int]] = set()
    by_name: dict[str, list[str]] = {}
    by_qualname: dict[str, list[str]] = {}
    items_of: dict[str, dict[str, str]] = {}  # path -> qualname -> node id
    symbols: dict[str, dict[str, tuple[str, str]]] = {}  # path -> local name -> (file, qualname there)
    module_aliases: dict[str, dict[str, str]] = {}  # path -> local name -> module file
    external: dict[str, dict[str, str]] = {}  # path -> local name -> external crate

    def module_file(path: str, segments: list[str]) -> tuple[str | None, list[str]]:
        """The file a `use` path's module part names, and the rest of the path inside it."""
        crate, here = rg.module_path(path)
        if not segments:
            return None, []
        head, rest = segments[0], segments[1:]
        if head == "crate":
            base = ()
        elif head == "self":
            base = here
        elif head == "super":
            base, rest = here[:-1], rest
            while rest[:1] == ["super"]:
                base, rest = base[:-1], rest[1:]
        elif (crate, (*here, head)) in by_module:
            base, rest = here, segments
        elif (crate, (head,)) in by_module:
            base, rest = (), segments
        else:
            return None, segments  # an external crate
        module = base
        while rest and (crate, (*module, rest[0])) in by_module:
            module, rest = (*module, rest[0]), rest[1:]
        return by_module.get((crate, module)), rest

    for path, (result, text) in sorted(read.items()):
        lines = text.splitlines()
        file_id = node_id(path)
        nodes[file_id] = m.GraphNode(id=file_id, kind="file", path=path, name=path, line=1,
                                     end_line=max(1, len(lines)), concepts=_concepts(text), data=[])
        symbols[path], module_aliases[path], external[path] = {}, {}, {}
        for local, segments, name in result["uses"]:
            target, rest = module_file(path, segments + ([name] if name and name != "*" else []))
            if target is None:
                root = (segments or [name])[0]
                if root not in ("crate", "self", "super") and local != "*":
                    external[path][local] = root
                continue
            if target != path:
                edges.add((file_id, "imports", node_id(target), "extracted", 1))
            if name == "*" or not rest:
                if local != "*":
                    module_aliases[path][local] = target
                continue
            symbols[path][local] = (target, ".".join(rest))
        crate, here = rg.module_path(path)
        for name in result["modules"]:
            child = by_module.get((crate, (*here, name)))
            if child is not None:
                edges.add((file_id, "imports", node_id(child), "extracted", 1))
                module_aliases[path][name] = child
        items_of[path] = {}
        tokens = result["tokens"]
        for item in result["items"]:
            identity = node_id(path, item["qualname"])
            words = rg.item_words(tokens, item)
            crates = sorted({external[path][word] for word in words if word in external[path]})
            segment = "\n".join(lines[item["line"] - 1:item["end_line"]]) + ("\n" + " ".join(crates) if crates else "")
            kinds = set()
            for word in set(words):
                kinds |= _identifier_data(word)
            nodes[identity] = m.GraphNode(id=identity, kind=item["kind"], path=path, name=item["qualname"],
                                          line=item["line"], end_line=max(item["line"], item["end_line"]),
                                          concepts=_concepts(segment), data=[kind for kind in DATA if kind in kinds])
            items_of[path][item["qualname"]] = identity
            by_name.setdefault(item["qualname"].rsplit(".", 1)[-1], []).append(identity)
            by_qualname.setdefault(item["qualname"], []).append(identity)
        for item in result["items"]:
            identity = items_of[path][item["qualname"]]
            owner = item["qualname"].rsplit(".", 1)[0] if "." in item["qualname"] else ""
            edges.add((items_of[path].get(owner, file_id), "defines", identity, "extracted", item["line"]))

    def lookup(path: str, caller: str, qualifier: str | None, name: str) -> tuple[list[str], bool]:
        """(targets, guessed): Rust's lookup order, then a unique project name, else candidates."""
        own = items_of.get(path, {})
        if qualifier is None:
            scope = caller.rsplit(".", 1)[0] if "." in caller else ""
            for candidate in ([f"{scope}.{name}"] if scope else []) + [name]:
                if candidate in own:
                    return [own[candidate]], False
            if name in symbols.get(path, {}):
                target, qualname = symbols[path][name]
                found = items_of.get(target, {}).get(qualname)
                return ([found], False) if found else ([], False)
            if name in external.get(path, {}):
                return [], False
        elif qualifier in ("crate", "self", "super"):
            target, rest = module_file(path, [qualifier, name])
            found = items_of.get(target, {}).get(".".join(rest)) if target else None
            return ([found], False) if found else ([], False)
        elif qualifier == ".":
            # A method call: only its name is known, and only a method (Type.name) can answer it.
            methods = sorted({target for target in by_name.get(name, []) if "." in nodes[target].name})
            return (methods, False) if len(methods) == 1 else (methods[:MAX_AMBIGUOUS], True)
        else:
            if qualifier in module_aliases.get(path, {}):
                found = items_of.get(module_aliases[path][qualifier], {}).get(name)
                return ([found], False) if found else ([], False)
            if qualifier in external.get(path, {}):
                return [], False  # an external crate's type or function: no guess
            if f"{qualifier}.{name}" in own:
                return [own[f"{qualifier}.{name}"]], False
            if qualifier in symbols.get(path, {}):
                target, qualname = symbols[path][qualifier]
                found = items_of.get(target, {}).get(f"{qualname}.{name}")
                if found:
                    return [found], False
            matches = sorted(set(by_qualname.get(f"{qualifier}.{name}", [])))
            return (matches, False) if len(matches) == 1 else (matches[:MAX_AMBIGUOUS], True)
        targets = sorted(set(by_name.get(name, [])))  # a name defined twice (cfg, if/else) is one node
        return (targets, False) if len(targets) == 1 else (targets[:MAX_AMBIGUOUS], True)

    for path, (result, _) in sorted(read.items()):
        for caller, qualifier, name, line in result["calls"]:
            source = items_of[path].get(caller)
            if source is None:
                continue
            targets, guessed = lookup(path, caller, qualifier, name)
            for target in targets:
                if target != source:
                    edges.add((source, "calls", target, "ambiguous" if guessed else "extracted", line))
    return nodes, edges, len(read), skipped, rust


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
                                           end_line=max(1, len(text.splitlines())), concepts=_concepts(text), data=[])
        for identity, kind, qualname, line, end, concepts, data, parent in visitor.definitions:
            nodes[identity] = m.GraphNode(id=identity, kind=kind, path=path, name=qualname, line=line, end_line=end,
                                          concepts=concepts, data=data)
            edges.add((parent, "defines", identity, "extracted", line))
            by_name.setdefault(qualname.rsplit(".", 1)[-1], []).append(identity)
        pending_calls += [(path, *call) for call in visitor.calls]
        top_level[path] = {item[2]: item[0] for item in visitor.definitions if "." not in item[2]}
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
        targets = sorted(set(by_name.get(name, [])))  # a name defined twice (cfg, if/else) is one node
        if len(targets) == 1:
            edges.add((caller, "calls", targets[0], "extracted", line))
        else:
            for target in targets[:MAX_AMBIGUOUS]:
                edges.add((caller, "calls", target, "ambiguous", line))
    rust_nodes, rust_edges, rust_parsed, rust_skipped, rust = _rust_graph(files)
    nodes.update(rust_nodes)
    edges |= rust_edges
    parsed += rust_parsed
    skipped += rust_skipped
    digest = m.content_digest(json.dumps(sorted((path, m.content_digest(raw)) for path, raw, _ in [*python, *rust])).encode("utf-8"))
    ordered = sorted(edges, key=lambda edge: (edge[0], edge[1], edge[2], edge[4], edge[3]))
    unique: dict[tuple, tuple] = {}
    for edge in ordered:
        # One edge per (source, kind, target, line): an extracted reading wins over an ambiguous one.
        unique.setdefault((edge[0], edge[1], edge[2], edge[4]), edge)
    return m.ProjectGraph(
        schema_version=1, graph_version=1, files=len(python) + len(rust), parsed=parsed, skipped=skipped, digest=digest,
        nodes=[nodes[key] for key in sorted(nodes)],
        edges=[m.GraphEdge(source=s, kind=k, target=t, provenance=p, line=n) for s, k, t, p, n in unique.values()],
        notice=m.GRAPH_NOTICE)


def flows(graph: m.ProjectGraph, max_depth: int = MAX_FLOW_DEPTH) -> list[dict]:
    """Shortest call paths from a function that handles personal data to one that reaches an AI model,
    tracking, a third party or marketing. A flow through an ambiguous call is labelled ambiguous.
    Flows never start in test code.

    These are possible paths found by static parsing; they show where to look, never a finding.
    """
    nodes = {node.id: node for node in graph.nodes}
    calls: dict[str, list[tuple[str, str]]] = {}
    for edge in graph.edges:
        if edge.kind == "calls":
            calls.setdefault(edge.source, []).append((edge.target, edge.provenance))
    found = []
    for start in sorted(node.id for node in graph.nodes
                        if node.kind == "function" and node.data and not is_test_file(node.path)):
        previous: dict[str, tuple[str, str] | None] = {start: None}
        guesses = {start: 0}
        frontier = [start]
        for _ in range(max_depth + 1):
            following = []
            for current in frontier:
                sinks = [concept for concept in nodes[current].concepts if concept in SINKS]
                if sinks:
                    hops, cursor, provenance = [], current, "extracted"
                    while cursor is not None:
                        hops.append(cursor)
                        step = previous[cursor]
                        if step is not None and step[1] == "ambiguous":
                            provenance = "ambiguous"
                        cursor = step[0] if step else None
                    hops.reverse()
                    found.append({"data": nodes[start].data, "sinks": sinks, "provenance": provenance,
                                  "hops": [{"name": nodes[hop].name, "location": f"{nodes[hop].path}:{nodes[hop].line}",
                                            "end_line": nodes[hop].end_line} for hop in hops]})
                    continue  # the first sink on a route ends it; what it calls is the sink's own detail
                for target, provenance in sorted(calls.get(current, []), key=lambda item: (item[1] != "extracted", item)):
                    count = guesses[current] + (provenance == "ambiguous")
                    if target not in previous and count <= MAX_AMBIGUOUS_HOPS:
                        previous[target] = (current, provenance)
                        guesses[target] = count
                        following.append(target)
            frontier = following
    # Extracted routes first, then the shortest: the cap keeps the most reliable flows.
    found.sort(key=lambda flow: (flow["provenance"] != "extracted", len(flow["hops"]),
                                 flow["hops"][0]["location"], flow["hops"][-1]["location"]))
    return found[:MAX_FLOWS]


def covers(flow: dict, refs: set[str]) -> bool:
    """A flow is accounted for when a pinned `path:line` lies inside any of its functions."""
    for hop in flow["hops"]:
        path, _, start = hop["location"].rpartition(":")
        for ref in refs:
            ref_path, _, number = ref.rpartition(":")
            if ref_path == path and number.isdigit() and int(start) <= int(number) <= hop["end_line"]:
                return True
    return False


def describe_flow(flow: dict) -> str:
    """'special_category → ai: app/coach.py:5 plan_meals → app/llm.py:1 ask_model (extracted)'."""
    route = " → ".join(f"{hop['location']} {hop['name']}" for hop in flow["hops"])
    return f"{', '.join(flow['data'])} → {', '.join(flow['sinks'])}: {route} ({flow['provenance']})"


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
