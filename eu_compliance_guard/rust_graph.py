"""Rust in the project graph (2.4): items, `use` imports and calls, read without a Rust toolchain.

A small tokenizer (comments, strings, raw strings, chars and lifetimes) and an item reader find
modules, functions, methods (`Type.method`), structs, enums and traits, `use` trees and call
expressions. Calls resolve like the Python side: this file's items, then `use` imports and
modules of the same crate, then a unique name in the project, else up to five ambiguous
candidates. Macros are not expanded and generics are skipped, so some calls are missed; every
path stays a possible path. Code under `#[cfg(test)]` or `#[test]` is test code and is left out.
Nothing is compiled or run.
"""
from __future__ import annotations

from pathlib import PurePosixPath

KEYWORDS = frozenset({"as", "async", "await", "break", "const", "continue", "crate", "dyn", "else", "enum", "extern",
                      "false", "fn", "for", "if", "impl", "in", "let", "loop", "match", "mod", "move", "mut", "pub", "ref",
                      "return", "self", "Self", "static", "struct", "super", "trait", "true", "type", "unsafe", "use",
                      "where", "while", "union", "yield"})
# Enum constructors of the standard library look like calls but never reach project code.
CONSTRUCTORS = frozenset({"Ok", "Err", "Some", "None", "Box", "Vec", "String", "Arc", "Rc"})
# Methods of the standard library's common traits and types. A call such as `.clone()` or
# `.into()` almost always reaches the standard library, even when a project type also implements
# the trait, so it is never linked to project code by name.
STD_METHODS = frozenset({
    "clone", "clone_from", "into", "from", "try_into", "try_from", "as_ref", "as_mut", "borrow", "borrow_mut", "deref",
    "to_string", "to_owned", "fmt", "eq", "ne", "cmp", "partial_cmp", "hash", "default", "drop", "next", "iter",
    "iter_mut", "into_iter", "map", "map_err", "and_then", "or_else", "unwrap", "unwrap_or", "unwrap_or_default",
    "unwrap_or_else", "expect", "ok", "err", "ok_or", "ok_or_else", "is_some", "is_none", "is_ok", "is_err", "as_str",
    "as_bytes", "as_deref", "len", "is_empty", "push", "push_str", "pop", "insert", "remove", "get", "get_mut", "contains",
    "contains_key", "extend", "collect", "filter", "filter_map", "find", "any", "all", "count", "sum", "fold", "for_each",
    "chain", "zip", "rev", "take", "skip", "join", "split", "trim", "starts_with", "ends_with", "parse", "lock", "read",
    "write", "await", "poll", "boxed", "to_vec", "copied", "cloned", "flatten", "first", "last", "entry", "or_insert",
    "or_default", "with_capacity", "capacity", "clear", "sort", "sort_by", "dedup", "retain", "replace", "take_while"})
MAX_TOKENS = 2_000_000
MAX_KEY = 40


def tokenize(text: str) -> list[tuple[str, str, int]]:
    """(kind, text, line) for identifiers, strings, numbers and punctuation; comments are dropped."""
    tokens, index, line, size = [], 0, 1, len(text)

    def push(kind: str, value: str, at_line: int):
        if len(tokens) >= MAX_TOKENS:
            raise ValueError("too many tokens")
        tokens.append((kind, value, at_line))

    while index < size:
        char = text[index]
        if char == "\n":
            line += 1
            index += 1
        elif char.isspace():
            index += 1
        elif text.startswith("//", index):
            end = text.find("\n", index)
            index = size if end == -1 else end
        elif text.startswith("/*", index):
            depth, index = 1, index + 2
            while index < size and depth:
                if text.startswith("/*", index):
                    depth, index = depth + 1, index + 2
                elif text.startswith("*/", index):
                    depth, index = depth - 1, index + 2
                else:
                    line += text[index] == "\n"
                    index += 1
        elif char in "rbc" and _raw_string_start(text, index):
            start_line, (value, index) = line, _raw_string(text, index)
            line += value.count("\n")
            push("str", value, start_line)
        elif char == '"' or (char in "bc" and text[index + 1:index + 2] == '"'):
            start_line = line
            index += 1 if char == '"' else 2
            chars = []
            while index < size and text[index] != '"':
                if text[index] == "\\" and index + 1 < size:
                    chars.append(text[index:index + 2])
                    index += 2
                    continue
                line += text[index] == "\n"
                chars.append(text[index])
                index += 1
            index += 1
            push("str", "".join(chars), start_line)
        elif char == "'":
            # A char literal ('a', '\n', '\u{1F600}') or a lifetime ('a, 'static).
            if text[index + 1:index + 2] == "\\":
                end = text.find("'", index + 3)  # past the escaped character, which may itself be a quote
                index = size if end == -1 else end + 1
                push("char", "", line)
            elif text[index + 2:index + 3] == "'":
                index += 3
                push("char", "", line)
            else:
                end = index + 1
                while end < size and (text[end].isalnum() or text[end] == "_"):
                    end += 1
                push("lifetime", text[index:end], line)
                index = max(end, index + 1)
        elif char.isalpha() or char == "_":
            end = index + 1
            while end < size and (text[end].isalnum() or text[end] == "_"):
                end += 1
            word = text[index:end]
            if word == "r" and text[end:end + 1] == "#" and end + 1 < size and (text[end + 1].isalpha() or text[end + 1] == "_"):
                start, end = end + 1, end + 2  # a raw identifier: r#type
                while end < size and (text[end].isalnum() or text[end] == "_"):
                    end += 1
                word = text[start:end]
            push("ident", word, line)
            index = end
        elif char.isdigit():
            end = index + 1
            while end < size and (text[end].isalnum() or text[end] == "_" or
                                  (text[end] == "." and text[end + 1:end + 2].isdigit())):
                end += 1
            push("num", text[index:end], line)
            index = end
        else:
            pair = text[index:index + 2]
            if pair in ("::", "->", "=>"):
                push("punct", pair, line)
                index += 2
            else:
                push("punct", char, line)
                index += 1
    return tokens


