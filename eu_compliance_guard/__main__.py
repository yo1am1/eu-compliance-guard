"""Read-only requirements-to-law revalidation; offline unless --fetch-official is given."""

import argparse
import sys

_ERROR_CODES = {
    "invalid-input", "unsafe-path", "capacity-exceeded", "io-failed",
    "output-exists", "privacy-unavailable", "budget-exceeded", "invalid-output", "retrieval-failed",
    "incomplete-run", "corrupt-run",
    "wrong-project", "invalid-revision", "not-observable", "bad-location", "unrelated-line", "no-run",
    "unknown-id", "unreviewed-decision", "bad-principal", "signing-failed", "pack-conflict", "unsigned-pack",
    "bad-signature",
}
_DEFAULT_INPUT = ".eu-compliance-guard/declarations.json"


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # argparse's default includes untrusted argument values in diagnostics.
        self.exit(2, "eu-compliance-guard: invalid-arguments: use --help for supported arguments\n")

    def print_help(self, file=None) -> None:
        # argparse drops a failed write; help that cannot be written is io-failed like any other output.
        if file is not None:
            return super().print_help(file)
        _emit(self.format_help(), end="")


class _OutputFailed(Exception):
    """Standard output could not take the result (closed pipe, full disk or a closed stream)."""


def _emit(text: str, end: str = "\n") -> None:
    """Print a result; a failed write becomes _OutputFailed, never a traceback."""
    if sys.stdout is None:
        raise _OutputFailed
    try:
        print(text, end=end)
    except (OSError, ValueError) as error:
        raise _OutputFailed from error


def _emit_text(text: str) -> None:
    """A human-readable result, always followed by the legal notice."""
    from .notice import LEGAL_NOTICE
    _emit(text)
    _emit(LEGAL_NOTICE)


def _flush() -> None:
    try:
        if sys.stdout is not None:
            sys.stdout.flush()
    except (OSError, ValueError) as error:
        raise _OutputFailed from error


def main(argv: list[str] | None = None) -> int:
    """Run one command; exit 0 ok, 2 handled error (also output that cannot be written), 130 interrupt."""
    for stream in (sys.stdout, sys.stderr):
        # Text the console cannot encode (owners, statements, paths) is escaped, so the
        # console's encoding can never change an outcome.
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, OSError, ValueError):
            pass
    try:
        try:
            code = _command(argv)
        finally:
            # Results are buffered; a closed pipe or full disk shows here, not at interpreter exit.
            _flush()
    except KeyboardInterrupt:
        return 130
    except _OutputFailed:
        _discard_stdout()
        try:
            print("eu-compliance-guard: io-failed: output failed", file=sys.stderr)
        except (OSError, ValueError, AttributeError):
            pass
        return 2
    return code


def _discard_stdout() -> None:
    """Point standard output at the null device, so the exit flush cannot fail again (Python's SIGPIPE advice)."""
    import os
    try:
        descriptor = sys.stdout.fileno()
    except (AttributeError, OSError, ValueError):
        return
    null = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(null, descriptor)
    finally:
        os.close(null)


