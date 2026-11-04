"""Help authors write declarations: a valid starter file and located, value-free diagnostics.

Diagnostics name JSON locations, error kinds and digests only; they never echo
declared values, file contents or evidence. Checking is not a legal assessment.
"""
from __future__ import annotations

import codecs
from datetime import date
import errno
from functools import cache
import json
import os
from pathlib import Path
import re
from typing import Literal, get_args, get_origin

from pydantic import ValidationError

from . import models as m, revalidation as r

DEFAULT_PATH = ".eu-compliance-guard/declarations.json"
MAX_PROBLEMS = 50
ENCODING = "declarations must be UTF-8 JSON without a byte-order mark"
RUN_CAPACITY = ("a run of these declarations would exceed the output limits (5,000 gaps or items per list, "
                "50,000 items in all, 16 MiB per bundle or report); declare fewer or smaller records")
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


def starter(project_id: str, assessment_date: str | None = None, jurisdictions: list[str] | None = None,
            synthetic: bool = False, files_root: str = "project") -> m.RevalidationInput:
    """The smallest valid declaration: scope only, every register empty and therefore an explicit gap."""
    return m.RevalidationInput.model_validate({
        "schema_version": 1, "project_id": project_id, "synthetic": synthetic,
        "declaration_run_id": "declarations", "declaration_manifest_id": "declarations",
        "files_root": files_root,
        "scope": {"id": "scope", "revision": 0, "project_id": project_id,
                  "assessment_date": date.today().isoformat() if assessment_date is None else assessment_date, "environment": "production",
                  "activities": [], "establishment": [], "markets": [], "customer_types": [], "roles": [],
                  "size_and_sector": [], "jurisdictions": jurisdictions or ["EU"], "included_scenarios": [],
                  "exclusions": [], "permission_id": "declared-scope"},
    })


