"""Small original fake fragments; no test establishes native compatibility."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import unittest

from eu_compliance_guard import agent
from eu_compliance_guard import models as m

NOW = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
CONFIGURATION = b'{"fixture":"synthetic-only","tools":"isolated"}'
VERSION = "synthetic-version"


def protocol_fragments():
    definitions = {"Init": {"required": ["clientInfo"]}, "Thread": {"type": "object"},
                   "Turn": {"required": ["threadId", "input"], "properties": {
                       "outputSchema": {}, "sandboxPolicy": {"type": "object"},
                       "disabledPluginIds": {"type": "array"}}}}
    requests = {"definitions": definitions, "oneOf": [
        {"properties": {"method": {"enum": [method]}, "params": {"$ref": "#/definitions/" + params}}}
        for method, params in (("initialize", "Init"), ("thread/start", "Thread"), ("turn/start", "Turn"))]}
    notifications = {"oneOf": [{"properties": {"method": {"enum": ["initialized"]}}}]}
    return requests, notifications


def admission_context():
    grant = m.PermissionGrant(
        id="synthetic-grant", project_id="synthetic-project", root_identity=m.content_digest(b"synthetic-root"),
        operations=["finding.discuss"], relative_paths=["web/app.js"], test_origins=[],
        synthetic_fixture_ids=["synthetic-fixture"],
        provider=m.ProviderBoundary(provider="synthetic-provider", authorized=True, data_classes=["synthetic"]),
        expires_at=(NOW + timedelta(minutes=5)).isoformat())
    records = [m.CapabilityObservation(
        capability=name, mechanism="codex-config:" + m.content_digest(CONFIGURATION),
        mechanism_version=VERSION, level="observed", state="passed", observed_at=NOW.isoformat(),
        evidence_ids=["synthetic-proof"], reason="Synthetic executor-proof stand-in, not native evidence")
        for name in agent.REQUIRED_OBSERVED_CAPABILITIES]
    arguments = dict(configuration=CONFIGURATION, version=VERSION, grant=grant,
                     project_id=grant.project_id, root_identity=grant.root_identity,
                     provider="synthetic-provider", data_classes=["synthetic"],
                     now=NOW, not_before=NOW - timedelta(minutes=1))
    return records, arguments


def reply_context():
    payload = dict(schema_version=1, conversation_id="conversation-synthetic", context_manifest_id="context-synthetic",
                   finding_assessment_id="assessment-synthetic", message="Synthetic proposal", proposal={
                       "kind": "one_file_text_patch", "relative_path": "web/app.js",
                       "preimage_digest": m.content_digest(b"old"), "proposed_postimage": "new",
                       "retest_ids": ["synthetic-check"]})
    context = {k: payload[k] for k in ("conversation_id", "context_manifest_id", "finding_assessment_id")}
    context.update(allowed_preimages={"web/app.js": m.content_digest(b"old")}, registered_retests=["synthetic-check"])
    return payload, context


class AgentTests(unittest.TestCase):
    def test_schema_advertisements_are_static_without_proof(self):
        records = agent.inspect_protocol(*protocol_fragments(), version=VERSION, inspected_at=NOW.isoformat())
        self.assertEqual(len(records), 7)
        self.assertTrue(all(x.level == "static" and x.state == "passed" and not x.evidence_ids for x in records))
        _, arguments = admission_context()
        self.assertEqual(set(agent.admission_blockers(records, **arguments)), set(agent.REQUIRED_OBSERVED_CAPABILITIES))

    def test_missing_ambiguous_or_false_schema_features_block(self):
        for mutate, expected in (
            (lambda r, n: r["definitions"]["Turn"]["properties"].pop("outputSchema"), "structured_output"),
            (lambda r, n: r["definitions"]["Turn"]["properties"].update(outputSchema=False), "structured_output"),
            (lambda r, n: r["definitions"]["Turn"].update(required=["threadId"]), "turn_start"),
            (lambda r, n: r["oneOf"].append(deepcopy(r["oneOf"][0])), "initialize"),
            (lambda r, n: r["definitions"].pop("Thread"), "thread_start"),
            (lambda r, n: n.update(oneOf=[]), "initialized")):
            with self.subTest(feature=expected):
                requests, notifications = protocol_fragments()
                mutate(requests, notifications)
                records = agent.inspect_protocol(requests, notifications, version=VERSION, inspected_at=NOW.isoformat())
                self.assertEqual(next(x.state for x in records if x.capability == expected), "blocked")

    def test_complete_synthetic_records_exercise_only_the_predicate(self):
        records, arguments = admission_context()
        self.assertEqual(agent.admission_blockers(records, **arguments), ())

    def test_each_required_proof_must_be_current_matching_and_observed(self):
        for capability in agent.REQUIRED_OBSERVED_CAPABILITIES:
            for update in (None, {"level": "fake"}, {"level": "static"}, {"state": "failed"},
                           {"state": "blocked"}, {"state": "not_run"}, {"mechanism_version": "other"},
                           {"mechanism": "generic-cli-name"},
                           {"observed_at": (NOW - timedelta(hours=1)).isoformat()},
                           {"observed_at": (NOW + timedelta(seconds=1)).isoformat()}):
                records, arguments = admission_context()
                index = next(i for i, x in enumerate(records) if x.capability == capability)
                if update is None:
                    records.pop(index)
                else:
                    records[index] = m.CapabilityObservation.model_validate({**records[index].model_dump(), **update})
                with self.subTest(capability=capability, update=update):
                    self.assertIn(capability, agent.admission_blockers(records, **arguments))

    def test_duplicate_proof_and_changed_configuration_block(self):
        records, arguments = admission_context()
        records.append(records[0])
        self.assertIn(records[0].capability, agent.admission_blockers(records, **arguments))
        records, arguments = admission_context()
        arguments["configuration"] = b"changed-synthetic-policy"
        self.assertEqual(set(agent.admission_blockers(records, **arguments)), set(agent.REQUIRED_OBSERVED_CAPABILITIES))

    def test_authorization_target_operation_revocation_expiry_and_processing(self):
        for update, expected in (
            ({"project_id": "other"}, "authorization_target_mismatch"),
            ({"root_identity": m.content_digest(b"other")}, "authorization_target_mismatch"),
            ({"operations": []}, "discussion_not_authorized"),
            ({"revoked_at": NOW.isoformat()}, "authorization_expired_or_revoked"),
            ({"expires_at": NOW.isoformat()}, "authorization_expired_or_revoked"),
            ({"provider": m.ProviderBoundary()}, "provider_processing_not_authorized")):
            records, arguments = admission_context()
            arguments["grant"] = m.PermissionGrant.model_validate({**arguments["grant"].model_dump(), **update})
            with self.subTest(update=update):
                self.assertIn(expected, agent.admission_blockers(records, **arguments))
        for update in ({"provider": "unapproved"}, {"data_classes": ["private"]}, {"data_classes": []}):
            records, arguments = admission_context()
            arguments.update(update)
            self.assertIn("provider_processing_not_authorized", agent.admission_blockers(records, **arguments))

    def test_invalid_time_or_configuration_rejected(self):
        for update in ({"now": NOW.replace(tzinfo=None)}, {"not_before": NOW + timedelta(seconds=1)},
                       {"configuration": b""}, {"version": ""}):
            records, arguments = admission_context()
            arguments.update(update)
            with self.subTest(update=update), self.assertRaises(ValueError):
                agent.admission_blockers(records, **arguments)

    def test_bound_reply_is_data_without_applying_a_patch(self):
        payload, context = reply_context()
        self.assertEqual(agent.validate_reply(json.dumps(payload), **context).proposal.proposed_postimage, "new")
        payload.pop("proposal")
        self.assertIsNone(agent.validate_reply(json.dumps(payload), **context).proposal)

    def test_wrong_binding_unknown_fields_version_and_malformed_json_rejected(self):
        payload, context = reply_context()
        for key in ("conversation_id", "context_manifest_id", "finding_assessment_id"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                agent.validate_reply(json.dumps({**payload, key: "other"}), **context)
        for raw in (b"not JSON", b"\xff", json.dumps({**payload, "schema_version": True}),
                    json.dumps({**payload, "shell": "never execute"}), b" " * (m.MAX_REQUEST_BYTES + 1)):
            with self.assertRaises(ValueError):
                agent.validate_reply(raw, **context)

    def test_paths_preimages_retests_size_and_invalid_text_rejected(self):
        for update in ({"relative_path": "../private"}, {"relative_path": "/private"},
                       {"relative_path": "other.js"}, {"preimage_digest": m.content_digest(b"changed")},
                       {"retest_ids": ["unregistered"]}, {"retest_ids": []},
                       {"retest_ids": ["synthetic-check", "synthetic-check"]},
                       {"proposed_postimage": "x" * 524289}, {"proposed_postimage": "\ud800"}):
            payload, context = reply_context()
            payload["proposal"].update(update)
            with self.subTest(fields=list(update)), self.assertRaises(ValueError):
                agent.validate_reply(json.dumps(payload), **context)


if __name__ == "__main__":
    unittest.main()