def _command(argv: list[str] | None) -> int:
    from . import __version__
    parser = _Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--version", action="version", version=f"eu-compliance-guard {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    revalidate = commands.add_parser("revalidate", help="Create a private revalidation report", allow_abbrev=False)
    revalidate.add_argument("--input", required=True, help="Explicit declaration JSON file")
    revalidate.add_argument("--output", required=True, help="New run directory under an existing private parent")
    revalidate.add_argument("--previous", help="Explicit completed predecessor run directory; never modified")
    network = revalidate.add_mutually_exclusive_group()
    network.add_argument("--offline", action="store_true", help="Use selected local files only (also the default)")
    network.add_argument("--fetch-official", action="store_true",
                         help="Also GET each declared source target from the fixed official-host registry")
    init = commands.add_parser("init", help="Write a starter declarations file (never overwrites)", allow_abbrev=False)
    init.add_argument("--project-id", required=True, help="Stable project identifier")
    init.add_argument("--path", default=".eu-compliance-guard/declarations.json", help="Declarations file to create")
    init.add_argument("--assessment-date", help="ISO date the assessment is for (default: today)")
    init.add_argument("--jurisdiction", action="append", help="Declared jurisdiction; repeat for several (default: EU)")
    init.add_argument("--synthetic", action="store_true", help="Mark the declarations as a fictional example")
    check = commands.add_parser("check", help="Validate declarations and selected files with located diagnostics",
                                allow_abbrev=False)
    check.add_argument("--input", default=".eu-compliance-guard/declarations.json", help="Declarations file to check")
    check.add_argument("--previous", help="Completed predecessor run; also check that changed records have new revisions")
    check.add_argument("--json", action="store_true", help="Print the result as JSON")
    state = commands.add_parser("state-dir", help="Print (and create) the private run directory for a project",
                                allow_abbrev=False)
    state.add_argument("--input", default=".eu-compliance-guard/declarations.json", help="Declarations file naming the project")
    lock = commands.add_parser("lock", help="Record the law a run's reviews read: versions and article digests",
                               allow_abbrev=False)
    lock.add_argument("--input", default=".eu-compliance-guard/declarations.json", help="Declarations file")
    lock.add_argument("--run", help="Completed run directory (default: the newest run in this project's state-dir)")
    lock.add_argument("--output", help="Lockfile (default: eu-law.lock beside the declarations)")
    impact = commands.add_parser("impact", help="List the articles changed since the lock and the decisions citing them",
                                 allow_abbrev=False)
    impact.add_argument("--input", default=".eu-compliance-guard/declarations.json", help="Declarations file")
    impact.add_argument("--run", help="Newer completed run (default: the newest run in this project's state-dir)")
    impact.add_argument("--lock", help="Lockfile (default: eu-law.lock beside the declarations)")
    impact.add_argument("--json", action="store_true", help="Print the result as JSON")
    impact.add_argument("--strict", action="store_true", help="Exit 1 when a declared obligation cites a changed article")
    sign = commands.add_parser("sign", help="Sign a reviewed decision with your SSH key, against the locked law and evidence",
                               allow_abbrev=False)
    sign.add_argument("--decision", required=True, help="Applicability decision ID")
    sign.add_argument("--input", default=".eu-compliance-guard/declarations.json", help="Declarations file")
    sign.add_argument("--key", required=True, help="SSH private key (or its .pub with an agent), as for git signing")
    sign.add_argument("--principal", required=True, help="Signer identity as written in the allowed-signers file")
    sign.add_argument("--lock", help="Lockfile (default: eu-law.lock beside the declarations, if present)")
    verify = commands.add_parser("verify", help="Verify signed decisions and say which changed since they were signed",
                                 allow_abbrev=False)
    verify.add_argument("--input", default=".eu-compliance-guard/declarations.json", help="Declarations file")
    verify.add_argument("--allowed-signers", required=True, help="ssh-keygen allowed-signers file")
    verify.add_argument("--lock", help="Lockfile (default: eu-law.lock beside the declarations, if present)")
    verify.add_argument("--json", action="store_true", help="Print the result as JSON")
    when = commands.add_parser("timeline", help="List application, entry-into-force and transposition dates quoted from the retained text",
                               allow_abbrev=False)
    when.add_argument("--input", default=".eu-compliance-guard/declarations.json", help="Declarations file")
    when.add_argument("--run", help="Completed run directory (default: the newest run in this project's state-dir)")
    when.add_argument("--json", action="store_true", help="Print the result as JSON")
    cite = commands.add_parser("cite-check", help="Check article citations and quotations against the retained official text",
                               allow_abbrev=False)
    cite.add_argument("file", help="Text file to check, or - for standard input")
    cite.add_argument("--input", default=".eu-compliance-guard/declarations.json", help="Declarations file")
    cite.add_argument("--run", help="Completed run directory (default: the newest run in this project's state-dir)")
    cite.add_argument("--json", action="store_true", help="Print the result as JSON")
    mcp = commands.add_parser("mcp", help="Serve cite_check, article_search and next_steps as MCP tools over stdio",
                              allow_abbrev=False)
    mcp.add_argument("--input", default=".eu-compliance-guard/declarations.json", help="Declarations file")
    pack = commands.add_parser("pack", help="Build, sign, verify or import a reusable obligation pack (never a decision)",
                               allow_abbrev=False)
    packs = pack.add_subparsers(dest="pack_command", required=True, parser_class=_Parser)
    build = packs.add_parser("build", help="Draft a pack from this project's obligations", allow_abbrev=False)
    build.add_argument("--input", default=".eu-compliance-guard/declarations.json", help="Declarations file")
    build.add_argument("--id", required=True, help="Pack ID")
    build.add_argument("--title", required=True, help="Pack title")
    build.add_argument("--obligation", action="append", help="Obligation ID to include (repeatable; default: all)")
    build.add_argument("--revision", type=int, default=0, help="Pack revision (default 0)")
    build.add_argument("--status", choices=["draft", "reviewed"], default="draft", help="Declared review status")
    build.add_argument("--lock", help="Lockfile (default: eu-law.lock beside the declarations, if present)")
    build.add_argument("--output", required=True, help="Pack file to write")
    pack_sign = packs.add_parser("sign", help="Sign a pack file with your SSH key, as <pack>.sig", allow_abbrev=False)
    pack_sign.add_argument("pack", help="Pack file")
    pack_sign.add_argument("--key", required=True, help="SSH private key (or its .pub with an agent)")
    pack_sign.add_argument("--principal", required=True, help="Signer identity as written in the allowed-signers file")
    pack_verify = packs.add_parser("verify", help="Verify a pack's signature", allow_abbrev=False)
    pack_verify.add_argument("pack", help="Pack file")
    pack_verify.add_argument("--allowed-signers", required=True, help="ssh-keygen allowed-signers file")
    pack_verify.add_argument("--json", action="store_true", help="Print the result as JSON")
    pack_starters = packs.add_parser("starters", help="List the draft starter packs shipped with the tool", allow_abbrev=False)
    pack_starters.add_argument("--json", action="store_true", help="Print the result as JSON")
    pack_import = packs.add_parser("import", help="Add a pack's targets and obligations to the declarations",
                                   allow_abbrev=False)
    pack_import.add_argument("pack", help="Pack file")
    pack_import.add_argument("--input", default=".eu-compliance-guard/declarations.json", help="Declarations file")
    trust = pack_import.add_mutually_exclusive_group(required=True)
    trust.add_argument("--allowed-signers", help="Import only if the pack's signature verifies against this file")
    trust.add_argument("--unsigned", action="store_true", help="Import a pack without checking any signature")
    pack_import.add_argument("--json", action="store_true", help="Print the result as JSON")
    imported = commands.add_parser("import-evidence", help="Keep a WEC or SARIF result as untrusted evidence, summarised by concept",
                                   allow_abbrev=False)
    imported.add_argument("file", help="EDPS Website Evidence Collector inspection.json or a SARIF log")
    imported.add_argument("--kind", required=True, choices=["wec", "sarif"], help="Format of the file")
    imported.add_argument("--input", default=".eu-compliance-guard/declarations.json", help="Declarations file")
    imported.add_argument("--json", action="store_true", help="Print the summary as JSON")
    accept = commands.add_parser("accept", help="Map a requirement to a candidate obligation citing an article (no decision)",
                                 allow_abbrev=False)
    accept.add_argument("mapping", metavar="REQ=TARGET:ARTICLE", help="For example req-delete=target-gdpr:Article 17")
    accept.add_argument("--input", default=".eu-compliance-guard/declarations.json", help="Declarations file")
    accept.add_argument("--json", action="store_true", help="Print the result as JSON")
    graph = commands.add_parser("graph", help="Map the project's Python files, functions, imports and calls (static, read-only)",
                                allow_abbrev=False)
    graph.add_argument("--input", default=".eu-compliance-guard/declarations.json",
                       help="Declarations file; its files root is the project that is mapped")
    graph.add_argument("--json", action="store_true", help="Print the whole graph as JSON")
    graph.add_argument("--view", action="store_true",
                       help="Write a static graph page to <state-dir>/views/graph.html and print its path")
    graph.add_argument("--open", action="store_true", help="With --view, open the page in the default browser")
    ground = commands.add_parser("ground", help="Find code evidence for assumed facts; --apply pins one as observed",
                                 allow_abbrev=False)
    ground.add_argument("--input", default=".eu-compliance-guard/declarations.json", help="Declarations file")
    ground.add_argument("--top", type=int, default=3, choices=range(1, 11), metavar="1-10", help="Candidates per fact")
    ground.add_argument("--json", action="store_true", help="Print the result as JSON")
    ground.add_argument("--apply", action="append", metavar="FACT=PATH:LINE",
                        help="Mark a technical fact observed, pinned to this file line; repeat for several "
                             "(all are checked before any is written)")
    view = commands.add_parser("view", help="Write and optionally open a static HTML view of a verified run", allow_abbrev=False)
    view.add_argument("--run", required=True, help="Existing run directory with a valid completion marker")
    view.add_argument("--open", action="store_true", help="Open the view in the default browser")
    view.add_argument("--dashboard", action="store_true",
                      help="Print (and with --open, open) the one-page review-progress dashboard instead of the full report")
    step = commands.add_parser("next", help="Rank the next review steps of a run by the open requirements they unblock",
                               allow_abbrev=False)
    step.add_argument("--run", help="Completed run directory (default: the newest run in this project's state-dir)")
    step.add_argument("--input", default=".eu-compliance-guard/declarations.json", help="Declarations file naming the project")
    step.add_argument("--top", type=int, default=3, choices=range(1, 11), metavar="1-10", help="Steps to show")
    step.add_argument("--json", action="store_true", help="Print the result as JSON")
    score = commands.add_parser("score", help="Show the review progress of a run: separate meters, points out of 10, "
                                               "never a compliance score", allow_abbrev=False)
    score.add_argument("--run", help="Completed run directory (default: the newest run in this project's state-dir)")
    score.add_argument("--input", default=".eu-compliance-guard/declarations.json", help="Declarations file naming the project")
    score.add_argument("--against", help="Completed run to compare with; deltas only when it is the run's recorded parent")
    score.add_argument("--top", type=int, default=3, choices=range(1, 11), metavar="1-10",
                       help="Next steps to include in --json")
    score.add_argument("--json", action="store_true", help="Print the result as JSON")
    pr = commands.add_parser("pr-check", help="Screen a unified diff for EU legal touchpoints (for pull requests and CI)",
                             allow_abbrev=False)
    pr.add_argument("--diff", default="-", help="Unified diff file, or - for standard input (default)")
    pr.add_argument("--input", help="Declarations file; must exist when given "
                                    "(default: .eu-compliance-guard/declarations.json, if present)")
    output = pr.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="Print the result as JSON")
    output.add_argument("--markdown", action="store_true", help="Print a pull-request comment")
    pr.add_argument("--strict", action="store_true", help="Exit 1 when any item needs attention")
    arguments = sys.argv[1:] if argv is None else argv
    args = parser.parse_args(arguments)
    if args.command == "view":
        return _view(args.run, args.open, args.dashboard)
    if args.command == "next":
        return _next(args)
    if args.command == "score":
        return _score(args)
    if args.command == "pr-check":
        return _pr_check(args)
    if args.command == "init":
        return _init(args)
    if args.command == "ground":
        return _ground(args)
    if args.command == "graph":
        return _graph(args)
    if args.command == "accept":
        return _accept(args)
    if args.command in ("lock", "impact"):
        return _lawlock(args)
    if args.command in ("sign", "verify"):
        return _signing(args)
    if args.command == "cite-check":
        return _cite_check(args)
    if args.command == "timeline":
        return _timeline(args)
    if args.command == "import-evidence":
        return _import(args)
    if args.command == "pack":
        return _pack(args)
    if args.command == "mcp":
        from .mcp_server import serve
        try:
            return serve(args.input)
        except KeyboardInterrupt:
            return 130
    if args.command == "state-dir":
        try:
            from .authoring import state_dir
            path = state_dir(args.input)
        except Exception as error:
            code = getattr(error, "code", None)
            print(f"eu-compliance-guard: {code if code in _ERROR_CODES else 'io-failed'}: state-dir failed", file=sys.stderr)
            return 2
        _emit(str(path))
        return 0
    if args.command == "check":
        return _check(args.input, args.json, args.previous)
    try:
        from .revalidation import run
        options = {}
        if args.fetch_official:
            options["fetch_official"] = True
        if args.previous is not None:
            options["previous"] = args.previous
        bundle = run(args.input, args.output, **options)
    except KeyboardInterrupt:
        print("eu-compliance-guard: interrupted: report assembly interrupted", file=sys.stderr)
        return 130
    except Exception as error:
        # Never echo exception text or unrecognised codes containing private input.
        code = getattr(error, "code", None)
        if not isinstance(code, str) or code not in _ERROR_CODES:
            code = "revalidation-failed"
        print(f"eu-compliance-guard: {code}: revalidation failed", file=sys.stderr)
        return 2
    _emit(f"Run {bundle.run.id}: processing state {bundle.run.state}; report.md and bundle.json retained.")
    _emit_text("Processing state is not a compliance verdict.")
    return 0


