"""Validated shared records and closed commands; authorization belongs to the engine."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import hashlib
import json
from typing import Annotated, Literal, TypeVar
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
Value = Annotated[JsonValue, AfterValidator(_json_value)]
Ids = Annotated[list[Id], Field(max_length=1000)]
Texts = Annotated[list[Text], Field(max_length=1000)]

Applicability = Literal["applicable", "not_applicable", "unresolved"]
Outcome = Literal["passed", "observed_failure", "unresolved_review", "blocked", "not_tested", "lead"]
Freshness = Literal["current_for_recorded_inputs", "stale", "unknown"]
RunState = Literal["planned", "running", "cancelling", "completed", "partial", "cancelled", "interrupted"]
PatchState = Literal["proposed", "running", "applied-awaiting-verification", "verified", "failed", "blocked"]
SourceType = Literal["eu_act", "national_act", "judgment", "final_guidance", "draft_guidance", "proposal", "standard", "engineering_practice", "synthetic_fixture"]
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

    @model_validator(mode="after")
    def retrieval_state(self) -> SourceAttempt:
        if self.state == "retrieved" and (self.retrieved_source is None or self.failure is not None):
            raise ValueError("retrieved attempt requires source and no failure")
        if self.state != "retrieved" and self.failure is None:
            raise ValueError("unsuccessful attempt requires a safe failure reason")
        if self.state == "retrieval_failed" and self.retrieved_source is not None:
            raise ValueError("failed retrieval cannot invent a retrieved source")
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
