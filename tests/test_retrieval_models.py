"""Retrieval provenance contract checks on synthetic records; no source is contacted."""

from copy import deepcopy
import unittest

from pydantic import ValidationError

from eu_compliance_guard import models as m
from test_revalidation_models import FIXTURE, STAMP, bundle_payload, supported_payload

URL = FIXTURE["source_targets"][0]["intended_url"]
CONTENT = b"fictional retrieved bytes"
DIGEST = m.content_digest(CONTENT)
LATER = "2026-10-18T10:00:01Z"


def provenance(**changes):
    value = {"requested_url": URL, "final_url": URL, "redirects": [], "started_at": STAMP, "ended_at": LATER,
             "status": 200, "media_type": "text/plain", "charset": "utf-8", "bytes_read": len(CONTENT),
             "digest": DIGEST, "artifact_path": "sources/" + DIGEST.removeprefix("sha256:") + ".bin",
             "admission": "accepted", "admission_reason": "content-only-not-authority", "comparison": "different_bytes"}
    value.update(changes)
    return value


def failed_provenance(**changes):
    return provenance(final_url=None, status=None, media_type=None, charset=None, bytes_read=0, digest=None,
                      artifact_path=None, admission=None, admission_reason=None, comparison="not_compared", **changes)


def attempt(**changes):
    target = FIXTURE["source_targets"][0]
    value = {"id": "attempt-example", "source_target_id": target["id"], "intended_url": target["intended_url"],
             "intended_identifier": target["intended_identifier"], "publisher": target["publisher"],
             "intended_type": target["intended_type"], "language": target["language"], "attempted_at": STAMP,
             "state": "retrieved", "retrieved_source": {"id": "retrieved-example", "revision": 0},
             "last_successful_source": {"id": "source-example", "revision": 0}, "failure": None,
             "retrieval": provenance()}
    value.update(changes)
    return value


def candidate(**changes):
    target = FIXTURE["source_targets"][0]
    value = {"id": "retrieved-example", "revision": 0, "type": target["intended_type"], "publisher": target["publisher"],
             "identifier": target["intended_identifier"], "url": URL, "language": target["language"],
             "jurisdiction": target["jurisdiction"], "retrieved_at": LATER, "content_digest": DIGEST,
             "provisions": [], "related_source_ids": [], "synthetic": True}
    value.update(changes)
    return value


def completed_payload():
    """Fictional single-mapping bundle whose offline assembly has no open gaps."""
    payload = supported_payload()
    declared = payload["declarations"]
    declared["obligations"] = declared["obligations"][:1]
    declared["requirements"] = declared["requirements"][:1]
    declared["controls"] = [item for item in declared["controls"] if item["obligation_ids"] == ["obligation-example"]]
    for key in ("effective_applicability_decisions", "obligation_dispositions", "requirement_assessments"):
        payload[key] = payload[key][:1]
    payload["run"].update(state="completed", gaps=[])
    payload["gaps"] = []
    for screening in payload["family_screenings"]:
        screening.update(applicability="not_applicable", gaps=[], reviewer="Fictional reviewer", reviewed_at=STAMP,
                         fact_refs=[{"id": "fact-declared", "revision": 0}],
                         source_refs=[{"id": "source-example", "revision": 0}])
    declared["family_screenings"] = deepcopy(payload["family_screenings"])
    return payload


def with_retrieval(payload, attempts=None, sources=None):
    payload["source_attempts"] = [attempt()] if attempts is None else attempts
    payload["retrieved_sources"] = [candidate()] if sources is None else sources
    return payload


