"""Bounded offline declarations and selected files; no discovery or legal inference.

The recorded 300-second budget is cooperative, not hard containment or an I/O deadline.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import math
import os
from pathlib import Path
import re
import stat
import time
from typing import get_args
from uuid import uuid4

from pydantic import ValidationError

from . import __version__, models as m

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_REPORT_BYTES = 16 * 1024 * 1024
CHUNK_BYTES = 64 * 1024
BUDGET_SECONDS = 300
ERRORS = {
    "invalid-input": "Declaration input is invalid.",
    "unsafe-path": "An explicit path could not be opened safely.",
    "capacity-exceeded": "An offline processing limit was exceeded.",
    "io-failed": "An offline file operation failed.",
    "output-exists": "The output location already exists.",
    "privacy-unavailable": "Required private file primitives or parent permissions are unavailable.",
    "budget-exceeded": "The cooperative processing budget was exceeded.",
    "invalid-output": "The assembled output could not be validated.",
    "retrieval-failed": "The official-source retrieval helper could not be stopped safely.",
}
FAMILY_DESCRIPTIONS = dict(zip(m.LEGAL_FAMILIES, (
    "GDPR: processing roles, lawful bases, transparency, minimization, rights, retention, security, vendors, transfers, accountability and risk assessments.",
    "ePrivacy and national implementations: device storage/access, tracking and electronic marketing.",
    "Online-service identity and commercial disclosures.",
    "Consumer contracts, digital content/services, subscriptions, pricing, withdrawal, refunds, unfair terms and commercial practices.",
    "Accessibility requirements for covered services/products.",
    "Intermediary, hosting and platform responsibilities, including the DSA; marketplace or gatekeeper rules where relevant.",
    "AI Act responsibilities according to activity, role and risk classification.",
    "Cybersecurity and software-product responsibilities, including NIS2 and the Cyber Resilience Act where relevant.",
    "Connected-product/data-processing responsibilities, including the Data Act where relevant.",
    "Copyright, content permissions and software/asset licensing.",
    "Additional sector or national rules discovered from facts, including financial, health, employment, children and product-safety contexts; unsupported specialist review must be exposed.",
)))
POLICY = {"workflow": "offline-declared-review-v1", "tool_version": __version__,
          "budget": "cooperative-only", "network": False, "technical_execution": False}
LANGUAGE = re.compile(rb"<html\b[^>]{0,2048}?\blang\s*=\s*[\"']?([A-Za-z]{1,8})", re.I)


class RevalidationError(ValueError):
    """Only fixed tool-owned codes/messages may cross the diagnostic boundary."""
    def __init__(self, code: str):
        self.code = code if code in ERRORS else "io-failed"
        super().__init__(ERRORS[self.code])


def _output_validation_error(error: ValidationError) -> RevalidationError:
    bounds = {"record exceeds nested collection limit", "record exceeds aggregate collection limit", "record exceeds nesting limit"}
    for detail in error.errors(include_input=False, include_url=False):
        reason = detail.get("ctx", {}).get("error")
        if detail["type"] in ("too_long", "string_too_long", "bytes_too_long") or (
                isinstance(reason, ValueError) and reason.args and reason.args[0] in bounds):
            return RevalidationError("capacity-exceeded")
    return RevalidationError("invalid-output")


@dataclass(frozen=True)
class FileObservation:
    availability: str
    digest: str | None = None
    content: bytes | None = None  # Only explicitly selected source bytes, never evidence-only bodies.
    size: int = 0


@dataclass(frozen=True)
class ContentAdmission:
    state: str
    reason: str


def _check_budget(deadline: float | None) -> None:
    if deadline is not None and time.monotonic() > deadline:
        raise RevalidationError("budget-exceeded")


def _primitives() -> None:
    if (os.name != "posix" or not all(hasattr(os, flag) for flag in
            ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY", "O_CLOEXEC", "geteuid"))
            or not {os.open, os.mkdir, os.unlink} <= os.supports_dir_fd
            or not all(hasattr(os, name) for name in ("fchmod", "fsync"))):
        raise RevalidationError("privacy-unavailable")


@contextmanager
def _parent(path: str | os.PathLike, base_fd: int | None = None):
    """Walk named directory components only, anchored at an already opened descriptor."""
    path = Path(path)
    if ".." in path.parts or not path.name:
        raise RevalidationError("unsafe-path")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open("/" if path.is_absolute() else ".", flags) if base_fd is None else os.dup(base_fd)
    try:
        parts = path.parts[1:] if path.is_absolute() else path.parts
        if base_fd is not None and path.is_absolute():
            raise RevalidationError("unsafe-path")
        for part in parts[:-1]:
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        yield fd, path.name
    finally:
        os.close(fd)


def _read_file(parent_fd: int, path: str, *, limit: int, retain: bool,
               deadline: float | None = None) -> FileObservation:
    _check_budget(deadline)
    try:
        with _parent(path, parent_fd) as (fd, name):
            file_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=fd)
    except FileNotFoundError:
        return FileObservation("missing")
    except OSError:
        return FileObservation("blocked")
    try:
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode):
            return FileObservation("blocked")
        if before.st_size > limit:
            raise RevalidationError("capacity-exceeded")
        digest = hashlib.sha256()
        chunks = [] if retain else None
        size = 0
        while True:
            _check_budget(deadline)
            chunk = os.read(file_fd, min(CHUNK_BYTES, limit - size + 1))
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                raise RevalidationError("capacity-exceeded")
            digest.update(chunk)
            if chunks is not None:
                chunks.append(chunk)
        after = os.fstat(file_fd)
        fingerprint = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        stable = fingerprint(before) == fingerprint(after) and size == after.st_size
        return FileObservation("available" if stable else "corrupt", "sha256:" + digest.hexdigest(),
                               b"".join(chunks) if chunks is not None and stable else None, size)
    except OSError:
        return FileObservation("blocked")
    finally:
        os.close(file_fd)


def _check_json_depth(raw: bytes) -> None:
    depth = 0
    quoted = escaped = False
    for char in raw:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):
            depth += 1
            if depth > 32:
                raise RevalidationError("capacity-exceeded")
        elif char in (93, 125):
            depth -= 1


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise RevalidationError("invalid-input")
        value[key] = item
    return value


def _finite(value: str):
    number = float(value)
    if not math.isfinite(number):
        raise RevalidationError("invalid-input")
    return number


def _reject_constant(value: str):
    raise RevalidationError("invalid-input")


def _derived_id(prefix: str, identity: str) -> str:
    return prefix + "-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _load(parent_fd: int, name: str, deadline: float | None = None):
    observation = _read_file(parent_fd, name, limit=m.MAX_REQUEST_BYTES, retain=True, deadline=deadline)
    if observation.availability != "available":
        raise RevalidationError("unsafe-path")
    raw = observation.content
    _check_json_depth(raw)
    try:
        json.loads(raw, object_pairs_hook=_pairs, parse_float=_finite, parse_constant=_reject_constant)
        declared = m.parse_record(m.RevalidationInput, raw)
    except (ValueError, RecursionError, UnicodeError) as error:
        if isinstance(error, RevalidationError):
            raise
        raise RevalidationError("invalid-input") from None
    supplied = {item.id for records in (
        [declared.scope], declared.requirements, declared.source_targets, [item.source for item in declared.sources],
        declared.obligations, declared.controls, declared.applicability_decisions,
        [item.evidence for item in declared.evidence], declared.evidence_reviews,
        m.scope_facts(declared.scope), declared.scope.activities) for item in records}
    for obligation in declared.obligations:
        if (any(_derived_id(prefix, obligation.id) in supplied for prefix in ("unresolved", "disposition"))
                or len(obligation.required_methods) != len(set(obligation.required_methods))):
            raise RevalidationError("invalid-input")
        try:
            for method in obligation.required_methods:
                m.MethodDisposition(method=method, outcome="unresolved_review", attempt_ids=[], review_ids=[], missing_evidence=[])
        except ValidationError:
            raise RevalidationError("invalid-input") from None
    return declared, observation.digest


def load_input(path: str | os.PathLike) -> m.RevalidationInput:
    """Validate bounded declarations without opening any selected source/evidence file."""
    _primitives()
    try:
        with _parent(path) as (fd, name):
            return _load(fd, name)[0]
    except OSError:
        raise RevalidationError("unsafe-path") from None


class _HTMLSignals(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = set()
        self.password = False
        self.in_title = False
        self.title = []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag)
        self.in_title |= tag == "title"
        self.password |= tag == "input" and any(key == "type" and str(value).lower() == "password" for key, value in attrs)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)


def admit_source_content(content: bytes, media_type: str, charset: str | None = None) -> ContentAdmission:
    """Conservative format/page screening, never proof of document identity or authority."""
    media_type = media_type.lower()
    if media_type not in ("text/plain", "text/html", "application/xhtml+xml", "application/pdf"):
        return ContentAdmission("needs_review", "unsupported-format")
    if media_type == "application/pdf":
        if charset is not None or not content.startswith(b"%PDF-"):
            return ContentAdmission("needs_review", "format-mismatch")
        return ContentAdmission("needs_review", "pdf-manual-identity-review")
    if charset is not None and charset.lower() != "utf-8":
        return ContentAdmission("needs_review", "unsupported-charset")
    try:
        text = content.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return ContentAdmission("needs_review", "invalid-utf8")
    if not text.strip() or content.startswith(b"%PDF-") or any(ord(char) < 32 and char not in "\n\r\t" for char in text):
        return ContentAdmission("needs_review", "format-mismatch")
    markup = bool(re.search(r"<\s*(?:!doctype|\?xml|[a-z][\w:-]*(?:\s|>|/))", text, re.I))
    signals = _HTMLSignals()
    if markup:
        try:
            signals.feed(text)
        except (AssertionError, ValueError):
            return ContentAdmission("needs_review", "uncertain-html")
    title = " ".join(signals.title).lower()
    lowered = text.lower()
    markers = ("verify you are human", "checking your browser", "captcha", "access denied", "cloudflare ray id",
               "service unavailable", "internal server error", "page not found", "404 not found",
               "just a moment", "cf-chl-", "browser verification", "sign in to continue", "please log in", "please sign in",
               "sign in to access", "log in to access", "login required",
               "authentication required", "enable javascript and cookies to continue")
    if (signals.password or any(marker in lowered for marker in markers)
            or any(marker in title for marker in ("login", "log in", "sign in", "challenge", "error", "403", "404", "503"))
            or ("form" in signals.tags and any(marker in lowered for marker in ("login", "log in", "sign in")))):
        return ContentAdmission("rejected", "login-challenge-error-page")
    if media_type == "text/plain" and markup:
        return ContentAdmission("needs_review", "format-mismatch")
    if media_type != "text/plain" and (not markup or not {"html", "body"} <= signals.tags):
        return ContentAdmission("needs_review", "uncertain-html")
    return ContentAdmission("accepted", "content-only-not-authority")


def _selected_files(declared: m.RevalidationInput) -> dict[str, str]:
    files = {item.file.path: item.file.digest for item in declared.sources if item.file}
    files.update((item.origin.path, item.origin.digest) for item in declared.requirements if item.origin)
    files.update((item.path, item.evidence.digest) for item in declared.evidence if item.path)
    return files


def _observe(declared: m.RevalidationInput, parent_fd: int, deadline: float) -> dict[str, FileObservation]:
    source_paths = {item.file.path for item in declared.sources if item.file}
    observations = {}
    total = 0
    for path in _selected_files(declared):
        observation = _read_file(parent_fd, path, limit=min(MAX_FILE_BYTES, MAX_TOTAL_BYTES - total),
                                 retain=path in source_paths, deadline=deadline)
        total += observation.size
        observations[path] = observation
    return observations


def _json_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def fetch_policy() -> dict:
    from .sources import OFFICIAL_HOSTS
    return {**POLICY, "workflow": "official-retrieval-declared-review-v1", "network": "selected-official-sources",
            "official_hosts": sorted(OFFICIAL_HOSTS)}


def _retrieval_review(content: bytes, media_type: str, target: m.SourceTarget) -> list[str]:
    """Conservative identity/language signals; their absence never proves document identity."""
    if media_type == "application/pdf":
        return []
    reasons = []
    if target.intended_identifier and target.intended_identifier.lower().encode("utf-8") not in content.lower():
        reasons.append("intended-identifier-not-found")
    declared = LANGUAGE.search(content[:CHUNK_BYTES]) if media_type != "text/plain" else None
    if declared and declared.group(1).decode("ascii").lower() != target.language.split("-")[0].lower():
        reasons.append("declared-language-unverified")
    return reasons


def assemble(declarations: m.RevalidationInput, observations: dict[str, FileObservation], *,
             input_digest: str, timestamp: str, run_id: str, manifest_id: str,
             retrievals: list | None = None) -> m.RevalidationBundle:
    """Pure recorded-review assembly; observations/time/IDs/retrieval results are explicit testable inputs."""
    from .sources import FAILURES
    declared = m.RevalidationInput.model_validate(declarations)
    gaps = []
    actions = []
    facts = {item.id: item for item in m.scope_facts(declared.scope)}
    sources = {item.source.id: item for item in declared.sources}
    targets = {item.id: item for item in declared.source_targets}
    source_reviews = {(item.source_id, item.assessment_date): item for item in declared.source_reviews}
    evidence = {}
    selected_evidence = {item.evidence.id: item for item in declared.evidence}
    source_gaps = {}

    def record_gap(message):
        if message not in gaps:
            gaps.append(message)
            actions.append("Resolve recorded gap: " + message)

    attempts, candidates, outcomes = [], [], {}
    prior_by_target = {}
    for item in declared.sources:
        prior_by_target.setdefault(item.target_id, item.source)
    for result in retrievals or []:
        target = targets[result.target_id]
        if result.requested_url != target.intended_url:
            raise RevalidationError("invalid-output")
        prior = prior_by_target.get(target.id)
        failure, admission, reasons = result.failure, None, []
        digest = m.content_digest(result.content) if result.content is not None else None
        if failure is None:
            admission = admit_source_content(result.content, result.media_type, result.charset)
            reasons = _retrieval_review(result.content, result.media_type, target)
            if admission.state == "rejected":
                failure = "content-rejected"
        retained = failure is None
        candidate = None
        if retained:
            candidate = m.LegalSource(id=_derived_id("retrieved", f"{target.id}:{digest}"), revision=0,
                type=target.intended_type, publisher=target.publisher, identifier=target.intended_identifier,
                url=result.final_url, language=target.language, jurisdiction=target.jurisdiction,
                retrieved_at=result.ended_at, content_digest=digest, provisions=[], related_source_ids=[],
                synthetic=target.intended_type == "synthetic_fixture")
            candidates.append(candidate)
        comparison = ("not_compared" if not retained else "no_prior_source" if prior is None
                      else "same_bytes" if prior.content_digest == digest else "different_bytes")
        translation = "declared-language-unverified" in reasons
        state = "retrieval_failed" if not retained else "translation_unverified" if translation else "retrieved"
        safe = None
        if failure is not None:
            safe = m.SafeError(code=failure, safe_message=FAILURES.get(failure, "Retrieved content looks like a login, challenge or error page."))
        elif translation:
            safe = m.SafeError(code="language-unverified", safe_message="Retrieved page language differs from the target; translation is unverified.")
        provenance = m.RetrievalProvenance(requested_url=result.requested_url,
            final_url=result.final_url if result.content is not None else None, redirects=list(result.redirects),
            started_at=result.started_at, ended_at=result.ended_at, status=result.status,
            media_type=result.media_type, charset=result.charset, bytes_read=result.bytes_read, digest=digest,
            artifact_path="sources/" + digest.removeprefix("sha256:") + ".bin" if retained else None,
            admission=admission.state if admission else None, admission_reason=admission.reason if admission else None,
            comparison=comparison)
        attempts.append(m.SourceAttempt(id=_derived_id("attempt", f"{run_id}:{target.id}"), source_target_id=target.id,
            intended_url=target.intended_url, intended_identifier=target.intended_identifier, publisher=target.publisher,
            intended_type=target.intended_type, language=target.language, attempted_at=result.started_at, state=state,
            retrieved_source=m.SourceRef(id=candidate.id, revision=0) if candidate else None,
            last_successful_source=m.SourceRef(id=prior.id, revision=prior.revision) if prior else None,
            failure=safe, retrieval=provenance))
        if not retained:
            record_gap(f"Source target {target.id}: official retrieval failed ({failure}); no fresh content was recorded.")
            outcomes[target.id] = "unconfirmed"
            continue
        record_gap(f"Source target {target.id}: retrieved candidate {candidate.id} requires accountable source review; "
                   "official hosting establishes neither binding status, completeness, applicability nor currency.")
        if admission.state != "accepted":
            record_gap(f"Source target {target.id}: retrieved content needs review ({admission.reason}).")
        for reason in reasons:
            record_gap(f"Source target {target.id}: retrieved content needs review ({reason}).")
        outcomes[target.id] = ("changed" if comparison == "different_bytes" else "confirmed"
                               if comparison == "same_bytes" and state == "retrieved" and admission.state == "accepted" and not reasons
                               else "unconfirmed")

    for selected in declared.evidence:
        item = selected.evidence
        observation = observations.get(selected.path, FileObservation("missing"))
        availability = item.availability
        if observation.digest is not None and observation.digest != item.digest:
            availability = "corrupt"
        elif availability == "available":
            availability = observation.availability
        updated = item.model_dump()
        updated.update(run_id=run_id, manifest_id=manifest_id, availability=availability,
                       digest=observation.digest or item.digest)
        evidence[item.id] = m.Evidence.model_validate(updated)

    def retained_evidence(identity):
        item = evidence[identity]
        selected = selected_evidence[identity]
        observation = observations.get(selected.path)
        return bool(item.availability == "available" and item.redaction == "safe" and selected.path
                    and observation and observation.availability == "available" and observation.digest == selected.evidence.digest)

    def evidence_ready(identity):
        item = evidence[identity]
        return retained_evidence(identity) and (item.provenance != "independently_verified" or any(
            ref != identity and ref in evidence and retained_evidence(ref)
            and evidence[ref].provenance in ("documented", "observed") for ref in item.source_refs))

    for identity in evidence:
        if not evidence_ready(identity):
            record_gap(f"Evidence {identity}: availability, redaction or independent verification proof unresolved.")
    for fact in facts.values():
        if fact.basis in ("assumed", "unknown") or fact.conflicts:
            record_gap(f"Fact {fact.id}: assumed, unknown or conflicting declaration needs review.")
    for selected in declared.sources:
        source = selected.source
        problems = []
        observation = observations.get(selected.file.path) if selected.file else None
        if not observation or observation.availability != "available" or observation.digest != source.content_digest or observation.content is None:
            problems.append("selected content unavailable or corrupt")
        else:
            admission = admit_source_content(observation.content, selected.media_type, selected.charset)
            if admission.state != "accepted":
                problems.append(admission.reason)
        target = targets[selected.target_id]
        if any(getattr(source, field) != getattr(target, target_field) for field, target_field in (
                ("type", "intended_type"), ("url", "intended_url"), ("identifier", "intended_identifier"),
                ("publisher", "publisher"), ("language", "language"), ("jurisdiction", "jurisdiction"))):
            problems.append("candidate identity/classification disagrees with selected source")
        if target.family not in m.LEGAL_FAMILIES:
            problems.append("unsupported source topic requires specialist/national research")
        review = source_reviews.get((source.id, declared.scope.assessment_date))
        if not review or review.state != "reviewed_for_assessment" or not review.reviewer or not review.reviewer.strip() or not review.last_successful_verification:
            problems.append("accountable source review missing for assessment date")
        if review:
            problems.extend("source review gap: " + gap for gap in review.gaps)
        for topic in get_args(m.SourceReviewTopic):
            if not review or not review.review_notes.get(topic, "").strip():
                problems.append("source note missing: " + topic)
        outcome = outcomes.get(selected.target_id)
        if outcome == "changed":
            problems.append("official retrieval returned different bytes; review the new candidate revision")
        if not source.synthetic and outcome != "confirmed":
            problems.append("offline real-source freshness is unverified" if retrievals is None
                            else "official retrieval did not confirm the declared bytes; current freshness is unknown")
        source_gaps[source.id] = problems
        for problem in problems:
            record_gap(f"Source {source.id}: {problem}")
    for _ in sources:
        changed = False
        for identity, selected in sources.items():
            review = source_reviews.get((identity, declared.scope.assessment_date))
            dependencies = [*selected.source.related_source_ids]
            if review:
                dependencies.extend([*review.act_chain, *review.case_law_refs, *review.national_overlay_ids])
            if not source_gaps[identity] and any(source_gaps[ref] for ref in dependencies):
                problem = "referenced source content/review unresolved"
                source_gaps[identity].append(problem)
                record_gap(f"Source {identity}: {problem}")
                changed = True
        if not changed:
            break
    for target in declared.source_targets:
        if not any(item.target_id == target.id for item in declared.sources):
            record_gap(f"Source target {target.id}: no selected source candidate.")
        if target.family not in m.LEGAL_FAMILIES:
            record_gap(f"Source target {target.id}: unsupported topic requires specialist/national research.")
    for requirement in declared.requirements:
        if requirement.origin:
            observation = observations.get(requirement.origin.path)
            if not observation or observation.availability != "available" or observation.digest != requirement.origin.digest:
                record_gap(f"Requirement {requirement.id}: origin unavailable or corrupt.")

    def fact_problems(pins):
        problems = []
        if not pins:
            problems.append("relied-on fact pins missing")
        for pin in pins:
            fact = facts[pin.id]
            if fact.basis in ("assumed", "unknown") or fact.conflicts:
                problems.append("relied-on fact assumption, uncertainty or conflict")
            if not all(evidence_ready(identity) for identity in fact.evidence_ids):
                problems.append("relied-on fact evidence unavailable")
        return problems

    def provision_problems(pins, duty=False):
        problems = []
        if not pins:
            problems.append("source provision pins missing")
        for pin in pins:
            selected = sources.get(pin.source_id)
            if not selected or source_gaps.get(pin.source_id) or pin.locator not in selected.source.provisions or not pin.locator.strip():
                problems.append("source provision or reviewed source support unresolved")
            if selected and duty and selected.source.type not in ("eu_act", "national_act", "judgment", "synthetic_fixture"):
                problems.append("candidate authority cannot establish a binding duty")
        return problems

    original_decisions = {item.obligation.id: item for item in declared.applicability_decisions}
    decisions = []
    dispositions = []
    reviews = {(item.obligation.id, item.method): item for item in declared.evidence_reviews}
    for obligation in declared.obligations:
        original = original_decisions.get(obligation.id)
        problems = []
        if original:
            problems.extend(original.gaps)
            if original.applicability == "unresolved":
                problems.append("declared applicability remains unresolved")
            if not original.reviewer or not original.reviewer.strip() or not original.reviewed_at or not original.rationale.strip():
                problems.append("accountable applicability reasoning missing")
            if original.assessment_date != declared.scope.assessment_date:
                problems.append("applicability assessment date mismatch")
            if not original.jurisdictions or any(j not in declared.scope.jurisdictions for j in original.jurisdictions):
                problems.append("jurisdiction scope review unresolved")
            if not original.condition_answers or not all(answer.strip() for answer in original.condition_answers):
                problems.append("condition reasoning missing")
            if not original.exception_answers or not all(answer.strip() for answer in original.exception_answers):
                problems.append("exception reasoning missing")
            problems.extend(fact_problems(original.fact_refs))
            problems.extend(provision_problems(original.provisions))
            if not all(pin in original.provisions for pin in obligation.source_provisions):
                problems.append("obligation provisions missing from applicability review")
            if not all(evidence_ready(identity) for identity in original.evidence_ids):
                problems.append("applicability evidence unavailable")
        else:
            problems.append("applicability attestation missing")
        problems.extend(provision_problems(obligation.source_provisions, obligation.classification == "duty"))
        if any(source_gaps[identity] for identity in obligation.overlay_ids):
            problems.append("referenced national overlay content/review unresolved")
        if obligation.family not in m.LEGAL_FAMILIES:
            problems.append("unsupported obligation topic requires specialist/national research")
        if original and not problems:
            decision = original.model_copy(update={"synthetic": declared.synthetic or original.synthetic})
        else:
            data = original.model_dump() if original else dict(
                revision=0, project_id=declared.project_id, obligation={"id": obligation.id, "revision": obligation.revision},
                scope={"id": declared.scope.id, "revision": declared.scope.revision},
                assessment_date=declared.scope.assessment_date, jurisdictions=declared.scope.jurisdictions,
                fact_refs=[], provisions=obligation.source_provisions, evidence_ids=[], condition_answers=[], exception_answers=[])
            data.update(id=_derived_id("unresolved", obligation.id), synthetic=declared.synthetic,
                        applicability="unresolved", rationale="Effective applicability awaits accountable review.", gaps=list(dict.fromkeys(problems)))
            decision = m.ApplicabilityDecision.model_validate(data)
        decisions.append(decision)
        for problem in problems:
            record_gap(f"Obligation {obligation.id}: {problem}")
        method_dispositions = []
        manual_states = []
        if not obligation.required_methods:
            record_gap(f"Obligation {obligation.id}: required review methods are undeclared.")
        for method in dict.fromkeys(obligation.required_methods):
            review = reviews.get((obligation.id, method))
            missing = []
            outcome = "unresolved_review"
            if method == "technical":
                outcome = "not_tested"
                missing.append("Technical checks are outside the offline workflow.")
            elif not review:
                missing.append("Accountable evidence review missing.")
                manual_states.append("pending")
            else:
                accountable = bool(review.reviewer and review.reviewer.strip() and review.reviewed_at and review.rationale.strip())
                if review.state == "insufficient" and accountable:
                    outcome = "observed_failure"
                    manual_states.append("unsupported")
                elif (review.state == "reviewed" and accountable and review.period.strip() and review.owner.strip()
                      and review.evidence_ids and not review.missing_evidence and not review.contrary_evidence
                      and all(evidence_ready(identity) for identity in review.evidence_ids)
                      and decision.applicability == "applicable" and not problems):
                    outcome = "passed"
                    manual_states.append("supported")
                else:
                    missing.append("Evidence sufficiency, provenance, period, owner or legal support unresolved.")
                    manual_states.append("unresolved")
                missing.extend(review.missing_evidence)
                missing.extend(review.contrary_evidence)
            if missing:
                record_gap(f"Obligation {obligation.id}, method {method}: review or evidence incomplete.")
            method_dispositions.append(m.MethodDisposition(method=method, outcome=outcome, attempt_ids=[],
                review_ids=[review.id] if review else [], missing_evidence=list(dict.fromkeys(missing))))
        manual = ("unsupported" if "unsupported" in manual_states else "pending" if not manual_states or "pending" in manual_states
                  else "unresolved" if "unresolved" in manual_states else "supported")
        dispositions.append(m.ObligationDisposition(id=_derived_id("disposition", obligation.id), project_id=declared.project_id,
            run_id=run_id, obligation_id=obligation.id, obligation_revision=obligation.revision,
            applicability=decision.applicability, applicability_decision_id=decision.id,
            rationale=decision.rationale, required_method_dispositions=method_dispositions, manual_review=manual))
    dispositions_by_obligation = {item.obligation_id: item for item in dispositions}
    assessments = []
    for requirement in declared.requirements:
        mapped = [dispositions_by_obligation[pin.id] for pin in requirement.obligation_refs]
        requirement_gaps = fact_problems(requirement.fact_refs) if requirement.fact_refs else []
        if not all(evidence_ready(identity) for identity in requirement.evidence_ids):
            requirement_gaps.append("Declared requirement evidence unavailable or unverified.")
        if requirement.origin:
            observation = observations.get(requirement.origin.path)
            if not observation or observation.availability != "available" or observation.digest != requirement.origin.digest:
                requirement_gaps.append("Declared requirement origin unavailable or corrupt.")
        if not mapped:
            requirement_gaps.append("No declared obligation mapping.")
        supported = bool(mapped and not requirement_gaps and all(item.manual_review == "supported" and item.applicability == "applicable"
            and item.required_method_dispositions and all(method.outcome == "passed" for method in item.required_method_dispositions)
            for item in mapped))
        if not supported and mapped:
            requirement_gaps.append("Mapped obligations retain unresolved, insufficient or untested methods.")
        state = "supported" if supported else "conflicting" if any(item.manual_review == "unsupported" for item in mapped) else "unresolved"
        for problem in requirement_gaps:
            record_gap(f"Requirement {requirement.id}: {problem}")
        review_ids = list(dict.fromkeys(identity for item in mapped for method in item.required_method_dispositions for identity in method.review_ids))
        evidence_ids = list(dict.fromkeys([*requirement.evidence_ids, *(identity for review in declared.evidence_reviews
            if review.id in review_ids for identity in review.evidence_ids)]))
        assessments.append(m.RequirementAssessment(requirement=m.SourceRef(id=requirement.id, revision=requirement.revision),
            obligation_disposition_ids=[item.id for item in mapped], evidence_ids=evidence_ids, review_ids=review_ids,
            state=state, rationale="Recorded mapping supports this declared requirement only." if supported else "Declared mapping needs review.",
            gaps=requirement_gaps, next_actions=["Review declared requirement and every mapped method."] if requirement_gaps else []))
    screenings = []
    supplied_screenings = {item.family: item for item in declared.family_screenings}
    for family in m.LEGAL_FAMILIES:
        original = supplied_screenings.get(family)
        problems = list(original.gaps) if original else ["Family screening attestation missing."]
        if original:
            if original.applicability == "unresolved":
                problems.append("Family applicability remains unresolved.")
            if (not original.reviewer or not original.reviewer.strip() or not original.reviewed_at
                    or not original.rationale.strip() or original.assessment_date != declared.scope.assessment_date):
                problems.append("Accountable family reasoning/date missing.")
            problems.extend(fact_problems(original.fact_refs))
            if not original.source_refs or any(source_gaps[pin.id] for pin in original.source_refs):
                problems.append("Reviewed family sources unresolved.")
        if original and not problems:
            item = original.model_copy(update={"synthetic": declared.synthetic or original.synthetic})
        else:
            data = original.model_dump() if original else dict(family=family,
                scope={"id": declared.scope.id, "revision": declared.scope.revision}, assessment_date=declared.scope.assessment_date,
                rationale=FAMILY_DESCRIPTIONS[family], fact_refs=[], source_refs=[])
            data.update(synthetic=declared.synthetic, applicability="unresolved", gaps=list(dict.fromkeys(problems)))
            item = m.FamilyScreening.model_validate(data)
        screenings.append(item)
        for problem in problems:
            record_gap(f"Family {family}: {problem}")
    if not declared.requirements:
        record_gap("Declared requirement register is empty.")
    if not declared.obligations:
        record_gap("Candidate obligation register is empty.")
    if declared.scope.exclusions:
        record_gap("Declared scope exclusions remain outside this assessment.")
    if not declared.scope.jurisdictions or any(j not in {item.source.jurisdiction for item in declared.sources}
                                                for j in declared.scope.jurisdictions):
        record_gap("Specialist/national jurisdiction coverage requires an explicit reviewed legal basis.")
    manifest_data = dict(id=manifest_id, source_files=[{"path": path, "digest": item.digest}
        for path, item in observations.items() if path in _selected_files(declared) and item.digest],
        exclusions=declared.scope.exclusions, scope_revision=declared.scope.revision,
        fact_digest=m.content_digest(_json_bytes([item.model_dump(mode="json") for item in facts.values()])),
        registry_digest=m.content_digest(_json_bytes({"targets": [item.model_dump(mode="json") for item in declared.source_targets],
            "obligations": [item.model_dump(mode="json") for item in declared.obligations],
            "controls": [item.model_dump(mode="json") for item in declared.controls]})),
        source_versions=[f"{item.id}:{item.revision}:{item.content_digest}" for item in [*(selected.source for selected in declared.sources), *candidates]],
        fixture_digest=input_digest, tool_versions=["eu-compliance-guard:" + __version__],
        config_digest=m.content_digest(_json_bytes(POLICY if retrievals is None else fetch_policy())),
        environment_identity=declared.scope.environment, browser_state=None, graph_digest=None)
    manifest = m.InputManifest.model_validate({**manifest_data, "digest": m.content_digest(_json_bytes(manifest_data))})
    run_record = m.AuditRun(id=run_id, project_id=declared.project_id, revision=0, state="partial" if gaps else "completed",
        manifest_id=manifest_id, permission_id=declared.scope.permission_id, coverage_plan=list(FAMILY_DESCRIPTIONS.values()),
        started_at=timestamp, ended_at=timestamp, terminal_sequence=0, gaps=gaps, budgets=m.Budgets(run_seconds=300, check_seconds=300))
    try:
        return m.RevalidationBundle(schema_version=1, project_id=declared.project_id, synthetic=declared.synthetic,
            input_digest=input_digest, run=run_record, manifest=manifest, declarations=declared, evidence=list(evidence.values()),
            obligation_dispositions=dispositions, requirement_assessments=assessments,
            effective_applicability_decisions=decisions, family_screenings=screenings, gaps=gaps, next_actions=actions,
            source_attempts=attempts, retrieved_sources=candidates)
    except ValidationError as error:
        raise _output_validation_error(error) from None


def _write(fd: int, name: str, content: bytes, deadline: float) -> None:
    _check_budget(deadline)
    file_fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=fd)
    try:
        os.fchmod(file_fd, 0o600)
        view = memoryview(content)
        while view:
            _check_budget(deadline)
            size = os.write(file_fd, view[:CHUNK_BYTES])
            if size <= 0:
                raise RevalidationError("io-failed")
            view = view[size:]
        os.fsync(file_fd)
    finally:
        os.close(file_fd)


def _private_parent(parent_fd: int) -> None:
    info = os.fstat(parent_fd)
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise RevalidationError("privacy-unavailable")


def _preflight_output(output_path) -> None:
    """Refuse unusable output before any network operation; publication re-checks exclusively."""
    with _parent(output_path) as (parent_fd, name):
        _private_parent(parent_fd)
        try:
            os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        raise RevalidationError("output-exists")


def _publish(output_path, bundle: m.RevalidationBundle, observations: dict[str, FileObservation],
             report: str, deadline: float, retrieved: dict[str, bytes] | None = None) -> None:
    artifacts = {"input.json": m.canonical_json(bundle.declarations), "manifest.json": m.canonical_json(bundle.manifest),
                 "bundle.json": m.canonical_json(bundle), "report.md": report.encode("utf-8")}
    if len(artifacts["bundle.json"]) > m.MAX_REQUEST_BYTES or len(artifacts["report.md"]) > MAX_REPORT_BYTES:
        raise RevalidationError("capacity-exceeded")
    retained = {}
    for selected in bundle.declarations.sources:
        observation = observations.get(selected.file.path) if selected.file else None
        if not observation or observation.availability != "available" or observation.content is None or observation.digest != selected.source.content_digest:
            continue
        admission = admit_source_content(observation.content, selected.media_type, selected.charset)
        if admission.state == "accepted" or admission.reason == "pdf-manual-identity-review":
            if m.content_digest(observation.content) != selected.source.content_digest:
                raise RevalidationError("invalid-output")
            retained["sources/" + observation.digest.removeprefix("sha256:") + ".bin"] = observation.content
    for attempt in bundle.source_attempts:
        path = attempt.retrieval.artifact_path
        if path is not None:
            content = (retrieved or {}).get(attempt.retrieval.digest)
            if content is None or m.content_digest(content) != attempt.retrieval.digest:
                raise RevalidationError("invalid-output")
            retained[path] = content
    marker = m.RunCompletion(schema_version=1, run_id=bundle.run.id,
        files=[m.SourceFile(path=path, digest=m.content_digest(content)) for path, content in {**retained, **artifacts}.items()])
    marker_bytes = m.canonical_json(marker)
    with _parent(output_path) as (parent_fd, name):
        _private_parent(parent_fd)
        try:
            os.mkdir(name, 0o700, dir_fd=parent_fd)
        except FileExistsError:
            raise RevalidationError("output-exists") from None
        run_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent_fd)
        try:
            os.fchmod(run_fd, 0o700)
            if retained:
                os.mkdir("sources", 0o700, dir_fd=run_fd)
                source_fd = os.open("sources", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=run_fd)
                try:
                    os.fchmod(source_fd, 0o700)
                    for path, content in retained.items():
                        _write(source_fd, path.split("/")[1], content, deadline)
                    os.fsync(source_fd)
                finally:
                    os.close(source_fd)
            for path, content in artifacts.items():
                _write(run_fd, path, content, deadline)
            os.fsync(run_fd)
            try:
                _write(run_fd, "complete.json", marker_bytes, deadline)
                os.fsync(run_fd)
                os.fsync(parent_fd)
            except BaseException:
                try:
                    os.unlink("complete.json", dir_fd=run_fd)
                except FileNotFoundError:
                    pass
                raise
        finally:
            os.close(run_fd)


def run(input_path: str | os.PathLike, output_path: str | os.PathLike, *, fetch_official: bool = False,
        transport_factory=None) -> m.RevalidationBundle:
    """Assemble and publish a new private run; existing output is never overwritten.

    Only with fetch_official are the declared targets requested, under the fixed network policy.
    """
    from .report import render_report
    _primitives()
    deadline = time.monotonic() + BUDGET_SECONDS
    try:
        with _parent(input_path) as (fd, name):
            declared, input_digest = _load(fd, name, deadline)
            observations = _observe(declared, fd, deadline)
        _check_budget(deadline)
        retrievals = None
        if fetch_official:
            from . import sources
            _preflight_output(output_path)
            requests = [sources.TargetRequest(item.id, item.intended_url, tuple(item.redirect_hosts),
                                              item.intended_type == "synthetic_fixture") for item in declared.source_targets]
            try:
                retrievals = sources.retrieve(requests, **({"transport_factory": transport_factory} if transport_factory else {}))
            except sources.RetrievalHelperError:
                raise RevalidationError("retrieval-failed") from None
            # The network has its own fixed budget; local assembly keeps its cooperative budget.
            deadline = time.monotonic() + BUDGET_SECONDS
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        bundle = assemble(declared, observations, input_digest=input_digest, timestamp=timestamp,
                          run_id="run-" + uuid4().hex, manifest_id="manifest-" + uuid4().hex, retrievals=retrievals)
        try:
            report = render_report(bundle)
        except ValueError as error:
            if error.args == ("report-too-large",):
                raise RevalidationError("capacity-exceeded") from None
            raise
        _check_budget(deadline)
        _publish(output_path, bundle, observations, report, deadline,
                 {m.content_digest(item.content): item.content for item in retrievals or [] if item.content is not None})
        return bundle
    except RevalidationError:
        raise
    except OSError:
        raise RevalidationError("io-failed") from None
    except ValidationError as error:
        raise _output_validation_error(error) from None
    except (ValueError, RecursionError):
        raise RevalidationError("invalid-output") from None
