"""Verify one explicit predecessor and compare recorded dependencies without changing it."""

from datetime import datetime, timezone
from pathlib import Path
import json
import os

from . import models as m, revalidation as r


def _parse(record, raw):
    r._check_json_depth(raw)
    json.loads(raw, object_pairs_hook=r._pairs, parse_float=r._finite, parse_constant=r._reject_constant)
    return m.parse_record(record, raw, m.MAX_BUNDLE_BYTES)


def load_run(path, deadline=None, sources_out=None):
    """Read only marker-listed files, with the workflow's byte and time bounds.

    With ``sources_out`` (a dict), digest-verified ``sources/*.bin`` bytes are copied into it.
    A path that names no directory, or a file that cannot be opened safely (permissions,
    symbolic links, non-regular files), is ``unsafe-path``: the run may be intact. Only an
    existing directory without a marker is incomplete, and only failed integrity is corrupt.
    """
    r._primitives()
    if not os.fspath(path):
        raise r.RevalidationError("unsafe-path")  # Never fall back to the working directory.
    try:
        with r._parent(Path(path) / "complete.json") as (fd, _):
            marker_file = r._read_file(fd, "complete.json", limit=64 * 1024, retain=True, deadline=deadline)
            if marker_file.availability == "blocked":
                raise r.RevalidationError("unsafe-path")
            if marker_file.availability != "available":
                raise r.RevalidationError("incomplete-run")
            marker = _parse(m.RunCompletion, marker_file.content)
            files, total = {}, 0
            for item in marker.files:
                limit = (r.MAX_REPORT_BYTES if item.path == "report.md" else r.MAX_FILE_BYTES
                         if item.path.startswith("sources/") else m.MAX_BUNDLE_BYTES)
                observed = r._read_file(fd, item.path, limit=min(limit, r.MAX_TOTAL_BYTES - total),
                    retain=item.path in {"input.json", "manifest.json", "bundle.json", "comparison.json"}
                    or (sources_out is not None and item.path.startswith("sources/")), deadline=deadline)
                total += observed.size
                if observed.availability == "blocked":
                    raise r.RevalidationError("unsafe-path")
                if observed.availability != "available" or observed.digest != item.digest:
                    raise r.RevalidationError("corrupt-run")
                files[item.path] = observed
            bundle = _parse(m.RevalidationBundle, files["bundle.json"].content)
            manifest = _parse(m.InputManifest, files["manifest.json"].content)
            declared = _parse(m.RevalidationInput, files["input.json"].content)
            if (bundle.run.id != marker.run_id or manifest != bundle.manifest or declared != bundle.declarations
                    or manifest.digest != m.content_digest(r._json_bytes(manifest.model_dump(mode="json", exclude={"digest"})))):
                raise r.RevalidationError("corrupt-run")
            if ("comparison.json" in files) != (bundle.comparison is not None):
                raise r.RevalidationError("corrupt-run")
            if bundle.comparison is not None and files["comparison.json"].content != m.canonical_json(bundle.comparison):
                raise r.RevalidationError("corrupt-run")
            required = {item.retrieval.artifact_path for item in bundle.source_attempts if item.retrieval.artifact_path}
            sources = {item.source.id: item.source for item in declared.sources}
            reviews = {item.source_id: item for item in declared.source_reviews}
            pending = [pin.source_id for decision in bundle.effective_applicability_decisions
                       if decision.applicability != "unresolved" for pin in decision.provisions if pin.source_id]
            pending.extend(pin.id for screening in bundle.family_screenings
                           if screening.applicability != "unresolved" for pin in screening.source_refs)
            seen = set()
            while pending:
                identity = pending.pop()
                if identity in seen:
                    continue
                seen.add(identity)
                source = sources[identity]
                required.add("sources/" + source.content_digest.removeprefix("sha256:") + ".bin")
                pending.extend(source.related_source_ids)
                review = reviews.get(identity)
                if review:
                    pending.extend([*review.act_chain, *review.case_law_refs, *review.national_overlay_ids])
            if not required <= files.keys():
                raise r.RevalidationError("corrupt-run")
            if sources_out is not None:
                sources_out.update((key, item.content) for key, item in files.items() if key.startswith("sources/"))
            return bundle, files["bundle.json"].digest
    except OSError:
        # Includes a missing run directory: a wrong path is not an incomplete run.
        raise r.RevalidationError("unsafe-path") from None
    except r.RevalidationError as error:
        if error.code in {"invalid-input", "invalid-output"}:
            raise r.RevalidationError("corrupt-run") from None
        raise
    except (ValueError, RecursionError, KeyError):
        # Invalid data never becomes an untrusted diagnostic or a usable predecessor.
        raise r.RevalidationError("corrupt-run") from None