def _raw_string_start(text: str, index: int) -> bool:
    prefix = text[index:index + 2]
    if prefix in ("br", "cr"):
        rest = text[index + 2:index + 3]
    elif text[index] == "r":
        rest = text[index + 1:index + 2]
    else:
        return False
    return rest in ('"', "#") and (rest == '"' or _hashes_then_quote(text, text.index(rest, index)))


def _hashes_then_quote(text: str, index: int) -> bool:
    while index < len(text) and text[index] == "#":
        index += 1
    return text[index:index + 1] == '"'


def _raw_string(text: str, index: int) -> tuple[str, int]:
    index += 2 if text[index:index + 2] in ("br", "cr") else 1
    hashes = 0
    while text[index:index + 1] == "#":
        hashes, index = hashes + 1, index + 1
    index += 1  # the opening quote
    closing = '"' + "#" * hashes
    end = text.find(closing, index)
    if end == -1:
        return text[index:], len(text)
    return text[index:end], end + len(closing)


PAIRS = {"(": ")", "[": "]", "{": "}"}
MAX_HEADER = 4096  # tokens searched for an item's `{` or `;`; real headers are far shorter
MAX_NESTING = 64  # mod/impl/trait scopes; deeper ones keep the enclosing name, so names stay short


def _pairs(tokens) -> list[int]:
    """For each opening bracket, the index of the token that closes it (each kind nests on its own;
    an unclosed bracket closes at the last token). One pass, so reading stays linear."""
    last = len(tokens) - 1
    closing = [last] * len(tokens)
    stacks: dict[str, list[int]] = {opening: [] for opening in PAIRS}
    closers = {value: opening for opening, value in PAIRS.items()}
    for index, (kind, value, _) in enumerate(tokens):
        if kind != "punct":
            continue
        if value in stacks:
            stacks[value].append(index)
        elif value in closers and stacks[closers[value]]:
            closing[stacks[closers[value]].pop()] = index
    return closing


def _ahead(tokens, index: int, values: tuple[str, ...]) -> int:
    """The next token at or after index whose value is one of `values`, within MAX_HEADER tokens."""
    stop = min(len(tokens), index + MAX_HEADER)
    return next((at for at in range(index, stop) if tokens[at][1] in values), stop - 1 if stop else 0)


MAX_GENERICS = 256  # tokens; real generic arguments are far shorter, and a cap keeps reading linear


def _skip_generics(tokens, index: int) -> int:
    """Past a `<…>` that starts at index (angle brackets nest; `->` and `=>` are single tokens).
    A `<` that does not close within MAX_GENERICS tokens is not generics."""
    depth = 0
    start = index
    while index < len(tokens) and index - start <= MAX_GENERICS:
        kind, value, _ = tokens[index]
        if kind == "punct" and value == "<":
            depth += 1
        elif kind == "punct" and value == ">":
            depth -= 1
            if depth == 0:
                return index + 1
        elif kind == "punct" and value in ("{", ";") and depth:
            return index  # not generics after all
        index += 1
    return start + 1 if index - start > MAX_GENERICS else index


