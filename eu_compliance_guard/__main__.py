"""Read-only requirements-to-law revalidation; offline unless --fetch-official is given."""

import argparse
import sys

_ERROR_CODES = {
    "invalid-input", "unsafe-path", "capacity-exceeded", "io-failed",
    "output-exists", "privacy-unavailable", "budget-exceeded", "invalid-output", "retrieval-failed",
    "incomplete-run", "corrupt-run",
    "wrong-project", "invalid-revision", "not-observable", "bad-location", "unrelated-line",
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
                        help="Mark a technical fact observed, pinned to this file line; repeat for several")
    view = commands.add_parser("view", help="Write and optionally open a static HTML view of a verified run", allow_abbrev=False)
    view.add_argument("--run", required=True, help="Existing run directory with a valid completion marker")
    view.add_argument("--open", action="store_true", help="Open the view in the default browser")
    arguments = sys.argv[1:] if argv is None else argv
    args = parser.parse_args(arguments)
    if args.command == "view":
        return _view(args.run, args.open)
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
    try:
        if args.apply:
            for item in args.apply:
                fact, separator, location = item.partition("=")
                if not separator:
                    raise grounding.GroundingError("bad-location")
                grounding.apply(args.input, fact, location)
                print(f"{fact}: observed, pinned to {location}")
            print("Run check, then a new revalidate run; a later change to the file makes this evidence unavailable.")
            return 0
        report = grounding.ground(args.input, args.top)
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        code = getattr(error, "code", None)
        print(f"eu-compliance-guard: {code if code in _ERROR_CODES else 'ground-failed'}: grounding failed", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2) if args.json else grounding.format_ground(report))
    return 0


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
        import webbrowser
        if not webbrowser.open(path.as_uri()):
            print("eu-compliance-guard: no-browser: open the file above manually", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
