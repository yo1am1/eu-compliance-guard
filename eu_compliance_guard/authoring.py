"""Help authors write declarations: a valid starter file and located, value-free diagnostics.

Diagnostics name JSON locations, error kinds and digests only; they never echo
declared values, file contents or evidence. Checking is not a legal assessment.
"""
from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
import re

from pydantic import ValidationError

from . import models as m, revalidation as r

DEFAULT_PATH = ".eu-compliance-guard/declarations.json"
MAX_PROBLEMS = 50
FIELD = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
LOCATED = re.compile(r"^[a-z_]+(?:\[\d+\]|\[\])?[^:]{0,200}: ")


def starter(project_id: str, assessment_date: str | None = None, jurisdictions: list[str] | None = None,
            synthetic: bool = False) -> m.RevalidationInput:
    """The smallest valid declaration: scope only, every register empty and therefore an explicit gap."""
    return m.RevalidationInput.model_validate({
        "schema_version": 1, "project_id": project_id, "synthetic": synthetic,
        "declaration_run_id": "declarations", "declaration_manifest_id": "declarations",
        "scope": {"id": "scope", "revision": 0, "project_id": project_id,
                  "assessment_date": assessment_date or date.today().isoformat(), "environment": "production",
                  "activities": [], "establishment": [], "markets": [], "customer_types": [], "roles": [],
                  "size_and_sector": [], "jurisdictions": jurisdictions or ["EU"], "included_scenarios": [],
                  "exclusions": [], "permission_id": "declared-scope"},
    })


