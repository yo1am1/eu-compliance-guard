"""Pure, bounded Markdown projection of validated revalidation records."""

import json
import unicodedata

from . import models as m

MAX_REPORT_BYTES = 16 * 1024 * 1024


def _text(value: object) -> str:
    if value is None:
        return "not supplied"
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    # Encode punctuation before Markdown parsing, including autolink URL delimiters.
    return "".join(
        f"&#92;u{ord(char):04x}" if unicodedata.category(char).startswith("C") or char.isspace() and char != " "
        else char if char.isalnum() or char == " " else f"&#{ord(char)};"
        for char in value
    )


def render_report(bundle: m.RevalidationBundle) -> str:
    """Render metadata only; selected file bodies never enter this interface."""
    lines = []
    size = 0
    label = "FICTIONAL / SYNTHETIC — " if bundle.synthetic else "Recorded assessment — "

    def emit(line: str = "") -> None:
        nonlocal size
        size += len(line.encode("utf-8")) + 1
        if size > MAX_REPORT_BYTES:
            raise ValueError("report-too-large")
        lines.append(line)

    def field(name: str, value: object) -> None:
        emit(f"- {name}: {_text(value)}")

    def record(title: str, item: m.Record, *, exclude: set[str] | None = None) -> None:
        emit(f"### {label}{title}")
        emit()
        for key, value in item.model_dump(mode="json", exclude=exclude).items():
            field(key.replace("_", " ").capitalize(), value)
        emit()

    declared = bundle.declarations
    fetched = bool(bundle.source_attempts)
    emit("# Requirements-to-law revalidation with selected official-source retrieval" if fetched
         else "# Offline requirements-to-law revalidation")
    emit()
    if bundle.synthetic:
        emit("**FICTIONAL / SYNTHETIC DATA, INCLUDING MIXED DECLARATIONS. Every conclusion below is labelled fictional; none establishes real EU duties.**")
    elif fetched:
        emit("**Recorded local declarations and unauthenticated reviewer attestations. Retrieved official bytes are unreviewed candidates; retrieval establishes neither binding status, completeness, applicability nor currency.**")
    else:
        emit("**Recorded local declarations and unauthenticated reviewer attestations. Offline legal freshness remains unverified.**")
    emit()
    emit("Processing status describes report assembly only. No compliance verdict, legal approval, exhaustive law search or technical test is established.")
    emit("Only explicitly selected local files were considered. Evidence bodies are excluded from this report; metadata and declarations remain private.")
    emit("Recorded processing budgets use cooperative checks; they do not establish a hard CPU/filesystem deadline or process containment.")
    emit()
    emit("## What needs attention and the declared legal basis")
    emit()
    emit("Reviewed evidence deficiencies describe the named reviewer's assessment. Missing evidence and unresolved applicability are review gaps. Neither establishes a legal breach; a not-applicable decision is not a violation.")
    emit("References below are candidate declarations, not extracted or independently verified legal provisions.")
    emit()
    requirements = {item.id: item for item in declared.requirements}
    obligations = {item.id: item for item in declared.obligations}
    assessments = {item.requirement.id: item for item in bundle.requirement_assessments}
    dispositions = {item.obligation_id: item for item in bundle.obligation_dispositions}
    decisions = {item.obligation.id: item for item in bundle.effective_applicability_decisions}
    sources = {item.source.id: item.source for item in declared.sources}
    targets = {item.id: item for item in declared.source_targets}
    reviews = {item.id: item for item in declared.evidence_reviews}
    activities = {item.id: item for item in declared.scope.activities}

    def requirement_context(requirement: m.DeclaredRequirement) -> None:
        field("Project requirement", f"{requirement.id}@{requirement.revision}: {requirement.statement}")
        if requirement.origin:
            field("Declared project location", f"{requirement.origin.path} — {requirement.locator}")
        for identity in requirement.activity_ids:
            field("Declared project activity", f"{identity}: {activities[identity].purpose}")

    def legal_context(obligation: m.Obligation) -> None:
        field("Candidate obligation", f"{obligation.id}@{obligation.revision}: {obligation.classification}; family {obligation.family}")
        for pin in obligation.source_provisions:
            source = sources.get(pin.source_id)
            target = targets[pin.source_target_id]
            if source:
                field("Candidate legal reference", f"{source.identifier or source.id} — {pin.locator}; type {source.type}; source {source.id}@{source.revision}; URL {source.url}")
            else:
                field("Unpinned candidate legal reference", f"{target.intended_identifier or target.id} — {pin.locator}; intended type {target.intended_type}; target {target.id}@{target.revision}; URL {target.intended_url}")
        if not obligation.source_provisions:
            field("Legal reference gap", "No provision locator declared; identify and review a candidate source before drawing a legal conclusion.")
        decision = decisions[obligation.id]
        field("Effective applicability", f"{decision.applicability}; decision {decision.id}@{decision.revision}; assessment date {decision.assessment_date}")
        field("Applicability reasoning", decision.rationale)
        field("Applicability reviewer", decision.reviewer)
        field("Applicability reviewed at", decision.reviewed_at)
        field("Applicability evidence references", decision.evidence_ids)
        field("Applicability gaps", decision.gaps)

    for obligation in declared.obligations:
        disposition = dispositions[obligation.id]
        pending = [item for item in disposition.required_method_dispositions if item.outcome != "passed"]
        if not pending and disposition.required_method_dispositions and decisions[obligation.id].applicability != "unresolved":
            continue
        for method in pending or [None]:
            deficiency = method is not None and method.outcome == "observed_failure"
            title = "Reviewed evidence deficiency" if deficiency else "Review gap"
            emit(f"### {label}{title}")
            emit()
            linked = [item for item in declared.requirements if any(pin.id == obligation.id for pin in item.obligation_refs)]
            for requirement in linked:
                requirement_context(requirement)
            if not linked:
                field("Project mapping gap", "Unmapped obligation; no project requirement declares this mapping.")
            legal_context(obligation)
            if method is not None:
                field("Review method and recorded outcome", f"{method.method}: {method.outcome}")
                field("Missing evidence or review", method.missing_evidence)
                for identity in method.review_ids:
                    review = reviews[identity]
                    field("Evidence review", f"{review.id}@{review.revision}: {review.state}")
                    field("What the reviewer found", review.rationale)
                    field("Reviewer and review time", f"{review.reviewer or 'not supplied'}; {review.reviewed_at or 'not supplied'}")
                    field("Evidence owner and period", f"{review.owner}; {review.period}")
                    field("Evidence references", review.evidence_ids)
                    field("Missing evidence", review.missing_evidence)
                    field("Contrary evidence", review.contrary_evidence)
            else:
                field("Review gap", "Required review methods or effective applicability remain unresolved.")
            field("Conclusion limit", "Recorded evidence insufficiency, not an established legal breach." if deficiency else "Review is incomplete; no violation is inferred, including for unknown or not-applicable cases.")
            field("Next review action", "Ask the named evidence owner to address the recorded insufficiency and obtain an accountable review against the declared provision." if deficiency else "Resolve the listed applicability and evidence gaps with an accountable reviewer before drawing a legal conclusion.")
            emit()

    for requirement in declared.requirements:
        assessment = assessments[requirement.id]
        title = "Recorded mapping support" if assessment.state == "supported" else "Requirement review gap or recorded exclusion"
        emit(f"### {label}{title}")
        emit()
        requirement_context(requirement)
        field("Requirement assessment", assessment.state)
        field("Reason", assessment.rationale)
        for pin in requirement.obligation_refs:
            legal_context(obligations[pin.id])
        if not requirement.obligation_refs:
            field("Mapping gap", "Unmapped requirement; no candidate obligation or exact legal provision has been declared.")
        field("Requirement gaps", assessment.gaps)
        field("Next review actions", assessment.next_actions)
        if not requirement.obligation_refs:
            field("Next review action", "Request an explicit, reviewed obligation and provision mapping; do not infer a duty from requirement text.")
        emit()
    if not requirements:
        field("Coverage gap", "No requirements supplied; declare the project requirements to be assessed.")
    if not obligations:
        field("Coverage gap", "No candidate obligations supplied; identify and review source provisions before mapping requirements.")
    for gap in bundle.gaps:
        field("Additional coverage, source or review gap", gap)
    for action in bundle.next_actions:
        field("Grounded next review action", action)
    emit()
    emit("## Run and retained artifacts")
    emit()
    field("Processing state", bundle.run.state)
    field("Project", bundle.project_id)
    field("Input digest", bundle.input_digest)
    field("Manifest digest", bundle.manifest.digest)
    record("Run", bundle.run)
    emit("[Normalized declarations](input.json) · [Manifest](manifest.json) · [Validated bundle](bundle.json) · [Completion marker](complete.json)")
    emit()
    if bundle.comparison is not None:
        emit("## Predecessor comparison and renewed review actions")
        emit()
        field("Historical run", bundle.comparison.previous_run_id)
        field("Historical bundle digest", bundle.comparison.previous_bundle_digest)
        emit("[Retained dependency comparison](comparison.json)")
        emit()
        for change in bundle.comparison.changes:
            record("Dependency change", change)
        if not bundle.comparison.changes:
            emit("Recorded dependencies unchanged; this renews neither legal currency nor reviewer approval.")
        for overlay in bundle.current_assessments:
            record("Historical claim freshness", overlay)
    emit("## Declared scope, jurisdictions and exclusions")
    emit()
    record("Scope", declared.scope, exclude={"roles", "size_and_sector", "activities"})
    for activity in declared.scope.activities:
        record("Processing activity", activity)
    emit("## Facts and retained uncertainty")
    emit()
    facts = {fact.id: fact for fact in m.scope_facts(declared.scope)}
    if not facts:
        emit("No facts supplied; applicability requires explicit review.")
        emit()
    for fact in facts.values():
        record("Fact", fact)

    emit("## Every declared requirement and mapping")
    emit()
    if not declared.requirements:
        emit("No requirements supplied. This is an explicit coverage gap.")
        emit()
    for requirement in declared.requirements:
        record("Requirement", requirement)
        record("Requirement assessment", assessments[requirement.id])
        if not requirement.obligation_refs:
            emit(f"{label}Unmapped requirement; see its assessment gaps and next actions.")
            emit()
        for pin in requirement.obligation_refs:
            disposition = dispositions[pin.id]
            decision = decisions[pin.id]
            field("Mapping chain", f"{requirement.id}@{requirement.revision} → {pin.id}@{pin.revision} → {disposition.id} → {decision.id}@{decision.revision}")
        emit()

    emit("## Every candidate obligation, including unmapped obligations")
    emit()
    mapped = {pin.id for requirement in declared.requirements for pin in requirement.obligation_refs}
    claimed = {item.obligation.id: item for item in declared.applicability_decisions}
    if not declared.obligations:
        emit("No obligation register supplied. This is an explicit coverage gap.")
        emit()
    for obligation in declared.obligations:
        record("Candidate obligation", obligation)
        field("Requirement mapping", "mapped" if obligation.id in mapped else "unmapped obligation")
        emit()
        if obligation.id in claimed:
            record("Supplied applicability claim", claimed[obligation.id])
        record("Effective applicability", decisions[obligation.id])
        record("Independent legal and method dispositions", dispositions[obligation.id])
    for control in declared.controls:
        record("Declared control (no execution)", control)

    emit("## Coverage of eleven candidate legal families")
    emit()
    emit("Family screening records candidate coverage only; it does not assert that all applicable EU law was searched.")
    emit()
    for screening in declared.family_screenings:
        record("Supplied family screening", screening)
    for screening in bundle.family_screenings:
        record("Effective family screening", screening)

    emit("## Candidate source identity, classification and review")
    emit()
    for target in declared.source_targets:
        record("Candidate source target (no fetch authorization)", target)
    for selected in declared.sources:
        record("Selected source metadata", selected.source)
        field("Target id", selected.target_id)
        field("Declared local media type", selected.media_type)
        field("Declared local charset", selected.charset)
        field("Selected source file", selected.file.model_dump(mode="json") if selected.file else None)
        emit()
    for review in declared.source_reviews:
        record("Source review and seven review dimensions", review)
    emit("## Official-source retrieval attempts")
    emit()
    if not fetched:
        emit("No retrieval was requested; no network operation occurred.")
        emit()
    else:
        emit("Each attempt records which bytes an approved host served at retrieval time. Official hosting establishes neither binding status, completeness, applicability nor currency for the assessment date; retrieved candidates need an accountable source review before any use.")
        emit()
    for attempt in bundle.source_attempts:
        retrieval = attempt.retrieval
        emit(f"### {label}Retrieval attempt")
        emit()
        field("Source target", attempt.source_target_id)
        field("Attempt", attempt.id)
        field("State", attempt.state)
        field("Intended type, publisher and identifier", f"{attempt.intended_type}; {attempt.publisher}; {attempt.intended_identifier or 'not supplied'}")
        field("Requested URL", retrieval.requested_url)
        field("Validated redirects", retrieval.redirects)
        field("Final URL", retrieval.final_url)
        field("Started and ended", f"{retrieval.started_at}; {retrieval.ended_at}")
        field("HTTP status", retrieval.status)
        field("Media type and charset", f"{retrieval.media_type or 'not recorded'}; {retrieval.charset or 'not recorded'}")
        field("Bytes read", retrieval.bytes_read)
        field("Content digest", retrieval.digest)
        field("Retained artifact", retrieval.artifact_path)
        field("Content screening", f"{retrieval.admission}; {retrieval.admission_reason}" if retrieval.admission else None)
        field("Comparison with declared source", retrieval.comparison)
        field("Declared source (historical fallback only)", f"{attempt.last_successful_source.id}@{attempt.last_successful_source.revision}" if attempt.last_successful_source else None)
        field("Retrieved candidate", f"{attempt.retrieved_source.id}@{attempt.retrieved_source.revision}" if attempt.retrieved_source else None)
        field("Failure", f"{attempt.failure.code}: {attempt.failure.safe_message}" if attempt.failure else None)
        emit()
    for source in bundle.retrieved_sources:
        record("Retrieved candidate source (unreviewed, no provisions)", source)
    emit("## Evidence metadata and accountable reviews")
    emit()
    for selected in declared.evidence:
        record("Declared evidence metadata", selected.evidence)
        field("Selected evidence path (body excluded)", selected.path)
        emit()
    for evidence in bundle.evidence:
        record("Observed evidence metadata", evidence)
    for review in declared.evidence_reviews:
        record("Evidence review, period, missing and contrary evidence", review)
    emit("## Remaining gaps and next actions")
    emit()
    field("Run gaps", bundle.run.gaps)
    field("Assessment gaps", bundle.gaps)
    field("Next actions", bundle.next_actions)
    emit()
    return "\n".join(lines) + "\n"