def _use_tree(tokens, index: int, prefix: list[str], found: list[tuple[str, list[str], str]]) -> int:
    """Read one `use` tree from index; append (local name, module path, imported name)."""
    path = list(prefix)
    while index < len(tokens):
        kind, value, _ = tokens[index]
        if kind == "ident" and value != "as":
            path.append(value)
            index += 1
        elif value == "::":
            index += 1
        elif value == "{":
            index += 1
            while index < len(tokens) and tokens[index][1] != "}":
                start = index
                index = _use_tree(tokens, index, path, found)
                if index < len(tokens) and tokens[index][1] == ",":
                    index += 1
                if index == start:
                    return index  # malformed input: give up on the group rather than loop
            return index + 1
        elif value == "*":
            found.append(("*", path, "*"))
            return index + 1
        else:
            break
    if tokens[index][1] == "as" if index < len(tokens) else False:
        local = tokens[index + 1][1] if index + 1 < len(tokens) else ""
        index += 2
    else:
        local = path[-1] if path else ""
    if path:
        if path[-1] == "self":
            path = path[:-1]
            local = local if local != "self" else (path[-1] if path else "")
            found.append((local, path, ""))
        else:
            found.append((local, path[:-1], path[-1]))
    return index


def read_file(path: str, text: str) -> dict:
    """Items, calls, uses and module declarations of one Rust file."""
    tokens = tokenize(text)
    pairs = _pairs(tokens)

    def _matching(start: int) -> int:
        return pairs[start] if 0 <= start < len(tokens) and tokens[start][1] in PAIRS else len(tokens) - 1

    items: list[dict] = []  # qualname, kind, line, end_line, start, stop (token range)
    calls: list[tuple[str, str | None, str, int]] = []  # caller qualname ("" for the file), qualifier, name, line
    uses: list[tuple[str, list[str], str]] = []
    modules: list[str] = []  # `mod name;` declarations
    scopes: list[tuple[str, int, str | None]] = []  # (qualname prefix, closing token index, nearest impl type)
    functions: list[tuple[str, int]] = []  # enclosing functions: (qualname, closing token index)
    test_next = False
    index = 0
    while index < len(tokens):
        while scopes and index > scopes[-1][1]:
            scopes.pop()
        while functions and index > functions[-1][1]:
            functions.pop()
        kind, value, line = tokens[index]
        prefix = scopes[-1][0] if scopes else ""
        impl_type = scopes[-1][2] if scopes else None
        if kind == "punct" and value == "#" and index + 1 < len(tokens) and tokens[index + 1][1] in ("[", "!"):
            opening = index + 1 if tokens[index + 1][1] == "[" else index + 2
            close = _matching(opening)
            # `feature = "test"` names a feature and `not(test)` gates production code: neither is test code.
            words = [token[1] for token in tokens[opening + 1:close] if token[0] != "str"]
            head = words[:words.index("(")] if "(" in words else words  # test, tokio::test, cfg
            negated = any(words[at:at + 3] == ["not", "(", "test"] for at in range(len(words)))
            if head[-1:] == ["test"] or (head == ["cfg"] and "test" in words and not negated):
                test_next = True
            index = close + 1
            continue
        if kind != "ident":
            index += 1
            continue
        following = tokens[index + 1] if index + 1 < len(tokens) else ("", "", line)
        if value == "macro_rules" and following[1] == "!":
            index = _matching(_ahead(tokens, index, ("{", "(", "["))) + 1
            continue
        if value == "pub" and following[1] == "(":
            index = _matching(index + 1) + 1  # pub(crate), pub(in path): a visibility, which names no code
            continue
        if value == "use" and not functions:
            index = _use_tree(tokens, index + 1, [], [] if test_next else uses)
            test_next = False  # a test-only import ends here; the next item is production code
            continue
        if value in ("mod", "fn", "struct", "enum", "union", "trait", "impl") and (
                value == "impl" or following[0] == "ident"):
            if test_next:
                # Skip the whole test item.
                test_next = False
                end = _ahead(tokens, index, ("{", ";"))
                index = (_matching(end) if tokens[end][1] == "{" else end) + 1
                continue
            if value == "impl":
                end = index + 1
                if end < len(tokens) and tokens[end][1] == "<":
                    end = _skip_generics(tokens, end)
                header = []
                while end < len(tokens) and tokens[end][1] not in ("{", ";") and end - index < MAX_HEADER:
                    header.append(tokens[end])
                    end += 1
                words = [token[1] for token in header]
                if "where" in words:
                    header = header[:words.index("where")]
                    words = words[:words.index("where")]
                if "for" in words:
                    header = header[words.index("for") + 1:]
                type_name = None
                depth = 0
                for token in header:
                    if token[1] == "<":
                        depth += 1
                    elif token[1] == ">":
                        depth -= 1
                    elif depth == 0 and token[0] == "ident" and token[1] not in KEYWORDS:
                        type_name = token[1]
                if end < len(tokens) and tokens[end][1] == "{" and len(scopes) < MAX_NESTING:
                    close = _matching(end)
                    scopes.append((f"{prefix}.{type_name}" if prefix and type_name else type_name or prefix, close,
                                   type_name or impl_type))
                index = end + 1
                continue
            name = following[1]
            qualname = f"{prefix}.{name}" if prefix else name
            end = index + 2
            depth = 0
            while end < len(tokens) and end - index < MAX_HEADER:
                token = tokens[end][1]
                if token in ("(", "[", "<"):
                    depth += 1
                elif token in (")", "]", ">"):
                    depth -= 1
                elif depth <= 0 and token in ("{", ";"):
                    break
                end += 1
            if value == "mod":
                if end < len(tokens) and tokens[end][1] == "{":
                    if len(scopes) < MAX_NESTING:
                        scopes.append((qualname, _matching(end), impl_type))
                else:
                    modules.append(name)
                index = end + 1
                continue
            close = _matching(end) if end < len(tokens) and tokens[end][1] == "{" else min(end, len(tokens) - 1)
            items.append({"qualname": qualname, "kind": "function" if value == "fn" else "class", "line": line,
                          "end_line": tokens[min(close, len(tokens) - 1)][2], "start": index, "stop": close})
            if value == "fn" and tokens[min(end, len(tokens) - 1)][1] == "{":
                functions.append((qualname, close))
                index = end + 1
                continue
            if value == "trait" and tokens[min(end, len(tokens) - 1)][1] == "{" and len(scopes) < MAX_NESTING:
                scopes.append((qualname, close, name))  # a trait's methods take the trait as their type
                index = end + 1
                continue
            index = close + 1
            continue
        test_next = False if value not in ("pub", "async", "unsafe", "const", "extern") else test_next
        # A call: name(…), path::name(…), name::<T>(…), or .method(…); never a macro or a keyword.
        if functions and value not in KEYWORDS and value not in CONSTRUCTORS:
            after = index + 1
            if after + 1 < len(tokens) and tokens[after][1] == "::" and tokens[after + 1][1] == "<":
                after = _skip_generics(tokens, after + 1)
            if after < len(tokens) and tokens[after][1] == "(":
                previous = tokens[index - 1][1] if index else ""
                qualifier = None
                if previous == "::" and index >= 2 and tokens[index - 2][0] == "ident":
                    qualifier = tokens[index - 2][1]
                    if qualifier == "Self":
                        qualifier = impl_type
                elif previous == ".":
                    qualifier = "."
                if not (qualifier == "." and value in STD_METHODS):
                    calls.append((functions[-1][0], qualifier, value, line))
        index += 1
    return {"items": items, "calls": calls, "uses": uses, "modules": modules, "tokens": tokens}