def init(path: str | os.PathLike, project_id: str, **options) -> Path:
    """Write a starter declaration; an existing file is never replaced."""
    record = starter(project_id, **options)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o644)
    except FileExistsError:
        raise r.RevalidationError("output-exists") from None
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(record.model_dump(mode="json"), handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path


def project_id(path: str | os.PathLike) -> str:
    """The declared project identifier, read without requiring the rest of the file to be valid."""
    r._primitives()
    try:
        with r._parent(path) as (fd, name):
            observed = r._read_file(fd, name, limit=m.MAX_REQUEST_BYTES, retain=True)
    except OSError:
        raise r.RevalidationError("unsafe-path") from None
    if observed.availability != "available":
        raise r.RevalidationError("unsafe-path")
    try:
        value = json.loads(observed.content).get("project_id")
    except (ValueError, AttributeError):
        raise r.RevalidationError("invalid-input") from None
    if not isinstance(value, str) or not ID.match(value):
        raise r.RevalidationError("invalid-input")
    return value


def state_dir(path: str | os.PathLike = DEFAULT_PATH, create: bool = True) -> Path:
    """Private per-project run storage, keyed by the declared project_id and free of symlinks.

    `${XDG_STATE_HOME:-~/.local/state}/eu-compliance-guard/<project_id>`; the session hook and the
    band derive the same path. Missing directories are created 0700; existing ones are not changed.
    """
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    directory = Path(os.path.realpath(base)) / "eu-compliance-guard" / project_id(path)
    if create:
        os.makedirs(directory.parent.parent, 0o700, exist_ok=True)
        for part in (directory.parent, directory):
            try:
                os.mkdir(part, 0o700)
            except FileExistsError:
                pass
    return directory


def _location(loc) -> str:
    text = ""
    for part in loc:
        # Model field names are plain identifiers; anything else is a key from the input, never printed.
        name = str(part) if isinstance(part, str) and FIELD.match(part) else "(unknown field)"
        text += f"[{part}]" if isinstance(part, int) else ("." if text else "") + name
    return text or "(document)"


def check(path: str | os.PathLike, previous: str | os.PathLike | None = None) -> dict:
    """Validate a declaration and observe its selected files, reporting problems by location.

    With `previous`, also verify that run and name every record that needs a higher revision.
    """
    errors, warnings, files, targets = [], [], [], []
    report = {"valid": False, "errors": errors, "warnings": warnings, "files": files, "targets": targets}
    r._primitives()
    try:
        with r._parent(path) as (fd, name):
            observed = r._read_file(fd, name, limit=m.MAX_REQUEST_BYTES, retain=True)
            if observed.availability != "available":
                errors.append({"at": "(file)", "problem": "declarations file is " + observed.availability})
                return report
            raw = observed.content
            try:
                r._check_json_depth(raw)
                json.loads(raw, object_pairs_hook=r._pairs, parse_float=r._finite, parse_constant=r._reject_constant)
            except json.JSONDecodeError as error:
                errors.append({"at": f"line {error.lineno}, column {error.colno}", "problem": "invalid JSON: " + error.msg})
                return report
            except UnicodeDecodeError:
                errors.append({"at": "(file)", "problem": "declarations must be UTF-8 JSON"})
                return report
            except r.RevalidationError as error:
                errors.append({"at": "(document)", "problem": "JSON nesting deeper than 32 levels" if error.code == "capacity-exceeded"
                               else "duplicate JSON key or non-finite number"})
                return report
            try:
                declared = m.parse_record(m.RevalidationInput, raw)
            except ValidationError as error:
                for detail in error.errors(include_input=False, include_url=False)[:MAX_PROBLEMS]:
                    at, problem = _location(detail["loc"]), detail["msg"].removeprefix("Value error, ")
                    # Cross-reference checks carry their own location: "<path>: <problem>".
                    if at == "(document)" and LOCATED.match(problem):
                        at, problem = problem.split(": ", 1)
                    errors.append({"at": at, "problem": problem})
                return report
            try:
                r._load(fd, name)
            except r.RevalidationError:
                errors.append({"at": "obligations", "problem": "duplicate required methods, an unknown method name, "
                               "or an identifier that collides with a derived disposition/unresolved identifier"})
            sources = {item.file.path for item in declared.sources if item.file}
            selected = [(f"sources[{index}].file", item.file.path, item.file.digest)
                        for index, item in enumerate(declared.sources) if item.file]
            selected += [(f"requirements[{index}].origin", item.origin.path, item.origin.digest)
                         for index, item in enumerate(declared.requirements) if item.origin]
            selected += [(f"evidence[{index}].path", item.path, item.evidence.digest)
                         for index, item in enumerate(declared.evidence) if item.path]
            total = 0
            for at, relative, digest in selected:
                try:
                    seen = r._read_file(fd, relative, limit=min(r.MAX_FILE_BYTES, r.MAX_TOTAL_BYTES - total),
                                        retain=relative in sources)
                except r.RevalidationError as error:
                    errors.append({"at": at, "problem": "selected file exceeds the 8 MiB per-file or 64 MiB total limit"
                                   if error.code == "capacity-exceeded" else "selected file could not be read safely"})
                    continue
                total += seen.size
                entry = {"at": at, "availability": seen.availability, "observed_digest": seen.digest,
                         "matches_declared": seen.digest == digest}
                files.append(entry)
                if seen.availability != "available":
                    errors.append({"at": at, "problem": f"selected file is {seen.availability} (paths resolve "
                                   "relative to the declarations file)"})
                elif seen.digest != digest:
                    errors.append({"at": at, "problem": "declared digest differs from the file; observed " + seen.digest})
                elif seen.content is not None:
                    media = next(item for item in declared.sources if item.file and item.file.path == relative)
                    admission = r.admit_source_content(seen.content, media.media_type, media.charset)
                    if admission.state != "accepted":
                        warnings.append({"at": at, "problem": f"source content needs review ({admission.reason})"})
    except FileNotFoundError:
        errors.append({"at": "(file)", "problem": "declarations file or its folder was not found"})
        return report
    except OSError:
        errors.append({"at": "(file)", "problem": "declarations file could not be opened safely (symlink or permissions)"})
        return report
    from . import sources as s
    for index, target in enumerate(declared.source_targets):
        state = "never fetched (fictional fixture)" if target.intended_type == "synthetic_fixture" else "fetchable"
        if state == "fetchable":
            try:
                s.allowed_hosts(s.TargetRequest(target.id, target.intended_url, tuple(target.redirect_hosts)))
            except s.RetrievalFailure as failure:
                state = "not fetchable: " + failure.code
                warnings.append({"at": f"source_targets[{index}]", "problem": "--fetch-official will refuse this target ("
                                 + failure.code + "); declare a manually downloaded copy as a selected source instead"})
        targets.append({"at": f"source_targets[{index}]", "id": target.id, "fetch": state})
    if not declared.requirements:
        warnings.append({"at": "requirements", "problem": "empty: every run will report a coverage gap"})
    if not declared.obligations:
        warnings.append({"at": "obligations", "problem": "empty: requirements cannot be mapped to candidate obligations"})
    unmapped = [index for index, item in enumerate(declared.requirements) if not item.obligation_refs]
    if unmapped:
        warnings.append({"at": "requirements", "problem": f"{len(unmapped)} requirement(s) have no obligation_refs"})
    uncertain = sum(item.basis in ("assumed", "unknown") for item in m.scope_facts(declared.scope))
    if uncertain:
        warnings.append({"at": "scope", "problem": f"{uncertain} fact occurrence(s) are assumed or unknown and stay review gaps"})
    if previous is not None:
        from . import history
        try:
            prior = history.load_run(previous)[0]
        except r.RevalidationError as error:
            errors.append({"at": "--previous", "problem": f"predecessor run is unusable ({error.code})"})
        else:
            if (prior.project_id, prior.synthetic) != (declared.project_id, declared.synthetic):
                errors.append({"at": "--previous", "problem": "predecessor belongs to another project or synthetic class"})
            for problem in history.revision_problems(prior, declared):
                at, detail = problem.split(": ", 1)
                errors.append({"at": at, "problem": detail})
    report["valid"] = not errors
    report["counts"] = {"requirements": len(declared.requirements), "obligations": len(declared.obligations),
                        "source_targets": len(declared.source_targets), "sources": len(declared.sources),
                        "evidence": len(declared.evidence), "family_screenings": len(declared.family_screenings)}
    return report


def format_check(report: dict) -> str:
    lines = ["declarations: " + ("valid" if report["valid"] else f"invalid ({len(report['errors'])} problem(s))")]
    if "counts" in report:
        lines.append("counts: " + ", ".join(f"{value} {key}" for key, value in report["counts"].items()))
    lines += [f"error   {item['at']}: {item['problem']}" for item in report["errors"]]
    lines += [f"warning {item['at']}: {item['problem']}" for item in report["warnings"]]
    lines += [f"file    {item['at']}: {item['availability']}, {item['observed_digest'] or 'no digest'}"
              + ("" if item["matches_declared"] else " (differs from declared)") for item in report["files"]]
    lines += [f"target  {item['at']} {item['id']}: {item['fetch']}" for item in report["targets"]]
    lines.append("A valid declaration is not a compliance conclusion.")
    return "\n".join(lines)
