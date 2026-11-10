"""Read-only requirements-to-law revalidation; offline unless --fetch-official or `semantic setup` is given."""

import argparse
import sys

_ERROR_CODES = {
    "invalid-input", "unsafe-path", "capacity-exceeded", "io-failed",
    "output-exists", "privacy-unavailable", "budget-exceeded", "invalid-output", "retrieval-failed",
    "incomplete-run", "corrupt-run",
    "wrong-project", "invalid-revision", "not-observable", "bad-location", "unrelated-line", "no-run",
    "unknown-id", "unreviewed-decision", "bad-principal", "signing-failed", "pack-conflict", "unsigned-pack",
    "bad-signature", "unknown-article", "seal-conflict", "invalid-seal-log",
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


def _parser() -> _Parser:
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
    init.add_argument("--path", default=_DEFAULT_INPUT, help="Declarations file to create")
    init.add_argument("--assessment-date", help="ISO date the assessment is for (default: today)")
    init.add_argument("--jurisdiction", action="append", help="Declared jurisdiction; repeat for several (default: EU)")
    init.add_argument("--synthetic", action="store_true", help="Mark the declarations as a fictional example")
    check = commands.add_parser("check", help="Validate declarations and selected files with located diagnostics",
                                allow_abbrev=False)
    check.add_argument("--input", default=_DEFAULT_INPUT, help="Declarations file to check")
    check.add_argument("--previous", help="Completed predecessor run; also check that changed records have new revisions")
    check.add_argument("--json", action="store_true", help="Print the result as JSON")
    state = commands.add_parser("state-dir", help="Print (and create) the private run directory for a project",
                                allow_abbrev=False)
    state.add_argument("--input", default=_DEFAULT_INPUT, help="Declarations file naming the project")
    lock = commands.add_parser("lock", help="Record the law a run's reviews read: versions and article digests",
                               allow_abbrev=False)
    lock.add_argument("--input", default=_DEFAULT_INPUT, help="Declarations file")
    lock.add_argument("--run", help="Completed run directory (default: the newest run in this project's state-dir)")
    lock.add_argument("--output", help="Lockfile (default: eu-law.lock beside the declarations)")
    impact = commands.add_parser("impact", help="List the articles changed since the lock and the decisions citing them",
                                 allow_abbrev=False)
    impact.add_argument("--input", default=_DEFAULT_INPUT, help="Declarations file")
    impact.add_argument("--run", help="Newer completed run (default: the newest run in this project's state-dir)")
    impact.add_argument("--lock", help="Lockfile (default: eu-law.lock beside the declarations)")
    impact.add_argument("--json", action="store_true", help="Print the result as JSON")
    impact.add_argument("--strict", action="store_true", help="Exit 1 when a declared obligation cites a changed article")
    sign = commands.add_parser("sign", help="Sign a reviewed decision with your SSH key, against the locked law and evidence",
                               allow_abbrev=False)
    sign.add_argument("--decision", required=True, help="Applicability decision ID")
    sign.add_argument("--input", default=_DEFAULT_INPUT, help="Declarations file")
    sign.add_argument("--key", required=True, help="SSH private key (or its .pub with an agent), as for git signing")
    sign.add_argument("--principal", required=True, help="Signer identity as written in the allowed-signers file")
    sign.add_argument("--lock", help="Lockfile (default: eu-law.lock beside the declarations, if present)")
    verify = commands.add_parser("verify", help="Verify signed decisions and say which changed since they were signed",
                                 allow_abbrev=False)
    verify.add_argument("--input", default=_DEFAULT_INPUT, help="Declarations file")
    verify.add_argument("--allowed-signers", required=True, help="ssh-keygen allowed-signers file")
    verify.add_argument("--lock", help="Lockfile (default: eu-law.lock beside the declarations, if present)")
    verify.add_argument("--json", action="store_true", help="Print the result as JSON")
    export = commands.add_parser("export", help="Draft a record of processing (Art. 30) or DPIA screening inputs (Art. 35)",
                                 allow_abbrev=False)
    export.add_argument("kind", choices=["ropa", "dpia"], help="ropa: record of processing; dpia: DPIA screening inputs")
    export.add_argument("--input", default=_DEFAULT_INPUT, help="Declarations file")
    export.add_argument("--format", choices=["md", "json", "csv"], default="md", help="Output format (csv: ropa only)")
    export.add_argument("--output", help="Write to this file (never through a link) instead of printing")
    when = commands.add_parser("timeline", help="List application, entry-into-force and transposition dates quoted from the retained text",
                               allow_abbrev=False)
    when.add_argument("--input", default=_DEFAULT_INPUT, help="Declarations file")
    when.add_argument("--run", help="Completed run directory (default: the newest run in this project's state-dir)")
    when.add_argument("--json", action="store_true", help="Print the result as JSON")
    seal = commands.add_parser("seal", help="Append a run to the tamper-evident log runs.log, or check the log with --check",
                               allow_abbrev=False)
    seal.add_argument("--run", help="Completed run directory (default: the newest run in this project's state-dir)")
    seal.add_argument("--input", default=_DEFAULT_INPUT, help="Declarations file")
    seal.add_argument("--key", help="SSH private key to sign the entry with (optional)")
    seal.add_argument("--principal", help="Signer identity, required with --key")
    seal.add_argument("--check", action="store_true", help="Verify the chain, the sealed runs on this machine and signatures")
    seal.add_argument("--allowed-signers", help="With --check: OpenSSH allowed-signers file to verify signatures against")
    seal.add_argument("--json", action="store_true", help="With --check: print the result as JSON")
    semantic = commands.add_parser("semantic", help="Optional semantic search for article suggestions: show its status or set it up",
                                   allow_abbrev=False)
    semantic.add_argument("action", choices=["status", "setup"],
                          help="status: what is on and ready; setup: download the pinned model once (network: huggingface.co)")
    semantic.add_argument("--json", action="store_true", help="Print the status as JSON")
    cite = commands.add_parser("cite-check", help="Check article citations and quotations against the retained official text",
                               allow_abbrev=False)
    cite.add_argument("file", help="Text file to check, or - for standard input")
    cite.add_argument("--input", default=_DEFAULT_INPUT, help="Declarations file")
    cite.add_argument("--run", help="Completed run directory (default: the newest run in this project's state-dir)")
    cite.add_argument("--json", action="store_true", help="Print the result as JSON")
    mcp = commands.add_parser("mcp", help="Serve cite_check, article_search, ground, pr_check, timeline and next_steps as MCP tools over stdio",
                              allow_abbrev=False)
    mcp.add_argument("--input", default=_DEFAULT_INPUT, help="Declarations file")
    pack = commands.add_parser("pack", help="Build, sign, verify or import a reusable obligation pack (never a decision)",
                               allow_abbrev=False)
    packs = pack.add_subparsers(dest="pack_command", required=True, parser_class=_Parser)
    build = packs.add_parser("build", help="Draft a pack from this project's obligations", allow_abbrev=False)
    build.add_argument("--input", default=_DEFAULT_INPUT, help="Declarations file")
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
    pack_import.add_argument("--input", default=_DEFAULT_INPUT, help="Declarations file")
    trust = pack_import.add_mutually_exclusive_group(required=True)
    trust.add_argument("--allowed-signers", help="Import only if the pack's signature verifies against this file")
    trust.add_argument("--unsigned", action="store_true", help="Import a pack without checking any signature")
    pack_import.add_argument("--json", action="store_true", help="Print the result as JSON")
    imported = commands.add_parser("import-evidence", help="Keep a WEC or SARIF result as untrusted evidence, summarised by concept",
                                   allow_abbrev=False)
    imported.add_argument("file", help="EDPS Website Evidence Collector inspection.json or a SARIF log")
    imported.add_argument("--kind", required=True, choices=["wec", "sarif"], help="Format of the file")
    imported.add_argument("--input", default=_DEFAULT_INPUT, help="Declarations file")
    imported.add_argument("--json", action="store_true", help="Print the summary as JSON")
    accept = commands.add_parser("accept", help="Map a requirement to a candidate obligation citing an article (no decision)",
                                 allow_abbrev=False)
    accept.add_argument("mapping", metavar="REQ=TARGET:ARTICLE", help="For example req-delete=target-gdpr:Article 17")
    accept.add_argument("--input", default=_DEFAULT_INPUT, help="Declarations file")
    accept.add_argument("--json", action="store_true", help="Print the result as JSON")
    graph = commands.add_parser("graph", help="Map the project's Python and Rust files, functions, imports and calls (static, read-only)",
                                allow_abbrev=False)
    graph.add_argument("--input", default=".eu-compliance-guard/declarations.json",
                       help="Declarations file; its files root is the project that is mapped")
    graph.add_argument("--json", action="store_true", help="Print the whole graph as JSON")
    graph.add_argument("--view", action="store_true",
                       help="Write a static graph page to <state-dir>/views/graph.html and print its path")
    graph.add_argument("--open", action="store_true", help="With --view, open the page in the default browser")
    ground = commands.add_parser("ground", help="Find code evidence for assumed facts; --apply pins one as observed",
                                 allow_abbrev=False)
    ground.add_argument("--input", default=_DEFAULT_INPUT, help="Declarations file")
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
    step.add_argument("--input", default=_DEFAULT_INPUT, help="Declarations file naming the project")
    step.add_argument("--top", type=int, default=3, choices=range(1, 11), metavar="1-10", help="Steps to show")
    step.add_argument("--json", action="store_true", help="Print the result as JSON")
    score = commands.add_parser("score", help="Show the review progress of a run: separate meters, points out of 10, "
                                               "never a compliance score", allow_abbrev=False)
    score.add_argument("--run", help="Completed run directory (default: the newest run in this project's state-dir)")
    score.add_argument("--input", default=_DEFAULT_INPUT, help="Declarations file naming the project")
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
    return parser


class _Exit(Exception):
    """Ends the command with this exit code; the diagnostic is already printed."""

    def __init__(self, code: int):
        self.code = code


def _try(work, fallback: str, label: str, known=_ERROR_CODES):
    """Run a command's work and return its result.

    A failure prints one fixed diagnostic and exits 2: a known error code, else `fallback`. Exception
    text and unrecognised codes are never echoed, because they may hold private input."""
    try:
        return work()
    except KeyboardInterrupt:
        raise _Exit(130) from None
    except Exception as error:
        code = getattr(error, "code", None)
        print(f"eu-compliance-guard: {code if isinstance(code, str) and code in known else fallback}: {label}", file=sys.stderr)
        raise _Exit(2) from None


def _show(as_json: bool, data, text) -> None:
    """Print a result as JSON, or as text (a string, or a formatter of `data`) with the legal notice."""
    import json
    if as_json:
        _emit(json.dumps(data, indent=2))
    else:
        _emit_text(text if isinstance(text, str) else text(data))


def _run_dir(args) -> str:
    """The run named by --run, else the newest completed run of the declared project."""
    if args.run is not None:
        return args.run
    from . import authoring, nextstep
    found = nextstep.latest_run(authoring.state_dir(args.input, create=False))
    if found is None:
        raise nextstep.NoRun("no-run")
    return str(found)


def _retained_text(args):
    """(bundle, article catalogue) of the run a command reads the law from."""
    from .view import catalogue, verify_run
    contents: dict[str, bytes] = {}
    bundle = verify_run(_run_dir(args), contents)
    return bundle, catalogue(bundle, contents)


def _command(argv: list[str] | None) -> int:
    args = _parser().parse_args(sys.argv[1:] if argv is None else argv)
    try:
        return _HANDLERS[args.command](args)
    except _Exit as done:
        return done.code


def _revalidate(args) -> int:
    def work():
        from .revalidation import run
        options = {}
        if args.fetch_official:
            options["fetch_official"] = True
        if args.previous is not None:
            options["previous"] = args.previous
        return run(args.input, args.output, **options)
    try:
        bundle = _try(work, "revalidation-failed", "revalidation failed")
    except _Exit as done:
        if done.code == 130:
            print("eu-compliance-guard: interrupted: report assembly interrupted", file=sys.stderr)
        raise
    _emit(f"Run {bundle.run.id}: processing state {bundle.run.state}; report.md and bundle.json retained.")
    _emit_text("Processing state is not a compliance verdict.")
    return 0


def _mcp(args) -> int:
    from .mcp_server import serve
    try:
        return serve(args.input)
    except KeyboardInterrupt:
        return 130


def _state_dir(args) -> int:
    def work():
        from .authoring import state_dir
        return state_dir(args.input)
    _emit(str(_try(work, "io-failed", "state-dir failed")))
    return 0


def _init(args) -> int:
    def work():
        from .authoring import init
        return init(args.path, args.project_id, assessment_date=args.assessment_date,
                    jurisdictions=args.jurisdiction, synthetic=args.synthetic)
    _emit(str(_try(work, "invalid-input", "init failed")))
    _emit_text("Starter declarations written. Add requirements, facts, source targets and obligations, then run check.")
    return 0


def _check(args) -> int:
    from .authoring import check, format_check
    report = _try(lambda: check(args.input, args.previous), "check-failed", "check failed")
    _show(args.json, report, format_check)
    return 0 if report["valid"] else 2


def _lawlock(args) -> int:
    from pathlib import Path
    from . import lawlock
    from .revalidation import load_input
    default = Path(args.input).parent / lawlock.LOCK_NAME

    def work():
        built = lawlock.build(_run_dir(args))
        if args.command == "lock":
            return built, lawlock.write(built, args.output or default)
        return built, lawlock.impact(lawlock.read(args.lock or default), built, load_input(args.input))
    built, result = _try(work, args.command + "-failed", args.command + " failed")
    if args.command == "lock":
        _emit_text(f"{result}: {len(built.entries)} act(s), "
                   f"{sum(len(item.articles) for item in built.entries)} provision(s) locked from run {built.run_id}.")
        return 0
    _show(args.json, result, lawlock.format_impact)
    return 1 if args.strict and result["obligations"] else 0


def _sign(args) -> int:
    from pathlib import Path
    from . import lawlock, signing
    path = _try(lambda: signing.sign(args.input, args.decision, args.key, args.principal, args.lock), "sign-failed", "sign failed")
    unpinned = not (args.lock or (Path(args.input).parent / lawlock.LOCK_NAME).exists())
    _emit_text(f"{path}: decision {args.decision} signed by {args.principal}."
               + (" No eu-law.lock was found, so the signature pins no article text: run lock first and sign "
                  "again to bind it to the law." if unpinned else ""))
    return 0


def _verify(args) -> int:
    from . import signing
    results = _try(lambda: signing.verify(args.input, args.allowed_signers, args.lock), "verify-failed", "verify failed")
    _show(args.json, results, signing.format_verify)
    # A missing signature is listed but is not a failure: signing is optional.
    return 0 if all(item["signature"] in ("valid", "missing") and not item["changed"] for item in results) else 1


def _export(args) -> int:
    def work():
        import json
        from . import exports, lawlock
        from .revalidation import RevalidationError, load_input
        if args.format == "csv" and args.kind != "ropa":
            raise RevalidationError("invalid-input")
        declared = load_input(args.input)
        result = exports.ropa(declared) if args.kind == "ropa" else exports.dpia(declared)
        text = (json.dumps(result, indent=2, ensure_ascii=False) + "\n" if args.format == "json"
                else exports.to_csv(result) if args.format == "csv" else exports.to_markdown(result))
        if args.output:
            lawlock.write_bytes(args.output, text.encode("utf-8"))
        return text
    text = _try(work, "export-failed", "export failed")
    if args.output:
        _emit_text(f"{args.output}: draft {args.kind} export written ({args.format}). Review it before relying on it.")
    else:
        _emit(text, end="")
    return 0


def _seal(args) -> int:
    from . import authoring, seal

    def work():
        state = authoring.state_dir(args.input, create=False)
        if args.check:
            return seal.check(args.input, state, args.allowed_signers)
        return seal.seal(args.input, _run_dir(args), args.key, args.principal)
    result = _try(work, "seal-failed", "seal failed")
    if args.check:
        _show(args.json, result, seal.format_check)
        return 0 if result["ok"] else 1
    _emit_text(f"{result['path']}: run {result['run_id']} " + ("was already sealed" if result["already"] else "sealed")
               + f" as entry {result['seq']}" + (", signed" if result["signed"] else "")
               + ". Commit runs.log to Git so a rewrite is visible.")
    return 0


def _semantic(args) -> int:
    from . import semantic
    report = _try(lambda: semantic.setup() if args.action == "setup" else semantic.status(), "semantic-failed",
                  f"semantic {args.action} failed", {"semantic-not-installed", "model-download-failed", "model-digest-mismatch"})
    _show(args.json, report, semantic.format_status)
    return 0


def _timeline(args) -> int:
    from . import timeline

    def work():
        bundle, acts = _retained_text(args)
        assessment = bundle.declarations.scope.assessment_date
        return assessment, timeline.timeline(acts, assessment), sorted(acts)
    assessment, entries, acts = _try(work, "timeline-failed", "timeline failed")
    _show(args.json, {"assessment_date": assessment, "entries": entries}, timeline.format_timeline(entries, assessment, acts))
    return 0


def _cite_check(args) -> int:
    from . import citations

    def work():
        if args.file == "-":
            text = sys.stdin.read(citations.MAX_TEXT)
        else:
            with open(args.file, encoding="utf-8") as handle:
                text = handle.read(citations.MAX_TEXT)
        bundle, acts = _retained_text(args)
        return citations.check(text, acts, citations.act_names(bundle.declarations.source_targets))
    report = _try(work, "cite-check-failed", "cite-check failed")
    _show(args.json, report, citations.format_check)
    return 0 if report["ok"] else 1


def _pack(args) -> int:
    from . import packs

    def work():
        """(text, JSON result or None) of one pack subcommand."""
        if args.pack_command == "build":
            built = packs.build(args.input, args.id, args.title, args.obligation, args.revision, args.lock, args.status)
            path = packs.write(built, args.output)
            return (f"{path}: pack {built.id} revision {built.revision} ({built.status}), {len(built.obligations)} "
                    f"obligation(s), {len(built.source_targets)} source target(s). Sign it with pack sign after review."), None
        if args.pack_command == "sign":
            return f"{packs.sign(args.pack, args.key, args.principal)}: pack signed by {args.principal}.", None
        if args.pack_command == "starters":
            result = packs.starters()
            return packs.format_starters(result), result
        if args.pack_command == "verify":
            result = packs.verify(args.pack, args.allowed_signers)
            return packs.format_verify(result), result
        result = packs.import_pack(args.input, args.pack, args.allowed_signers, args.unsigned)
        return packs.format_import(result), result
    text, result = _try(work, "pack-failed", f"pack {args.pack_command} failed")
    _show(getattr(args, "json", False) and result is not None, result, text)
    return 1 if args.pack_command == "verify" and result["signature"] != "valid" else 0


def _import(args) -> int:
    from . import imports
    _, summary = _try(lambda: imports.import_file(args.input, args.file, args.kind), "import-failed", "import-evidence failed")
    _show(args.json, summary, imports.format_summary)
    return 0


def _accept(args) -> int:
    from . import mapping
    result = _try(lambda: mapping.accept(args.input, args.mapping), "accept-failed", "accept failed",
                  _ERROR_CODES | {"bad-mapping", "unknown-id"})
    _show(args.json, result, mapping.format_result)
    return 0


def _graph(args) -> int:
    from pathlib import Path
    from . import graph, grounding
    if args.view or args.open:
        def page():
            from .graph_view import write
            return write(args.input)
        path = _try(page, "graph-failed", "graph failed")
        _emit(str(path))
        if args.open:
            _open_in_browser(path)
        return 0

    def work():
        path = Path(args.input)
        _, root = grounding._declarations(path)
        return graph.build_graph(root, grounding._own_files(path, root))
    built = _try(work, "graph-failed", "graph failed")
    if args.json:
        _emit(graph.to_json(built).decode("utf-8"), end="")
    else:
        _emit_text(graph.format_graph(built))
    return 0


def _ground(args) -> int:
    from . import grounding
    pins = []

    def work():
        if not args.apply:
            return grounding.ground(args.input, args.top)
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
    report = _try(work, "ground-failed", "grounding failed")
    if not pins:
        _show(args.json, report, grounding.format_ground)
    elif args.json:
        _show(True, {"applied": [{"fact": fact, "location": location} for fact, location in pins]}, "")
    else:
        for fact, location in pins:
            _emit(f"{fact}: observed, pinned to {location}")
        _emit_text("Run check, then a new revalidate run; a later change to the file makes this evidence unavailable.")
    return 0


def _next(args) -> int:
    from . import nextstep
    from .view import verify_run

    def work():
        run = _run_dir(args)
        return run, nextstep.next_steps(verify_run(run), args.top)
    run, steps = _try(work, "next-failed", "next step failed")
    _show(args.json, {"run": run, "steps": steps}, nextstep.format_steps(steps))
    return 0


def _score(args) -> int:
    """Exit 0 whatever the points: there is deliberately no threshold to pass or fail."""
    from . import nextstep, scorecard
    from .view import verify_run

    def work():
        run = _run_dir(args)
        bundle = verify_run(run)
        card = scorecard.score(bundle, verify_run(args.against) if args.against is not None else None)
        return run, card, nextstep.next_steps(bundle, args.top) if args.json else []
    run, card, steps = _try(work, "score-failed", "score failed")
    _show(args.json, {"run": run, "scorecard": card.model_dump(mode="json"), "steps": steps}, scorecard.format_text(card))
    return 0


def _pr_check(args) -> int:
    from . import prcheck
    from .revalidation import load_input

    def work():
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
            project_graph, root_prefix = prcheck.project_context(args.input or _DEFAULT_INPUT)
        return prcheck.pr_check(diff.decode("utf-8", "replace"), declared, project_graph, root_prefix)
    report = _try(work, "pr-check-failed", "pr check failed")
    _show(args.json, report, prcheck.format_markdown if args.markdown else prcheck.format_text)
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


def _view(args) -> int:
    def work():
        from .view import write_view
        return write_view(args.run, dashboard=args.dashboard)
    path = _try(work, "view-failed", "run view failed")
    _emit(str(path))
    if args.open:
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


_HANDLERS = {
    "revalidate": _revalidate, "init": _init, "check": _check, "state-dir": _state_dir, "lock": _lawlock,
    "impact": _lawlock, "sign": _sign, "verify": _verify, "seal": _seal, "export": _export, "timeline": _timeline,
    "cite-check": _cite_check, "semantic": _semantic, "mcp": _mcp, "pack": _pack, "import-evidence": _import,
    "accept": _accept, "graph": _graph, "ground": _ground, "view": _view, "next": _next, "score": _score,
    "pr-check": _pr_check,
}


if __name__ == "__main__":
    raise SystemExit(main())