def _records(bundle):
    declared = bundle.declarations
    records = {("scope", declared.scope.id): declared.scope.model_dump(mode="json", exclude={"activities", "roles", "size_and_sector"})}
    for kind, items in (("fact", m.scope_facts(declared.scope)), ("activity", declared.scope.activities),
            ("requirement", declared.requirements), ("target", declared.source_targets),
            ("obligation", declared.obligations), ("control", declared.controls),
            ("decision", declared.applicability_decisions), ("evidence_review", declared.evidence_reviews)):
        records.update(((kind, item.id), item.model_dump(mode="json")) for item in items)
    for selected in declared.sources:
        identity = selected.source.id
        records["source", identity] = selected.source.model_dump(mode="json", exclude={"retrieved_at"})
        records["source_selection", identity] = selected.model_dump(mode="json", exclude={"source"})
    records.update((("source_review", item.source_id), item.model_dump(mode="json")) for item in declared.source_reviews)
    records.update((("family", item.family), item.model_dump(mode="json")) for item in declared.family_screenings)
    for selected in declared.evidence:
        identity = selected.evidence.id
        records["evidence", identity] = selected.evidence.model_dump(mode="json", exclude={"run_id", "manifest_id"})
        records["evidence_path", identity] = selected.path
    declared_ids = {item.evidence.id for item in declared.evidence}
    for item in bundle.evidence:
        if item.id in declared_ids:
            records["evidence_bytes", item.id] = item.digest
            records["evidence_availability", item.id] = item.availability
    records.update((("file", item.path), item.digest) for item in bundle.manifest.source_files)
    observed = {item.source_target_id: item.retrieval.digest for item in bundle.source_attempts if item.retrieved_source}
    for selected in declared.sources:
        observed.setdefault(selected.target_id, selected.source.content_digest)
    records.update((("source_bytes", identity), digest) for identity, digest in observed.items())
    # Offline and fetch runs of one tool version differ only in how sources were observed; fetched
    # bytes are compared separately, so the network mode alone is not a changed dependency.
    policies = {m.content_digest(r._json_bytes(policy)) for policy in (r.POLICY, r.fetch_policy())}
    config = bundle.manifest.config_digest
    records["runtime", "config"] = "policy:" + r.__version__ if config in policies else config
    records["runtime", "tools"] = bundle.manifest.tool_versions
    return records


def revision_problems(previous, declared) -> list[str]:
    """Each versioned record edited in place or rolled back, named by kind and identifier only."""
    old = previous.declarations
    groups = lambda value: [value.scope, *m.scope_facts(value.scope), *value.requirements,
        *value.source_targets, *(item.source for item in value.sources), *value.obligations,
        *value.controls, *value.applicability_decisions, *value.evidence_reviews]
    records = {(type(item).__name__, item.id): item for item in groups(old)}
    problems = []
    for item in groups(declared):
        prior = records.get((type(item).__name__, item.id))
        if prior is None:
            continue
        exclude = {"retrieved_at"} if isinstance(item, m.LegalSource) else set()
        if item.revision < prior.revision:
            problem = f"{type(item).__name__} {item.id}: revision {item.revision} is lower than the predecessor's {prior.revision}"
        elif item.revision == prior.revision and item.model_dump(exclude=exclude) != prior.model_dump(exclude=exclude):
            problem = (f"{type(item).__name__} {item.id}: content changed but revision is still {item.revision}; "
                       f"raise it to {prior.revision + 1} and update the pins that reference it")
        else:
            continue
        if problem not in problems:
            problems.append(problem)
    return problems


def validate_revisions(previous, declared):
    """Versioned semantic records cannot be edited in place or roll backwards."""
    if revision_problems(previous, declared):
        raise r.RevalidationError("invalid-revision")


