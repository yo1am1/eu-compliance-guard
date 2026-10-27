"""Validated shared records and closed commands; authorization belongs to the engine."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import hashlib
import json
from typing import Annotated, Literal, TypeVar, get_args
from urllib.parse import urlsplit

from pydantic import (
    AfterValidator, BeforeValidator, BaseModel, ConfigDict, Field, JsonValue, TypeAdapter,
    model_validator,
)

MAX_REQUEST_BYTES = 4 * 1024 * 1024
MAX_SEQUENCE = 2**53 - 1


def _date(value: str) -> str:
    if date.fromisoformat(value).isoformat() != value:
        raise ValueError("expected an ISO calendar date")
    return value


def _timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    if "T" not in value or parsed.utcoffset() != timedelta(0):
        raise ValueError("expected a UTC timestamp")
    return value


def _relative_path(value: str) -> str:
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("control character in path")
    if "\\" in value or ":" in value or any(p in ("", ".", "..") for p in value.split("/")):
        raise ValueError("expected a normalized project-relative path")
    return value


def _http_url(value: str) -> str:
    if any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError("whitespace in URL")
    parsed = urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("expected an HTTP(S) URL without credentials")
    parsed.port  # Reject malformed ports, without resolving or accessing a destination.
    return value


def _json_value(value: JsonValue) -> JsonValue:
    stack = [(value, 0)]
    nodes = 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if depth > 12 or nodes > 10000:
            raise ValueError("JSON value exceeds nesting/item limit")
        if isinstance(item, str) and len(item) > 65536:
            raise ValueError("JSON string exceeds limit")
        if isinstance(item, dict):
            if any(len(k) > 256 for k in item):
                raise ValueError("JSON key exceeds limit")
            stack.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            stack.extend((v, depth + 1) for v in item)
    return value


def _schema_version(value: object) -> object:
    if type(value) is not int:
        raise ValueError("schema version must be an integer")
    return value


SchemaVersion = Annotated[Literal[1], BeforeValidator(_schema_version)]
Id = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")]
Text = Annotated[str, Field(max_length=8192)]
Name = Annotated[str, Field(min_length=1, max_length=256)]
Revision = Annotated[int, Field(ge=0, le=MAX_SEQUENCE)]
Digest = Annotated[str, Field(pattern=r"^sha256:[a-f0-9]{64}$")]
ISODate = Annotated[str, Field(json_schema_extra={"format": "date"}), AfterValidator(_date)]
Timestamp = Annotated[str, Field(max_length=40, json_schema_extra={"format": "date-time"}), AfterValidator(_timestamp)]
RelativePath = Annotated[str, Field(min_length=1, max_length=1024), AfterValidator(_relative_path)]
HttpURL = Annotated[str, Field(max_length=4096), AfterValidator(_http_url)]
HostName = Annotated[str, Field(min_length=1, max_length=253, pattern=r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$")]
MediaType = Annotated[str, Field(min_length=3, max_length=256, pattern=r"^[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+$")]
Value = Annotated[JsonValue, AfterValidator(_json_value)]
Ids = Annotated[list[Id], Field(max_length=1000)]
Texts = Annotated[list[Text], Field(max_length=1000)]

Applicability = Literal["applicable", "not_applicable", "unresolved"]
Outcome = Literal["passed", "observed_failure", "unresolved_review", "blocked", "not_tested", "lead"]
Freshness = Literal["current_for_recorded_inputs", "stale", "unknown"]
RunState = Literal["planned", "running", "cancelling", "completed", "partial", "cancelled", "interrupted"]
PatchState = Literal["proposed", "running", "applied-awaiting-verification", "verified", "failed", "blocked"]
SourceType = Literal["eu_act", "national_act", "judgment", "final_guidance", "draft_guidance", "proposal", "standard", "engineering_practice", "synthetic_fixture"]
SourceReviewTopic = Literal["identity", "classification", "amendments_repeal", "case_law", "national_overlays", "translation", "application_transition_dates"]
TERMINAL_RUN_STATES = frozenset({"completed", "partial", "cancelled", "interrupted"})


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True,
                              allow_inf_nan=False, hide_input_in_errors=True,
                              revalidate_instances="always")


class SourceRef(Record):
    id: Id
    revision: Revision


class SafeError(Record):
    code: Id
    safe_message: Text


class Fact(Record):
    id: Id
    revision: Revision
    key: Name
    value: Value
    basis: Literal["observed", "declared", "assumed", "unknown"]
    evidence_ids: Ids
    owner: Text
    observed_at: Timestamp
    conflicts: Ids


class ProcessingActivity(Record):
    id: Id
    purpose: Text
    subjects: Texts
    data_categories: Texts
    roles: list[Fact]
    lawful_basis: Fact
    recipients: list[Fact]
    locations: list[Fact]
    stores: list[Fact]
    retention: list[Fact]
    evidence_owner: Text


class Scope(Record):
    id: Id
    revision: Revision
    project_id: Id
    assessment_date: ISODate
    environment: Name
    activities: list[ProcessingActivity]
    establishment: Texts
    markets: Texts
    customer_types: Texts
    roles: list[Fact]
    size_and_sector: list[Fact]
    jurisdictions: Texts
    included_scenarios: Texts
    exclusions: Texts
    permission_id: Id


class LegalSource(Record):
    id: Id
    revision: Revision
    type: SourceType
    publisher: Name
    identifier: Text | None = None
    url: HttpURL
    language: Name
    jurisdiction: Name
    document_date: ISODate | None = None
    retrieved_at: Timestamp
    content_digest: Digest
    provisions: Texts
    related_source_ids: Ids
    synthetic: bool

    @model_validator(mode="after")
    def synthetic_classification(self) -> LegalSource:
        if self.synthetic != (self.type == "synthetic_fixture"):
            raise ValueError("synthetic source must be explicitly classified")
        return self


class RetrievalProvenance(Record):
    """Safe per-attempt metadata; response headers, cookies and bodies are never retained here."""
    requested_url: HttpURL
    final_url: HttpURL | None = None
    redirects: Annotated[list[HttpURL], Field(max_length=3)]
    started_at: Timestamp
    ended_at: Timestamp
    status: Annotated[int, Field(ge=100, le=599)] | None = None
    media_type: MediaType | None = None
    charset: Name | None = None
    bytes_read: Annotated[int, Field(ge=0, le=16 * 1024 * 1024)]
    digest: Digest | None = None
    artifact_path: RelativePath | None = None
    admission: Literal["accepted", "needs_review", "rejected"] | None = None
    admission_reason: Name | None = None
    comparison: Literal["same_bytes", "different_bytes", "no_prior_source", "not_compared"]

    @model_validator(mode="after")
    def consistent(self) -> RetrievalProvenance:
        if datetime.fromisoformat(self.ended_at) < datetime.fromisoformat(self.started_at):
            raise ValueError("retrieval ends before it starts")
        if self.final_url is not None and self.final_url != (self.redirects[-1] if self.redirects else self.requested_url):
            raise ValueError("final URL must end the recorded redirect chain")
        if (self.admission is None) != (self.admission_reason is None):
            raise ValueError("content admission and reason must be supplied together")
        if self.artifact_path is not None and (self.digest is None or self.artifact_path != "sources/" + self.digest.removeprefix("sha256:") + ".bin"):
            raise ValueError("retained retrieval artifact must be named by its digest")
        if self.comparison in ("same_bytes", "different_bytes") and self.digest is None:
            raise ValueError("byte comparison requires a retrieved digest")
        return self


class SourceAttempt(Record):
    id: Id
    source_target_id: Id
    intended_url: HttpURL
    intended_identifier: Text | None = None
    publisher: Name
    intended_type: SourceType
    language: Name
    attempted_at: Timestamp
    state: Literal["retrieved", "retrieval_failed", "translation_unverified"]
    retrieved_source: SourceRef | None = None
    last_successful_source: SourceRef | None = None
    failure: SafeError | None = None
    retrieval: RetrievalProvenance | None = None

    @model_validator(mode="after")
    def retrieval_state(self) -> SourceAttempt:
        if self.state == "retrieved" and (self.retrieved_source is None or self.failure is not None):
            raise ValueError("retrieved attempt requires source and no failure")
        if self.state != "retrieved" and self.failure is None:
            raise ValueError("unsuccessful attempt requires a safe failure reason")
        if self.state == "retrieval_failed" and self.retrieved_source is not None:
            raise ValueError("failed retrieval cannot invent a retrieved source")
        if self.retrieval is not None:
            retrieval = self.retrieval
            if retrieval.requested_url != self.intended_url:
                raise ValueError("retrieval provenance must start at the intended URL")
            retained = (retrieval.final_url is not None and retrieval.status == 200 and retrieval.digest is not None
                        and retrieval.artifact_path is not None and retrieval.admission in ("accepted", "needs_review"))
            if (self.retrieved_source is not None) != retained:
                raise ValueError("retrieved source requires retained accepted or reviewable bytes")
            if self.state == "retrieval_failed" and retrieval.comparison in ("same_bytes", "different_bytes"):
                raise ValueError("failed retrieval cannot be compared as fresh bytes")
        return self


class SourceReview(Record):
    source_id: Id
    source_revision: Revision
    assessment_date: ISODate
    state: Literal["unreviewed", "reviewed_for_assessment", "stale", "unavailable", "superseded"]
    act_chain: Ids
    case_law_refs: Ids
    national_overlay_ids: Ids
    entry_date: ISODate | None = None
    application_dates: list[ISODate]
    transition_dates: list[ISODate]
    last_successful_verification: Timestamp | None = None
    reviewer: Name | None = None
    gaps: Texts
    synthetic: bool = False
    review_notes: dict[SourceReviewTopic, Text] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reviewed_state(self) -> SourceReview:
        if self.state == "reviewed_for_assessment" and (not self.reviewer or not self.last_successful_verification or self.gaps):
            raise ValueError("reviewed source needs accountable verification without open gaps")
        return self


class ProvisionRef(Record):
    source_target_id: Id
    source_id: Id | None = None
    revision: Revision | None = None
    locator: Name

    @model_validator(mode="after")
    def pinned_source(self) -> ProvisionRef:
        if (self.source_id is None) != (self.revision is None):
            raise ValueError("source ID and revision must be supplied together")
        return self


class Obligation(Record):
    id: Id
    revision: Revision
    family: Name
    classification: Literal["duty", "recommendation"]
    source_provisions: list[ProvisionRef]
    conditions: Texts
    exceptions: Texts
    overlay_ids: Ids
    control_ids: Ids
    required_methods: Texts
    limitations: Texts


class Control(Record):
    id: Id
    revision: Revision
    obligation_ids: Ids
    assertion_or_question: Text
    required_facts: Texts
    check_ids: Ids
    required_evidence: Texts
    owner: Text
    provenance: Texts
    limitations: Texts


class SourceFile(Record):
    path: RelativePath
    digest: Digest


class InputManifest(Record):
    id: Id
    digest: Digest
    source_files: Annotated[list[SourceFile], Field(max_length=10000)]
    exclusions: Texts
    scope_revision: Revision
    fact_digest: Digest
    registry_digest: Digest
    source_versions: Texts
    fixture_digest: Digest
    tool_versions: Texts
    config_digest: Digest
    environment_identity: Name
    browser_state: dict[Name, Text] | None = None
    graph_digest: Digest | None = None

    @model_validator(mode="after")
    def unique_paths(self) -> InputManifest:
        paths = [f.path for f in self.source_files]
        if len(paths) != len(set(paths)):
            raise ValueError("manifest source paths must be unique")
        return self


class Budgets(Record):
    run_seconds: Annotated[int, Field(ge=1, le=86400)]
    check_seconds: Annotated[int, Field(ge=1, le=86400)]

    @model_validator(mode="after")
    def check_within_run(self) -> Budgets:
        if self.check_seconds > self.run_seconds:
            raise ValueError("check budget exceeds run budget")
        return self


class AuditRun(Record):
    id: Id
    project_id: Id
    parent_run_id: Id | None = None
    revision: Revision
    state: RunState
    manifest_id: Id
    permission_id: Id
    coverage_plan: Texts
    started_at: Timestamp | None = None
    ended_at: Timestamp | None = None
    terminal_sequence: Revision | None = None
    gaps: Texts
    budgets: Budgets

    @model_validator(mode="after")
    def terminal_state(self) -> AuditRun:
        terminal = self.state in TERMINAL_RUN_STATES
        if terminal != (self.ended_at is not None and self.terminal_sequence is not None):
            raise ValueError("terminal state and retained terminal metadata must agree")
        if not terminal and (self.ended_at is not None or self.terminal_sequence is not None):
            raise ValueError("active run cannot have terminal metadata")
        if self.state in ("running", "cancelling") and self.started_at is None:
            raise ValueError("active run needs its actual start time")
        if self.started_at and self.ended_at and datetime.fromisoformat(self.ended_at) < datetime.fromisoformat(self.started_at):
            raise ValueError("run ends before it starts")
        return self


class CheckAttempt(Record):
    id: Id
    project_id: Id
    run_id: Id
    check_id: Id
    check_version: Name
    manifest_id: Id
    retry_of: Id | None = None
    state: Literal["pending", "running", "completed", "cancelled", "interrupted"]
    outcome: Outcome | None
    expected: Value | None
    actual: Value | None
    evidence_ids: Ids
    tool_and_rule_versions: Texts
    errors: Texts
    exclusions: Texts
    inconsistent_with: Ids

    @model_validator(mode="after")
    def outcome_matches_state(self) -> CheckAttempt:
        if self.state in ("pending", "running") and self.outcome is not None:
            raise ValueError("unfinished attempt cannot publish an outcome")
        if self.state == "completed" and self.outcome is None:
            raise ValueError("completed attempt requires an observed outcome")
        if self.state in ("cancelled", "interrupted") and self.outcome not in ("blocked", "not_tested"):
            raise ValueError("cancelled/interrupted attempt cannot pass")
        return self


class Evidence(Record):
    id: Id
    project_id: Id
    run_id: Id
    attempt_id: Id | None = None
    kind: Name
    provenance: Literal["declared", "documented", "observed", "independently_verified"]
    digest: Digest
    captured_at: Timestamp
    manifest_id: Id
    media_type: Name
    redaction: Literal["safe", "blocked", "unknown"]
    availability: Literal["available", "missing", "purged", "corrupt", "blocked"]
    retention_until: Timestamp | None = None
    source_refs: Texts
    browser_context: dict[Name, Text] | None = None


class MethodDisposition(Record):
    method: Name
    outcome: Outcome
    attempt_ids: Ids
    review_ids: Ids
    missing_evidence: Texts

    @model_validator(mode="after")
    def sufficient_evidence(self) -> MethodDisposition:
        if self.outcome == "passed" and self.missing_evidence:
            raise ValueError("missing required evidence cannot support a passed method")
        return self


class ObligationDisposition(Record):
    id: Id
    project_id: Id
    run_id: Id
    obligation_id: Id
    obligation_revision: Revision
    applicability: Applicability
    applicability_decision_id: Id
    rationale: Text
    required_method_dispositions: list[MethodDisposition]
    manual_review: Literal["pending", "supported", "unsupported", "unresolved"]

    @model_validator(mode="after")
    def unique_methods(self) -> ObligationDisposition:
        methods = [entry.method for entry in self.required_method_dispositions]
        if len(methods) != len(set(methods)):
            raise ValueError("duplicate obligation method dispositions")
        return self


class Finding(Record):
    id: Id
    project_id: Id
    control_id: Id
    subject_id: Id


class FindingAssessment(Record):
    id: Id
    project_id: Id
    run_id: Id
    finding_id: Id
    revision: Revision
    manifest_id: Id
    control_revision: Revision
    obligation_disposition_ids: Ids
    attempt_ids: Ids
    evidence_ids: Ids
    validation_ids: Ids
    technical_outcome: Outcome
    impact: Text
    affected_parties: Texts
    owner: Text
    action_ids: Ids


class CurrentAssessment(Record):
    id: Id
    revision: Revision
    project_id: Id
    historical_run_id: Id
    finding_assessment_id: Id | None = None
    obligation_disposition_id: Id | None = None
    expected_manifest_id: Id
    observed_manifest_id: Id | None = None
    checked_at: Timestamp
    freshness: Freshness
    reasons: Texts
    changed_dependencies: Texts
    comparison_evidence_ids: Ids = Field(default_factory=list)

    @model_validator(mode="after")
    def assessment_target(self) -> CurrentAssessment:
        if (self.finding_assessment_id is None) == (self.obligation_disposition_id is None):
            raise ValueError("current overlay must reference exactly one historical assessment")
        if self.freshness == "current_for_recorded_inputs":
            if self.observed_manifest_id is None or self.changed_dependencies:
                raise ValueError("current claim requires observed inputs without relevant changes")
            if self.observed_manifest_id != self.expected_manifest_id and not self.comparison_evidence_ids:
                raise ValueError("different manifests require retained dependency-comparison evidence")
        return self


class RunRelation(Record):
    project_id: Id
    run_id: Id
    parent_run_id: Id | None = None
    creating_request_id: Id
    operation: Name
    created_at: Timestamp
    state: RunState


class Conversation(Record):
    id: Id
    project_id: Id
    finding_id: Id
    finding_assessment_id: Id
    origin_run_id: Id
    execution_run_id: Id
    context_manifest_id: Id
    revision: Revision
    message_ids: Ids


class ConversationMessage(Record):
    id: Id
    conversation_id: Id
    author: Literal["owner", "agent"]
    content: Annotated[str, Field(max_length=65536)]
    state: Literal["partial", "accepted", "blocked"]
    context_manifest_id: Id
    proposal_ids: Ids


class PatchProposal(Record):
    id: Id
    project_id: Id
    run_id: Id
    finding_ids: Ids
    revision: Revision
    diff_digest: Digest
    relative_paths: Annotated[list[RelativePath], Field(min_length=1, max_length=1)]
    preimages: Annotated[list[Digest], Field(min_length=1, max_length=1)]
    expected_postimages: Annotated[list[Digest], Field(min_length=1, max_length=1)]
    permission_id: Id
    retest_ids: Annotated[Ids, Field(min_length=1)]
    state: PatchState
    before_attempt_ids: Ids
    after_attempt_ids: Ids

    @model_validator(mode="after")
    def verification_evidence(self) -> PatchProposal:
        if self.state == "verified" and (not self.before_attempt_ids or not self.after_attempt_ids):
            raise ValueError("verified patch needs before/after attempt references")
        return self


class TextPatch(Record):
    kind: Literal["one_file_text_patch"]
    relative_path: RelativePath
    preimage_digest: Digest
    proposed_postimage: Annotated[str, Field(max_length=524288)]
    retest_ids: Annotated[Ids, Field(min_length=1)]


class AgentReplyEnvelope(Record):
    schema_version: SchemaVersion
    conversation_id: Id
    context_manifest_id: Id
    finding_assessment_id: Id
    message: Annotated[str, Field(max_length=65536)]
    proposal: TextPatch | None = None


class CommandReceipt(Record):
    request_id: Id
    payload_digest: Digest
    project_id: Id
    origin_run_id: Id | None = None
    execution_run_id: Id | None = None
    action_id: Id | None = None
    revision: Revision
    state: Literal["accepted", "pending", "blocked", "conflict", "failed", "completed"]
    error: SafeError | None = None


class Event(Record):
    schema_version: SchemaVersion
    project_id: Id
    run_id: Id
    sequence: Revision
    type: Name
    entity_id: Id | None = None
    entity_revision: Revision | None = None
    request_id: Id | None = None
    occurred_at: Timestamp
    payload: Value


class Snapshot(Record):
    schema_version: SchemaVersion
    project_id: Id
    run: AuditRun
    findings: list[Finding]
    finding_assessments: list[FindingAssessment]
    obligation_dispositions: list[ObligationDisposition]
    attempts: list[CheckAttempt]
    actions: list[PatchProposal]
    cursor: Annotated[str, Field(max_length=160)]
    terminal: bool
    current_assessments: list[CurrentAssessment]
    relations_revision: Revision

    @model_validator(mode="after")
    def membership(self) -> Snapshot:
        if self.run.project_id != self.project_id or self.terminal != (self.run.state in TERMINAL_RUN_STATES):
            raise ValueError("snapshot run/project/terminal mismatch")
        run_id, sequence = parse_cursor(self.cursor, self.run.id)
        if self.run.terminal_sequence is not None and sequence > self.run.terminal_sequence:
            raise ValueError("snapshot cursor is beyond terminal")
        collections = (self.findings, self.finding_assessments, self.obligation_dispositions,
                       self.attempts, self.actions, self.current_assessments)
        for records in collections:
            ids = [record.id for record in records]
            if len(ids) != len(set(ids)):
                raise ValueError("duplicate snapshot record identity")
            for record in records:
                if record.project_id != self.project_id:
                    raise ValueError("cross-project snapshot record")
                if hasattr(record, "run_id") and record.run_id != run_id:
                    raise ValueError("cross-run snapshot record")
                if isinstance(record, (FindingAssessment, CheckAttempt)) and record.manifest_id != self.run.manifest_id:
                    raise ValueError("snapshot record pins a different input manifest")
                if isinstance(record, CurrentAssessment) and record.historical_run_id != run_id:
                    raise ValueError("overlay belongs to another historical run")
        finding_ids = {item.id for item in self.findings}
        assessment_ids = {item.id for item in self.finding_assessments}
        disposition_ids = {item.id for item in self.obligation_dispositions}
        attempt_ids = {item.id for item in self.attempts}
        for assessment in self.finding_assessments:
            if assessment.finding_id not in finding_ids or not set(assessment.obligation_disposition_ids) <= disposition_ids or not set(assessment.attempt_ids) <= attempt_ids:
                raise ValueError("dangling finding assessment reference")
        for overlay in self.current_assessments:
            if overlay.expected_manifest_id != self.run.manifest_id:
                raise ValueError("overlay expected inputs differ from its historical run")
            if overlay.finding_assessment_id and overlay.finding_assessment_id not in assessment_ids:
                raise ValueError("dangling finding overlay reference")
            if overlay.obligation_disposition_id and overlay.obligation_disposition_id not in disposition_ids:
                raise ValueError("dangling obligation overlay reference")
        for proposal in self.actions:
            if not set(proposal.finding_ids) <= finding_ids:
                raise ValueError("dangling patch finding reference")
        return self


class DetailQuery(Record):
    section: Literal["obligations", "controls", "sources", "reviews", "conversations", "patches", "graph"]
    entity_id: Id | None = None
    cursor: Id | None = None
    limit: Annotated[int, Field(ge=1, le=100)] = 50


class SafeEvidence(Record):
    evidence: Evidence
    content_text: Annotated[str, Field(max_length=524288)] | None = None
    blocked_reason: Text | None = None

    @model_validator(mode="after")
    def delivery_gate(self) -> SafeEvidence:
        deliverable = self.evidence.redaction == "safe" and self.evidence.availability == "available"
        if self.content_text is not None:
            if not deliverable or self.blocked_reason or content_digest(self.content_text.encode("utf-8")) != self.evidence.digest:
                raise ValueError("unsafe or mismatched evidence preview")
        elif not deliverable and not self.blocked_reason:
            raise ValueError("unavailable evidence needs an explicit blocked reason")
        return self


class PatchPreview(Record):
    project_id: Id
    run_id: Id
    proposal_id: Id
    revision: Revision
    diff_digest: Digest
    preview_digest: Digest | None = None
    redaction: Literal["safe", "blocked", "unknown"]
    diff: Annotated[str, Field(max_length=524288)] | None = None
    blocked_reason: Text | None = None

    @model_validator(mode="after")
    def preview_gate(self) -> PatchPreview:
        if self.diff is not None:
            if self.redaction != "safe" or self.blocked_reason or content_digest(self.diff.encode("utf-8")) != self.preview_digest:
                raise ValueError("unsafe or mismatched patch preview")
        elif not self.blocked_reason:
            raise ValueError("missing patch preview needs an explicit blocked reason")
        return self


class GraphRelationship(Record):
    id: Id
    from_id: Id
    to_id: Id
    kind: Name
    origin: Literal["structural", "static_inferred", "semantic", "ambiguous", "unknown"]
    evidence_ids: Ids
    source_paths: Annotated[list[RelativePath], Field(max_length=100)]
    provenance: Texts


class DetailPage(Record):
    schema_version: SchemaVersion
    project_id: Id
    origin_run_id: Id
    section: Literal["obligations", "controls", "sources", "reviews", "conversations", "patches", "graph"]
    projection_revision: Revision
    records: Annotated[list[Obligation | ObligationDisposition | Control | LegalSource | SourceAttempt | SourceReview | Conversation | ConversationMessage | PatchProposal | PatchPreview | GraphRelationship], Field(max_length=100)]
    next_cursor: Id | None = None

    @model_validator(mode="after")
    def section_membership(self) -> DetailPage:
        allowed = {"obligations": (Obligation, ObligationDisposition), "controls": (Control,),
                   "sources": (LegalSource, SourceAttempt), "reviews": (SourceReview,),
                   "conversations": (Conversation, ConversationMessage),
                   "patches": (PatchProposal, PatchPreview), "graph": (GraphRelationship,)}
        for record in self.records:
            if not isinstance(record, allowed[self.section]):
                raise ValueError("record does not belong to requested detail section")
            if hasattr(record, "project_id") and record.project_id != self.project_id:
                raise ValueError("cross-project detail record")
            if isinstance(record, Conversation) and record.origin_run_id != self.origin_run_id:
                raise ValueError("conversation belongs to another origin run")
            if hasattr(record, "run_id") and record.run_id != self.origin_run_id:
                raise ValueError("cross-run detail record")
        return self


Operation = Literal["project.register", "scope.register", "permission.grant", "permission.revoke", "registry.accept", "audit.start", "audit.cancel", "audit.resume", "results.import", "evidence.import", "legal.refresh", "finding.discuss", "patch.propose", "patch.apply", "checks.retest", "inputs.refresh"]


class ProviderBoundary(Record):
    provider: Name | None = None
    authorized: bool = False
    data_classes: Texts = Field(default_factory=list)

    @model_validator(mode="after")
    def explicit_processing(self) -> ProviderBoundary:
        if self.authorized and (not self.provider or not self.data_classes):
            raise ValueError("provider processing needs an explicit recipient and data scope")
        return self


class PermissionGrant(Record):
    id: Id
    project_id: Id
    root_identity: Digest
    operations: Annotated[list[Operation], Field(max_length=100)]
    relative_paths: Annotated[list[RelativePath], Field(max_length=1000)]
    test_origins: Annotated[list[HttpURL], Field(max_length=100)]
    synthetic_fixture_ids: Ids
    provider: ProviderBoundary
    expires_at: Timestamp
    revoked_at: Timestamp | None = None


class CapabilityObservation(Record):
    capability: Id
    mechanism: Name
    mechanism_version: Name | None = None
    level: Literal["static", "fake", "observed"]
    state: Literal["not_run", "passed", "failed", "blocked"]
    observed_at: Timestamp
    evidence_ids: Ids
    reason: Text

    @model_validator(mode="after")
    def observed_proof(self) -> CapabilityObservation:
        if self.level == "observed" and self.state == "passed" and not self.evidence_ids:
            raise ValueError("observed pass requires retained proof references")
        return self


class CapabilityReport(Record):
    project_id: Id
    observations: Annotated[list[CapabilityObservation], Field(max_length=100)]
    blocked: Ids


class ProjectRegisterArgs(Record):
    repository_root: Annotated[str, Field(min_length=1, max_length=4096, pattern=r"^/")]
    scope: Scope
    test_origins: Annotated[list[HttpURL], Field(max_length=100)]


class ScopeRegisterArgs(Record):
    scope: Scope


class PermissionGrantArgs(Record):
    grant: PermissionGrant


class PermissionRevokeArgs(Record):
    permission_id: Id


class RegistryAcceptArgs(Record):
    candidate_digest: Digest
    reviewer: Name


class AuditStartArgs(Record):
    scope_id: Id
    manifest_id: Id
    permission_id: Id
    check_ids: Ids
    budgets: Budgets


class AuditCancelArgs(Record):
    reason: Text


class AuditResumeArgs(Record):
    manifest_id: Id
    permission_id: Id


class ResultsImportArgs(Record):
    attempt: CheckAttempt


class EvidenceImportArgs(Record):
    evidence: Evidence
    content: Annotated[str, Field(max_length=524288)]


class LegalRefreshArgs(Record):
    source_target_ids: Ids


class FindingDiscussArgs(Record):
    finding_assessment_id: Id
    context_manifest_id: Id
    message: Annotated[str, Field(min_length=1, max_length=65536)]


class PatchProposeArgs(Record):
    reply: AgentReplyEnvelope


class PatchApplyArgs(Record):
    proposal_id: Id
    permission_id: Id


class ChecksRetestArgs(Record):
    manifest_id: Id
    check_ids: Annotated[Ids, Field(min_length=1)]
    permission_id: Id


class InputsRefreshArgs(Record):
    finding_assessment_ids: Ids
    obligation_disposition_ids: Ids


class CommandBase(Record):
    schema_version: SchemaVersion
    request_id: Id
    project_id: Id
    run_id: Id | None = None
    expected_revision: Revision


class ProjectRegisterCommand(CommandBase):
    operation: Literal["project.register"]
    arguments: ProjectRegisterArgs


class ScopeRegisterCommand(CommandBase):
    operation: Literal["scope.register"]
    arguments: ScopeRegisterArgs


class PermissionGrantCommand(CommandBase):
    operation: Literal["permission.grant"]
    arguments: PermissionGrantArgs


class PermissionRevokeCommand(CommandBase):
    operation: Literal["permission.revoke"]
    arguments: PermissionRevokeArgs


class RegistryAcceptCommand(CommandBase):
    operation: Literal["registry.accept"]
    arguments: RegistryAcceptArgs


class AuditStartCommand(CommandBase):
    operation: Literal["audit.start"]
    arguments: AuditStartArgs


class AuditCancelCommand(CommandBase):
    operation: Literal["audit.cancel"]
    arguments: AuditCancelArgs


class AuditResumeCommand(CommandBase):
    operation: Literal["audit.resume"]
    arguments: AuditResumeArgs


class ResultsImportCommand(CommandBase):
    operation: Literal["results.import"]
    arguments: ResultsImportArgs


class EvidenceImportCommand(CommandBase):
    operation: Literal["evidence.import"]
    arguments: EvidenceImportArgs


class LegalRefreshCommand(CommandBase):
    operation: Literal["legal.refresh"]
    arguments: LegalRefreshArgs


class FindingDiscussCommand(CommandBase):
    operation: Literal["finding.discuss"]
    arguments: FindingDiscussArgs


class PatchProposeCommand(CommandBase):
    operation: Literal["patch.propose"]
    arguments: PatchProposeArgs


class PatchApplyCommand(CommandBase):
    operation: Literal["patch.apply"]
    arguments: PatchApplyArgs


class ChecksRetestCommand(CommandBase):
    operation: Literal["checks.retest"]
    arguments: ChecksRetestArgs


class InputsRefreshCommand(CommandBase):
    operation: Literal["inputs.refresh"]
    arguments: InputsRefreshArgs


Command = Annotated[ProjectRegisterCommand | ScopeRegisterCommand | PermissionGrantCommand | PermissionRevokeCommand | RegistryAcceptCommand | AuditStartCommand | AuditCancelCommand | AuditResumeCommand | ResultsImportCommand | EvidenceImportCommand | LegalRefreshCommand | FindingDiscussCommand | PatchProposeCommand | PatchApplyCommand | ChecksRetestCommand | InputsRefreshCommand, Field(discriminator="operation")]
COMMAND_ADAPTER = TypeAdapter(Command)
TRecord = TypeVar("TRecord", bound=Record)


def parse_record(model: type[TRecord], payload: bytes | str) -> TRecord:
    raw = payload.encode("utf-8") if isinstance(payload, str) else payload
    if len(raw) > MAX_REQUEST_BYTES:
        raise ValueError("record exceeds byte limit")
    return model.model_validate_json(raw)


def parse_command(payload: bytes | str) -> Command:
    raw = payload.encode("utf-8") if isinstance(payload, str) else payload
    if len(raw) > MAX_REQUEST_BYTES:
        raise ValueError("command exceeds byte limit")
    return COMMAND_ADAPTER.validate_json(raw)


def content_digest(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def canonical_json(record: Record) -> bytes:
    return json.dumps(record.model_dump(mode="json"), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def parse_cursor(cursor: str, expected_run: str) -> tuple[str, int]:
    run_id, separator, sequence = cursor.rpartition(":")
    if not separator or run_id != expected_run or not sequence.isascii() or not sequence.isdecimal():
        raise ValueError("invalid or wrong-run event cursor")
    value = int(sequence)
    if str(value) != sequence or value > MAX_SEQUENCE:
        raise ValueError("invalid event sequence")
    return run_id, value


# Stable screening keys describe candidate domains, not a reviewed legal corpus.
LegalFamily = Literal["gdpr", "eprivacy", "service_disclosures", "consumer", "accessibility", "platforms", "ai", "cybersecurity", "data_products", "copyright", "sector_national"]
LEGAL_FAMILIES: tuple[LegalFamily, ...] = (
    "gdpr", "eprivacy", "service_disclosures", "consumer", "accessibility",
    "platforms", "ai", "cybersecurity", "data_products", "copyright", "sector_national",
)


class DeclaredRequirement(Record):
    id: Id
    revision: Revision
    project_id: Id
    synthetic: bool
    statement: Text
    origin: SourceFile | None = None
    locator: Name | None = None
    activity_ids: Ids
    fact_refs: Annotated[list[SourceRef], Field(max_length=500)]
    obligation_refs: Annotated[list[SourceRef], Field(max_length=200)]
    evidence_ids: Ids

    @model_validator(mode="after")
    def paired_origin(self) -> DeclaredRequirement:
        if (self.origin is None) != (self.locator is None):
            raise ValueError("requirement origin and locator must be supplied together")
        return self


class SourceTarget(Record):
    id: Id
    revision: Revision
    family: Name
    intended_url: HttpURL
    intended_identifier: Text | None = None
    publisher: Name
    intended_type: SourceType
    language: Name
    jurisdiction: Name
    # Explicitly approved redirect destinations; retrieval also requires the code registry.
    redirect_hosts: Annotated[list[HostName], Field(max_length=4)] = Field(default_factory=list)


class SelectedSource(Record):
    target_id: Id
    source: LegalSource
    media_type: MediaType
    charset: Name | None = None
    file: SourceFile | None = None

    @model_validator(mode="after")
    def declared_digest(self) -> SelectedSource:
        if self.file and self.file.digest != self.source.content_digest:
            raise ValueError("selected source digest declarations disagree")
        return self


class SelectedEvidence(Record):
    evidence: Evidence
    path: RelativePath | None = None


class FamilyScreening(Record):
    family: LegalFamily
    synthetic: bool
    scope: SourceRef
    assessment_date: ISODate
    applicability: Applicability = "unresolved"
    rationale: Text
    fact_refs: Annotated[list[SourceRef], Field(max_length=500)]
    source_refs: Annotated[list[SourceRef], Field(max_length=16)]
    reviewer: Name | None = None
    reviewed_at: Timestamp | None = None
    gaps: Texts


class ApplicabilityDecision(Record):
    id: Id
    revision: Revision
    project_id: Id
    synthetic: bool
    obligation: SourceRef
    scope: SourceRef
    assessment_date: ISODate
    jurisdictions: Texts
    fact_refs: Annotated[list[SourceRef], Field(max_length=500)]
    provisions: Annotated[list[ProvisionRef], Field(max_length=1000)]
    evidence_ids: Ids
    applicability: Applicability = "unresolved"
    rationale: Text
    condition_answers: Texts
    exception_answers: Texts
    reviewer: Name | None = None
    reviewed_at: Timestamp | None = None
    gaps: Texts


class EvidenceReview(Record):
    id: Id
    revision: Revision
    project_id: Id
    synthetic: bool
    obligation: SourceRef
    method: Name
    evidence_ids: Ids
    period: Text
    owner: Text
    state: Literal["reviewed", "insufficient", "unresolved"] = "unresolved"
    rationale: Text
    missing_evidence: Texts
    contrary_evidence: Texts
    reviewer: Name | None = None
    reviewed_at: Timestamp | None = None


class RequirementAssessment(Record):
    requirement: SourceRef
    obligation_disposition_ids: Ids
    evidence_ids: Ids
    review_ids: Ids
    state: Literal["supported", "conflicting", "unresolved", "outside_declared_assessment"]
    rationale: Text
    gaps: Texts
    next_actions: Texts


def _unique_records(records: list, key=lambda item: item.id) -> dict:
    indexed = {}
    for record in records:
        identity = key(record)
        if identity in indexed:
            raise ValueError("duplicate record identity")
        indexed[identity] = record
    return indexed


def _require_ids(ids: list[str], records: dict) -> None:
    if len(ids) != len(set(ids)) or any(identity not in records for identity in ids):
        raise ValueError("duplicate or dangling reference")


def _require_pin(pin: SourceRef, records: dict) -> None:
    if pin.id not in records or pin.revision != records[pin.id].revision:
        raise ValueError("missing or mismatched record revision")


def scope_facts(scope: Scope) -> list[Fact]:
    """Return explicit fact occurrences only; no project discovery or inference."""
    facts = [*scope.roles, *scope.size_and_sector]
    for activity in scope.activities:
        facts.extend([activity.lawful_basis, *activity.roles, *activity.recipients,
                      *activity.locations, *activity.stores, *activity.retention])
    return facts


def _collection_bounds(record: Record) -> None:
    """Bound nested collections without counting model field names as data items."""
    total = 0
    stack = [(record, 0)]
    while stack:
        item, depth = stack.pop()
        if depth > 32:
            raise ValueError("record exceeds nesting limit")
        if isinstance(item, Record):
            values = [getattr(item, name) for name in type(item).model_fields]
            own_items = sum(len(value) for value in values if isinstance(value, (list, dict)))
            if own_items > 1000:
                raise ValueError("record exceeds nested collection limit")
            stack.extend((value, depth + 1) for value in values)
        elif isinstance(item, (list, dict)):
            total += len(item)
            if len(item) > 1000 or total > 5000:
                raise ValueError("record exceeds aggregate collection limit")
            values = item.values() if isinstance(item, dict) else item
            stack.extend((value, depth + 1) for value in values)


class RevalidationInput(Record):
    schema_version: SchemaVersion
    project_id: Id
    synthetic: bool
    declaration_run_id: Id
    declaration_manifest_id: Id
    scope: Scope
    requirements: Annotated[list[DeclaredRequirement], Field(max_length=200)] = Field(default_factory=list)
    source_targets: Annotated[list[SourceTarget], Field(max_length=16)] = Field(default_factory=list)
    sources: Annotated[list[SelectedSource], Field(max_length=16)] = Field(default_factory=list)
    source_reviews: Annotated[list[SourceReview], Field(max_length=16)] = Field(default_factory=list)
    obligations: Annotated[list[Obligation], Field(max_length=200)] = Field(default_factory=list)
    controls: Annotated[list[Control], Field(max_length=200)] = Field(default_factory=list)
    family_screenings: Annotated[list[FamilyScreening], Field(max_length=11)] = Field(default_factory=list)
    applicability_decisions: Annotated[list[ApplicabilityDecision], Field(max_length=200)] = Field(default_factory=list)
    evidence: Annotated[list[SelectedEvidence], Field(max_length=200)] = Field(default_factory=list)
    evidence_reviews: Annotated[list[EvidenceReview], Field(max_length=200)] = Field(default_factory=list)

    def validate_provisions(self, provisions: list[ProvisionRef]) -> None:
        targets = {item.id for item in self.source_targets}
        sources = {item.source.id: item for item in self.sources}
        for provision in provisions:
            if provision.source_target_id not in targets:
                raise ValueError("provision references missing source target")
            if provision.source_id is not None:
                selected = sources.get(provision.source_id)
                if (selected is None or selected.source.revision != provision.revision
                        or selected.target_id != provision.source_target_id):
                    raise ValueError("provision source/target/revision mismatch")

    @model_validator(mode="after")
    def membership(self) -> RevalidationInput:
        _collection_bounds(self)
        if self.scope.project_id != self.project_id or len(self.scope.activities) > 100:
            raise ValueError("scope project or activity bound mismatch")
        facts = {}
        occurrences = scope_facts(self.scope)
        if len(occurrences) > 500:
            raise ValueError("scope exceeds fact limit")
        for fact in occurrences:
            if fact.id in facts and canonical_json(fact) != canonical_json(facts[fact.id]):
                raise ValueError("conflicting copies of fact identity")
            facts[fact.id] = fact
        activities = _unique_records(self.scope.activities)
        _unique_records(self.requirements)
        targets = _unique_records(self.source_targets)
        sources = _unique_records([item.source for item in self.sources])
        obligations = _unique_records(self.obligations)
        controls = _unique_records(self.controls)
        evidence = _unique_records([item.evidence for item in self.evidence])
        _unique_records(self.applicability_decisions)
        _unique_records(self.applicability_decisions, lambda item: item.obligation.id)
        _unique_records(self.evidence_reviews)
        _unique_records(self.evidence_reviews, lambda item: (item.obligation.id, item.method))
        _unique_records(self.source_reviews, lambda item: (item.source_id, item.source_revision, item.assessment_date))
        _unique_records(self.family_screenings, lambda item: item.family)
        records = [*self.requirements, *self.applicability_decisions, *self.evidence_reviews, *evidence.values()]
        if any(item.project_id != self.project_id for item in records):
            raise ValueError("cross-project declaration")
        if any(item.run_id != self.declaration_run_id or item.manifest_id != self.declaration_manifest_id
               for item in evidence.values()):
            raise ValueError("evidence declaration namespace mismatch")
        for selected in self.sources:
            if selected.target_id not in targets:
                raise ValueError("source references missing target")
            _require_ids(selected.source.related_source_ids, sources)
        for review in self.source_reviews:
            _require_pin(SourceRef(id=review.source_id, revision=review.source_revision), sources)
            for refs in (review.act_chain, review.case_law_refs, review.national_overlay_ids):
                _require_ids(refs, sources)
        for fact in facts.values():
            _require_ids(fact.evidence_ids, evidence)
            _require_ids(fact.conflicts, facts)
        for requirement in self.requirements:
            _require_ids(requirement.activity_ids, activities)
            _require_ids(requirement.evidence_ids, evidence)
            for pin in requirement.fact_refs:
                _require_pin(pin, facts)
            for pin in requirement.obligation_refs:
                _require_pin(pin, obligations)
        for obligation in self.obligations:
            self.validate_provisions(obligation.source_provisions)
            _require_ids(obligation.overlay_ids, sources)
            _require_ids(obligation.control_ids, controls)
        for control in self.controls:
            _require_ids(control.obligation_ids, obligations)
        for decision in self.applicability_decisions:
            _require_pin(decision.obligation, obligations)
            self.validate_provisions(decision.provisions)
            _require_ids(decision.evidence_ids, evidence)
        for item in [*self.applicability_decisions, *self.family_screenings]:
            _require_pin(item.scope, {self.scope.id: self.scope})
            for pin in item.fact_refs:
                _require_pin(pin, facts)
        for screening in self.family_screenings:
            for pin in screening.source_refs:
                _require_pin(pin, sources)
        for review in self.evidence_reviews:
            _require_pin(review.obligation, obligations)
            _require_ids(review.evidence_ids, evidence)
            if review.method not in obligations[review.obligation.id].required_methods:
                raise ValueError("review method not required by obligation")
        synthetic_records = [*self.requirements, *sources.values(), *self.source_reviews,
                             *self.applicability_decisions, *self.evidence_reviews, *self.family_screenings]
        if not self.synthetic and (any(item.synthetic for item in synthetic_records)
                                   or any(item.intended_type == "synthetic_fixture" for item in self.source_targets)):
            raise ValueError("synthetic declarations require a synthetic envelope")
        files = {}
        selected_files = [item.file for item in self.sources if item.file]
        selected_files.extend(item.origin for item in self.requirements if item.origin)
        selected_files.extend(SourceFile(path=item.path, digest=item.evidence.digest)
                              for item in self.evidence if item.path)
        for file in selected_files:
            if file.path in files and files[file.path] != file.digest:
                raise ValueError("conflicting selected file digests")
            files[file.path] = file.digest
        if len(files) > 32:
            raise ValueError("too many selected files")
        return self


class DependencyChange(Record):
    kind: Name
    identity: Text
    before: Digest | None
    after: Digest | None

    @model_validator(mode="after")
    def different(self) -> DependencyChange:
        if self.before == self.after:
            raise ValueError("dependency change needs different digests")
        return self


class DependencyComparison(Record):
    previous_run_id: Id
    previous_manifest_id: Id
    previous_bundle_digest: Digest
    historical_disposition_ids: Annotated[list[Id], Field(max_length=200)]
    changes: Annotated[list[DependencyChange], Field(max_length=1000)]

    @model_validator(mode="after")
    def unique_dependencies(self) -> DependencyComparison:
        _require_ids(self.historical_disposition_ids, dict.fromkeys(self.historical_disposition_ids))
        _unique_records(self.changes, lambda item: (item.kind, item.identity))
        return self


class RevalidationBundle(Record):
    schema_version: SchemaVersion
    project_id: Id
    synthetic: bool
    input_digest: Digest
    run: AuditRun
    manifest: InputManifest
    declarations: RevalidationInput
    evidence: Annotated[list[Evidence], Field(max_length=201)]
    obligation_dispositions: Annotated[list[ObligationDisposition], Field(max_length=200)]
    requirement_assessments: Annotated[list[RequirementAssessment], Field(max_length=200)]
    effective_applicability_decisions: Annotated[list[ApplicabilityDecision], Field(max_length=200)]
    family_screenings: Annotated[list[FamilyScreening], Field(min_length=11, max_length=11)]
    gaps: Texts
    next_actions: Texts
    # One attempt per fetched target; retrieved bytes are unreviewed candidates, never declared sources.
    source_attempts: Annotated[list[SourceAttempt], Field(max_length=16)] = Field(default_factory=list)
    retrieved_sources: Annotated[list[LegalSource], Field(max_length=16)] = Field(default_factory=list)
    comparison: DependencyComparison | None = None
    current_assessments: Annotated[list[CurrentAssessment], Field(max_length=200)] = Field(default_factory=list)

    @model_validator(mode="after")
    def membership(self) -> RevalidationBundle:
        _collection_bounds(self)
        declared = self.declarations
        if (self.project_id != declared.project_id or self.run.project_id != self.project_id
                or self.synthetic != declared.synthetic or self.run.manifest_id != self.manifest.id
                or self.run.permission_id != declared.scope.permission_id
                or self.manifest.scope_revision != declared.scope.revision
                or self.manifest.fixture_digest != self.input_digest):
            raise ValueError("bundle project/synthetic/run/manifest mismatch")
        if self.run.state not in ("partial", "completed"):
            raise ValueError("bundle requires a finished run")
        evidence = _unique_records(self.evidence)
        expected_evidence = {item.evidence.id: item.evidence for item in declared.evidence}
        proof_ids = set(evidence) - set(expected_evidence)
        if self.comparison is None:
            if self.run.parent_run_id is not None or self.current_assessments or proof_ids:
                raise ValueError("first run cannot contain predecessor claims")
        else:
            comparison = self.comparison
            if (self.run.parent_run_id != comparison.previous_run_id or self.run.id == comparison.previous_run_id
                    or self.manifest.id == comparison.previous_manifest_id or len(proof_ids) != 1):
                raise ValueError("comparison predecessor/proof mismatch")
            proof = evidence[next(iter(proof_ids))]
            if (proof.project_id != self.project_id or proof.run_id != self.run.id
                    or proof.manifest_id != self.manifest.id or proof.kind != "dependency_comparison"
                    or proof.digest != content_digest(canonical_json(comparison))
                    or proof.provenance != "observed" or proof.availability != "available"
                    or proof.redaction != "safe" or proof.media_type != "application/json"
                    or proof.attempt_id is not None or proof.source_refs != ["comparison.json"]
                    or proof.browser_context is not None):
                raise ValueError("comparison proof must describe retained comparison metadata")
            overlays = _unique_records(self.current_assessments, lambda item: item.obligation_disposition_id)
            _unique_records(self.current_assessments)
            changed_keys = {f"{item.kind}:{item.identity}" for item in comparison.changes}
            if set(overlays) != set(comparison.historical_disposition_ids):
                raise ValueError("comparison must cover every historical disposition")
            for overlay in overlays.values():
                if (overlay.project_id != self.project_id or overlay.historical_run_id != comparison.previous_run_id
                        or overlay.expected_manifest_id != comparison.previous_manifest_id
                        or overlay.observed_manifest_id != self.manifest.id
                        or overlay.comparison_evidence_ids != [proof.id] or not overlay.reasons):
                    raise ValueError("historical freshness overlay membership mismatch")
                if (bool(overlay.changed_dependencies) != (overlay.freshness == "stale")
                        or not set(overlay.changed_dependencies) <= changed_keys):
                    raise ValueError("stale overlay needs retained changed dependencies")
        if not set(expected_evidence) <= set(evidence):
            raise ValueError("bundle must retain every declared evidence record")
        for identity in expected_evidence:
            item = evidence[identity]
            if (item.project_id != self.project_id or item.run_id != self.run.id
                    or item.manifest_id != self.manifest.id):
                raise ValueError("output evidence membership mismatch")
            original = expected_evidence[item.id]
            if item.model_dump(exclude={"run_id", "manifest_id", "digest", "availability"}) != original.model_dump(exclude={"run_id", "manifest_id", "digest", "availability"}):
                raise ValueError("output evidence changed declared provenance")
            if item.digest != original.digest and item.availability != "corrupt":
                raise ValueError("changed evidence digest must remain corrupt")
            if original.availability != "available" and item.availability == "available":
                raise ValueError("offline observation cannot upgrade unavailable evidence")
        obligations = {item.id: item for item in declared.obligations}
        requirements = {item.id: item for item in declared.requirements}
        reviews = {item.id: item for item in declared.evidence_reviews}
        decisions = _unique_records(self.effective_applicability_decisions)
        by_obligation = _unique_records(self.effective_applicability_decisions, lambda item: item.obligation.id)
        dispositions = _unique_records(self.obligation_dispositions)
        by_disposition = _unique_records(self.obligation_dispositions, lambda item: item.obligation_id)
        assessments = _unique_records(self.requirement_assessments, lambda item: item.requirement.id)
        if set(by_obligation) != set(obligations) or set(by_disposition) != set(obligations) or set(assessments) != set(requirements):
            raise ValueError("bundle must cover every requirement and obligation")
        source_by_id = {item.source.id: item.source for item in declared.sources}
        facts = {item.id: item for item in scope_facts(declared.scope)}
        observed_files = {item.path: item.digest for item in self.manifest.source_files}
        selected_sources = {item.source.id: item for item in declared.sources}
        selected_evidence = {item.evidence.id: item for item in declared.evidence}
        targets = {item.id: item for item in declared.source_targets}
        source_reviews = {(item.source_id, item.assessment_date): item for item in declared.source_reviews}
        attempts = _unique_records(self.source_attempts)
        _unique_records(self.source_attempts, lambda item: item.source_target_id)
        retrieved = _unique_records(self.retrieved_sources)
        if set(retrieved) & set(source_by_id):
            raise ValueError("retrieved candidate identity collides with a declared source")
        referenced = set()
        for attempt in attempts.values():
            target = targets.get(attempt.source_target_id)
            retrieval = attempt.retrieval
            if target is None or retrieval is None or (
                    attempt.intended_url, attempt.intended_identifier, attempt.publisher, attempt.intended_type, attempt.language
                    ) != (target.intended_url, target.intended_identifier, target.publisher, target.intended_type, target.language):
                raise ValueError("source attempt must record provenance for its declared target")
            prior = None
            if attempt.last_successful_source is not None:
                _require_pin(attempt.last_successful_source, source_by_id)
                if selected_sources[attempt.last_successful_source.id].target_id != target.id:
                    raise ValueError("last successful source belongs to another target")
                prior = source_by_id[attempt.last_successful_source.id]
            expected = ("not_compared" if attempt.retrieved_source is None else "no_prior_source" if prior is None
                        else "same_bytes" if retrieval.digest == prior.content_digest else "different_bytes")
            if retrieval.comparison != expected:
                raise ValueError("retrieval comparison disagrees with the declared source")
            if attempt.retrieved_source is not None:
                _require_pin(attempt.retrieved_source, retrieved)
                source = retrieved[attempt.retrieved_source.id]
                if ((source.type, source.publisher, source.identifier, source.language, source.jurisdiction)
                        != (target.intended_type, target.publisher, target.intended_identifier, target.language, target.jurisdiction)
                        or source.url != retrieval.final_url or source.content_digest != retrieval.digest
                        or source.retrieved_at != retrieval.ended_at or source.provisions or source.related_source_ids):
                    raise ValueError("retrieved candidate must mirror its target and provenance without reviewed provisions")
                referenced.add(source.id)
        if referenced != set(retrieved):
            raise ValueError("every retrieved candidate needs exactly one attempt")
        changed_targets = {item.source_target_id for item in attempts.values() if item.retrieval.comparison == "different_bytes"}

        def admitted_source(source_id: str) -> bool:
            pending = [source_id]
            seen = set()
            while pending:
                identity = pending.pop()
                if identity in seen:
                    continue
                seen.add(identity)
                selected = selected_sources[identity]
                source = selected.source
                target = targets[selected.target_id]
                review = source_reviews.get((identity, declared.scope.assessment_date))
                if not (
                        selected.target_id not in changed_targets
                        and selected.file and observed_files.get(selected.file.path) == source.content_digest
                        and selected.media_type.lower() in ("text/plain", "text/html", "application/xhtml+xml")
                        and (selected.charset is None or selected.charset.lower() == "utf-8")
                        and source.type == target.intended_type and source.url == target.intended_url
                        and source.identifier == target.intended_identifier and source.publisher == target.publisher
                        and source.language == target.language and source.jurisdiction == target.jurisdiction
                        and review and review.state == "reviewed_for_assessment"
                        and review.reviewer and review.reviewer.strip() and review.last_successful_verification
                        and not review.gaps and all(review.review_notes.get(topic, "").strip()
                                                   for topic in get_args(SourceReviewTopic))):
                    return False
                pending.extend([*source.related_source_ids, *review.act_chain,
                                *review.case_law_refs, *review.national_overlay_ids])
            return True

        def retained_evidence(identity: str) -> bool:
            item = evidence[identity]
            selected = selected_evidence[identity]
            return bool(item.availability == "available" and item.redaction == "safe"
                        and item.digest == selected.evidence.digest and selected.path
                        and observed_files.get(selected.path) == item.digest)

        def admitted_evidence(identity: str) -> bool:
            item = evidence[identity]
            proof = item.provenance != "independently_verified" or any(
                ref != identity and ref in evidence and retained_evidence(ref)
                and evidence[ref].provenance in ("documented", "observed") for ref in item.source_refs)
            return retained_evidence(identity) and proof

        for decision in decisions.values():
            if decision.project_id != self.project_id:
                raise ValueError("effective decision project mismatch")
            _require_pin(decision.obligation, obligations)
            _require_pin(decision.scope, {declared.scope.id: declared.scope})
            declared.validate_provisions(decision.provisions)
            _require_ids(decision.evidence_ids, evidence)
            for pin in decision.fact_refs:
                _require_pin(pin, facts)
            obligation = obligations[decision.obligation.id]
            dependency_pins = [*obligation.source_provisions, *decision.provisions]
            synthetic_dependency = any(source_by_id[pin.source_id].synthetic for pin in dependency_pins if pin.source_id)
            synthetic_dependency |= any(item.synthetic and any(pin.id == decision.obligation.id for pin in item.obligation_refs)
                                        for item in declared.requirements)
            synthetic_dependency |= any(item.synthetic and item.obligation.id == decision.obligation.id
                                        for item in declared.applicability_decisions)
            synthetic_dependency |= any(item.synthetic and item.obligation.id == decision.obligation.id
                                        for item in declared.evidence_reviews)
            synthetic_dependency |= any(item.synthetic and any(pin.source_id == item.source_id for pin in dependency_pins)
                                        for item in declared.source_reviews)
            synthetic_dependency |= declared.synthetic and not any(
                item.id == decision.id for item in declared.applicability_decisions)
            if synthetic_dependency and not decision.synthetic:
                raise ValueError("effective decision lost synthetic provenance")
            if decision.synthetic and not self.synthetic:
                raise ValueError("synthetic effective decision in real bundle")
            original = next((item for item in declared.applicability_decisions if item.id == decision.id), None)
            if decision.applicability != "unresolved" and (
                    original is None or decision.model_dump(exclude={"synthetic"}) != original.model_dump(exclude={"synthetic"})
                    or not decision.reviewer or not decision.reviewer.strip() or not decision.reviewed_at
                    or not decision.rationale.strip() or decision.gaps
                    or decision.assessment_date != declared.scope.assessment_date
                    or not decision.fact_refs or any(facts[pin.id].basis in ("assumed", "unknown") or facts[pin.id].conflicts
                        or any(not admitted_evidence(eid) for eid in facts[pin.id].evidence_ids)
                        for pin in decision.fact_refs)
                    or not decision.jurisdictions or any(j not in declared.scope.jurisdictions for j in decision.jurisdictions)
                    or not decision.provisions or any(pin.source_id is None or not pin.locator.strip()
                        or pin.locator not in source_by_id[pin.source_id].provisions
                        or not admitted_source(pin.source_id) for pin in decision.provisions)
                    or not decision.condition_answers or not all(answer.strip() for answer in decision.condition_answers)
                    or not decision.exception_answers or not all(answer.strip() for answer in decision.exception_answers)
                    or not all(admitted_evidence(identity) for identity in decision.evidence_ids)
                    or not all(admitted_source(identity) for identity in obligation.overlay_ids)
                    or not all(pin in decision.provisions for pin in obligation.source_provisions)):
                raise ValueError("resolved effective decision lacks accountable review")
        for disposition in dispositions.values():
            if disposition.project_id != self.project_id or disposition.run_id != self.run.id:
                raise ValueError("disposition membership mismatch")
            _require_pin(SourceRef(id=disposition.obligation_id, revision=disposition.obligation_revision), obligations)
            decision = decisions.get(disposition.applicability_decision_id)
            if decision is None or decision.obligation.id != disposition.obligation_id or decision.applicability != disposition.applicability:
                raise ValueError("disposition decision mismatch")
            methods = {item.method for item in disposition.required_method_dispositions}
            if methods != set(obligations[disposition.obligation_id].required_methods):
                raise ValueError("disposition must retain every required method")
            for method in disposition.required_method_dispositions:
                _require_ids(method.review_ids, reviews)
                if method.attempt_ids or (method.method == "technical" and method.outcome != "not_tested"):
                    raise ValueError("offline legal workflow cannot invent technical attempts")
                for review_id in method.review_ids:
                    review = reviews[review_id]
                    if review.obligation.id != disposition.obligation_id or review.method != method.method:
                        raise ValueError("method review membership mismatch")
                if method.outcome == "passed" and (
                        decision.applicability != "applicable" or decision.gaps
                        or not method.review_ids
                        or not all(admitted_source(identity) for identity in obligations[disposition.obligation_id].overlay_ids)
                        or not obligations[disposition.obligation_id].source_provisions
                        or any(pin.source_id is None or not admitted_source(pin.source_id)
                               or (obligations[disposition.obligation_id].classification == "duty"
                                   and source_by_id[pin.source_id].type not in
                                   ("eu_act", "national_act", "judgment", "synthetic_fixture"))
                               for pin in obligations[disposition.obligation_id].source_provisions)
                        or any(
                            reviews[identity].state != "reviewed" or not reviews[identity].reviewer
                            or not reviews[identity].reviewer.strip() or not reviews[identity].reviewed_at
                            or not reviews[identity].rationale.strip() or not reviews[identity].period.strip()
                            or not reviews[identity].owner.strip() or reviews[identity].missing_evidence
                            or reviews[identity].contrary_evidence or not reviews[identity].evidence_ids
                            or not all(admitted_evidence(eid) for eid in reviews[identity].evidence_ids)
                            for identity in method.review_ids)):
                    raise ValueError("passed documentary method lacks admitted sources, applicability or evidence")
                if method.outcome == "observed_failure" and not any(
                        reviews[identity].state == "insufficient" and reviews[identity].reviewer
                        and reviews[identity].reviewer.strip() and reviews[identity].reviewed_at
                        and reviews[identity].rationale.strip() for identity in method.review_ids):
                    raise ValueError("documentary failure lacks an accountable insufficient review")
        for assessment in self.requirement_assessments:
            _require_pin(assessment.requirement, requirements)
            _require_ids(assessment.obligation_disposition_ids, dispositions)
            _require_ids(assessment.evidence_ids, evidence)
            _require_ids(assessment.review_ids, reviews)
            requirement = requirements[assessment.requirement.id]
            mapped = {pin.id for pin in requirement.obligation_refs}
            if {dispositions[identity].obligation_id for identity in assessment.obligation_disposition_ids} != mapped:
                raise ValueError("requirement assessment mapping mismatch")
            if any(reviews[identity].obligation.id not in mapped for identity in assessment.review_ids):
                raise ValueError("requirement review does not belong to a mapped obligation")
            if assessment.state == "supported" and (
                    not mapped or assessment.gaps or not assessment.rationale.strip()
                    or not set(requirement.evidence_ids) <= set(assessment.evidence_ids)
                    or any(not admitted_evidence(identity) for identity in assessment.evidence_ids)
                    or any(facts[pin.id].basis in ("assumed", "unknown") or facts[pin.id].conflicts
                           or any(not admitted_evidence(identity) for identity in facts[pin.id].evidence_ids)
                           for pin in requirement.fact_refs)
                    or (requirement.origin is not None
                        and observed_files.get(requirement.origin.path) != requirement.origin.digest)
                    or any(dispositions[identity].manual_review != "supported"
                           or dispositions[identity].applicability != "applicable"
                           or not dispositions[identity].required_method_dispositions
                           or any(method.outcome != "passed" for method in dispositions[identity].required_method_dispositions)
                           for identity in assessment.obligation_disposition_ids)):
                raise ValueError("supported requirement lacks complete supported mapping")
            if assessment.state == "outside_declared_assessment" and not assessment.rationale.strip():
                raise ValueError("outside assessment needs a reasoned exclusion")
        screenings = _unique_records(self.family_screenings, lambda item: item.family)
        if set(screenings) != set(LEGAL_FAMILIES):
            raise ValueError("bundle must screen every candidate legal family")
        for item in self.family_screenings:
            _require_pin(item.scope, {declared.scope.id: declared.scope})
            if item.synthetic and not self.synthetic:
                raise ValueError("synthetic screening in real bundle")
            for pin in item.fact_refs:
                _require_pin(pin, facts)
            for pin in item.source_refs:
                _require_pin(pin, source_by_id)
            synthetic_dependency = any(original.family == item.family and original.synthetic for original in declared.family_screenings)
            synthetic_dependency |= any(source_by_id[pin.id].synthetic for pin in item.source_refs)
            synthetic_dependency |= any(review.synthetic and any(pin.id == review.source_id for pin in item.source_refs)
                                        for review in declared.source_reviews)
            synthetic_dependency |= declared.synthetic and not any(original.family == item.family for original in declared.family_screenings)
            if synthetic_dependency and not item.synthetic:
                raise ValueError("screening lost synthetic provenance")
            original = next((original for original in declared.family_screenings if original.family == item.family), None)
            if item.applicability != "unresolved" and (
                    original is None or item.model_dump(exclude={"synthetic"}) != original.model_dump(exclude={"synthetic"})
                    or item.assessment_date != declared.scope.assessment_date or not item.reviewer
                    or not item.reviewer.strip() or not item.reviewed_at or not item.rationale.strip()
                    or item.gaps or not item.fact_refs or not item.source_refs
                    or any(facts[pin.id].basis in ("assumed", "unknown") or facts[pin.id].conflicts
                           or any(not admitted_evidence(eid) for eid in facts[pin.id].evidence_ids)
                           for pin in item.fact_refs)
                    or not all(admitted_source(pin.id) for pin in item.source_refs)):
                raise ValueError("resolved screening lacks accountable admitted review")
        if self.run.state == "completed" and (self.gaps or self.run.gaps or not requirements or not obligations
                or self.source_attempts or self.retrieved_sources
                or any(item.gaps or item.state in ("unresolved", "conflicting") for item in self.requirement_assessments)
                or any(item.gaps or item.applicability == "unresolved" for item in decisions.values())
                or any(item.manual_review in ("pending", "unresolved")
                       or any(method.outcome in ("unresolved_review", "blocked", "not_tested", "lead")
                              or method.missing_evidence for method in item.required_method_dispositions)
                       for item in dispositions.values())
                or any(not admitted_source(identity) or not source.synthetic for identity, source in source_by_id.items())
                or any(not admitted_evidence(identity) for identity in expected_evidence)
                or any(item.freshness != "current_for_recorded_inputs" for item in self.current_assessments)
                or any(item.gaps or item.applicability == "unresolved" for item in self.family_screenings)):
            raise ValueError("completed processing cannot hide open gaps")
        if len(self.manifest.source_files) > 32 or self.manifest.browser_state is not None or self.manifest.graph_digest is not None:
            raise ValueError("manifest exceeds offline workflow scope")
        return self


class RunCompletion(Record):
    schema_version: SchemaVersion
    run_id: Id
    files: Annotated[list[SourceFile], Field(min_length=4, max_length=37)]

    @model_validator(mode="after")
    def artifact_paths(self) -> RunCompletion:
        files = _unique_records(self.files, lambda item: item.path)
        required = {"input.json", "manifest.json", "bundle.json", "report.md"}
        if not required <= files.keys():
            raise ValueError("completion marker is missing required artifacts")
        for path, file in files.items():
            if path not in required | {"comparison.json"} and path != "sources/" + file.digest.removeprefix("sha256:") + ".bin":
                raise ValueError("completion marker contains a nongenerated artifact path")
        return self
