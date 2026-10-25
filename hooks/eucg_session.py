"""SessionStart hook: inject EU Compliance Guard mode, CLI command and latest-run summary.

Standard library only. Silent unless the project has a .eu-compliance-guard/ directory.
Run data is summarized as counts and fixed-format fields only; gap text never enters
the context. Any failure exits 0 without output so a session never breaks.
"""
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
MODES = ("lite", "full", "strict", "off")
MAX_BUNDLE_BYTES = 4 * 1024 * 1024
SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:+-]{0,127}$")


def _mode() -> str:
    mode = os.environ.get("EUCG_DEFAULT_MODE", "").strip().lower()
    if not mode:
        config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "eu-compliance-guard/config.json"
        try:
            mode = str(json.loads(config.read_text(encoding="utf-8")).get("defaultMode", "")).lower()
        except (OSError, ValueError, AttributeError):
            mode = ""
    return mode if mode in MODES else "full"


def _project(payload: dict) -> Path:
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else None
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or cwd or os.getcwd())


def cli_command() -> str:
    root = shlex.quote(str(ROOT))
    if shutil.which("uv"):
        return f"uv run --project {root} --locked python -m eu_compliance_guard"
    return f"PYTHONPATH={root} python3 -m eu_compliance_guard"


def state_dir(project: Path) -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    return base / "eu-compliance-guard" / project.name


def _safe(value) -> str:
    return value if isinstance(value, str) and SAFE.match(value) else "unrecorded"


def latest_run(project: Path) -> str:
    """Fixed-format summary of the newest run with a completion marker, or a fixed notice."""
    try:
        runs = [path for path in state_dir(project).iterdir() if path.name.startswith("run-")
                and not path.is_symlink() and path.is_dir() and (path / "complete.json").is_file()]
    except OSError:
        runs = []
    if not runs:
        return "No completed run yet; use /eucg-audit."
    newest = max(runs, key=lambda path: path.name)  # Run names carry their UTC start time, as the band reads them.
    try:
        with open(newest / "bundle.json", "rb") as handle:
            raw = handle.read(MAX_BUNDLE_BYTES + 1)
        if len(raw) > MAX_BUNDLE_BYTES:
            raise ValueError
        bundle = json.loads(raw)
        run, scope = bundle["run"], bundle["declarations"]["scope"]
        states = [item.get("state") for item in bundle.get("requirement_assessments", [])]
        attempts = [item.get("state") for item in bundle.get("source_attempts", [])]
        gaps = len(bundle.get("gaps", []))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return "Latest run directory could not be summarized; use /eucg-status."
    summary = (f"Latest run {_safe(run.get('id'))} ended {_safe(run.get('ended_at'))}: state {_safe(run.get('state'))}, "
               f"assessment date {_safe(scope.get('assessment_date'))}, {gaps} open gaps, "
               f"requirements {states.count('supported')} supported / {states.count('unresolved')} unresolved / "
               f"{states.count('conflicting')} conflicting")
    if attempts:
        summary += f", source attempts {attempts.count('retrieved')} retrieved / {len(attempts) - attempts.count('retrieved')} not confirmed"
    return summary + ". Processing state is not a compliance verdict."


def rules(mode: str) -> str:
    text = (ROOT / "skills/eucg/SKILL.md").read_text(encoding="utf-8")
    body = text.split("---", 2)[2].strip() if text.startswith("---") else text
    return f"EU COMPLIANCE GUARD MODE ACTIVE — level: {mode}. Behave at this level until changed.\n\n{body}"


def context(payload: dict) -> str | None:
    mode = _mode()
    project = _project(payload)
    if mode == "off" or not (project / ".eu-compliance-guard").is_dir():
        return None
    declarations = project / ".eu-compliance-guard/declarations.json"
    lines = [rules(mode), "", f"CLI for this machine: `{cli_command()}`",
             f"Private run directory: `{state_dir(project)}` (create with mode 0700; never inside the repository).",
             "Declarations: " + ("present." if declarations.is_file() else "missing; /eucg-audit can draft them."),
             latest_run(project)]
    return "\n".join(lines)


def main() -> int:
    try:
        raw = sys.stdin.read(64 * 1024) if not sys.stdin.isatty() else ""
        payload = json.loads(raw) if raw.strip() else {}
        text = context(payload if isinstance(payload, dict) else {})
        if text:
            sys.stdout.write(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}))
    except Exception:
        pass  # A guard hook must never break a session.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