def _dependencies(previous, current, identity):
    keys = {("runtime", "config"), ("runtime", "tools"), ("obligation", identity)}
    complete = True
    source_ids, evidence_ids, target_ids = set(), set(), set()
    for bundle in (previous, current):
        declared = bundle.declarations
        obligations = {item.id: item for item in declared.obligations}
        if identity not in obligations:
            continue
        obligation = obligations[identity]
        keys.update({("scope", declared.scope.id), ("family", obligation.family)})
        keys.update(("control", key) for key in obligation.control_ids)
        decisions = [item for item in declared.applicability_decisions if item.obligation.id == identity]
        requirements = [item for item in declared.requirements if any(pin.id == identity for pin in item.obligation_refs)]
        reviews = [item for item in declared.evidence_reviews if item.obligation.id == identity]
        provisions = [*obligation.source_provisions, *(pin for item in decisions for pin in item.provisions)]
        complete &= bool(decisions and provisions and all(pin.source_id for pin in provisions)
                         and all(item.fact_refs for item in decisions))
        source_ids.update(pin.source_id for pin in provisions if pin.source_id)
        source_ids.update(obligation.overlay_ids)
        target_ids.update(pin.source_target_id for pin in provisions)
        for kind, items in (("decision", decisions), ("requirement", requirements), ("evidence_review", reviews)):
            for item in items:
                keys.add((kind, item.id))
                evidence_ids.update(item.evidence_ids)
        facts = {item.id: item for item in m.scope_facts(declared.scope)}
        for item in [*decisions, *requirements]:
            for pin in item.fact_refs:
                keys.add(("fact", pin.id))
                evidence_ids.update(facts[pin.id].evidence_ids)
        for item in requirements:
            keys.update(("activity", key) for key in item.activity_ids)
            if item.origin:
                keys.add(("file", item.origin.path))
        sources = {item.source.id: item for item in declared.sources}
        source_reviews = {item.source_id: item for item in declared.source_reviews}
        pending, seen = list(source_ids), set()
        while pending:
            key = pending.pop()
            if key in seen or key not in sources:
                continue
            seen.add(key)
            selected = sources[key]
            source_ids.add(key)
            keys.update({("source", key), ("source_selection", key), ("source_review", key)})
            target_ids.add(selected.target_id)
            if selected.file:
                keys.add(("file", selected.file.path))
            review = source_reviews.get(key)
            pending.extend(selected.source.related_source_ids)
            if review:
                pending.extend([*review.act_chain, *review.case_law_refs, *review.national_overlay_ids])
        selected_evidence = {item.evidence.id: item for item in declared.evidence}
        pending, seen = list(evidence_ids), set()
        while pending:
            key = pending.pop()
            if key in seen or key not in selected_evidence:
                continue
            seen.add(key)
            selected = selected_evidence[key]
            evidence_ids.add(key)
            keys.update((kind, key) for kind in ("evidence", "evidence_path", "evidence_bytes", "evidence_availability"))
            if selected.path:
                keys.add(("file", selected.path))
            if selected.evidence.provenance == "independently_verified":
                pending.extend(selected.evidence.source_refs)
    keys.update((kind, key) for key in target_ids for kind in ("target", "source_bytes"))
    return keys, complete, source_ids, evidence_ids, target_ids


MAX_LISTED_CHANGES = 20
FAMILY_WITHDRAWN_GAP = "Predecessor withdrew this family screening; renew it with complete dependency attribution."
INVALIDATED_GAP = "Predecessor dependencies changed or incomplete; accountable review must be renewed."
SAME_RUN_RENEWAL = ("Reviews renewed in the same run as these changes do not count, because they cannot be shown "
                    "to follow them; renew them again after this run.")
WITHDRAWN_DECISION_RATIONALE = "Support withdrawn after the predecessor comparison; effective applicability awaits renewed accountable review."
WITHDRAWN_MAPPING_RATIONALE = "Mapped obligation support withdrawn after the predecessor comparison; renew the mapped reviews."
RENEW_REQUIREMENT_GAP = "Mapped historical dependencies changed or incomplete; renew review."


def _reviewed_between(value, previous, started_at) -> bool:
    """A review time after the predecessor run and no later than this run; future dates never count."""
    return bool(value) and (datetime.fromisoformat(previous.run.ended_at) < datetime.fromisoformat(value)
                            <= datetime.fromisoformat(started_at))


def _attestations(declared) -> dict:
    records = {("decision", item.id): item for item in declared.applicability_decisions}
    records.update((("evidence_review", item.id), item) for item in declared.evidence_reviews)
    records.update((("family", item.family), item) for item in declared.family_screenings)
    return records


