"""A minimal MCP server over stdio (2.0 bolts 018 and 021): the citation guard and the read-only
review tools (article search, grounding, the PR screen, next steps) for other agents.

Newline-delimited JSON-RPC 2.0 (`initialize`, `tools/list`, `tools/call`, `ping`). Every tool
reads one project's declarations, files or latest completed run, and changes nothing. Tool output
is workflow evidence ending with the legal notice; an empty result is never a compliance verdict.
"""
from __future__ import annotations

import json
import sys

from . import __version__, articles, authoring, citations, grounding, nextstep, prcheck, revalidation
from .notice import LEGAL_NOTICE

PROTOCOL = "2025-06-18"
MAX_LINE = 2_000_000
TOOLS = [
    {"name": "cite_check",
     "description": "Check that every 'Article N' the text cites exists in the retained official text of the latest run, "
                    "and that every quotation appears in the cited article word for word.",
     "inputSchema": {"type": "object", "properties": {"text": {"type": "string", "description": "Text to check"}},
                     "required": ["text"], "additionalProperties": False}},
    {"name": "article_search",
     "description": "Search the articles of the retained official text for a statement (BM25 over text and titles).",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"},
                                                       "top": {"type": "integer", "minimum": 1, "maximum": 20}},
                     "required": ["query"], "additionalProperties": False}},
    {"name": "ground",
     "description": "Find code lines that may confirm assumed technical facts, with explained matches. Read-only: "
                    "pinning a line stays a person's step (eu-compliance-guard ground --apply).",
     "inputSchema": {"type": "object", "properties": {"top": {"type": "integer", "minimum": 1, "maximum": 20}},
                     "additionalProperties": False}},
    {"name": "pr_check",
     "description": "Screen a unified diff (git diff output) for changes touching personal data, tracking, AI and "
                    "other review concepts, and the declared facts and obligations they may reopen.",
     "inputSchema": {"type": "object", "properties": {"diff": {"type": "string", "description": "Unified diff text"}},
                     "required": ["diff"], "additionalProperties": False}},
    {"name": "next_steps",
     "description": "The next review steps of the latest run, ranked by how many open requirements each unblocks.",
     "inputSchema": {"type": "object", "properties": {"top": {"type": "integer", "minimum": 1, "maximum": 20}},
                     "additionalProperties": False}},
]
for _tool in TOOLS:
    _tool["annotations"] = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}


class ToolError(ValueError):
    pass


def _latest(declarations: str):
    from .view import catalogue, verify_run
    run = nextstep.latest_run(authoring.state_dir(declarations, create=False))
    if run is None:
        raise ToolError("No completed run for these declarations: run revalidate first.")
    contents: dict[str, bytes] = {}
    bundle = verify_run(run, contents)
    return bundle, catalogue(bundle, contents)


def _top(arguments: dict, default: int) -> int:
    top = arguments.get("top", default)
    if not isinstance(top, int) or isinstance(top, bool) or not 1 <= top <= 20:
        raise ToolError("'top' must be an integer from 1 to 20.")
    return top


def _text(arguments: dict, name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ToolError(f"'{name}' must be a non-empty string.")
    return value


def call(declarations: str, name: str, arguments: dict) -> tuple[str, dict | None]:
    if name == "cite_check":
        text = _text(arguments, "text")
        report = citations.check(text, _latest(declarations)[1])
        return citations.format_check(report), report
    if name == "article_search":
        query, top = _text(arguments, "query"), _top(arguments, 5)
        found = articles.suggest(query, _latest(declarations)[1], top)
        lines = [f"- {item['source']} {item['article']} ({item['title']}), score {item['score']}" for item in found]
        return "\n".join(lines or ["No retained article matches."]) + "\nCandidates to read, not a mapping decision.", \
            {"results": found}
    if name == "ground":
        report = grounding.ground(declarations, _top(arguments, 3))
        return grounding.format_ground(report), report
    if name == "pr_check":
        diff = _text(arguments, "diff")
        if len(diff.encode("utf-8")) > prcheck.MAX_DIFF_BYTES:
            raise ToolError("The diff is larger than pr-check accepts.")
        declared = revalidation.load_input(declarations)
        project_graph, prefix = prcheck.project_context(declarations)
        report = prcheck.pr_check(diff, declared, project_graph, prefix)
        return prcheck.format_text(report), report
    if name == "next_steps":
        steps = nextstep.next_steps(_latest(declarations)[0], _top(arguments, 3))
        return nextstep.format_steps(steps), {"steps": steps}
    raise ToolError(f"Unknown tool '{name}'.")


def _result(identity, result) -> dict:
    return {"jsonrpc": "2.0", "id": identity, "result": result}


def _error(identity, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": identity, "error": {"code": code, "message": message}}


def handle(declarations: str, message) -> dict | None:
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
        return _error(message.get("id") if isinstance(message, dict) else None, -32600, "Invalid request")
    identity, method = message.get("id"), message["method"]
    if "id" not in message:
        return None  # a notification (such as notifications/initialized) gets no response
    params = message.get("params") if isinstance(message.get("params"), dict) else {}
    if method == "initialize":
        requested = params.get("protocolVersion")
        return _result(identity, {"protocolVersion": requested if isinstance(requested, str) and requested else PROTOCOL,
                                  "capabilities": {"tools": {"listChanged": False}},
                                  "serverInfo": {"name": "eu-compliance-guard", "version": __version__},
                                  "instructions": "Read-only checks against the retained official EU text of the latest "
                                                  "run. " + LEGAL_NOTICE})
    if method == "ping":
        return _result(identity, {})
    if method == "tools/list":
        return _result(identity, {"tools": TOOLS})
    if method == "tools/call":
        name, arguments = params.get("name"), params.get("arguments") or {}
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return _error(identity, -32602, "Invalid params")
        try:
            text, structured = call(declarations, name, arguments)
        except ToolError as error:
            return _result(identity, {"content": [{"type": "text", "text": str(error)}], "isError": True})
        except Exception as error:
            # Never echo exception text, which can contain private input.
            code = getattr(error, "code", None)
            return _result(identity, {"content": [{"type": "text", "text": f"{name} failed: {code or 'internal error'}."}],
                                      "isError": True})
        result = {"content": [{"type": "text", "text": text + "\n" + LEGAL_NOTICE}]}
        if structured is not None:
            result["structuredContent"] = structured
        return _result(identity, result)
    return _error(identity, -32601, "Method not found")


def serve(declarations: str, stdin=None, stdout=None) -> int:
    stdin, stdout = stdin or sys.stdin, stdout or sys.stdout
    while True:
        line = stdin.readline(MAX_LINE + 1)
        if not line:
            return 0
        if len(line) > MAX_LINE:
            while line and not line.endswith("\n"):
                line = stdin.readline(MAX_LINE + 1)  # drop the rest of an oversized message
            response = _error(None, -32600, "Message too large")
        elif not line.strip():
            continue
        else:
            try:
                response = handle(declarations, json.loads(line))
            except ValueError:
                response = _error(None, -32700, "Parse error")
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()