def _init(args) -> int:
    try:
        from .authoring import init
        path = init(args.path, args.project_id, assessment_date=args.assessment_date,
                    jurisdictions=args.jurisdiction, synthetic=args.synthetic)
    except Exception as error:
        code = getattr(error, "code", None)
        print(f"eu-compliance-guard: {code if code in _ERROR_CODES else 'invalid-input'}: init failed", file=sys.stderr)
        return 2
    _emit(str(path))
    _emit_text("Starter declarations written. Add requirements, facts, source targets and obligations, then run check.")
    return 0


def _check(path: str, as_json: bool, previous: str | None = None) -> int:
    import json
    from .authoring import check, format_check
    try:
        report = check(path, previous)
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        code = getattr(error, "code", None)
        print(f"eu-compliance-guard: {code if code in _ERROR_CODES else 'check-failed'}: check failed", file=sys.stderr)
        return 2
    (_emit(json.dumps(report, indent=2)) if as_json else _emit_text(format_check(report)))
    return 0 if report["valid"] else 2


def _lawlock(args) -> int:
    import json
    from pathlib import Path
    from . import authoring, lawlock, nextstep
    from .revalidation import load_input
    try:
        run = args.run
        if run is None:
            found = nextstep.latest_run(authoring.state_dir(args.input, create=False))
            if found is None:
                raise nextstep.NoRun("no-run")
            run = str(found)
        default = Path(args.input).parent / lawlock.LOCK_NAME
        built = lawlock.build(run)
        if args.command == "lock":
            path = lawlock.write(built, args.output or default)
        else:
            report = lawlock.impact(lawlock.read(args.lock or default), built, load_input(args.input))
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        code = getattr(error, "code", None)
        print(f"eu-compliance-guard: {code if code in _ERROR_CODES else args.command + '-failed'}: {args.command} failed",
              file=sys.stderr)
        return 2
    if args.command == "lock":
        _emit_text(f"{path}: {len(built.entries)} act(s), "
                   f"{sum(len(item.articles) for item in built.entries)} provision(s) locked from run {built.run_id}.")
        return 0
    (_emit(json.dumps(report, indent=2)) if args.json else _emit_text(lawlock.format_impact(report)))
    return 1 if args.strict and report["obligations"] else 0