def _classify_attestations(previous, declared, started_at) -> tuple[set, set]:
    """Split new or changed review records into renewals and stale attestations.

    A renewal is reviewed between the two runs (and is a higher revision where the record has
    one); it is the review a withdrawal asks for, not a new change. Any other new or changed
    review record cannot carry support, whatever obligation id it is attached to now.
    """
    before, after = _attestations(previous.declarations), _attestations(declared)
    renewals, stale = set(), set()
    for key, item in after.items():
        prior = before.get(key)
        if prior is not None and prior.model_dump() == item.model_dump():
            continue
        newer = prior is None or not hasattr(item, "revision") or item.revision > prior.revision
        (renewals if newer and _reviewed_between(item.reviewed_at, previous, started_at) else stale).add(key)
    return renewals, stale


def _own_attestations(declared, identity) -> set:
    own = {("decision", item.id) for item in declared.applicability_decisions if item.obligation.id == identity}
    return own | {("evidence_review", item.id) for item in declared.evidence_reviews if item.obligation.id == identity}


def _carried(previous) -> tuple[set, set]:
    """Obligations and families whose support the predecessor withdrew; the marker gaps carry it forward."""
    return ({item.obligation.id for item in previous.effective_applicability_decisions if INVALIDATED_GAP in item.gaps},
            {item.family for item in previous.family_screenings if FAMILY_WITHDRAWN_GAP in item.gaps})


def renewal_problems(previous, declared, now: str | None = None) -> list[str]:
    """Withdrawn support these declarations would not restore yet, named by kind and identifier only.

    ``now`` (default: the current time) bounds the renewal window as the next run's start would.
    Changes made together with a renewal are not visible here; the run reports those (SAME_RUN_RENEWAL).
    """
    now = now or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    renewals, _ = _classify_attestations(previous, declared, now)
    obligations, families = _carried(previous)
    problems = []
    for obligation in declared.obligations:
        own = _own_attestations(declared, obligation.id)
        if obligation.id in obligations and not (any(kind == "decision" for kind, _ in own) and own <= renewals):
            problems.append(f"Obligation {obligation.id}: the predecessor withdrew its support; give its applicability "
                            "decision and every evidence review a higher revision and a reviewed_at after that run, "
                            "or support stays withdrawn")
    for screening in declared.family_screenings:
        if (screening.family in families and screening.applicability != "unresolved"
                and ("family", screening.family) not in renewals):
            problems.append(f"Family {screening.family}: the predecessor withdrew this screening; renew it with a "
                            "reviewed_at after that run, or it stays withdrawn")
    return problems


