"""Synthetic retrieval assembly/run checks with fake transports; no external service is contacted."""

from copy import deepcopy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from eu_compliance_guard import models as m, revalidation as r, sources as s
from eu_compliance_guard.report import render_report
from test_sources import FakeResponse, FakeTransport

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/revalidation-synthetic.json"
STAMP = "2026-10-18T10:00:00Z"
LATER = "2026-10-18T10:00:01Z"
URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:FICTIONAL-REAL-1"
PAGE = b"<!doctype html><html lang='en'><head><title>Text</title></head><body>FICTIONAL-REAL-1 Article 1</body></html>"
CHANGED = PAGE.replace(b"Article 1", b"Article 1a")
LOGIN = b"<html><head><title>Sign in</title></head><body><form><input type='password'></form></body></html>"
HTML = [("Content-Type", "text/html; charset=utf-8")]


def real_target_payload():
    """The fictional fixture plus one real-type candidate on a registered host, pinned to local bytes."""
    payload = json.loads(FIXTURE.read_bytes())
    payload["source_targets"].append({
        "id": "target-real", "revision": 0, "family": "gdpr", "intended_url": URL,
        "intended_identifier": "FICTIONAL-REAL-1", "publisher": "Publications Office", "intended_type": "eu_act",
        "language": "en", "jurisdiction": "EU"})
    payload["sources"].append({
        "target_id": "target-real", "media_type": "text/html", "charset": "utf-8",
        "file": {"path": "revalidation-synthetic/real.html", "digest": m.content_digest(PAGE)},
        "source": {"id": "source-real", "revision": 0, "type": "eu_act", "publisher": "Publications Office",
                   "identifier": "FICTIONAL-REAL-1", "url": URL, "language": "en", "jurisdiction": "EU",
                   "document_date": None, "retrieved_at": STAMP, "content_digest": m.content_digest(PAGE),
                   "provisions": ["Article 1"], "related_source_ids": [], "synthetic": False}})
    return payload


def result(target_id="target-real", url=URL, content=PAGE, failure=None, media_type="text/html", **changes):
    values = dict(target_id=target_id, requested_url=url, started_at=STAMP, ended_at=LATER, failure=failure)
    if failure is None or content is not None:
        values.update(final_url=url, status=200, media_type=media_type, charset="utf-8",
                      bytes_read=len(content or b""), content=content)
    values.update(changes)
    return s.FetchResult(**values)


def synthetic_refusal():
    return s.FetchResult(target_id="target-example", requested_url="https://example.invalid/synthetic-authority",
                         started_at=STAMP, ended_at=STAMP, failure="synthetic-target-not-fetched")


class RealTargetTransport(FakeTransport):
    """Picklable factory used inside the spawned helper."""
    def __init__(self):
        super().__init__(responses={("eur-lex.europa.eu", s.check_url(URL, s.OFFICIAL_HOSTS)[1]):
                                    lambda: FakeResponse(headers=HTML, body=CHANGED)})


class RetrievalWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="eucg-retrieval-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)
        assets = self.root / "revalidation-synthetic"
        assets.mkdir()
        for name in ("source.txt", "evidence.txt"):
            (assets / name).write_bytes((FIXTURE.parent / "revalidation-synthetic" / name).read_bytes())
        (assets / "real.html").write_bytes(PAGE)
        self.input = self.root / "input.json"
        self.input.write_text(json.dumps(real_target_payload()))

    def assemble(self, retrievals):
        declared = r.load_input(self.input)
        with r._parent(self.input) as (fd, _):
            observations = r._observe(declared, fd, r.time.monotonic() + 300)
        bundle = r.assemble(declared, observations, input_digest=m.content_digest(self.input.read_bytes()),
                            timestamp=LATER, run_id="run-test", manifest_id="manifest-test", retrievals=retrievals)
        self.assertEqual(m.parse_record(m.RevalidationBundle, m.canonical_json(bundle)), bundle)
        return bundle

    def source_gaps(self, bundle, source_id="source-real"):
        return [gap for gap in bundle.gaps if gap.startswith(f"Source {source_id}:")]

    def test_offline_real_source_freshness_stays_unverified(self):
        bundle = self.assemble(None)
        self.assertEqual(bundle.source_attempts, [])
        self.assertIn("Source source-real: offline real-source freshness is unverified", bundle.gaps)
        self.assertIn("No retrieval was requested", render_report(bundle))

    def test_same_bytes_record_provenance_without_claiming_authority(self):
        bundle = self.assemble([synthetic_refusal(), result()])
        fictional, real = bundle.source_attempts
        self.assertEqual((fictional.state, fictional.failure.code), ("retrieval_failed", "synthetic-target-not-fetched"))
        self.assertIsNone(fictional.retrieval.digest)
        self.assertEqual(real.state, "retrieved")
        provenance = real.retrieval
        self.assertEqual((provenance.requested_url, provenance.final_url, provenance.status), (URL, URL, 200))
        self.assertEqual((provenance.digest, provenance.bytes_read, provenance.comparison),
                         (m.content_digest(PAGE), len(PAGE), "same_bytes"))
        self.assertEqual((provenance.started_at, provenance.ended_at), (STAMP, LATER))
        self.assertEqual(real.last_successful_source, m.SourceRef(id="source-real", revision=0))
        candidate = bundle.retrieved_sources[0]
        self.assertEqual((candidate.type, candidate.publisher, candidate.identifier, candidate.language, candidate.provisions),
                         ("eu_act", "Publications Office", "FICTIONAL-REAL-1", "en", []))
        self.assertEqual(candidate.url, URL)
        self.assertNotIn("freshness", " ".join(self.source_gaps(bundle)))
        self.assertTrue(any("requires accountable source review" in gap and "binding status" in gap for gap in bundle.gaps))
        self.assertEqual(bundle.run.state, "partial")
        declared = bundle.declarations.sources[1].source
        self.assertEqual((declared.retrieved_at, declared.content_digest), (STAMP, m.content_digest(PAGE)))
        self.assertEqual({item.requirement.id: item.state for item in bundle.requirement_assessments}["requirement-example"], "supported")

    def test_changed_bytes_withdraw_declared_source_and_create_candidate(self):
        bundle = self.assemble([result(content=CHANGED)])
        self.assertEqual(bundle.source_attempts[0].retrieval.comparison, "different_bytes")
        self.assertIn("Source source-real: official retrieval returned different bytes; review the new candidate revision", bundle.gaps)
        self.assertEqual(bundle.retrieved_sources[0].content_digest, m.content_digest(CHANGED))
        self.assertNotEqual(bundle.retrieved_sources[0].id, "source-real")

    def test_failures_never_invent_content_or_freshness(self):
        failures = [result(content=None, failure="timeout"), result(content=None, failure="unsafe-destination"),
                    result(content=None, failure="response-too-large", bytes_read=s.MAX_RESPONSE_BYTES + 1),
                    result(content=None, failure="http-status", status=404)]
        for failed in failures:
            with self.subTest(failure=failed.failure):
                bundle = self.assemble([failed])
                attempt = bundle.source_attempts[0]
                self.assertEqual((attempt.state, attempt.failure.code, attempt.retrieved_source), ("retrieval_failed", failed.failure, None))
                self.assertEqual(attempt.last_successful_source.id, "source-real")
                self.assertIsNone(attempt.retrieval.artifact_path)
                self.assertEqual(bundle.retrieved_sources, [])
                self.assertIn("Source source-real: official retrieval did not confirm the declared bytes; current freshness is unknown", bundle.gaps)

    def test_login_challenge_pages_are_rejected_and_uncertain_text_needs_review(self):
        bundle = self.assemble([result(content=LOGIN)])
        attempt = bundle.source_attempts[0]
        self.assertEqual((attempt.state, attempt.failure.code), ("retrieval_failed", "content-rejected"))
        self.assertEqual((attempt.retrieval.admission, attempt.retrieval.artifact_path), ("rejected", None))
        self.assertEqual(bundle.retrieved_sources, [])
        missing_identifier = PAGE.replace(b"FICTIONAL-REAL-1 ", b"")
        bundle = self.assemble([result(content=missing_identifier)])
        self.assertEqual(bundle.source_attempts[0].state, "retrieved")
        self.assertIn("Source target target-real: retrieved content needs review (intended-identifier-not-found).", bundle.gaps)
        self.assertTrue(any("freshness is unknown" in gap for gap in self.source_gaps(bundle)))
        other_language = PAGE.replace(b"lang='en'", b"lang='de'")
        attempt = self.assemble([result(content=other_language)]).source_attempts[0]
        self.assertEqual((attempt.state, attempt.failure.code), ("translation_unverified", "language-unverified"))
        pdf = self.assemble([result(content=b"%PDF-1.7 fictional", media_type="application/pdf", charset=None)])
        self.assertIn("Source target target-real: retrieved content needs review (pdf-manual-identity-review).", pdf.gaps)

    def test_guidance_candidate_cannot_become_binding_duty(self):
        payload = real_target_payload()
        payload["source_targets"][1]["intended_type"] = "final_guidance"
        self.input.write_text(json.dumps(payload))
        bundle = self.assemble([result()])
        self.assertEqual(bundle.retrieved_sources[0].type, "final_guidance")
        self.assertIn("Source source-real: candidate identity/classification disagrees with selected source", bundle.gaps)

    def test_report_lists_escaped_attempt_provenance(self):
        report = render_report(self.assemble([synthetic_refusal(), result(content=None, failure="timeout")]))
        self.assertIn("## Official-source retrieval attempts", report)
        self.assertIn("Official hosting establishes neither binding status", report)
        self.assertIn("synthetic&#45;target&#45;not&#45;fetched", report)
        self.assertNotIn(URL, report)
        self.assertIn("eur&#45;lex&#46;europa&#46;eu", report)

    def test_run_fetches_through_helper_and_retains_candidate_bytes(self):
        output = self.root / "run-fetch"
        original = self.input.read_bytes()
        bundle = r.run(self.input, output, fetch_official=True, transport_factory=RealTargetTransport)
        self.assertEqual([item.state for item in bundle.source_attempts], ["retrieval_failed", "retrieved"])
        retained = output / bundle.source_attempts[1].retrieval.artifact_path
        self.assertEqual(retained.read_bytes(), CHANGED)
        self.assertEqual(retained.stat().st_mode & 0o777, 0o600)
        marker = m.parse_record(m.RunCompletion, (output / "complete.json").read_bytes())
        for file in marker.files:
            self.assertEqual(m.content_digest((output / file.path).read_bytes()), file.digest)
        self.assertIn(bundle.source_attempts[1].retrieval.artifact_path, {file.path for file in marker.files})
        self.assertEqual((self.root / "revalidation-synthetic/real.html").read_bytes(), PAGE)
        self.assertEqual(self.input.read_bytes(), original)
        self.assertEqual(m.parse_record(m.RevalidationBundle, (output / "bundle.json").read_bytes()), bundle)

    def test_offline_default_and_unusable_output_perform_no_network(self):
        with patch.object(s, "retrieve", side_effect=AssertionError("network")), \
                patch.object(socket, "getaddrinfo", side_effect=AssertionError("dns")), \
                patch.object(socket, "create_connection", side_effect=AssertionError("connect")):
            bundle = r.run(self.input, self.root / "run-offline")
            self.assertEqual(bundle.source_attempts, [])
            (self.root / "exists").mkdir()
            with self.assertRaises(r.RevalidationError) as caught:
                r.run(self.input, self.root / "exists", fetch_official=True)
            self.assertEqual(caught.exception.code, "output-exists")
            self.root.chmod(0o755)
            try:
                with self.assertRaises(r.RevalidationError) as caught:
                    r.run(self.input, self.root / "new", fetch_official=True)
            finally:
                self.root.chmod(0o700)
            self.assertEqual(caught.exception.code, "privacy-unavailable")

    def test_unstoppable_helper_fails_the_run_without_output(self):
        with patch.object(s, "retrieve", side_effect=s.RetrievalHelperError("stuck")):
            with self.assertRaises(r.RevalidationError) as caught:
                r.run(self.input, self.root / "run-stuck", fetch_official=True)
        self.assertEqual(caught.exception.code, "retrieval-failed")
        self.assertFalse((self.root / "run-stuck").exists())


if __name__ == "__main__":
    unittest.main()