class RetrievalContractTests(unittest.TestCase):
    def test_provenance_is_ordered_digest_named_and_chain_consistent(self):
        m.RetrievalProvenance.model_validate(provenance())
        m.RetrievalProvenance.model_validate(failed_provenance())
        redirect = URL + "/moved"
        m.RetrievalProvenance.model_validate(provenance(redirects=[redirect], final_url=redirect))
        for change in (dict(ended_at="2026-10-18T09:59:59Z"), dict(final_url=URL + "/other"),
                       dict(redirects=[redirect], final_url=URL), dict(redirects=[redirect] * 4, final_url=redirect),
                       dict(artifact_path="sources/private.bin"), dict(admission_reason=None),
                       dict(digest=None, artifact_path=None), dict(bytes_read=-1), dict(status=99),
                       dict(started_at="2026-10-18T10:00:00+01:00"), dict(headers={"set-cookie": "x"})):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                m.RetrievalProvenance.model_validate(provenance(**change))

    def test_attempt_retrieval_state_needs_retained_admitted_bytes(self):
        m.SourceAttempt.model_validate(attempt())
        failure = {"code": "timeout", "safe_message": "The official source request timed out."}
        m.SourceAttempt.model_validate(attempt(state="retrieval_failed", retrieved_source=None, failure=failure,
                                               retrieval=failed_provenance()))
        m.SourceAttempt.model_validate(attempt(state="translation_unverified", failure=failure))
        legacy = attempt(retrieval=None)
        self.assertIsNone(m.SourceAttempt.model_validate(legacy).retrieval)
        for change in (
            dict(retrieval=provenance(requested_url=URL + "/other", final_url=URL + "/other")),
            dict(retrieval=provenance(admission="rejected", admission_reason="login-challenge-error-page")),
            dict(retrieval=provenance(status=None)),
            dict(retrieved_source=None),
            dict(state="retrieval_failed", retrieved_source=None, failure=failure,
                 retrieval=provenance(artifact_path=None)),
        ):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                m.SourceAttempt.model_validate(attempt(**change))

    def test_redirect_hosts_are_exact_lowercase_names(self):
        target = deepcopy(FIXTURE["source_targets"][0])
        self.assertEqual(m.SourceTarget.model_validate(target).redirect_hosts, [])
        m.SourceTarget.model_validate({**target, "redirect_hosts": ["eur-lex.europa.eu"]})
        for hosts in (["EUR-LEX.europa.eu"], ["*.europa.eu"], ["127.0.0.1:443"], ["localhost"], ["a..b"],
                      ["eur-lex.europa.eu."], ["a.b"] * 5, ["xn--bcher-kva.example/"]):
            with self.subTest(hosts=hosts), self.assertRaises(ValidationError):
                m.SourceTarget.model_validate({**target, "redirect_hosts": hosts})

    def test_bundle_retains_attempt_and_unreviewed_candidate(self):
        bundle = m.RevalidationBundle.model_validate(with_retrieval(bundle_payload()))
        self.assertEqual(m.parse_record(m.RevalidationBundle, m.canonical_json(bundle)), bundle)
        failure = {"code": "timeout", "safe_message": "The official source request timed out."}
        m.RevalidationBundle.model_validate(with_retrieval(bundle_payload(), [attempt(
            state="retrieval_failed", retrieved_source=None, failure=failure, retrieval=failed_provenance())], []))

    def test_bundle_rejects_forged_or_inconsistent_retrieval(self):
        failure = {"code": "timeout", "safe_message": "The official source request timed out."}
        cases = [
            ([attempt(source_target_id="missing")], None),
            ([attempt(publisher="Another publisher")], None),
            ([attempt(retrieval=None)], None),
            ([attempt(), attempt(id="attempt-other")], None),
            ([attempt(retrieval=provenance(comparison="same_bytes"))], None),
            ([attempt(last_successful_source=None)], None),
            ([attempt(last_successful_source={"id": "source-example", "revision": 9})], None),
            (None, [candidate(provisions=["Fictional section 1"])]),
            (None, [candidate(related_source_ids=["source-example"])]),
            (None, [candidate(url=URL + "/other")]),
            (None, [candidate(retrieved_at=STAMP)]),
            (None, [candidate(publisher="Another publisher")]),
            (None, [candidate(), candidate(id="retrieved-unreferenced")]),
            (None, [candidate(id="source-example")]),
            ([attempt(state="retrieval_failed", retrieved_source=None, failure=failure, retrieval=failed_provenance())], None),
        ]
        for index, (attempts, sources) in enumerate(cases):
            with self.subTest(case=index), self.assertRaises(ValidationError):
                m.RevalidationBundle.model_validate(with_retrieval(bundle_payload(), attempts, sources))

    def test_comparison_matches_declared_source_bytes(self):
        declared_digest = FIXTURE["sources"][0]["source"]["content_digest"]
        same = provenance(digest=declared_digest, comparison="same_bytes",
                          artifact_path="sources/" + declared_digest.removeprefix("sha256:") + ".bin")
        m.RevalidationBundle.model_validate(with_retrieval(
            bundle_payload(), [attempt(retrieval=same)], [candidate(content_digest=declared_digest)]))
        m.RevalidationBundle.model_validate(with_retrieval(
            bundle_payload(), [attempt(last_successful_source=None, retrieval=provenance(comparison="no_prior_source"))]))

    def test_changed_bytes_withdraw_declared_support_and_attempts_block_completion(self):
        m.RevalidationBundle.model_validate(supported_payload())
        with self.assertRaises(ValidationError):
            m.RevalidationBundle.model_validate(with_retrieval(supported_payload()))
        m.RevalidationBundle.model_validate(completed_payload())
        failure = {"code": "timeout", "safe_message": "The official source request timed out."}
        failed = attempt(state="retrieval_failed", retrieved_source=None, failure=failure, retrieval=failed_provenance())
        with self.assertRaises(ValidationError):
            m.RevalidationBundle.model_validate(with_retrieval(completed_payload(), [failed], []))

    def test_generated_contracts_export_retrieval_records(self):
        from eu_compliance_guard.schema import contract_schema
        schema = contract_schema()
        self.assertIn("RetrievalProvenance", schema["$defs"])
        self.assertIn("redirect_hosts", schema["$defs"]["SourceTarget"]["properties"])
        self.assertIn("source_attempts", schema["$defs"]["RevalidationBundle"]["properties"])


if __name__ == "__main__":
    unittest.main()
