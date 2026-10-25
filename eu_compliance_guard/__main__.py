"""Read-only requirements-to-law revalidation; offline unless --fetch-official is given."""

import argparse
import sys

_ERROR_CODES = {
    "invalid-input", "unsafe-path", "capacity-exceeded", "io-failed",
    "output-exists", "privacy-unavailable", "budget-exceeded", "invalid-output", "retrieval-failed",
    "incomplete-run", "corrupt-run",
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
    network = revalidate.add_mutually_exclusive_group()
    network.add_argument("--offline", action="store_true", help="Use selected local files only (also the default)")
    network.add_argument("--fetch-official", action="store_true",
                         help="Also GET each declared source target from the fixed official-host registry")
    view = commands.add_parser("view", help="Write and optionally open a static HTML view of a verified run", allow_abbrev=False)
    view.add_argument("--run", required=True, help="Existing run directory with a valid completion marker")
    view.add_argument("--open", action="store_true", help="Open the view in the default browser")
    arguments = sys.argv[1:] if argv is None else argv
    if any(argument.split("=", 1)[0] == "--previous" for argument in arguments):
        parser.error("unsupported future argument")
    args = parser.parse_args(arguments)
    if args.command == "view":
        return _view(args.run, args.open)
    try:
        from .revalidation import run
        bundle = run(args.input, args.output, fetch_official=True) if args.fetch_official else run(args.input, args.output)
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