def _signing(args) -> int:
    import json
    from . import signing
    try:
        if args.command == "sign":
            path = signing.sign(args.input, args.decision, args.key, args.principal, args.lock)
        else:
            results = signing.verify(args.input, args.allowed_signers, args.lock)
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        code = getattr(error, "code", None)
        print(f"eu-compliance-guard: {code if code in _ERROR_CODES else args.command + '-failed'}: {args.command} failed",
              file=sys.stderr)
        return 2
    if args.command == "sign":
        from pathlib import Path
        from . import lawlock
        unpinned = not (args.lock or (Path(args.input).parent / lawlock.LOCK_NAME).exists())
        _emit_text(f"{path}: decision {args.decision} signed by {args.principal}."
                   + (" No eu-law.lock was found, so the signature pins no article text: run lock first and sign "
                      "again to bind it to the law." if unpinned else ""))
        return 0
    (_emit(json.dumps(results, indent=2)) if args.json else _emit_text(signing.format_verify(results)))
    # A missing signature is listed but is not a failure: signing is optional.
    return 0 if all(item["signature"] in ("valid", "missing") and not item["changed"] for item in results) else 1


def _timeline(args) -> int:
    import json
    from . import authoring, nextstep, timeline
    from .view import catalogue, verify_run
    try:
        run = args.run
        if run is None:
            found = nextstep.latest_run(authoring.state_dir(args.input, create=False))
            if found is None:
                raise nextstep.NoRun("no-run")
            run = str(found)
        contents: dict[str, bytes] = {}
        bundle = verify_run(run, contents)
        acts = catalogue(bundle, contents)
        assessment = bundle.declarations.scope.assessment_date
        entries = timeline.timeline(acts, assessment)
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        code = getattr(error, "code", None)
        print(f"eu-compliance-guard: {code if code in _ERROR_CODES else 'timeline-failed'}: timeline failed", file=sys.stderr)
        return 2
    (_emit(json.dumps({"assessment_date": assessment, "entries": entries}, indent=2)) if args.json
     else _emit_text(timeline.format_timeline(entries, assessment, sorted(acts))))
    return 0