def item_words(tokens, item: dict) -> list[str]:
    """Identifiers and short string keys within an item (for the data tags)."""
    words = []
    for kind, value, _ in tokens[item["start"]:item["stop"] + 1]:
        if kind == "ident" or (kind == "str" and value and len(value) <= MAX_KEY and not any(c.isspace() for c in value)):
            words.append(value)
    return words


def module_path(path: str) -> tuple[str, tuple[str, ...]]:
    """(crate directory, module path) of a file: src/lib.rs and src/main.rs are the crate root,
    src/a.rs and src/a/mod.rs the module a. A file outside any src folder is its own root."""
    parts = PurePosixPath(path).parts
    if "src" in parts:
        at = len(parts) - 1 - parts[::-1].index("src")
        crate, inner = "/".join(parts[:at]), list(parts[at + 1:])
    else:
        crate, inner = path, [parts[-1]]
    inner[-1] = inner[-1][:-3] if inner[-1].endswith(".rs") else inner[-1]
    if inner[-1] == "mod" or (len(inner) == 1 and inner[0] in ("lib", "main")) or crate == path:
        inner = inner[:-1]
    if inner[:1] == ["bin"]:
        return f"{crate}/src/bin/{inner[1] if len(inner) > 1 else ''}", ()
    return crate, tuple(inner)