def compare(previous, current, previous_digest):
    """Retain comparison proof and downgrade affected effective claims, leaving declarations intact."""
    before, after = _records(previous), _records(current)
    fresh_targets = {item.source_target_id for item in current.source_attempts if item.retrieved_source}
    for key in before.keys() & after.keys():
        if key[0] == "source_bytes" and key[1] not in fresh_targets:
            after[key] = before[key]  # A failed/offline refresh cannot compare fallback bytes as a fresh observation.
    declared_files = r._selected_files(previous.declarations)
    changes = []
    changed = set()
    for key in sorted(before.keys() | after.keys()):
        if (key in before) == (key in after) and before.get(key) == after.get(key):
            continue
        changes.append(m.DependencyChange(kind=key[0], identity=key[1],
            before=m.content_digest(r._json_bytes(before[key])) if key in before else None,
            after=m.content_digest(r._json_bytes(after[key])) if key in after else None))
        # Lost observations establish uncertainty; declared removals are compared independently.
        # Regaining exactly the bytes the predecessor declared, after it could not read them, is no change.
        lost = key[0] == "file" and key not in after
        regained = key[0] == "file" and key not in before and declared_files.get(key[1]) == after[key]
        if key[0] != "evidence_availability" and not lost and not regained:
            changed.add(key)
    renewals, stale_attestations = _classify_attestations(previous, current.declarations, current.run.started_at)
    changed -= renewals
    comparison = m.DependencyComparison(previous_run_id=previous.run.id, previous_manifest_id=previous.manifest.id,
        previous_bundle_digest=previous_digest, historical_disposition_ids=[item.id for item in previous.obligation_dispositions],
        changes=changes)
    proof = m.Evidence(id=r._derived_id("comparison", current.run.id), project_id=current.project_id,
        run_id=current.run.id, kind="dependency_comparison", provenance="observed",
        digest=m.content_digest(m.canonical_json(comparison)), captured_at=current.run.ended_at,
        manifest_id=current.manifest.id, media_type="application/json", redaction="safe", availability="available",
        source_refs=["comparison.json"])
    if any(item.id == proof.id for item in current.evidence):
        raise r.RevalidationError("invalid-output")
    observed_files = {item.path: item.digest for item in current.manifest.source_files}
    sources = {item.source.id: item for item in current.declarations.sources}
    evidence = {item.id: item for item in current.evidence}
    attempts = {item.source_target_id: item for item in current.source_attempts}
    overlays, invalidated, gaps = [], set(), []
    carried, withdrawn = _carried(previous)
    # What the predecessor's reviewers declared, not what it could observe: a file it could not read
    # leaves its effective decision unresolved, but the attestation still rests on the old dependencies.
    declared_support = {item.obligation.id for item in previous.declarations.applicability_decisions
                        if item.applicability != "unresolved"}
    own_attestations = lambda identity: _own_attestations(current.declarations, identity)

    stale_review = "A new or changed review record is not dated between the predecessor run and this run; record a renewed review."
    historical = {item.obligation_id for item in previous.obligation_dispositions}
    for obligation in current.declarations.obligations:
        # Obligations new to this comparison (including renamed or re-added ones) get no overlay but
        # still cannot rest on review records that were not renewed in this window.
        if obligation.id not in historical and own_attestations(obligation.id) & stale_attestations:
            invalidated.add(obligation.id)
            gaps.append(f"Obligation {obligation.id}: {stale_review}")
    for disposition in previous.obligation_dispositions:
        identity = disposition.obligation_id
        dependencies, complete, source_ids, evidence_ids, targets = _dependencies(previous, current, identity)
        own = own_attestations(identity)
        renewed = any(kind == "decision" for kind, _ in own) and own <= renewals
        relevant = sorted(changed & dependencies if complete else changed)
        reasons = []
        if own & stale_attestations:
            reasons.append(stale_review)
            invalidated.add(identity)
        if identity in carried and not renewed:
            # Invalidation persists across runs; rerunning without renewed reviews must not restore support.
            reasons.append("The predecessor already withdrew this support; it stays withdrawn until the applicability "
                           "decision and every evidence review are new revisions reviewed after the predecessor run.")
            invalidated.add(identity)
        # Only support the predecessor declared (or withdrew) can be withdrawn. An obligation it never
        # decided is decided for the first time here, like a new obligation: only stale attestations count.
        supported = identity in declared_support or identity in carried
        if relevant:
            reasons.append("Recorded dependencies changed; renew dependent reviews.")
            if supported:
                invalidated.add(identity)
                if own & renewals:
                    # Conservative: a review in the same window cannot be shown to follow the change.
                    reasons.append(SAME_RUN_RENEWAL)
        if not complete:
            reasons.append("Dependency attribution is incomplete; historical support cannot be renewed.")
            if supported:
                invalidated.add(identity)
        if any(key not in evidence or evidence[key].availability != "available" for key in evidence_ids):
            reasons.append("Dependent evidence is unavailable; current observation is unknown.")
        if any(key not in sources or not sources[key].file
               or observed_files.get(sources[key].file.path) != sources[key].source.content_digest for key in source_ids):
            reasons.append("Dependent source bytes are unavailable or changed.")
        def confirmed(target):
            attempt = attempts.get(target)
            own = [sources[key].source.content_digest for key in source_ids if key in sources and sources[key].target_id == target]
            return bool(attempt and attempt.state == "retrieved" and attempt.retrieval.admission == "accepted"
                        and own and all(digest == attempt.retrieval.digest for digest in own))
        if not all(confirmed(target) for target in targets):
            reasons.append("Current source freshness is unknown: offline, failed, changed or unconfirmed retrieval.")
        if len(relevant) > MAX_LISTED_CHANGES:
            reasons.append(f"{len(relevant) - MAX_LISTED_CHANGES} more changed dependencies are listed in comparison.json.")
        freshness = "stale" if relevant else "unknown" if reasons else "current_for_recorded_inputs"
        if not reasons:
            reasons.append("Only recorded dependencies match; bytes renew neither legal currency nor reviewer approval.")
        overlays.append(m.CurrentAssessment(id=r._derived_id("current", f"{current.run.id}:{disposition.id}"), revision=0,
            project_id=current.project_id, historical_run_id=previous.run.id, obligation_disposition_id=disposition.id,
            obligation_id=identity,
            expected_manifest_id=previous.manifest.id, observed_manifest_id=current.manifest.id,
            checked_at=current.run.ended_at, freshness=freshness, reasons=reasons,
            changed_dependencies=[f"{kind}:{key}" for kind, key in relevant[:MAX_LISTED_CHANGES]],
            comparison_evidence_ids=[proof.id]))
        if freshness != "current_for_recorded_inputs":
            gaps.append(f"Historical obligation {identity}: {freshness}. " + " ".join(reasons))
    data = current.model_dump(mode="json")
    data["comparison"] = comparison.model_dump(mode="json")
    data["current_assessments"] = [item.model_dump(mode="json") for item in overlays]
    data["evidence"].append(proof.model_dump(mode="json"))
    data["run"]["parent_run_id"] = previous.run.id
    # A withdrawn claim never keeps the reasoning that supported it; the declarations still record it.
    withdrawn_rationale = {}
    for decision in data["effective_applicability_decisions"]:
        if decision["obligation"]["id"] in invalidated:
            if decision["applicability"] != "unresolved":
                decision["rationale"] = withdrawn_rationale[decision["obligation"]["id"]] = WITHDRAWN_DECISION_RATIONALE
            decision.update(id=r._derived_id("unresolved", decision["obligation"]["id"]), applicability="unresolved")
            decision["gaps"].append(INVALIDATED_GAP)
    for disposition in data["obligation_dispositions"]:
        if disposition["obligation_id"] in invalidated:
            disposition["rationale"] = withdrawn_rationale.get(disposition["obligation_id"], disposition["rationale"])
            disposition.update(applicability="unresolved", manual_review="unresolved",
                applicability_decision_id=r._derived_id("unresolved", disposition["obligation_id"]))
            for method in disposition["required_method_dispositions"]:
                if method["method"] != "technical":
                    method["outcome"] = "unresolved_review"
                    method["missing_evidence"].append("Renew review for changed or incomplete predecessor dependencies.")
    for assessment in data["requirement_assessments"]:
        requirement = next(item for item in current.declarations.requirements if item.id == assessment["requirement"]["id"])
        if any(pin.id in invalidated for pin in requirement.obligation_refs):
            if assessment["state"] == "supported":
                assessment["rationale"] = WITHDRAWN_MAPPING_RATIONALE
            assessment["state"] = "unresolved"
            assessment["gaps"].append(RENEW_REQUIREMENT_GAP)
            assessment["next_actions"].append("Obtain accountable review of the changed dependency comparison.")
    declared_families = {item.family for item in previous.declarations.family_screenings if item.applicability != "unresolved"}
    screened = {item.family: item.applicability for item in current.declarations.family_screenings}
    for screening in data["family_screenings"]:
        family = screening["family"]
        if screened.get(family, "unresolved") == "unresolved":
            # No record, or one that now declares no applicability, carries no support to withdraw;
            # declaring support again is a changed record that needs a renewal anyway.
            continue
        renewed = ("family", family) in renewals
        # Like obligations, the marker is carried whatever else leaves the screening unresolved now,
        # and support the predecessor declared is withdrawn even if it could not confirm it then.
        held = screening["applicability"] != "unresolved" or family in declared_families or family in withdrawn
        # shortcut: family attestations lack complete dependency lists; renew all after any known change.
        if (changed and held) or (family in withdrawn and not renewed) or ("family", family) in stale_attestations:
            screening["applicability"] = "unresolved"
            if FAMILY_WITHDRAWN_GAP not in screening["gaps"]:
                screening["gaps"].append(FAMILY_WITHDRAWN_GAP)
            same_run = changed and held and renewed
            gaps.append(f"Family {family}: {FAMILY_WITHDRAWN_GAP}" + (f" {SAME_RUN_RENEWAL}" if same_run else ""))
    if gaps:
        data["gaps"].extend(gaps)
        data["next_actions"].append("Review comparison.json and renew affected reviews; preserve predecessor artifacts.")
        data["run"].update(state="partial", gaps=data["gaps"])
    return m.RevalidationBundle.model_validate(data)