def _cite_check(args) -> int:
    import json
    from . import authoring, citations, nextstep
    from .view import catalogue, verify_run
    try:
        if args.file == "-":
            text = sys.stdin.read(citations.MAX_TEXT)
        else:
            with open(args.file, encoding="utf-8") as handle:
                text = handle.read(citations.MAX_TEXT)
        run = args.run
        if run is None:
            found = nextstep.latest_run(authoring.state_dir(args.input, create=False))
            if found is None:
                raise nextstep.NoRun("no-run")
            run = str(found)
        contents: dict[str, bytes] = {}
        bundle = verify_run(run, contents)
        report = citations.check(text, catalogue(bundle, contents), citations.act_names(bundle.declarations.source_targets))
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        code = getattr(error, "code", None)
        print(f"eu-compliance-guard: {code if code in _ERROR_CODES else 'cite-check-failed'}: cite-check failed",
              file=sys.stderr)
        return 2
    (_emit(json.dumps(report, indent=2)) if args.json else _emit_text(citations.format_check(report)))
    return 0 if report["ok"] else 1


def _pack(args) -> int:
    import json
    from . import packs
    name = "pack " + args.pack_command
    try:
        if args.pack_command == "build":
            built = packs.build(args.input, args.id, args.title, args.obligation, args.revision, args.lock, args.status)
            path = packs.write(built, args.output)
            text = (f"{path}: pack {built.id} revision {built.revision} ({built.status}), {len(built.obligations)} "
                    f"obligation(s), {len(built.source_targets)} source target(s). Sign it with pack sign after review.")
            result = None
        elif args.pack_command == "sign":
            path = packs.sign(args.pack, args.key, args.principal)
            text, result = f"{path}: pack signed by {args.principal}.", None
        elif args.pack_command == "starters":
            result = packs.starters()
            text = packs.format_starters(result)
        elif args.pack_command == "verify":
            result = packs.verify(args.pack, args.allowed_signers)
            text = packs.format_verify(result)
        else:
            result = packs.import_pack(args.input, args.pack, args.allowed_signers, args.unsigned)
            text = packs.format_import(result)
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        code = getattr(error, "code", None)
        print(f"eu-compliance-guard: {code if code in _ERROR_CODES else 'pack-failed'}: {name} failed", file=sys.stderr)
        return 2
    (_emit(json.dumps(result, indent=2)) if getattr(args, "json", False) and result is not None else _emit_text(text))
    if args.pack_command == "verify":
        return 0 if result["signature"] == "valid" else 1
    return 0


