"""Verify one explicit predecessor and compare recorded dependencies without changing it."""

from pathlib import Path
import json

from . import models as m, revalidation as r


def _parse(record, raw):
    r._check_json_depth(raw)
    json.loads(raw, object_pairs_hook=r._pairs, parse_float=r._finite, parse_constant=r._reject_constant)
    return m.parse_record(record, raw)


def load_run(path, deadline=None):
    """Read only marker-listed files, with the workflow's byte and time bounds."""
    r._primitives()
    try:
        with r._parent(Path(path) / "complete.json") as (fd, _):
            marker_file = r._read_file(fd, "complete.json", limit=64 * 1024, retain=True, deadline=deadline)
            if marker_file.availability != "available":
                raise r.RevalidationError("incomplete-run")
            marker = _parse(m.RunCompletion, marker_file.content)
            files, total = {}, 0
            for item in marker.files:
                limit = (r.MAX_REPORT_BYTES if item.path == "report.md" else r.MAX_FILE_BYTES
                         if item.path.startswith("sources/") else m.MAX_REQUEST_BYTES)
                observed = r._read_file(fd, item.path, limit=min(limit, r.MAX_TOTAL_BYTES - total),
                    retain=item.path in {"input.json", "manifest.json", "bundle.json", "comparison.json"}, deadline=deadline)
                total += observed.size
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
            return bundle, files["bundle.json"].digest
    except FileNotFoundError:
        raise r.RevalidationError("incomplete-run") from None
    except OSError:
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
    records["runtime", "config"] = bundle.manifest.config_digest
    records["runtime", "tools"] = bundle.manifest.tool_versions
    return records


def validate_revisions(previous, declared):
    """Versioned semantic records cannot be edited in place or roll backwards."""
    old = previous.declarations
    groups = lambda value: [value.scope, *m.scope_facts(value.scope), *value.requirements,
        *value.source_targets, *(item.source for item in value.sources), *value.obligations,
        *value.controls, *value.applicability_decisions, *value.evidence_reviews]
    records = {(type(item).__name__, item.id): item for item in groups(old)}
    for item in groups(declared):
        prior = records.get((type(item).__name__, item.id))
        if prior is None:
            continue
        exclude = {"retrieved_at"} if isinstance(item, m.LegalSource) else set()
        if item.revision < prior.revision or (item.revision == prior.revision
                and item.model_dump(exclude=exclude) != prior.model_dump(exclude=exclude)):
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