def init(path: str | os.PathLike, project_id: str, **options) -> Path:
    """Write a starter declaration; an existing file is never replaced, and a failed write leaves nothing behind."""
    if os.fspath(path).endswith(os.sep):
        raise r.RevalidationError("invalid-input")  # names a folder; Path() would drop the slash and write a file
    path = Path(path)
    # Paths resolve against the project (the parent) only for the dedicated subfolder;
    # anywhere else that parent could be a folder of several projects.
    root = "project" if path.parent.name == ".eu-compliance-guard" else "declarations_dir"
    record = starter(project_id, files_root=root, **options)
    content = (json.dumps(record.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    r._primitives()
    try:
        _create(Path(os.path.abspath(path.parent)), path.name, content)
    except OSError as error:
        # O_NOFOLLOW reports a symlinked (or non-folder) path component as ELOOP or ENOTDIR.
        raise r.RevalidationError("unsafe-path" if error.errno in (errno.ELOOP, errno.ENOTDIR) else "io-failed") from None
    return path


def _create(folder: Path, name: str, content: bytes) -> None:
    """Create the missing folders, then the file exclusively, never through a symlink.

    If anything fails, the file and the folders this call created are removed again.
    """
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    folders, created = [os.open("/", flags)], []
    try:
        for part in folder.parts[1:]:
            try:
                next_fd = os.open(part, flags, dir_fd=folders[-1])
            except FileNotFoundError:
                os.mkdir(part, 0o777, dir_fd=folders[-1])
                created.append((folders[-1], part))
                next_fd = os.open(part, flags, dir_fd=folders[-1])
            folders.append(next_fd)
        try:
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o644, dir_fd=folders[-1])
        except FileExistsError:
            raise r.RevalidationError("output-exists") from None
        try:
            with open(fd, "wb", closefd=False) as handle:
                handle.write(content)
        except BaseException:
            os.unlink(name, dir_fd=folders[-1])
            raise
        finally:
            os.close(fd)
    except BaseException:
        for parent_fd, part in reversed(created):
            try:
                os.rmdir(part, dir_fd=parent_fd)
            except OSError:
                pass
        raise
    finally:
        for folder_fd in folders:
            os.close(folder_fd)


def project_id(path: str | os.PathLike) -> str:
    """The declared project identifier, read without requiring the rest of the file to be valid."""
    r._primitives()
    try:
        with r._parent(path) as (fd, name):
            observed = r._read_file(fd, name, limit=m.MAX_REQUEST_BYTES, retain=True)
    except FileNotFoundError:
        raise r.RevalidationError("io-failed") from None  # no declarations here; unsafe-path means a link or refusal
    except OSError:
        raise r.RevalidationError("unsafe-path") from None
    if observed.availability != "available":
        raise r.RevalidationError("io-failed" if observed.availability == "missing" else "unsafe-path")
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


@cache
def _field_names() -> frozenset[str]:
    """Every field name the record models define: the only key text a diagnostic may print."""
    names, pending = set(), [m.Record]
    while pending:
        model = pending.pop()
        names.update(model.model_fields)
        pending.extend(model.__subclasses__())
    return frozenset(names)


@cache
def _fixed_keys() -> dict[str, frozenset[str]]:
    """The keys a field's dict takes from a fixed vocabulary (a Literal), by field name.

    These keys are public words, so a diagnostic may print them; free-form dict keys stay hidden.
    """
    keys, pending, seen = {}, [m.Record], set()
    while pending:
        model = pending.pop()
        if model in seen:
            continue
        seen.add(model)
        pending.extend(model.__subclasses__())
        for name, field in model.model_fields.items():
            annotations = [field.annotation]
            while annotations:
                annotation = annotations.pop()
                arguments = get_args(annotation)
                if get_origin(annotation) is dict and get_origin(arguments[0]) is Literal:
                    keys[name] = keys.get(name, frozenset()) | frozenset(get_args(arguments[0]))
                annotations.extend(argument for argument in arguments if not isinstance(argument, str))
    return keys


def _location(loc, kind: str = "") -> str:
    text = ""
    for index, part in enumerate(loc):
        if isinstance(part, int):
            text += f"[{part}]"
            continue
        # Any other key comes from the input and is never printed, even when it looks like a field
        # name: an extra key is unknown where it stands.
        known = (part in _field_names() or (index and part in _fixed_keys().get(loc[index - 1], ()))) \
            and not (kind == "extra_forbidden" and index == len(loc) - 1)
        text += ("." if text else "") + (part if known else "(unknown field)")
    return text or "(document)"


def check(path: str | os.PathLike, previous: str | os.PathLike | None = None) -> dict:
    """Validate a declaration and observe its selected files, reporting problems by location.

    Every located problem is collected in one pass. With `previous`, also verify that run and
    name every record that needs a higher revision, including records whose pins must follow
    a raised revision. At most MAX_PROBLEMS errors are listed; `total_errors` counts all of them.
    """
    report = _check(path, previous)
    report["total_errors"] = len(report["errors"])
    del report["errors"][MAX_PROBLEMS:]
    return report


def _check(path, previous) -> dict:
    errors, warnings, files, targets, observations = [], [], [], [], {}
    report = {"valid": False, "total_errors": 0, "errors": errors, "warnings": warnings, "files": files, "targets": targets}
    r._primitives()
    try:
        with r._parent(path) as (fd, name):
            try:
                observed = r._read_file(fd, name, limit=m.MAX_REQUEST_BYTES, retain=True)
            except r.RevalidationError as error:
                if error.code != "capacity-exceeded":
                    raise
                errors.append({"at": "(file)", "problem": "declarations file exceeds the 4 MiB limit"})
                return report
            if observed.availability != "available":
                errors.append({"at": "(file)", "problem": "declarations file is " + observed.availability})
                return report
            raw = observed.content
            # json.loads(bytes) would silently accept a byte-order mark or UTF-16/32, which the
            # record parser then rejects at line 1, column 1. JSON text never holds a raw NUL byte.
            if raw.startswith(codecs.BOM_UTF8) or b"\x00" in raw:
                errors.append({"at": "(file)", "problem": ENCODING})
                return report
            try:
                r._check_json_depth(raw)
                json.loads(raw.decode("utf-8"), object_pairs_hook=r._pairs, parse_float=r._finite,
                           parse_constant=r._reject_constant)
            except json.JSONDecodeError as error:
                errors.append({"at": f"line {error.lineno}, column {error.colno}", "problem": "invalid JSON: " + error.msg})
                return report
            except UnicodeDecodeError:
                errors.append({"at": "(file)", "problem": ENCODING})
                return report
            except r.RevalidationError as error:
                errors.append({"at": "(document)", "problem": "JSON nesting deeper than 32 levels" if error.code == "capacity-exceeded"
                               else "duplicate JSON key or non-finite number"})
                return report
            problems = []
            try:
                declared = m.parse_record(m.RevalidationInput, raw, collect=problems)
            except ValidationError as error:
                for detail in error.errors(include_input=False, include_url=False):
                    at, problem = _location(detail["loc"], detail["type"]), detail["msg"].removeprefix("Value error, ")
                    errors.append({"at": at, "problem": problem})
                return report
            # Every cross-reference and bound problem at once, each with its own JSON location.
            errors.extend({"at": at, "problem": problem} for at, problem in problems)
            if not problems:
                observations = _observe_selected(declared, fd, name, errors, warnings, files)
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
                # The refusals sources.fetch applies before any request, in the same order.
                s.allowed_hosts(s.TargetRequest(target.id, target.intended_url, tuple(target.redirect_hosts)))
                if not s.LANGUAGE.fullmatch(target.language):
                    raise s.RetrievalFailure("invalid-language")
            except s.RetrievalFailure as failure:
                state = "not fetchable: " + failure.code
                advice = ("use a plain language tag such as en or de-DE" if failure.code == "invalid-language"
                          else "declare a manually downloaded copy as a selected source instead")
                warnings.append({"at": f"source_targets[{index}]", "problem": "--fetch-official will refuse this target ("
                                 + failure.code + "); " + advice})
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
    prior = None
    if previous is not None:
        revisions, prior = _previous_problems(declared, previous)
        errors.extend(revisions)
        if prior is not None:
            from . import history
            for problem in history.renewal_problems(prior[0], declared):
                at, detail = problem.split(": ", 1)
                warnings.append({"at": at, "problem": detail})
    if not errors:
        errors.extend(_run_problems(declared, observations, observed.digest, prior))
    report["valid"] = not errors
    report["counts"] = {"requirements": len(declared.requirements), "obligations": len(declared.obligations),
                        "source_targets": len(declared.source_targets), "sources": len(declared.sources),
                        "evidence": len(declared.evidence), "family_screenings": len(declared.family_screenings)}
    return report


def _observe_selected(declared: m.RevalidationInput, fd: int, name: str, errors: list, warnings: list, files: list) -> dict:
    """Observe each selected file of a declaration whose records are consistent, by path."""
    try:
        r._load(fd, name)
    except r.RevalidationError:
        errors.append({"at": "obligations", "problem": "duplicate required methods, an unknown method name, "
                       "or an identifier that collides with a derived disposition/unresolved identifier"})
    sources = {item.file.path for item in declared.sources if item.file}
    # Each selected source is screened with its own media type and charset, as a run does;
    # origins and evidence are never screened as source content.
    selected = [(f"sources[{index}].file", item.file.path, item.file.digest, item)
                for index, item in enumerate(declared.sources) if item.file]
    selected += [(f"requirements[{index}].origin", item.origin.path, item.origin.digest, None)
                 for index, item in enumerate(declared.requirements) if item.origin]
    selected += [(f"evidence[{index}].path", item.path, item.evidence.digest, None)
                 for index, item in enumerate(declared.evidence) if item.path]
    # Code evidence written by `ground --apply` (its id is derived from its path): when the code
    # changes, its facts return to review. Any other evidence keeps its digest error.
    from .grounding import code_evidence_id
    grounded = {f"evidence[{index}].path" for index, item in enumerate(declared.evidence)
                if item.path and item.evidence.id == code_evidence_id(item.path)}
    total, observations = 0, {}
    with r.files_root(declared, fd) as root_fd:
        for at, relative, digest, source in selected:
            try:
                seen = r._read_file(root_fd, relative, limit=min(r.MAX_FILE_BYTES, r.MAX_TOTAL_BYTES - total),
                                    retain=relative in sources)
            except r.RevalidationError as error:
                errors.append({"at": at, "problem": "selected file exceeds the 8 MiB per-file or 64 MiB total limit"
                               if error.code == "capacity-exceeded" else "selected file could not be read safely"})
                continue
            total += seen.size
            observations.setdefault(relative, seen)
            entry = {"at": at, "availability": seen.availability, "observed_digest": seen.digest,
                     "matches_declared": seen.digest == digest}
            files.append(entry)
            if seen.availability != "available":
                base = "project folder" if declared.files_root == "project" else "declarations file's folder"
                errors.append({"at": at, "problem": f"selected file is {seen.availability} (paths resolve "
                               f"relative to the {base})"})
            elif seen.digest != digest and at in grounded:
                # Only an owner-confirmed line re-pins it; copying the new digest would confirm nothing.
                warnings.append({"at": at, "problem": "grounded code changed, so this evidence is unavailable and its "
                                 "gaps return until the owner confirms a line again with ground --apply <fact>=<path>:<line>"})
            elif seen.digest != digest:
                errors.append({"at": at, "problem": "declared digest differs from the file; observed " + seen.digest})
            elif source is not None and seen.content is not None:
                admission = r.admit_source_content(seen.content, source.media_type, source.charset)
                if admission.state != "accepted":
                    warnings.append({"at": at, "problem": f"source content needs review ({admission.reason})"})
    return observations


def _previous_problems(declared: m.RevalidationInput, previous) -> tuple[list[dict], tuple | None]:
    """Verify the predecessor and name every record that needs a higher revision or a pin update.

    Also returns the predecessor run and its bundle digest when it is a usable baseline.
    """
    from . import history
    try:
        prior = history.load_run(previous)
    except r.RevalidationError as error:
        return [{"at": "--previous", "problem": f"predecessor run is unusable ({error.code})"}], None
    # As in revalidate, another project's run is never a revision baseline.
    if (prior[0].project_id, prior[0].synthetic) != (declared.project_id, declared.synthetic):
        return [{"at": "--previous", "problem": "predecessor belongs to another project or synthetic class"}], None
    problems = []
    for problem in history.revision_problems(prior[0], declared):
        at, detail = problem.split(": ", 1)
        problems.append({"at": at, "problem": detail})
    return problems + _revision_cascade(prior[0].declarations, declared, {item["at"] for item in problems}), prior


def _run_problems(declared: m.RevalidationInput, observations: dict, input_digest: str, prior: tuple | None) -> list[dict]:
    """Assemble, in memory only, the offline run revalidate would publish, so an output limit is reported now.

    Identifiers have the lengths revalidate uses; nothing is written or fetched. Records fetched
    with --fetch-official can still add to a run.
    """
    from datetime import datetime, timezone
    from . import history
    from .report import render_report
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        bundle = r.assemble(declared, observations, input_digest=input_digest, timestamp=timestamp,
                            run_id="run-" + "0" * 32, manifest_id="manifest-" + "0" * 32)
        if prior is not None:
            bundle = history.compare(prior[0], bundle, prior[1])
        report = render_report(bundle)
    except ValidationError as error:
        code = r._output_validation_error(error).code
    except r.RevalidationError as error:
        code = error.code
    except ValueError as error:
        code = "capacity-exceeded" if error.args == ("report-too-large",) else "invalid-output"
    else:
        too_large = len(m.canonical_json(bundle)) > m.MAX_BUNDLE_BYTES or len(report.encode("utf-8")) > r.MAX_REPORT_BYTES
        code = "capacity-exceeded" if too_large else None
    if code is None:
        return []
    return [{"at": "(document)", "problem": RUN_CAPACITY if code == "capacity-exceeded" else f"revalidate would fail ({code})"}]


def _versioned(declared: m.RevalidationInput) -> dict:
    """Versioned records by (kind, identifier), the kinds history.revision_problems names."""
    records = {}
    for item in (declared.scope, *m.scope_facts(declared.scope), *declared.requirements, *declared.source_targets,
                 *(selected.source for selected in declared.sources), *declared.obligations, *declared.controls,
                 *declared.applicability_decisions, *declared.evidence_reviews):
        records.setdefault((type(item).__name__, item.id), item)
    return records


def _pin_holders(declared: m.RevalidationInput):
    """Each record that pins versioned records: (name, versioned key or None, [(kind, id, pinned revision)])."""
    def sources(provisions):
        return [("LegalSource", pin.source_id, pin.revision) for pin in provisions if pin.source_id is not None]

    def facts(pins):
        return [("Fact", pin.id, pin.revision) for pin in pins]

    scope = declared.scope
    # A scope embeds its facts, so a fact's new revision changes the scope too.
    embedded = {fact.id: fact for fact in m.scope_facts(scope)}.values()
    yield f"Scope {scope.id}", ("Scope", scope.id), [("Fact", fact.id, fact.revision) for fact in embedded]
    for item in declared.requirements:
        yield (f"DeclaredRequirement {item.id}", ("DeclaredRequirement", item.id),
               [*facts(item.fact_refs), *(("Obligation", pin.id, pin.revision) for pin in item.obligation_refs)])
    for index, item in enumerate(declared.source_reviews):
        yield f"source_reviews[{index}]", None, [("LegalSource", item.source_id, item.source_revision)]
    for item in declared.obligations:
        yield f"Obligation {item.id}", ("Obligation", item.id), sources(item.source_provisions)
    for index, item in enumerate(declared.family_screenings):
        yield (f"family_screenings[{index}]", None, [("Scope", item.scope.id, item.scope.revision), *facts(item.fact_refs),
               *(("LegalSource", pin.id, pin.revision) for pin in item.source_refs)])
    for item in declared.applicability_decisions:
        yield (f"ApplicabilityDecision {item.id}", ("ApplicabilityDecision", item.id),
               [("Obligation", item.obligation.id, item.obligation.revision), ("Scope", item.scope.id, item.scope.revision),
                *facts(item.fact_refs), *sources(item.provisions)])
    for item in declared.evidence_reviews:
        yield (f"EvidenceReview {item.id}", ("EvidenceReview", item.id),
               [("Obligation", item.obligation.id, item.obligation.revision)])


def _revision_cascade(old: m.RevalidationInput, declared: m.RevalidationInput, reported: set[str]) -> list[dict]:
    """Name each record whose pins must follow a revision that rises, before that edit is made.

    A record pinning a raised revision changes too, so a versioned one also needs a higher
    revision. Records already named by their own revision problem are not repeated.
    """
    before, current = _versioned(old), _versioned(declared)
    # Any revision above the predecessor's is accepted; a record named above needs the next one.
    target = {key: before[key].revision + 1 if key in before and f"{key[0]} {key[1]}" in reported else item.revision
              for key, item in current.items()}
    holders = list(_pin_holders(declared))

    def moving(pins):
        return list(dict.fromkeys((kind, identity) for kind, identity, revision in pins
                                  if (kind, identity) in target and target[kind, identity] != revision))

    changed = True
    while changed:  # Each record rises at most once, so this ends.
        changed = False
        for _, key, pins in holders:
            if key in before and target[key] <= before[key].revision and moving(pins):
                target[key] = before[key].revision + 1
                changed = True
    problems, named = [], set(reported)
    for label, key, pins in holders:
        dependencies = moving(pins)
        raise_to = target[key] if key in before and target[key] > current[key].revision else None
        if raise_to is None:
            # A pin already behind its record's declared revision is reported where it stands.
            stale = {(kind, identity) for kind, identity, revision in pins
                     if (kind, identity) in current and current[kind, identity].revision != revision}
            dependencies = [item for item in dependencies if item not in stale]
        if not dependencies or label in named:
            continue
        named.add(label)
        kind, identity = dependencies[0]
        text = f"{kind} {identity} rises to revision {target[kind, identity]}"
        if len(dependencies) > 1:
            more = len(dependencies) - 1
            text += f" (and {more} more pinned record{'s' if more > 1 else ''}); update the pins to them"
        else:
            text += "; update the pin to it"
        if raise_to is not None:
            text += f" and raise this record's revision to {raise_to}"
        problems.append({"at": label, "problem": text})
    return problems


def format_check(report: dict) -> str:
    total, listed = report["total_errors"], len(report["errors"])
    lines = ["declarations: " + ("valid" if report["valid"] else f"invalid ({total} problem(s)"
                                 + (f"; the first {listed} are listed)" if total > listed else ")"))]
    if "counts" in report:
        lines.append("counts: " + ", ".join(f"{value} {key}" for key, value in report["counts"].items()))
    lines += [f"error   {item['at']}: {item['problem']}" for item in report["errors"]]
    lines += [f"warning {item['at']}: {item['problem']}" for item in report["warnings"]]
    lines += [f"file    {item['at']}: {item['availability']}, {item['observed_digest'] or 'no digest'}"
              + ("" if item["matches_declared"] else " (differs from declared)") for item in report["files"]]
    lines += [f"target  {item['at']} {item['id']}: {item['fetch']}" for item in report["targets"]]
    lines.append("A valid declaration is not a compliance conclusion.")
    return "\n".join(lines)