def _import(args) -> int:
    import json
    from . import imports
    try:
        _, summary = imports.import_file(args.input, args.file, args.kind)
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        code = getattr(error, "code", None)
        print(f"eu-compliance-guard: {code if code in _ERROR_CODES else 'import-failed'}: import-evidence failed",
              file=sys.stderr)
        return 2
    (_emit(json.dumps(summary, indent=2)) if args.json else _emit_text(imports.format_summary(summary)))
    return 0


def _accept(args) -> int:
    import json
    from . import mapping
    try:
        result = mapping.accept(args.input, args.mapping)
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        code = getattr(error, "code", None)
        known = _ERROR_CODES | {"bad-mapping", "unknown-id"}
        print(f"eu-compliance-guard: {code if code in known else 'accept-failed'}: accept failed", file=sys.stderr)
        return 2
    (_emit(json.dumps(result, indent=2)) if args.json else _emit_text(mapping.format_result(result)))
    return 0


def _graph(args) -> int:
    from pathlib import Path
    from . import graph, grounding
    if args.view or args.open:
        try:
            from .graph_view import write
            page = write(args.input)
        except KeyboardInterrupt:
            return 130
        except Exception as error:
            code = getattr(error, "code", None)
            print(f"eu-compliance-guard: {code if code in _ERROR_CODES else 'graph-failed'}: graph failed", file=sys.stderr)
            return 2
        _emit(str(page))
        if args.open:
            _open_in_browser(page)
        return 0
    try:
        path = Path(args.input)
        _, root = grounding._declarations(path)
        built = graph.build_graph(root, grounding._own_files(path, root))
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        code = getattr(error, "code", None)
        print(f"eu-compliance-guard: {code if code in _ERROR_CODES else 'graph-failed'}: graph failed", file=sys.stderr)
        return 2
    if args.json:
        _emit(graph.to_json(built).decode("utf-8"), end="")
    else:
        _emit_text(graph.format_graph(built))
    return 0