def compare(previous, current, previous_digest):
    """Retain comparison proof and downgrade affected effective claims, leaving declarations intact."""
    before, after = _records(previous), _records(current)
    fresh_targets = {item.source_target_id for item in current.source_attempts if item.retrieved_source}
    for key in before.keys() & after.keys():
        if key[0] == "source_bytes" and key[1] not in fresh_targets:
            after[key] = before[key]  # A failed/offline refresh cannot compare fallback bytes as a fresh observation.
    changes = []
    changed = set()
    for key in sorted(before.keys() | after.keys()):
        if (key in before) == (key in after) and before.get(key) == after.get(key):
            continue
        changes.append(m.DependencyChange(kind=key[0], identity=key[1],
            before=m.content_digest(r._json_bytes(before[key])) if key in before else None,
            after=m.content_digest(r._json_bytes(after[key])) if key in after else None))
        # Lost observations establish uncertainty; declared removals are compared independently.
        if key[0] != "evidence_availability" and not (key[0] == "file" and key not in after):
            changed.add(key)
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
    for disposition in previous.obligation_dispositions:
        identity = disposition.obligation_id
        dependencies, complete, source_ids, evidence_ids, targets = _dependencies(previous, current, identity)
        relevant = sorted(changed & dependencies if complete else changed)
        reasons = []
        if relevant:
            reasons.append("Recorded dependencies changed; renew dependent reviews.")
            invalidated.add(identity)
        if not complete:
            reasons.append("Dependency attribution is incomplete; historical support cannot be renewed.")
            invalidated.add(identity)
        if any(key not in evidence or evidence[key].availability != "available" for key in evidence_ids):
            reasons.append("Dependent evidence is unavailable; current observation is unknown.")
        if any(key not in sources or not sources[key].file
               or observed_files.get(sources[key].file.path) != sources[key].source.content_digest for key in source_ids):
            reasons.append("Dependent source bytes are unavailable or changed.")
        if any(key not in attempts or attempts[key].state != "retrieved"
               or attempts[key].retrieval.comparison != "same_bytes"
               or attempts[key].retrieval.admission != "accepted" for key in targets):
            reasons.append("Current source freshness is unknown: offline, failed, changed or unconfirmed retrieval.")
        freshness = "stale" if relevant else "unknown" if reasons else "current_for_recorded_inputs"
        if not reasons:
            reasons.append("Only recorded dependencies match; bytes renew neither legal currency nor reviewer approval.")
        overlays.append(m.CurrentAssessment(id=r._derived_id("current", f"{current.run.id}:{disposition.id}"), revision=0,
            project_id=current.project_id, historical_run_id=previous.run.id, obligation_disposition_id=disposition.id,
            expected_manifest_id=previous.manifest.id, observed_manifest_id=current.manifest.id,
            checked_at=current.run.ended_at, freshness=freshness, reasons=reasons,
            changed_dependencies=[f"{kind}:{key}" for kind, key in relevant], comparison_evidence_ids=[proof.id]))
        if freshness != "current_for_recorded_inputs":
            gaps.append(f"Historical obligation {identity}: {freshness}. " + " ".join(reasons))
    data = current.model_dump(mode="json")
    data["comparison"] = comparison.model_dump(mode="json")
    data["current_assessments"] = [item.model_dump(mode="json") for item in overlays]
    data["evidence"].append(proof.model_dump(mode="json"))
    data["run"]["parent_run_id"] = previous.run.id
    for decision in data["effective_applicability_decisions"]:
        if decision["obligation"]["id"] in invalidated:
            decision.update(id=r._derived_id("unresolved", decision["obligation"]["id"]), applicability="unresolved")
            decision["gaps"].append("Predecessor dependencies changed or incomplete; accountable review must be renewed.")
    for disposition in data["obligation_dispositions"]:
        if disposition["obligation_id"] in invalidated:
            disposition.update(applicability="unresolved", manual_review="unresolved",
                applicability_decision_id=r._derived_id("unresolved", disposition["obligation_id"]))
            for method in disposition["required_method_dispositions"]:
                if method["method"] != "technical":
                    method["outcome"] = "unresolved_review"
                    method["missing_evidence"].append("Renew review for changed or incomplete predecessor dependencies.")
    for assessment in data["requirement_assessments"]:
        requirement = next(item for item in current.declarations.requirements if item.id == assessment["requirement"]["id"])
        if any(pin.id in invalidated for pin in requirement.obligation_refs):
            assessment["state"] = "unresolved"
            assessment["gaps"].append("Mapped historical dependencies changed or incomplete; renew review.")
            assessment["next_actions"].append("Obtain accountable review of the changed dependency comparison.")
    for screening in data["family_screenings"]:
        # shortcut: family attestations lack complete dependency lists; renew all after any known change.
        if changed and screening["applicability"] != "unresolved":
            screening["applicability"] = "unresolved"
            reason = f"Family {screening['family']}: comparison changed; renew family screening with complete dependency attribution."
            screening["gaps"].append(reason)
            gaps.append(reason)
    if gaps:
        data["gaps"].extend(gaps)
        data["next_actions"].append("Review comparison.json and renew affected reviews; preserve predecessor artifacts.")
        data["run"].update(state="partial", gaps=data["gaps"])
    return m.RevalidationBundle.model_validate(data)
