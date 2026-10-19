"""Offline, read-only requirements-to-law revalidation command."""

import argparse
import sys

_ERROR_CODES = {
    "invalid-input", "unsafe-path", "capacity-exceeded", "io-failed",
    "output-exists", "privacy-unavailable", "budget-exceeded", "invalid-output",
}


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # argparse's default includes untrusted argument values in diagnostics.
        self.exit(2, "eu-compliance-guard: invalid-arguments: use --help for supported arguments\n")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    revalidate = commands.add_parser("revalidate", help="Create a private offline revalidation report", allow_abbrev=False)
    revalidate.add_argument("--input", required=True, help="Explicit declaration JSON file")
    revalidate.add_argument("--output", required=True, help="New run directory under an existing private parent")
    revalidate.add_argument("--offline", action="store_true", help="Use selected local files only (also the default)")
    arguments = sys.argv[1:] if argv is None else argv
    if any(argument.split("=", 1)[0] in ("--fetch-official", "--previous") for argument in arguments):
        parser.error("unsupported future argument")
    args = parser.parse_args(arguments)
    try:
        from .revalidation import run
        bundle = run(args.input, args.output)
    except KeyboardInterrupt:
        print("eu-compliance-guard: interrupted: report assembly interrupted", file=sys.stderr)
        return 130
    except Exception as error:
        # Never echo exception text or unrecognised codes containing private input.
        code = getattr(error, "code", None)
        if not isinstance(code, str) or code not in _ERROR_CODES:
            code = "revalidation-failed"
        print(f"eu-compliance-guard: {code}: offline revalidation failed", file=sys.stderr)
        return 2
    print(f"Run {bundle.run.id}: processing state {bundle.run.state}; report.md and bundle.json retained.")
    print("Processing state is not a compliance verdict.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