def _ground(args) -> int:
    import json
    from . import grounding
    pins = []
    try:
        if args.apply:
            for item in args.apply:
                fact, separator, location = item.partition("=")
                if not separator:
                    raise grounding.GroundingError("bad-location")
                pins.append((fact, location))
            # Check every pin before writing any, so a refused one leaves the declarations unchanged.
            for fact, location in pins:
                grounding.apply(args.input, fact, location, write=False)
            for fact, location in pins:
                grounding.apply(args.input, fact, location)
        else:
            report = grounding.ground(args.input, args.top)
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        code = getattr(error, "code", None)
        print(f"eu-compliance-guard: {code if code in _ERROR_CODES else 'ground-failed'}: grounding failed", file=sys.stderr)
        return 2
    if pins and args.json:
        _emit(json.dumps({"applied": [{"fact": fact, "location": location} for fact, location in pins]}, indent=2))
        return 0
    if pins:
        for fact, location in pins:
            _emit(f"{fact}: observed, pinned to {location}")
        _emit_text("Run check, then a new revalidate run; a later change to the file makes this evidence unavailable.")
        return 0
    (_emit(json.dumps(report, indent=2)) if args.json else _emit_text(grounding.format_ground(report)))
    return 0


def _next(args) -> int:
    import json
    from . import nextstep
    try:
        if args.run is None:
            from .authoring import state_dir
            latest = nextstep.latest_run(state_dir(args.input, create=False))
            if latest is None:
                raise nextstep.NoRun("no-run")
            args.run = str(latest)
        from .view import verify_run
        steps = nextstep.next_steps(verify_run(args.run), args.top)
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        code = getattr(error, "code", None)
        print(f"eu-compliance-guard: {code if code in _ERROR_CODES else 'next-failed'}: next step failed", file=sys.stderr)
        return 2
    (_emit(json.dumps({"run": args.run, "steps": steps}, indent=2)) if args.json
     else _emit_text(nextstep.format_steps(steps)))
    return 0


