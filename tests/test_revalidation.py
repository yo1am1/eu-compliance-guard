"""Synthetic offline workflow checks; no live law, target execution or containment proof."""
from copy import deepcopy
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from eu_compliance_guard import models as m, revalidation as r

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/revalidation-synthetic.json"
STAMP = "2026-10-18T10:00:00Z"


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="eucg-workflow-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.input = self.root / "input.json"
        self.payload = json.loads(FIXTURE.read_bytes())
        (self.root / "revalidation-synthetic").mkdir()
        for name in ("source.txt", "evidence.txt"):
            (self.root / "revalidation-synthetic" / name).write_bytes((FIXTURE.parent / "revalidation-synthetic" / name).read_bytes())
        self.save()

    def save(self):
        self.input.write_text(json.dumps(self.payload), encoding="utf-8")

    def observations(self, declarations=None):
        declarations = declarations or r.load_input(self.input)
        with r._parent(self.input) as (fd, name):
            return r._observe(declarations, fd, r.time.monotonic() + 300)

    def assemble(self):
        declared = r.load_input(self.input)
        return r.assemble(declared, self.observations(declared), input_digest=m.content_digest(self.input.read_bytes()),
                          timestamp=STAMP, run_id="run-test", manifest_id="manifest-test")

    def test_fixture_supports_only_accountable_fictional_mapping(self):
        declared = r.load_input(self.input)
        observations = self.observations(declared)
        self.assertIsNone(observations[declared.evidence[0].path].content)
        self.assertIsNotNone(observations[declared.sources[0].file.path].content)
        bundle = self.assemble()
        self.assertEqual(bundle.declarations, declared)
        self.assertEqual([item.state for item in bundle.requirement_assessments], ["supported", "unresolved"])
        self.assertEqual([item.applicability for item in bundle.effective_applicability_decisions], ["applicable", "unresolved"])
        self.assertEqual(bundle.run.state, "partial")
        self.assertEqual(len(bundle.family_screenings), 11)
        self.assertEqual(m.parse_record(m.RevalidationBundle, m.canonical_json(bundle)), bundle)
        manifest_fields = bundle.manifest.model_dump(mode="json", exclude={"digest"})
        self.assertEqual(bundle.manifest.digest, m.content_digest(r._json_bytes(manifest_fields)))
        self.assertEqual(bundle.input_digest, m.content_digest(self.input.read_bytes()))

    def test_json_rejected_before_selected_reads_and_output(self):
        original = self.input.read_bytes()
        bad = [b'{"schema_version":1,"schema_version":1}', b'{"value":NaN}', b'{"value":Infinity}',
               b'{"value":1e999}', b'{"private":"SENTINEL",', b"\xff"]
        for body in bad:
            self.input.write_bytes(body)
            with self.subTest(body=body), patch.object(r, "_observe", side_effect=AssertionError("selected read")), self.assertRaises(r.RevalidationError) as caught:
                r.run(self.input, self.root / "invalid")
            self.assertEqual(caught.exception.code, "invalid-input")
            self.assertNotIn("SENTINEL", str(caught.exception))
            self.assertFalse((self.root / "invalid").exists())
        self.input.write_bytes(original)
        for change in (
            lambda p: p.update(schema_version=True),
            lambda p: p["requirements"][0]["fact_refs"][0].update(id="dangling"),
            lambda p: p["evidence"][0]["evidence"].update(project_id="wrong"),
            lambda p: p["requirements"].append(deepcopy(p["requirements"][0])),
            lambda p: p["scope"].update(unexpected="secret"),
        ):
            self.payload = json.loads(original)
            change(self.payload)
            self.save()
            with patch.object(r, "_observe", side_effect=AssertionError("selected read")), self.assertRaises(r.RevalidationError):
                r.run(self.input, self.root / "invalid")

    def test_generated_id_collisions_and_unrepresentable_methods_fail_before_selected_reads(self):
        baseline = deepcopy(self.payload)
        for change in (
            lambda p: p["applicability_decisions"][0].update(id=r._derived_id("unresolved", "obligation-example")),
            lambda p: p["requirements"][0].update(id=r._derived_id("disposition", "obligation-example")),
            lambda p: p["obligations"][0].update(required_methods=["x" * 257]),
            lambda p: p["obligations"][0].update(required_methods=["document", "document"]),
        ):
            self.payload = deepcopy(baseline)
            change(self.payload)
            if len(self.payload["obligations"][0]["required_methods"][0]) > 256:
                self.payload["evidence_reviews"] = []
            self.save()
            with patch.object(r, "_observe", side_effect=AssertionError("selected read")), self.assertRaises(r.RevalidationError):
                r.run(self.input, self.root / "bad-generated")
            self.assertFalse((self.root / "bad-generated").exists())

    def test_json_exact_byte_and_string_aware_depth_bounds(self):
        raw = self.input.read_bytes()
        self.input.write_bytes(raw + b" " * (m.MAX_REQUEST_BYTES - len(raw)))
        r.load_input(self.input)
        with self.input.open("ab") as output:
            output.write(b" ")
        with self.assertRaises(r.RevalidationError) as caught:
            r.load_input(self.input)
        self.assertEqual(caught.exception.code, "capacity-exceeded")
        r._check_json_depth(b"[" * 32 + b"0" + b"]" * 32)
        r._check_json_depth(json.dumps({"text": "[" * 100 + '\\"' + "]" * 100}).encode())
        with self.assertRaises(r.RevalidationError):
            r._check_json_depth(b"[" * 33 + b"0" + b"]" * 33)

    def test_unresolved_claims_and_each_missing_source_dimension_are_retained(self):
        for topic in m.get_args(m.SourceReviewTopic):
            payload = deepcopy(self.payload)
            payload["source_reviews"][0]["review_notes"].pop(topic)
            self.input.write_text(json.dumps(payload))
            bundle = self.assemble()
            self.assertEqual(bundle.declarations.source_reviews[0].review_notes, payload["source_reviews"][0]["review_notes"])
            self.assertEqual(bundle.effective_applicability_decisions[0].applicability, "unresolved")
            self.assertTrue(any(topic in gap for gap in bundle.gaps))
        self.payload["applicability_decisions"][0].update(reviewer=None, rationale="")
        self.save()
        bundle = self.assemble()
        self.assertIsNone(bundle.declarations.applicability_decisions[0].reviewer)
        self.assertEqual(bundle.effective_applicability_decisions[0].applicability, "unresolved")
        self.assertNotEqual(bundle.effective_applicability_decisions[0].id, bundle.declarations.applicability_decisions[0].id)

    def test_mixed_synthetic_provenance_and_offline_real_freshness(self):
        self.payload["sources"][0]["source"].update(type="eu_act", synthetic=False)
        self.payload["source_targets"][0]["intended_type"] = "eu_act"
        for name in ("source_reviews", "applicability_decisions", "evidence_reviews"):
            for item in self.payload[name]:
                item["synthetic"] = False
        self.save()
        bundle = self.assemble()
        self.assertTrue(bundle.synthetic)
        self.assertTrue(all(item.synthetic for item in bundle.effective_applicability_decisions))
        self.assertFalse(bundle.declarations.sources[0].source.synthetic)
        self.assertEqual(bundle.effective_applicability_decisions[0].applicability, "unresolved")
        self.assertTrue(any("freshness" in gap for gap in bundle.gaps))
        self.assertEqual(bundle.declarations.sources[0].source.retrieved_at, self.payload["sources"][0]["source"]["retrieved_at"])

    def test_empty_registers_expand_coverage_without_invented_law(self):
        for name in ("requirements", "source_targets", "sources", "source_reviews", "obligations", "controls",
                     "applicability_decisions", "evidence", "evidence_reviews", "family_screenings"):
            self.payload[name] = []
        self.save()
        bundle = self.assemble()
        self.assertEqual(bundle.obligation_dispositions, [])
        self.assertEqual(bundle.requirement_assessments, [])
        self.assertEqual(len(bundle.family_screenings), 11)
        self.assertTrue(all(item.applicability == "unresolved" for item in bundle.family_screenings))
        self.assertTrue(any("empty" in gap for gap in bundle.gaps))
        self.assertEqual(bundle.run.state, "partial")

    def test_complete_means_assembly_only_and_empty_methods_leave_a_gap(self):
        unmapped = deepcopy(self.payload["obligations"][1])
        self.payload["scope"]["roles"] = self.payload["scope"]["roles"][:1]
        self.payload["scope"]["exclusions"] = []
        self.payload["requirements"] = self.payload["requirements"][:1]
        self.payload["obligations"] = self.payload["obligations"][:1]
        decision = self.payload["applicability_decisions"][0]
        self.payload["family_screenings"] = [{
            "family": family, "synthetic": True, "scope": deepcopy(decision["scope"]),
            "assessment_date": decision["assessment_date"], "applicability": "not_applicable",
            "rationale": "Explicit fictional family exclusion only; no real-law review.",
            "fact_refs": deepcopy(decision["fact_refs"]), "source_refs": [{"id": "source-example", "revision": 0}],
            "reviewer": "Fictional reviewer", "reviewed_at": STAMP, "gaps": [],
        } for family in m.LEGAL_FAMILIES]
        self.save()
        bundle = self.assemble()
        self.assertEqual(bundle.run.state, "completed")
        self.assertTrue(bundle.synthetic)
        unmapped["required_methods"] = []
        self.payload["obligations"].append(unmapped)
        second_decision = deepcopy(decision)
        second_decision.update(id="decision-second", obligation={"id": unmapped["id"], "revision": unmapped["revision"]})
        self.payload["applicability_decisions"].append(second_decision)
        self.save()
        bundle = self.assemble()
        self.assertEqual(bundle.run.state, "partial")
        self.assertTrue(any("methods are undeclared" in gap for gap in bundle.gaps))

    def test_referenced_source_material_and_overlays_cannot_be_ignored(self):
        baseline = deepcopy(self.payload)
        for relation in ("related_source_ids", "act_chain", "case_law_refs", "national_overlay_ids", "overlay_ids"):
            self.payload = deepcopy(baseline)
            target = deepcopy(self.payload["source_targets"][0])
            target["id"] = "dependency-target"
            self.payload["source_targets"].append(target)
            selected = deepcopy(self.payload["sources"][0])
            selected.update(target_id="dependency-target", file=None)
            selected["source"]["id"] = "dependency-source"
            self.payload["sources"].append(selected)
            if relation == "related_source_ids":
                self.payload["sources"][0]["source"][relation] = ["dependency-source"]
            elif relation == "overlay_ids":
                self.payload["obligations"][0][relation] = ["dependency-source"]
            else:
                self.payload["source_reviews"][0][relation] = ["dependency-source"]
            self.save()
            bundle = self.assemble()
            with self.subTest(relation=relation):
                self.assertEqual(bundle.effective_applicability_decisions[0].applicability, "unresolved")
                self.assertEqual(bundle.requirement_assessments[0].state, "unresolved")
                self.assertTrue(any("referenced" in gap for gap in bundle.gaps))

    def test_methods_stay_independent_and_technical_is_not_tested(self):
        obligation = self.payload["obligations"][0]
        obligation["required_methods"] += ["organizational", "technical"]
        self.save()
        bundle = self.assemble()
        methods = {item.method: item.outcome for item in bundle.obligation_dispositions[0].required_method_dispositions}
        self.assertEqual(methods, {"document": "passed", "organizational": "unresolved_review", "technical": "not_tested"})
        self.assertEqual(bundle.requirement_assessments[0].state, "unresolved")
        review = deepcopy(self.payload["evidence_reviews"][0])
        review.update(id="review-insufficient", method="organizational", state="insufficient", rationale="Fictional reviewed insufficiency")
        self.payload["evidence_reviews"].append(review)
        self.save()
        bundle = self.assemble()
        self.assertEqual(bundle.obligation_dispositions[0].manual_review, "unsupported")
        self.assertEqual(bundle.obligation_dispositions[0].required_method_dispositions[1].outcome, "observed_failure")
        self.assertEqual(bundle.requirement_assessments[0].state, "conflicting")

    def test_corrupt_missing_blocked_and_metadata_only_evidence_cannot_support(self):
        evidence_path = self.root / self.payload["evidence"][0]["path"]
        original = evidence_path.read_bytes()
        evidence_path.write_bytes(b"SECRET_SENTINEL changed evidence bytes")
        bundle = self.assemble()
        self.assertEqual(bundle.evidence[0].availability, "corrupt")
        self.assertEqual(bundle.evidence[0].digest, m.content_digest(evidence_path.read_bytes()))
        self.assertNotEqual(bundle.evidence[0].digest, bundle.declarations.evidence[0].evidence.digest)
        self.assertNotIn("SECRET_SENTINEL", m.canonical_json(bundle).decode())
        evidence_path.unlink()
        self.assertEqual(self.assemble().evidence[0].availability, "missing")
        evidence_path.write_bytes(original)
        for state in ("missing", "purged", "blocked", "corrupt"):
            self.payload["evidence"][0]["evidence"]["availability"] = state
            self.save()
            self.assertEqual(self.assemble().evidence[0].availability, state)
        self.payload["evidence"][0]["evidence"]["availability"] = "available"
        self.payload["evidence"][0]["path"] = None
        self.save()
        self.assertEqual(self.assemble().evidence[0].availability, "missing")

    def test_requirement_own_dependencies_do_not_borrow_obligation_support(self):
        baseline = deepcopy(self.payload)
        for dependency in ("evidence", "fact", "origin"):
            self.payload = deepcopy(baseline)
            requirement = self.payload["requirements"][0]
            if dependency == "evidence":
                selected = deepcopy(self.payload["evidence"][0])
                selected["evidence"].update(id="requirement-only-evidence", availability="missing")
                self.payload["evidence"].append(selected)
                requirement["evidence_ids"].append("requirement-only-evidence")
            elif dependency == "fact":
                requirement["fact_refs"].append({"id": "fact-unknown", "revision": 0})
            else:
                requirement.update(origin={"path": "missing-origin.txt", "digest": m.content_digest(b"missing")}, locator="section 1")
            self.save()
            bundle = self.assemble()
            with self.subTest(dependency=dependency):
                self.assertEqual(bundle.obligation_dispositions[0].required_method_dispositions[0].outcome, "passed")
                self.assertEqual(bundle.requirement_assessments[0].state, "unresolved")
                self.assertTrue(bundle.requirement_assessments[0].gaps)

    def test_independent_verification_does_not_follow_unretained_attestation(self):
        self.payload["evidence"][0]["evidence"]["provenance"] = "independently_verified"
        self.save()
        bundle = self.assemble()
        self.assertEqual(bundle.evidence[0].provenance, "independently_verified")
        self.assertEqual(bundle.obligation_dispositions[0].required_method_dispositions[0].outcome, "unresolved_review")
        self.assertTrue(any("verification proof" in gap for gap in bundle.gaps))

    def test_local_source_content_admission_is_conservative(self):
        cases = [
            (b"Fictional plain source", "text/plain", None, "accepted"),
            (b"Fictional plain source", "TEXT/PLAIN", "UTF-8", "accepted"),
            (b"<html><body>Fictional provision</body></html>", "text/html", None, "accepted"),
            (b"<html><body>Fictional provision</body></html>", "application/xhtml+xml", "utf-8", "accepted"),
            (b"<html><title>Login</title><body><form>Sign in</form></body></html>", "text/html", None, "rejected"),
            (b"<html><body><input type='password'></body></html>", "text/html", None, "rejected"),
            (b"Verify you are human captcha", "text/plain", None, "rejected"),
            (b"<html><title>Just a moment...</title><body>Wait</body></html>", "text/html", None, "rejected"),
            (b"Sign in to continue", "text/plain", None, "rejected"),
            (b"Please sign in to access this document.", "text/plain", None, "rejected"),
            (b"<html><body><h1>404 Not Found</h1></body></html>", "text/html", None, "rejected"),
            (b"<![UNKNOWN[broken]>", "text/html", None, "needs_review"),
            (b"<html><title>503 Error</title><body>Down</body></html>", "text/html", None, "rejected"),
            (b"<p>Uncertain fragment</p>", "text/html", None, "needs_review"),
            (b"<html><body>Markup</body></html>", "text/plain", None, "needs_review"),
            (b"plain", "text/html", None, "needs_review"),
            (b"plain", "text/plain", "latin-1", "needs_review"),
            (b"\xff", "text/plain", None, "needs_review"),
            (b"%PDF-1.7\n", "application/pdf", None, "needs_review"),
            (b"%PDF-1.7\n", "application/pdf", "utf-8", "needs_review"),
            (b"not pdf", "application/pdf", None, "needs_review"),
            (b"%PDF-1.7\n", "text/plain", None, "needs_review"),
            (b"plain", "application/octet-stream", None, "needs_review"),
        ]
        for content, media_type, charset, state in cases:
            with self.subTest(content=content, media_type=media_type, charset=charset):
                self.assertEqual(r.admit_source_content(content, media_type, charset).state, state)

    def test_rejected_source_not_retained_and_pdf_only_manual(self):
        source = self.payload["sources"][0]
        path = self.root / source["file"]["path"]
        for content, media_type, retain in (
            (b"<html><title>Sign in</title><body><form>Login</form></body></html>", "text/html", False),
            (b"%PDF-1.7\nfictional", "application/pdf", True),
        ):
            path.write_bytes(content)
            source.update(media_type=media_type, charset=None)
            source["file"]["digest"] = source["source"]["content_digest"] = m.content_digest(content)
            self.save()
            output = self.root / ("pdf" if retain else "rejected")
            bundle = r.run(self.input, output)
            self.assertEqual(bundle.effective_applicability_decisions[0].applicability, "unresolved")
            self.assertEqual((output / "sources").exists(), retain)
            if retain:
                self.assertEqual(next((output / "sources").iterdir()).read_bytes(), content)

    def test_no_network_execution_walk_or_unselected_read(self):
        selected = []
        original = r._read_file
        def read(fd, path, **kwargs):
            selected.append((path, kwargs["retain"]))
            return original(fd, path, **kwargs)
        with patch.object(r, "_read_file", side_effect=read), patch.object(socket, "socket", side_effect=AssertionError("network")), \
             patch.object(socket, "create_connection", side_effect=AssertionError("network")), \
             patch.object(subprocess, "Popen", side_effect=AssertionError("execution")), \
             patch.object(os, "walk", side_effect=AssertionError("walk")), patch.object(os, "scandir", side_effect=AssertionError("enumeration")):
            r.run(self.input, self.root / "run")
        self.assertEqual(selected, [("input.json", True), ("revalidation-synthetic/source.txt", True), ("revalidation-synthetic/evidence.txt", False)])

    def test_private_publication_exact_marker_and_no_overwrite_history(self):
        source_before = {self.input: self.input.read_bytes(), **{path: path.read_bytes() for path in (self.root / "revalidation-synthetic").iterdir()}}
        first = self.root / "run-one"
        bundle = r.run(self.input, first)
        before = {str(path.relative_to(first)): path.read_bytes() for path in first.rglob("*") if path.is_file()}
        marker = m.parse_record(m.RunCompletion, before["complete.json"])
        self.assertEqual(set(before) - {"complete.json"}, {item.path for item in marker.files})
        for item in marker.files:
            self.assertEqual(item.digest, m.content_digest(before[item.path]))
        self.assertEqual(stat.S_IMODE(first.stat().st_mode), 0o700)
        for path in first.rglob("*"):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700 if path.is_dir() else 0o600)
        self.assertNotIn("evidence.txt", " ".join(before))
        with self.assertRaises(r.RevalidationError) as caught:
            r.run(self.input, first)
        self.assertEqual(caught.exception.code, "output-exists")
        second = r.run(self.input, self.root / "run-two")
        self.assertNotEqual(bundle.run.id, second.run.id)
        self.assertNotEqual(bundle.manifest.id, second.manifest.id)
        self.assertEqual(before, {str(path.relative_to(first)): path.read_bytes() for path in first.rglob("*") if path.is_file()})
        self.assertEqual(source_before, {path: path.read_bytes() for path in source_before})

    def test_symlink_fifo_device_and_public_parent_fail_closed(self):
        link = self.root / "input-link.json"
        link.symlink_to(self.input)
        with self.assertRaises(r.RevalidationError):
            r.load_input(link)
        directory_link = self.root / "linked"
        directory_link.symlink_to(self.root / "revalidation-synthetic", target_is_directory=True)
        self.payload["evidence"][0]["path"] = "linked/evidence.txt"
        self.save()
        self.assertEqual(self.assemble().evidence[0].availability, "blocked")
        fifo = self.root / "fifo"
        os.mkfifo(fifo)
        with r._parent(fifo) as (fd, name), patch.object(os, "read", side_effect=AssertionError("special file read")):
            self.assertEqual(r._read_file(fd, name, limit=100, retain=False).availability, "blocked")
        original_fstat = os.fstat
        def device(fd):
            info = original_fstat(fd)
            values = list(info)
            values[0] = stat.S_IFCHR | 0o600
            return os.stat_result(values)
        with r._parent(self.input) as (fd, name), patch.object(os, "fstat", side_effect=device), \
             patch.object(os, "read", side_effect=AssertionError("device read")):
            self.assertEqual(r._read_file(fd, name, limit=100000, retain=False).availability, "blocked")
        public = self.root / "public"
        public.mkdir(mode=0o755)
        public.chmod(0o755)
        with self.assertRaises(r.RevalidationError) as caught:
            r.run(self.input, public / "run")
        self.assertEqual(caught.exception.code, "privacy-unavailable")
        self.assertEqual(stat.S_IMODE(public.stat().st_mode), 0o755)
        output_link = self.root / "output-link"
        output_link.symlink_to(public, target_is_directory=True)
        with self.assertRaises(r.RevalidationError):
            r.run(self.input, output_link / "run")
        self.assertFalse((public / "run").exists())

    def test_read_mutation_is_corrupt_without_stable_source_bytes(self):
        path = self.root / self.payload["sources"][0]["file"]["path"]
        original_read = os.read
        mutated = False
        def mutate(fd, size):
            nonlocal mutated
            data = original_read(fd, size)
            if data and not mutated:
                mutated = True
                with path.open("ab") as output:
                    output.write(b"changed during read")
            return data
        with r._parent(path) as (fd, name), patch.object(os, "read", side_effect=mutate):
            observation = r._read_file(fd, name, limit=100000, retain=True)
        self.assertEqual(observation.availability, "corrupt")
        self.assertIsNotNone(observation.digest)
        self.assertIsNone(observation.content)

    def test_file_and_aggregate_limits_do_not_silently_drop_records(self):
        path = self.root / "bounded"
        path.write_bytes(b"x" * r.MAX_FILE_BYTES)
        with r._parent(path) as (fd, name):
            self.assertEqual(r._read_file(fd, name, limit=r.MAX_FILE_BYTES, retain=False).size, r.MAX_FILE_BYTES)
        with path.open("ab") as output:
            output.write(b"x")
        with r._parent(path) as (fd, name), self.assertRaises(r.RevalidationError):
            r._read_file(fd, name, limit=r.MAX_FILE_BYTES, retain=False)
        declared = r.load_input(self.input)
        with patch.object(r, "MAX_TOTAL_BYTES", 2), r._parent(self.input) as (fd, name), self.assertRaises(r.RevalidationError):
            r._observe(declared, fd, r.time.monotonic() + 300)
        source_path = self.root / declared.sources[0].file.path
        evidence_path = self.root / declared.evidence[0].path
        total = source_path.stat().st_size + evidence_path.stat().st_size
        with patch.object(r, "MAX_TOTAL_BYTES", total), r._parent(self.input) as (fd, name):
            self.assertEqual(len(r._observe(declared, fd, r.time.monotonic() + 300)), 2)
        with patch.object(r, "MAX_TOTAL_BYTES", total - 1), r._parent(self.input) as (fd, name), self.assertRaises(r.RevalidationError):
            r._observe(declared, fd, r.time.monotonic() + 300)

    def test_output_caps_and_render_failure_happen_before_directory_creation(self):
        from eu_compliance_guard import report
        output = self.root / "too-large"
        with patch.object(report, "render_report", return_value="x" * (r.MAX_REPORT_BYTES + 1)), self.assertRaises(r.RevalidationError):
            r.run(self.input, output)
        self.assertFalse(output.exists())
        with patch.object(report, "render_report", side_effect=ValueError("SECRET_SENTINEL")), self.assertRaises(r.RevalidationError) as caught:
            r.run(self.input, output)
        self.assertNotIn("SECRET_SENTINEL", str(caught.exception))
        self.assertFalse(output.exists())
        bundle = self.assemble()
        size = len(m.canonical_json(bundle))
        with patch.object(m, "MAX_REQUEST_BYTES", size - 1), self.assertRaises(r.RevalidationError):
            r._publish(output, bundle, self.observations(), "report", r.time.monotonic() + 300)
        self.assertFalse(output.exists())

    def test_failures_and_interrupts_leave_incomplete_directory_without_marker(self):
        for failure in (OSError("PRIVATE_SENTINEL"), KeyboardInterrupt()):
            for after_marker in (False, True):
                output = self.root / f"failed-{type(failure).__name__}-{after_marker}"
                original_fsync = os.fsync
                def fail(fd):
                    if not after_marker or (output / "complete.json").exists():
                        raise failure
                    return original_fsync(fd)
                with patch.object(os, "fsync", side_effect=fail), self.assertRaises((r.RevalidationError, KeyboardInterrupt)) as caught:
                    r.run(self.input, output)
                self.assertTrue(output.is_dir())
                self.assertFalse((output / "complete.json").exists())
                self.assertNotIn("PRIVATE_SENTINEL", str(caught.exception))
        with patch.object(os, "write", side_effect=OSError("write failed")), self.assertRaises(r.RevalidationError):
            r.run(self.input, self.root / "write-failed")
        self.assertFalse((self.root / "write-failed/complete.json").exists())

    def test_assembly_validation_errors_distinguish_capacity_from_semantic_failure(self):
        valid = self.assemble().model_dump()
        with self.assertRaises(ValidationError) as semantic:
            m.RevalidationBundle.model_validate({**valid, "project_id": "wrong-project"})
        with patch.object(m, "RevalidationBundle", side_effect=semantic.exception), self.assertRaises(r.RevalidationError) as caught:
            self.assemble()
        self.assertEqual(caught.exception.code, "invalid-output")
        template = deepcopy(self.payload["obligations"][0])
        self.payload["obligations"] = [{**template, "id": f"obligation-{i}", "required_methods": [f"method-{j}" for j in range(7)]}
                                       for i in range(200)]
        self.payload["requirements"] = []
        self.payload["applicability_decisions"] = []
        self.payload["evidence_reviews"] = []
        self.save()
        with self.assertRaises(r.RevalidationError) as caught:
            r.run(self.input, self.root / "derived-over-capacity")
        self.assertEqual(caught.exception.code, "capacity-exceeded")
        self.assertFalse((self.root / "derived-over-capacity").exists())

    def test_cooperative_budget_expires_without_containment_claim(self):
        with patch.object(r.time, "monotonic", side_effect=[0, 301]), self.assertRaises(r.RevalidationError) as caught:
            r.run(self.input, self.root / "expired")
        self.assertEqual(caught.exception.code, "budget-exceeded")
        self.assertFalse((self.root / "expired").exists())
