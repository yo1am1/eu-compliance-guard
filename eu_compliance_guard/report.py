"""Pure, bounded Markdown projection of validated offline revalidation records."""

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
    emit("# Offline requirements-to-law revalidation")
    emit()
    if bundle.synthetic:
        emit("**FICTIONAL / SYNTHETIC DATA, INCLUDING MIXED DECLARATIONS. Every conclusion below is labelled fictional; none establishes real EU duties.**")
    else:
        emit("**Recorded local declarations and unauthenticated reviewer attestations. Offline legal freshness remains unverified.**")
    emit()
    emit("Processing status describes report assembly only. No compliance verdict, legal approval, exhaustive law search or technical test is established.")
    emit("Only explicitly selected local files were considered. Evidence bodies are excluded from this report; metadata and declarations remain private.")
    emit("Recorded processing budgets use cooperative checks; they do not establish a hard CPU/filesystem deadline or process containment.")
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
    assessments = {item.requirement.id: item for item in bundle.requirement_assessments}
    dispositions = {item.obligation_id: item for item in bundle.obligation_dispositions}
    decisions = {item.obligation.id: item for item in bundle.effective_applicability_decisions}
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
