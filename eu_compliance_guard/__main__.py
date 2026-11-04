"""Read-only requirements-to-law revalidation; offline unless --fetch-official is given."""

import argparse
import sys

_ERROR_CODES = {
    "invalid-input", "unsafe-path", "capacity-exceeded", "io-failed",
    "output-exists", "privacy-unavailable", "budget-exceeded", "invalid-output", "retrieval-failed",
    "incomplete-run", "corrupt-run",
    "wrong-project", "invalid-revision", "not-observable", "bad-location", "unrelated-line", "no-run",
}


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # argparse's default includes untrusted argument values in diagnostics.
        self.exit(2, "eu-compliance-guard: invalid-arguments: use --help for supported arguments\n")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description=__doc__, allow_abbrev=False)
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
    step = commands.add_parser("next", help="Rank the next review steps of a run by the open requirements they unblock",
                               allow_abbrev=False)
    step.add_argument("--run", help="Completed run directory (default: the newest run in this project's state-dir)")
    step.add_argument("--input", default=".eu-compliance-guard/declarations.json", help="Declarations file naming the project")
    step.add_argument("--top", type=int, default=3, choices=range(1, 11), metavar="1-10", help="Steps to show")
    step.add_argument("--json", action="store_true", help="Print the result as JSON")
    pr = commands.add_parser("pr-check", help="Screen a unified diff for EU legal touchpoints (for pull requests and CI)",
                             allow_abbrev=False)
    pr.add_argument("--diff", default="-", help="Unified diff file, or - for standard input (default)")
    pr.add_argument("--input", default=".eu-compliance-guard/declarations.json", help="Declarations file, if present")
    output = pr.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="Print the result as JSON")
    output.add_argument("--markdown", action="store_true", help="Print a pull-request comment")
    pr.add_argument("--strict", action="store_true", help="Exit 1 when any item needs attention")
    arguments = sys.argv[1:] if argv is None else argv
    args = parser.parse_args(arguments)
    if args.command == "view":
        return _view(args.run, args.open)
    if args.command == "next":
        return _next(args)
    if args.command == "pr-check":
        return _pr_check(args)
    if args.command == "init":
        return _init(args)
    if args.command == "ground":
        return _ground(args)
    if args.command == "state-dir":
        try:
            from .authoring import state_dir
            print(state_dir(args.input))
        except Exception as error:
            code = getattr(error, "code", None)
            print(f"eu-compliance-guard: {code if code in _ERROR_CODES else 'io-failed'}: state-dir failed", file=sys.stderr)
            return 2
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
    print(f"Run {bundle.run.id}: processing state {bundle.run.state}; report.md and bundle.json retained.")
    print("Processing state is not a compliance verdict.")
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
    print(path)
    print("Starter declarations written. Add requirements, facts, source targets and obligations, then run check.")
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
    print(json.dumps(report, indent=2) if as_json else format_check(report))
    return 0 if report["valid"] else 2


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
        print(json.dumps({"applied": [{"fact": fact, "location": location} for fact, location in pins]}, indent=2))
        return 0
    if pins:
        for fact, location in pins:
            print(f"{fact}: observed, pinned to {location}")
        print("Run check, then a new revalidate run; a later change to the file makes this evidence unavailable.")
        return 0
    print(json.dumps(report, indent=2) if args.json else grounding.format_ground(report))
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
    print(json.dumps({"run": args.run, "steps": steps}, indent=2) if args.json else nextstep.format_steps(steps))
    return 0


def _pr_check(args) -> int:
    import json
    import os
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
        declared = load_input(args.input) if os.path.lexists(args.input) else None
        report = prcheck.pr_check(diff.decode("utf-8", "replace"), declared)
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        code = getattr(error, "code", None)
        print(f"eu-compliance-guard: {code if code in _ERROR_CODES else 'pr-check-failed'}: pr check failed", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2) if args.json else prcheck.format_markdown(report) if args.markdown
          else prcheck.format_text(report))
    return 1 if args.strict and report["attention"] else 0


def _view(run_dir: str, open_browser: bool) -> int:
    try:
        from .view import write_view
        path = write_view(run_dir)
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        code = getattr(error, "code", None)
        print(f"eu-compliance-guard: {code if code in _ERROR_CODES else 'view-failed'}: run view failed", file=sys.stderr)
        return 2
    print(path)
    if open_browser:
        import os
        import webbrowser
        from pathlib import Path
        try:
            opened = webbrowser.open(Path(os.path.abspath(path)).as_uri())
        except Exception:
            opened = False
        if not opened:
            print("eu-compliance-guard: no-browser: open the file above manually", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