def _score(args) -> int:
    """Exit 0 whatever the points: there is deliberately no threshold to pass or fail."""
    import json
    from . import nextstep, scorecard
    try:
        if args.run is None:
            from .authoring import state_dir
            latest = nextstep.latest_run(state_dir(args.input, create=False))
            if latest is None:
                raise nextstep.NoRun("no-run")
            args.run = str(latest)
        from .view import verify_run
        bundle = verify_run(args.run)
        previous = verify_run(args.against) if args.against is not None else None
        card = scorecard.score(bundle, previous)
        steps = nextstep.next_steps(bundle, args.top) if args.json else []
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        code = getattr(error, "code", None)
        print(f"eu-compliance-guard: {code if code in _ERROR_CODES else 'score-failed'}: score failed", file=sys.stderr)
        return 2
    (_emit(json.dumps({"run": args.run, "scorecard": card.model_dump(mode="json"), "steps": steps}, indent=2))
     if args.json else _emit_text(scorecard.format_text(card)))
    return 0


def _pr_check(args) -> int:
    import json
    from . import prcheck
    from .revalidation import load_input
    try:
        if args.diff == "-":
            diff = sys.stdin.buffer.read(prcheck.MAX_DIFF_BYTES + 1)
        else:
            with open(args.diff, "rb") as handle:
                diff = handle.read(prcheck.MAX_DIFF_BYTES + 1)
        if len(diff) > prcheck.MAX_DIFF_BYTES:
            raise prcheck.PRCheckError("capacity-exceeded")
        declared = load_input(args.input) if args.input is not None else _default_declarations()
        project_graph = root_prefix = None
        if declared is not None:
            # The checked-out project, mapped by parsing only, shows which data flows the diff changes.
            project_graph, root_prefix = prcheck.project_context(args.input or ".eu-compliance-guard/declarations.json")
        report = prcheck.pr_check(diff.decode("utf-8", "replace"), declared, project_graph, root_prefix)
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        code = getattr(error, "code", None)
        print(f"eu-compliance-guard: {code if code in _ERROR_CODES else 'pr-check-failed'}: pr check failed", file=sys.stderr)
        return 2
    (_emit(json.dumps(report, indent=2)) if args.json
     else _emit_text(prcheck.format_markdown(report) if args.markdown else prcheck.format_text(report)))
    return 1 if args.strict and report["attention"] else 0


def _default_declarations():
    """The default declarations, or None only when they plainly do not exist.

    A folder that cannot be searched or resolved is not an absent file: load_input refuses it
    (unsafe-path), so a permission problem never quietly drops the declaration-backed checks.
    """
    import os
    from .revalidation import load_input
    try:
        os.lstat(_DEFAULT_INPUT)
    except FileNotFoundError:
        return None
    except OSError:
        pass
    return load_input(_DEFAULT_INPUT)


def _view(run_dir: str, open_browser: bool, dashboard: bool = False) -> int:
    try:
        from .view import write_view
        path = write_view(run_dir, dashboard=dashboard)
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        code = getattr(error, "code", None)
        print(f"eu-compliance-guard: {code if code in _ERROR_CODES else 'view-failed'}: run view failed", file=sys.stderr)
        return 2
    _emit(str(path))
    if open_browser:
        _open_in_browser(path)
    return 0


def _open_in_browser(path) -> None:
    import os
    import webbrowser
    from pathlib import Path
    try:
        opened = webbrowser.open(Path(os.path.abspath(path)).as_uri())
    except Exception:
        opened = False
    if not opened:
        print("eu-compliance-guard: no-browser: open the file above manually", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
