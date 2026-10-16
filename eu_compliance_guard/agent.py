"""Static protocol inspection and fail-closed admission; never launches a native child."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone

from .models import (
    AgentReplyEnvelope, CapabilityObservation, PermissionGrant, content_digest, parse_record,
)

REQUIRED_OBSERVED_CAPABILITIES = (
    "protocol_lifecycle", "structured_output", "engine_actions_enforced",
    "native_private_reads_denied", "native_mutations_denied", "tool_egress_denied",
    "auth_isolation_verified",
)


def _params(schema: Mapping, method: str) -> dict | None:
    matches = [branch for branch in schema.get("oneOf", [])
               if isinstance(branch, dict)
               and branch.get("properties", {}).get("method", {}).get("enum") == [method]]
    if len(matches) != 1:
        return None
    ref = matches[0].get("properties", {}).get("params", {}).get("$ref", "")
    if not ref.startswith("#/definitions/"):
        return None
    params = schema.get("definitions", {}).get(ref.removeprefix("#/definitions/"))
    return params if isinstance(params, dict) else None


def inspect_protocol(
    requests: Mapping, notifications: Mapping, *, version: str, inspected_at: str,
) -> tuple[CapabilityObservation, ...]:
    """Report advertised keys in local generated schemas, never containment proof."""
    initialize = _params(requests, "initialize")
    thread = _params(requests, "thread/start")
    turn = _params(requests, "turn/start")
    initialized = [branch for branch in notifications.get("oneOf", [])
                   if isinstance(branch, dict)
                   and branch.get("properties", {}).get("method", {}).get("enum") == ["initialized"]]
    features = {
        "initialize": (initialize is not None and "clientInfo" in initialize.get("required", []),
                       "ClientRequest initialize params.required: clientInfo"),
        "initialized": (len(initialized) == 1, "ClientNotification initialized"),
        "thread_start": (thread is not None, "ClientRequest thread/start params"),
        "turn_start": (turn is not None and {"threadId", "input"} <= set(turn.get("required", [])),
                       "ClientRequest turn/start params.required: threadId, input"),
    }
    for capability, key in (("structured_output", "outputSchema"),
                            ("sandbox_policy", "sandboxPolicy"),
                            ("plugin_selection", "disabledPluginIds")):
        properties = turn.get("properties", {}) if turn else {}
        features[capability] = (key in properties and properties[key] is not False,
                                f"ClientRequest turn/start params.properties.{key}")
    return tuple(CapabilityObservation(
        capability=name, mechanism="codex-schema", mechanism_version=version,
        level="static", state="passed" if supported else "blocked",
        observed_at=inspected_at, evidence_ids=[],
        reason=f"{'Advertised' if supported else 'Missing or incompatible'}: {location}; no native execution verified",
    ) for name, (supported, location) in features.items())


def admission_blockers(
    observations: Sequence[CapabilityObservation], *, configuration: bytes,
    version: str, grant: PermissionGrant, project_id: str, root_identity: str,
    provider: str, data_classes: Sequence[str], now: datetime, not_before: datetime,
) -> tuple[str, ...]:
    """Evaluate trusted executor evidence and authorization, not model declarations.

    Evidence producers use mechanism ``codex-config:<content_digest(configuration)>``
    for the exact immutable, secret-free launch configuration. This must bind the
    executable, protocol/schema, snapshot, tool policy and authentication mechanism.
    Root retains actual proof artifacts; these records alone cannot authenticate them.
    """
    if now.utcoffset() != timezone.utc.utcoffset(now) or not_before.utcoffset() != timezone.utc.utcoffset(not_before):
        raise ValueError("admission times must be UTC")
    if not_before > now or not configuration or not version:
        raise ValueError("invalid admission context")
    grant = PermissionGrant.model_validate(grant)
    blockers = []
    if grant.project_id != project_id or grant.root_identity != root_identity:
        blockers.append("authorization_target_mismatch")
    if grant.revoked_at is not None or datetime.fromisoformat(grant.expires_at) <= now:
        blockers.append("authorization_expired_or_revoked")
    if "finding.discuss" not in grant.operations:
        blockers.append("discussion_not_authorized")
    if (not grant.provider.authorized or grant.provider.provider != provider
            or not data_classes or not set(data_classes) <= set(grant.provider.data_classes)):
        blockers.append("provider_processing_not_authorized")
    mechanism = "codex-config:" + content_digest(configuration)
    records = [CapabilityObservation.model_validate(record) for record in observations]
    for capability in REQUIRED_OBSERVED_CAPABILITIES:
        matches = [record for record in records if record.capability == capability
                   and record.mechanism == mechanism and record.mechanism_version == version]
        # Conflicting or duplicate evidence requires reconciliation, not selecting a pass.
        if (len(matches) != 1 or matches[0].level != "observed" or matches[0].state != "passed"
                or not matches[0].evidence_ids
                or not not_before <= datetime.fromisoformat(matches[0].observed_at) <= now):
            blockers.append(capability)
    return tuple(blockers)


def validate_reply(
    payload: bytes | str, *, conversation_id: str, context_manifest_id: str,
    finding_assessment_id: str, allowed_preimages: Mapping[str, str],
    registered_retests: Sequence[str],
) -> AgentReplyEnvelope:
    """Validate bounded proposal data against trusted context; never apply it."""
    try:
        reply = parse_record(AgentReplyEnvelope, payload)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ValueError("invalid agent reply envelope") from None
    if (reply.conversation_id != conversation_id or reply.context_manifest_id != context_manifest_id
            or reply.finding_assessment_id != finding_assessment_id):
        raise ValueError("agent reply context mismatch")
    if reply.proposal:
        patch = reply.proposal
        if allowed_preimages.get(patch.relative_path) != patch.preimage_digest:
            raise ValueError("agent proposal path/preimage mismatch")
        if (len(patch.retest_ids) != len(set(patch.retest_ids))
                or not set(patch.retest_ids) <= set(registered_retests)):
            raise ValueError("agent proposal has unregistered or duplicate retests")
        try:
            patch.proposed_postimage.encode("utf-8")
        except UnicodeError:
            raise ValueError("agent proposal is not UTF-8 text") from None
    try:
        reply.message.encode("utf-8")
    except UnicodeError:
        raise ValueError("agent message is not UTF-8 text") from None
    return reply
