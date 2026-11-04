"""Starter declarations and located diagnostics on synthetic inputs; nothing is fetched."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import unittest

from eu_compliance_guard import authoring as a, models as m
from eu_compliance_guard.__main__ import main

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/revalidation-synthetic.json"
SECRET = "PRIVATE-VALUE-SENTINEL"


class AuthoringTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="eucg-authoring-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        assets = self.root / "revalidation-synthetic"
        assets.mkdir()
        for name in ("source.txt", "evidence.txt"):
            (assets / name).write_bytes((FIXTURE.parent / "revalidation-synthetic" / name).read_bytes())
        self.payload = json.loads(FIXTURE.read_bytes())
        self.input = self.root / "declarations.json"

    def check(self, payload=None, raw=None):
        self.input.write_bytes(raw if raw is not None else json.dumps(payload or self.payload).encode())
        return a.check(self.input)

    def cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_init_writes_a_valid_starter_once(self):
        path = self.root / "project/.eu-compliance-guard/declarations.json"
        code, stdout, _ = self.cli("init", "--project-id", "shop", "--path", str(path), "--assessment-date", "2026-11-03",
                                   "--jurisdiction", "EU", "--jurisdiction", "DE")
        self.assertEqual(code, 0)
        self.assertIn(str(path), stdout)
        record = m.parse_record(m.RevalidationInput, path.read_bytes())
        self.assertEqual((record.project_id, record.synthetic, record.scope.assessment_date, record.scope.jurisdictions),
                         ("shop", False, "2026-11-03", ["EU", "DE"]))
        self.assertTrue(a.check(path)["valid"])
        before = path.read_bytes()
        code, _, stderr = self.cli("init", "--project-id", "other", "--path", str(path))
        self.assertEqual((code, path.read_bytes()), (2, before))
        self.assertIn("output-exists", stderr)
        code, _, stderr = self.cli("init", "--project-id", "bad id!", "--path", str(self.root / "x.json"))
        self.assertEqual(code, 2)
        self.assertFalse((self.root / "x.json").exists())
        self.assertEqual(record.files_root, "project")

    def test_init_outside_the_dedicated_folder_resolves_files_beside_the_declarations(self):
        path = self.root / "project/decl.json"
        self.assertEqual(self.cli("init", "--project-id", "shop", "--path", str(path))[0], 0)
        self.assertEqual(m.parse_record(m.RevalidationInput, path.read_bytes()).files_root, "declarations_dir")

    def test_init_rejects_an_empty_date_and_symlinked_folders(self):
        code, _, stderr = self.cli("init", "--project-id", "shop", "--path", str(self.root / "d.json"), "--assessment-date", "")
        self.assertEqual(code, 2)
        self.assertFalse((self.root / "d.json").exists())
        (self.root / "real").mkdir()
        (self.root / "link").symlink_to(self.root / "real")
        code, _, stderr = self.cli("init", "--project-id", "shop", "--path", str(self.root / "link/sub/d.json"))
        self.assertEqual(code, 2)
        self.assertIn("unsafe-path", stderr)
        self.assertFalse((self.root / "real/sub").exists())

    def test_init_refuses_a_path_that_names_a_folder(self):
        code, stdout, stderr = self.cli("init", "--project-id", "shop", "--path", str(self.root / "newdir") + "/")
        self.assertEqual((code, stdout), (2, ""))
        self.assertIn("invalid-input", stderr)
        self.assertFalse((self.root / "newdir").exists())

    def test_init_reports_unusable_paths_by_cause_and_leaves_nothing_behind(self):
        (self.root / "file").touch()
        for path, expected in ((self.root / "file/decl.json", "unsafe-path"),
                               (self.root / "q2/r" / ("n" * 300), "io-failed")):
            with self.subTest(expected=expected):
                code, stdout, stderr = self.cli("init", "--project-id", "shop", "--path", str(path))
                self.assertEqual((code, stdout), (2, ""))
                self.assertIn(f"{expected}: init failed", stderr)
        self.assertFalse((self.root / "q2").exists())
        # A write that fails part-way (here the file-size limit) must not leave a file that blocks a retry.
        path = self.root / "limited/declarations.json"
        result = subprocess.run([sys.executable, "-m", "eu_compliance_guard", "init", "--project-id", "shop", "--path", str(path)],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=30,
                                preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_FSIZE,
                                                                      (0, resource.getrlimit(resource.RLIMIT_FSIZE)[1])))
        self.assertEqual(result.returncode, 2)
        self.assertIn("io-failed: init failed", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse((self.root / "limited").exists())
        self.assertEqual(self.cli("init", "--project-id", "shop", "--path", str(path))[0], 0)
        self.assertTrue(a.check(path)["valid"])

    def test_valid_fixture_reports_counts_files_targets_and_warnings(self):
        report = self.check()
        self.assertTrue(report["valid"])
        self.assertEqual(report["counts"]["requirements"], 2)
        self.assertEqual([item["matches_declared"] for item in report["files"]], [True, True])
        self.assertEqual(report["targets"][0]["fetch"], "never fetched (fictional fixture)")
        self.assertTrue(any("no obligation_refs" in item["problem"] for item in report["warnings"]))

    def test_sources_sharing_a_file_are_each_screened_with_their_own_media_type(self):
        second = deepcopy(self.payload["sources"][0])
        second["source"]["id"] = "source-two"
        second.update(media_type="application/msword", charset=None)
        for sources, flagged in (([self.payload["sources"][0], second], ["sources[1].file"]),
                                 ([second, self.payload["sources"][0]], ["sources[0].file"])):
            with self.subTest(flagged=flagged):
                report = self.check(dict(self.payload, sources=sources))
                self.assertTrue(report["valid"], report["errors"])
                self.assertEqual([item["at"] for item in report["warnings"] if "source content" in item["problem"]], flagged)

    def test_cross_reference_errors_are_located_with_identifiers(self):
        cases = [
            (lambda p: p["requirements"][0]["fact_refs"][0].update(revision=7),
             "requirements[0].fact_refs[0]", "pinned at revision 7 but declared at revision 0"),
            (lambda p: p["requirements"][0]["obligation_refs"][0].update(id="missing-obligation"),
             "requirements[0].obligation_refs[0]", "unknown reference missing-obligation"),
            (lambda p: p["sources"][0].update(target_id="nowhere"), "sources[0].target_id", "unknown reference nowhere"),
            (lambda p: p["requirements"].append(deepcopy(p["requirements"][0])), "requirements", "duplicate record identity"),
            (lambda p: p["evidence_reviews"][0].update(method="invented"), "evidence_reviews[0].method", "required_methods"),
        ]
        for change, at, problem in cases:
            payload = deepcopy(self.payload)
            change(payload)
            with self.subTest(at=at):
                report = self.check(payload)
                self.assertFalse(report["valid"])
                self.assertEqual(report["errors"][0]["at"], at)
                self.assertIn(problem, report["errors"][0]["problem"])

    def test_identifiers_with_colons_keep_the_json_location(self):
        for identity in ("fact-unknown", "fact:x"):
            payload = deepcopy(self.payload)
            payload["scope"]["roles"][2].update(id=identity, evidence_ids=["nope"])
            with self.subTest(identity=identity):
                self.assertEqual(self.check(payload)["errors"],
                                 [{"at": "scope.roles[2].evidence_ids", "problem": "unknown reference nope"}])

    def test_bound_and_scope_problems_name_their_json_location(self):
        def activity(index):
            return {"id": f"activity-{index}", "purpose": "Fictional processing", "subjects": [], "data_categories": [],
                    "roles": [], "lawful_basis": deepcopy(self.payload["scope"]["roles"][0]), "recipients": [],
                    "locations": [], "stores": [], "retention": [], "evidence_owner": "Fictional owner"}

        def evidence(index):
            item = deepcopy(self.payload["evidence"][0])
            item["evidence"]["id"] = f"evidence-{index}"
            item["path"] = f"revalidation-synthetic/evidence-{index}.txt"
            return item

        provision = self.payload["obligations"][0]["source_provisions"][0]
        cases = [
            (lambda p: p["scope"].update(project_id="other"), "scope.project_id", "differs from the envelope project_id"),
            (lambda p: p["scope"].update(activities=[activity(index) for index in range(101)]),
             "scope.activities", "more than 100 processing activities"),
            (lambda p: p["scope"].update(roles=[deepcopy(p["scope"]["roles"][0]) for _ in range(501)]),
             "scope", "more than 500 fact occurrences"),
            (lambda p: p["scope"]["roles"].append({**deepcopy(p["scope"]["roles"][0]), "value": "other"}),
             "scope.roles[3]", "conflicting copies of fact identity fact-declared"),
            (lambda p: p["evidence"].extend(evidence(index) for index in range(31)),
             "evidence[31].path", "more than 32 distinct selected files"),
            (lambda p: p["evidence"][0].update(path=p["sources"][0]["file"]["path"]),
             "evidence[0].path", "conflicting selected file digests"),
            (lambda p: p["obligations"][1].update(source_provisions=[deepcopy(provision) for _ in range(1001)]),
             "obligations[1]", "record exceeds nested collection limit"),
            (lambda p: p["obligations"][1]["source_provisions"][0].update(source_target_id="nowhere"),
             "obligations[1].source_provisions[0].source_target_id", "unknown reference nowhere"),
            (lambda p: p["requirements"][1].update(project_id="other"), "requirements[1].project_id",
             "cross-project declaration (differs from the envelope project_id)"),
            (lambda p: p.update(synthetic=False), "synthetic", "synthetic declarations require a synthetic envelope"),
        ]
        for change, at, problem in cases:
            payload = deepcopy(self.payload)
            change(payload)
            with self.subTest(at=at):
                self.assertEqual(self.check(payload)["errors"][:1], [{"at": at, "problem": problem}])

    def test_field_errors_json_errors_and_files_never_echo_values(self):
        payload = deepcopy(self.payload)
        payload["synthetic"] = SECRET
        payload["requirements"][0]["statement"] = 5
        report = self.check(payload)
        self.assertEqual({item["at"] for item in report["errors"]}, {"synthetic", "requirements[0].statement"})
        self.assertNotIn(SECRET, json.dumps(report))
        report = self.check(raw=b'{"schema_version": 1,\n "project_id": "x",,}')
        self.assertEqual(report["errors"][0]["at"], "line 2, column 20")
        report = self.check(raw=b'{"a": 1, "a": 2}')
        self.assertIn("duplicate JSON key", report["errors"][0]["problem"])
        (self.root / "revalidation-synthetic/evidence.txt").write_bytes(SECRET.encode())
        report = self.check()
        mismatch = next(item for item in report["errors"] if item["at"] == "evidence[0].path")
        self.assertIn("observed sha256:", mismatch["problem"])
        self.assertNotIn(SECRET, json.dumps(report))
        (self.root / "revalidation-synthetic/evidence.txt").unlink()
        self.assertIn("missing", next(item for item in self.check()["errors"] if item["at"] == "evidence[0].path")["problem"])
        self.assertIn("not found", a.check(self.root / "absent/declarations.json")["errors"][0]["problem"])

    def test_byte_order_marks_and_utf16_are_reported_as_encoding_problems(self):
        text = json.dumps(self.payload)
        for name, raw in (("utf-8 bom", b"\xef\xbb\xbf" + text.encode()), ("utf-16", text.encode("utf-16")),
                          ("utf-16-le without bom", text.encode("utf-16-le")), ("invalid utf-8", b"\xff" + text.encode())):
            with self.subTest(encoding=name):
                self.assertEqual(self.check(raw=raw)["errors"],
                                 [{"at": "(file)", "problem": "declarations must be UTF-8 JSON without a byte-order mark"}])

    def test_oversized_declarations_are_a_located_problem_in_the_report(self):
        text = json.dumps(self.payload).encode()
        exact = text[:-1] + b" " * (m.MAX_REQUEST_BYTES - len(text)) + text[-1:]
        self.assertTrue(self.check(raw=exact)["valid"])
        self.input.write_bytes(exact[:-1] + b" " + exact[-1:])
        code, stdout, stderr = self.cli("check", "--input", str(self.input), "--json")
        self.assertEqual((code, stderr), (2, ""))
        self.assertEqual(json.loads(stdout)["errors"],
                         [{"at": "(file)", "problem": "declarations file exceeds the 4 MiB limit"}])

    def test_a_truncated_problem_list_says_how_many_problems_exist(self):
        payload = deepcopy(self.payload)
        payload["requirements"] += [{"id": index} for index in range(60)]
        report = self.check(payload)
        self.assertEqual(len(report["errors"]), a.MAX_PROBLEMS)
        self.assertGreater(report["total_errors"], a.MAX_PROBLEMS)
        self.assertEqual(a.format_check(report).splitlines()[0],
                         f"declarations: invalid ({report['total_errors']} problem(s); the first 50 are listed)")
        payload["requirements"] = payload["requirements"][:3]
        report = self.check(payload)
        self.assertEqual(report["total_errors"], len(report["errors"]))
        self.assertEqual(a.format_check(report).splitlines()[0], f"declarations: invalid ({len(report['errors'])} problem(s))")
        self.assertEqual(self.check()["total_errors"], 0)

    def test_official_and_unofficial_targets_and_cli_exit_codes(self):
        payload = deepcopy(self.payload)
        for identifier, url in (("target-eurlex", "https://eur-lex.europa.eu/eli/reg/2016/679/oj"),
                                ("target-blog", "https://example.com/gdpr")):
            payload["source_targets"].append({"id": identifier, "revision": 0, "family": "gdpr", "intended_url": url,
                                              "publisher": "Example", "intended_type": "final_guidance",
                                              "language": "en", "jurisdiction": "EU"})
        self.input.write_text(json.dumps(payload))
        code, stdout, _ = self.cli("check", "--input", str(self.input))
        self.assertEqual(code, 0)
        self.assertIn("target  source_targets[1] target-eurlex: fetchable", stdout)
        self.assertIn("not fetchable: host-not-official", stdout)
        self.assertIn("not a compliance conclusion", stdout)
        code, stdout, _ = self.cli("check", "--input", str(self.input), "--json")
        self.assertEqual((code, json.loads(stdout)["valid"]), (0, True))
        payload["requirements"][0]["fact_refs"][0]["revision"] = 3
        self.input.write_text(json.dumps(payload))
        self.assertEqual(self.cli("check", "--input", str(self.input))[0], 2)

    def test_a_target_whose_language_the_fetch_refuses_is_not_fetchable(self):
        url = "https://publications.europa.eu/resource/celex/02002L0058-20091219"
        for language, fetch in (("english", "not fetchable: invalid-language"), ("en_GB", "not fetchable: invalid-language"),
                                ("zh-Hant-TW", "not fetchable: invalid-language"), ("de-DE", "fetchable")):
            payload = deepcopy(self.payload)
            payload["source_targets"].append({"id": "t-lang", "revision": 0, "family": "eprivacy", "intended_url": url,
                                              "publisher": "Fictional publisher", "intended_type": "eu_act",
                                              "language": language, "jurisdiction": "EU"})
            with self.subTest(language=language):
                report = self.check(payload)
                self.assertTrue(report["valid"], report["errors"])
                self.assertEqual(report["targets"][1]["fetch"], fetch)
                refusals = [item["problem"] for item in report["warnings"] if item["at"] == "source_targets[1]"]
                self.assertEqual(len(refusals), fetch != "fetchable")
                self.assertTrue(all("(invalid-language)" in problem and language not in problem for problem in refusals))

    def test_changed_grounded_code_is_a_review_warning_without_a_digest_to_copy(self):
        from eu_compliance_guard import grounding as g, revalidation as r
        project = self.root / "shop"
        (project / "app").mkdir(parents=True)
        code = project / "app/web.py"
        code.write_text('def landing(response, visitor_id):\n    response.set_cookie("_analytics", visitor_id, max_age=395)\n')
        path = a.init(project / ".eu-compliance-guard/declarations.json", "shop", synthetic=True)
        data = json.loads(path.read_text())
        data["scope"]["roles"] = [{"id": "fact-cookie-lifetime", "revision": 0, "key": "Analytics cookie lifetime",
                                   "value": None, "basis": "unknown", "evidence_ids": [], "owner": "Fictional owner",
                                   "observed_at": "2026-11-04T00:00:00Z", "conflicts": []}]
        path.write_text(json.dumps(data))
        g.apply(path, "fact-cookie-lifetime", "app/web.py:2")
        runs = self.root / "runs"
        runs.mkdir(mode=0o700)
        r.run(path, runs / "run-001")
        code.write_text("def landing(response):\n    return response\n")
        observed = m.content_digest(code.read_bytes())
        for previous in (None, runs / "run-001"):
            with self.subTest(previous=previous):
                report = a.check(path, previous)
                self.assertTrue(report["valid"], report["errors"])
                problem = next(item["problem"] for item in report["warnings"] if item["at"] == "evidence[0].path")
                self.assertIn("ground --apply", problem)
                self.assertNotIn(observed.removeprefix("sha256:"), problem)
        # Hand-declared evidence keeps its digest error, even when its id looks like a grounded one.
        (self.root / "revalidation-synthetic/evidence.txt").write_bytes(b"changed")
        lookalike = json.loads(json.dumps(self.payload).replace('"evidence-example"', '"evidence-code-0123456789abcdef"'))
        for payload in (self.payload, lookalike):
            with self.subTest(evidence_id=payload["evidence"][0]["evidence"]["id"]):
                report = self.check(payload)
                self.assertIn("observed sha256:", next(item for item in report["errors"]
                                                       if item["at"] == "evidence[0].path")["problem"])
                self.assertFalse(any(item["at"] == "evidence[0].path" for item in report["warnings"]))

    def test_check_previous_names_records_needing_new_revisions(self):
        from eu_compliance_guard import revalidation as r
        runs = self.root / "runs"
        runs.mkdir(mode=0o700)
        self.input.write_text(json.dumps(self.payload))
        r.run(self.input, runs / "run-001")
        self.assertTrue(a.check(self.input, runs / "run-001")["valid"])
        payload = deepcopy(self.payload)
        payload["scope"]["roles"][0]["value"] = "changed fictional role"
        self.input.write_text(json.dumps(payload))
        report = a.check(self.input, runs / "run-001")
        self.assertFalse(report["valid"])
        located = {item["at"]: item["problem"] for item in report["errors"]}
        fact_id = payload["scope"]["roles"][0]["id"]
        self.assertIn(f"Fact {fact_id}", located)
        self.assertIn("raise it to 1", located[f"Fact {fact_id}"])
        self.assertIn("Scope scope-example", located)
        self.assertNotIn("changed fictional role", json.dumps(report))
        code, stdout, _ = self.cli("check", "--input", str(self.input), "--previous", str(runs / "run-001"))
        self.assertEqual(code, 2)
        self.assertIn(f"error   Fact {fact_id}: content changed but revision is still 0", stdout)
        missing = a.check(self.input, runs / "absent")
        self.assertIn("predecessor run is unusable (unsafe-path)", missing["errors"][0]["problem"])
        # Another project's run is never a revision baseline: only the wrong-project error remains.
        other = json.loads(json.dumps(self.payload).replace('"project-example"', '"project-other"'))
        self.input.write_text(json.dumps(other))
        self.assertEqual(a.check(self.input, runs / "run-001")["errors"],
                         [{"at": "--previous", "problem": "predecessor belongs to another project or synthetic class"}])

    def test_one_check_lists_every_stale_pin_and_the_revision_cascade(self):
        from eu_compliance_guard import revalidation as r
        runs = self.root / "runs"
        runs.mkdir(mode=0o700)
        self.input.write_text(json.dumps(self.payload))
        r.run(self.input, runs / "run-001")
        payload = deepcopy(self.payload)
        payload["scope"]["roles"][0]["value"] = "changed fictional role"
        self.input.write_text(json.dumps(payload))
        # Before any revision is raised, the records whose pins must follow are named as well.
        cascade = {
            "DeclaredRequirement requirement-example":
                "Fact fact-declared rises to revision 1; update the pin to it and raise this record's revision to 1",
            "DeclaredRequirement requirement-unmapped":
                "Fact fact-declared rises to revision 1; update the pin to it and raise this record's revision to 1",
            "ApplicabilityDecision decision-example": "Scope scope-example rises to revision 1 (and 1 more pinned "
                                                      "record); update the pins to them and raise this record's revision to 1",
        }
        report = a.check(self.input, runs / "run-001")
        located = {item["at"]: item["problem"] for item in report["errors"]}
        self.assertEqual(set(located), {"Scope scope-example", "Fact fact-declared", *cascade})
        self.assertEqual({at: located[at] for at in cascade}, cascade)
        # Raising only the edited records leaves four stale pins: all of them are listed together.
        payload["scope"]["revision"] = payload["scope"]["roles"][0]["revision"] = 1
        self.input.write_text(json.dumps(payload))
        stale = ["requirements[0].fact_refs[0]", "requirements[1].fact_refs[0]",
                 "applicability_decisions[0].fact_refs[0]", "applicability_decisions[0].scope"]
        report = a.check(self.input)
        self.assertEqual(sorted(item["at"] for item in report["errors"]), sorted(stale))
        self.assertEqual(report["total_errors"], 4)
        self.assertIn("declarations: invalid (4 problem(s))", a.format_check(report))
        report = a.check(self.input, runs / "run-001")
        self.assertEqual({item["at"] for item in report["errors"]}, {*stale, *cascade})
        # Following that one report is enough for a valid declaration and a successor run.
        for requirement in payload["requirements"]:
            requirement["revision"] = requirement["fact_refs"][0]["revision"] = 1
        decision = payload["applicability_decisions"][0]
        decision["revision"] = decision["scope"]["revision"] = decision["fact_refs"][0]["revision"] = 1
        self.input.write_text(json.dumps(payload))
        self.assertEqual(a.check(self.input, runs / "run-001")["errors"], [])
        r.run(self.input, runs / "run-002", previous=runs / "run-001")
        # The cascade is transitive: a source pinned by obligations reaches every record pinning those.
        payload = deepcopy(self.payload)
        payload["sources"][0]["source"]["provisions"].append("Fictional section 9")
        self.input.write_text(json.dumps(payload))
        located = {item["at"]: item["problem"] for item in a.check(self.input, runs / "run-001")["errors"]}
        self.assertEqual(set(located), {"LegalSource source-example", "Obligation obligation-example",
                                        "Obligation obligation-unmapped", "DeclaredRequirement requirement-example",
                                        "ApplicabilityDecision decision-example", "EvidenceReview review-example",
                                        "source_reviews[0]"})
        self.assertEqual(located["source_reviews[0]"], "LegalSource source-example rises to revision 1; update the pin to it")

    def test_check_and_revalidate_agree_at_the_declared_limits(self):
        from eu_compliance_guard import revalidation as r
        payload = deepcopy(self.payload)
        obligation, requirement = payload["obligations"][0], payload["requirements"][0]
        payload.update(obligations=[], requirements=[], applicability_decisions=[], evidence_reviews=[])
        for index in range(200):
            payload["obligations"].append({**deepcopy(obligation), "id": f"obligation-{index}",
                                           "required_methods": ["document", "technical", "organizational"]})
            payload["requirements"].append({**deepcopy(requirement), "id": f"requirement-{index}",
                                             "obligation_refs": [{"id": f"obligation-{index}", "revision": 0}]})
        self.input.write_text(json.dumps(payload))
        self.assertTrue(a.check(self.input)["valid"])
        runs = self.root / "runs"
        runs.mkdir(mode=0o700)
        # Over a thousand gaps: the run record holds every gap its bundle allows.
        self.assertGreater(len(r.run(self.input, runs / "run-001").run.gaps), 1000)
        self.assertTrue(a.check(self.input, runs / "run-001")["valid"])
        r.run(self.input, runs / "run-002", previous=runs / "run-001")

    def test_check_reports_a_run_beyond_the_output_limits_before_revalidate(self):
        from unittest.mock import patch
        from eu_compliance_guard import history, revalidation as r
        expected = [{"at": "(document)", "problem": a.RUN_CAPACITY}]
        runs = self.root / "runs"
        runs.mkdir(mode=0o700)
        self.input.write_text(json.dumps(self.payload))
        r.run(self.input, runs / "run-001")
        # A comparison with the predecessor is assembled as revalidate --previous assembles it.
        with patch.object(history, "compare", side_effect=r.RevalidationError("capacity-exceeded")):
            self.assertEqual(a.check(self.input, runs / "run-001")["errors"], expected)
        # Each requirement repeats the review and evidence identifiers of one obligation's 200 methods.
        payload = deepcopy(self.payload)
        payload["obligations"] = payload["obligations"][:1]
        payload["obligations"][0]["required_methods"] = [f"method-{index}" for index in range(200)]
        evidence = payload["evidence"][0]
        payload["evidence"] += [{"evidence": {**evidence["evidence"], "id": f"evidence-{index}"}} for index in range(199)]
        review = payload["evidence_reviews"][0]
        payload["evidence_reviews"] = [{**review, "id": f"review-{index}", "method": f"method-{index}",
                                        "evidence_ids": [payload["evidence"][index]["evidence"]["id"]]} for index in range(200)]
        payload["requirements"] = [{**payload["requirements"][0], "id": f"requirement-{index}"} for index in range(200)]
        self.input.write_text(json.dumps(payload))
        code, stdout, stderr = self.cli("check", "--input", str(self.input), "--json")
        self.assertEqual((code, stderr, json.loads(stdout)["errors"]), (2, "", expected))
        with self.assertRaises(r.RevalidationError) as caught:
            r.run(self.input, runs / "over")
        self.assertEqual(caught.exception.code, "capacity-exceeded")

    def test_state_dir_is_private_keyed_by_project_id_and_symlink_free(self):
        from unittest.mock import patch as env_patch
        project = self.root / "app"
        self.cli("init", "--project-id", "client-a", "--path", str(project / ".eu-compliance-guard/declarations.json"))
        real = self.root / "real-state"
        real.mkdir()
        (self.root / "linked-state").symlink_to(real, target_is_directory=True)
        with env_patch.dict("os.environ", {"XDG_STATE_HOME": str(self.root / "linked-state")}):
            code, stdout, _ = self.cli("state-dir", "--input", str(project / ".eu-compliance-guard/declarations.json"))
        expected = real.resolve() / "eu-compliance-guard/client-a"
        self.assertEqual((code, stdout.strip()), (0, str(expected)))
        self.assertEqual([oct(path.stat().st_mode & 0o777) for path in (expected.parent, expected)], ["0o700", "0o700"])
        expected.chmod(0o750)
        with env_patch.dict("os.environ", {"XDG_STATE_HOME": str(real)}):
            self.assertEqual(a.state_dir(project / ".eu-compliance-guard/declarations.json"), expected)
        self.assertEqual(expected.stat().st_mode & 0o777, 0o750)
        (project / ".eu-compliance-guard/declarations.json").write_text('{"project_id": "../escape"}')
        code, _, stderr = self.cli("state-dir", "--input", str(project / ".eu-compliance-guard/declarations.json"))
        self.assertEqual(code, 2)
        self.assertIn("invalid-input", stderr)

    def test_a_missing_declarations_file_is_not_reported_as_an_unsafe_path(self):
        (self.root / "empty/.eu-compliance-guard").mkdir(parents=True)
        for path in (self.root / "empty/.eu-compliance-guard/declarations.json", self.root / "absent/declarations.json"):
            for command in ("state-dir", "next", "ground"):
                with self.subTest(command=command, path=path):
                    code, stdout, stderr = self.cli(command, "--input", str(path))
                    self.assertEqual((code, stdout), (2, ""))
                    self.assertIn("eu-compliance-guard: io-failed:", stderr)
        (self.root / "linked.json").symlink_to(self.input)
        self.input.write_text(json.dumps(self.payload))
        self.assertIn("unsafe-path", self.cli("state-dir", "--input", str(self.root / "linked.json"))[2])
        # A link to nothing is still a link, not missing declarations.
        (self.root / "dangling.json").symlink_to(self.root / "nowhere.json")
        for command in ("state-dir", "next", "ground"):
            with self.subTest(command=command, path="dangling.json"):
                self.assertIn("unsafe-path", self.cli(command, "--input", str(self.root / "dangling.json"))[2])

    def test_a_relative_xdg_state_home_is_ignored_so_the_state_dir_never_depends_on_the_cwd(self):
        import os
        from unittest.mock import patch as env_patch
        project = self.root / "app"
        declarations = project / ".eu-compliance-guard/declarations.json"
        self.cli("init", "--project-id", "client-a", "--path", str(declarations))
        home = self.root / "home"
        previous = os.getcwd()
        self.addCleanup(os.chdir, previous)
        seen = set()
        for name in ("one", "two"):
            (self.root / name).mkdir()
            os.chdir(self.root / name)
            # The XDG Base Directory spec: a relative path in these variables is invalid and ignored.
            for value in ("relstate", "./relstate", ""):
                with env_patch.dict("os.environ", {"HOME": str(home), "XDG_STATE_HOME": value}):
                    seen.add(a.state_dir(declarations))
            self.assertFalse((self.root / name / "relstate").exists())
        self.assertEqual(seen, {Path(os.path.realpath(home)) / ".local/state/eu-compliance-guard/client-a"})

    def test_no_declared_string_value_ever_reaches_check_output(self):
        marker = "LEAK-MARKER-\x1b[2J"

        def leaves(node, path=()):
            if isinstance(node, dict):
                for key, value in node.items():
                    yield from leaves(value, (*path, key))
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    yield from leaves(value, (*path, index))
            elif isinstance(node, str):
                yield path

        for path in list(leaves(self.payload)):
            payload = deepcopy(self.payload)
            parent = payload
            for key in path[:-1]:
                parent = parent[key]
            parent[path[-1]] = marker
            with self.subTest(path=path):
                text = a.format_check(self.check(payload))
                self.assertNotIn("LEAK-MARKER", text)
                self.assertNotIn("\x1b", text)
        payload = deepcopy(self.payload)
        payload["scope"]["\x1b[2J" + SECRET] = 1
        text = a.format_check(self.check(payload))
        self.assertIn("scope.(unknown field)", text)
        self.assertNotIn(SECRET, text)
        self.assertNotIn("\x1b", text)

    def test_identifier_shaped_unknown_keys_are_never_printed(self):
        payload = deepcopy(self.payload)
        payload["scope"]["ghp_FAKE0000TOKEN1111"] = "x"
        payload["SECRETKEY_zzz"] = 1
        payload["requirements"][0]["value"] = 1  # A field name of another record is still unknown here.
        report = self.check(payload)
        self.assertEqual(sorted(item["at"] for item in report["errors"]),
                         ["(unknown field)", "requirements[0].(unknown field)", "scope.(unknown field)"])
        text = a.format_check(report)
        for key in ("ghp_FAKE0000TOKEN1111", "SECRETKEY_zzz", "value"):
            self.assertNotIn(key, text)
        payload = deepcopy(self.payload)
        payload["scope"]["roles"][0]["value"] = {"ghp_FAKE0000TOKEN1111": "x" * 70000}
        self.assertEqual([item["at"] for item in self.check(payload)["errors"]], ["scope.roles[0].value"])

    def test_fixed_vocabulary_keys_are_printed_and_free_form_keys_are_not(self):
        for topic in ("identity", "classification", "amendments_repeal", "case_law", "national_overlays",
                      "translation", "application_transition_dates"):
            with self.subTest(topic=topic):
                payload = deepcopy(self.payload)
                payload["source_reviews"][0]["review_notes"] = {topic: [1, 2]}
                self.assertEqual([item["at"] for item in self.check(payload)["errors"]],
                                 [f"source_reviews[0].review_notes.{topic}"])
        payload = deepcopy(self.payload)
        payload["source_reviews"][0]["review_notes"] = {"ghp_FAKE0000TOKEN1111": "x"}
        report = self.check(payload)
        self.assertTrue(report["errors"])
        self.assertNotIn("ghp_FAKE0000TOKEN1111", a.format_check(report))
        # A vocabulary word is still hidden where the dict takes free-form keys.
        payload = deepcopy(self.payload)
        payload["evidence"][0]["evidence"]["browser_context"] = {"case_law": [1, 2]}
        self.assertEqual([item["at"] for item in self.check(payload)["errors"]],
                         ["evidence[0].evidence.browser_context.(unknown field)"])


if __name__ == "__main__":
    unittest.main()
