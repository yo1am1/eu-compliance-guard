"""CLI adapter tests and package-only synthetic subprocess checks."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

from eu_compliance_guard import models as m
from eu_compliance_guard.__main__ import main
from test_revalidation_models import FIXTURE, FIXTURE_PATH, bundle_payload

ROOT = Path(__file__).resolve().parents[1]


class RevalidationCliTests(unittest.TestCase):
    def call_main(self, args, run):
        module = ModuleType("eu_compliance_guard.revalidation")
        module.run = run
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.dict(sys.modules, {module.__name__: module}), redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(args)
        return result, stdout.getvalue(), stderr.getvalue()

    def test_default_and_offline_delegate_exact_paths_without_business_logic(self):
        for suffix in ([], ["--offline"]):
            run = Mock(return_value=m.RevalidationBundle.model_validate(bundle_payload()))
            code, stdout, stderr = self.call_main(
                ["revalidate", "--input", "declarations.json", "--output", "new-run", *suffix], run)
            self.assertEqual(code, 0)
            run.assert_called_once_with("declarations.json", "new-run")
            self.assertIn("not a compliance verdict", stdout)
            self.assertIn("Run run-output: processing state partial", stdout)
            self.assertIn("report.md and bundle.json", stdout)
            self.assertEqual(stderr, "")

    def test_fetch_official_delegates_only_when_explicit(self):
        run = Mock(return_value=m.RevalidationBundle.model_validate(bundle_payload()))
        code, stdout, stderr = self.call_main(
            ["revalidate", "--input", "declarations.json", "--output", "new-run", "--fetch-official"], run)
        self.assertEqual((code, stderr), (0, ""))
        run.assert_called_once_with("declarations.json", "new-run", fetch_official=True)
        self.assertIn("not a compliance verdict", stdout)

    def test_future_and_conflicting_arguments_reject_before_workflow_import_or_any_input_reads(self):
        for future in (["--offline", "--fetch-official"], ["--fetch-official", "--offline"], ["--fetch-official=true"],
                       ["--previous"]):
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch("builtins.open", side_effect=AssertionError("must reject before reads")), \
                    patch("pathlib.Path.read_bytes", side_effect=AssertionError("must reject before reads")), \
                    patch.dict(sys.modules, {"eu_compliance_guard.revalidation": None}), \
                    redirect_stdout(stdout), redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as caught:
                    main(["revalidate", "--input", "PRIVATE-SECRET", "--output", "PRIVATE-SECRET", *future])
            self.assertEqual(caught.exception.code, 2)
            self.assertNotIn("PRIVATE-SECRET", stderr.getvalue())
            self.assertEqual(stdout.getvalue(), "")

    def test_previous_delegates_explicit_path(self):
        run = Mock(return_value=m.RevalidationBundle.model_validate(bundle_payload()))
        code, _, stderr = self.call_main(
            ["revalidate", "--input", "in", "--output", "out", "--previous", "prior", "--fetch-official"], run)
        self.assertEqual((code, stderr), (0, ""))
        run.assert_called_once_with("in", "out", fetch_official=True, previous="prior")

    def test_parse_errors_do_not_echo_untrusted_arguments(self):
        for arguments in (["PRIVATE-SECRET"], ["revalidate", "--input", "PRIVATE-SECRET"],
                          ["revalidate", "--input", "in", "--output", "out", "PRIVATE-SECRET"]):
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr), self.assertRaises(SystemExit) as caught:
                main(arguments)
            self.assertEqual(caught.exception.code, 2)
            self.assertIn("invalid-arguments", stderr.getvalue())
            self.assertNotIn("PRIVATE-SECRET", stderr.getvalue())

    def test_errors_and_interrupt_are_safe_and_have_defined_exit_codes(self):
        class WorkflowError(ValueError):
            def __init__(self, code):
                self.code = code
                super().__init__("PRIVATE-SECRET raw evidence /private/path?token=PRIVATE-SECRET")

        for failure, expected_code, expected_text in (
            (WorkflowError("invalid-input"), 2, "invalid-input"),
            (WorkflowError("PRIVATE-SECRET"), 2, "revalidation-failed"),
            (OSError("PRIVATE-SECRET"), 2, "revalidation-failed"),
            (ValueError("PRIVATE-SECRET"), 2, "revalidation-failed"),
            (RuntimeError("PRIVATE-SECRET"), 2, "revalidation-failed"),
            (KeyboardInterrupt(), 130, "interrupted"),
        ):
            with self.subTest(failure=type(failure).__name__):
                code, stdout, stderr = self.call_main(
                    ["revalidate", "--input", "PRIVATE-SECRET", "--output", "PRIVATE-SECRET"],
                    Mock(side_effect=failure))
                self.assertEqual(code, expected_code)
                self.assertEqual(stdout, "")
                self.assertIn(expected_text, stderr)
                self.assertNotIn("PRIVATE-SECRET", stderr)
                self.assertNotIn("Traceback", stderr)

    def test_package_help_and_unsupported_argument_subprocess(self):
        for arguments in (["--help"], ["revalidate", "--help"]):
            result = self.package_cli(*arguments)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("revalidate" if len(arguments) == 1 else "--offline", result.stdout)
        self.assertIn("--fetch-official", self.package_cli("revalidate", "--help").stdout)
        result = self.package_cli("revalidate", "--input", "PRIVATE-SECRET", "--output", "PRIVATE-SECRET",
                                  "--offline", "--fetch-official")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid-arguments", result.stderr)
        self.assertNotIn("PRIVATE-SECRET", result.stderr)

    @staticmethod
    def package_cli(*args):
        return subprocess.run([sys.executable, "-m", "eu_compliance_guard", *map(str, args)],
                              cwd=ROOT, capture_output=True, text=True, timeout=30, check=False)

    def test_output_that_cannot_be_written_is_io_failed_not_a_traceback(self):
        class Unwritable(io.StringIO):
            def __init__(self, error):
                super().__init__()
                self.error = error

            def write(self, text):
                raise self.error

        for error in (BrokenPipeError(32, "Broken pipe"), OSError(28, "No space left on device"),
                      UnicodeEncodeError("ascii", "PRIVATE-é", 8, 9, "ordinal not in range(128)")):
            with self.subTest(error=type(error).__name__):
                run = Mock(return_value=m.RevalidationBundle.model_validate(bundle_payload()))
                module = ModuleType("eu_compliance_guard.revalidation")
                module.run = run
                stderr = io.StringIO()
                with patch.dict(sys.modules, {module.__name__: module}), redirect_stdout(Unwritable(error)), \
                        redirect_stderr(stderr):
                    code = main(["revalidate", "--input", "in", "--output", "out"])
                self.assertEqual((code, stderr.getvalue()), (2, "eu-compliance-guard: io-failed: output failed\n"))

    def project_cli(self, project, *args, stdin=b"", stdout=subprocess.PIPE, encoding=None):
        environment = {**os.environ, "PYTHONPATH": str(ROOT)}
        environment.pop("PYTHONIOENCODING", None)
        if encoding:
            environment["PYTHONIOENCODING"] = encoding
        return subprocess.run([sys.executable, "-m", "eu_compliance_guard", *args], cwd=project, env=environment,
                              input=stdin, stdout=stdout, stderr=subprocess.PIPE, timeout=60, check=False)

    def test_a_closed_or_full_stdout_is_io_failed_and_never_the_strict_attention_code(self):
        def closed_pipe():
            reader, writer = os.pipe()
            os.close(reader)
            return os.fdopen(writer, "wb")

        targets = {"closed pipe": closed_pipe}
        if os.path.exists("/dev/full"):
            targets["full device"] = lambda: open("/dev/full", "wb")
        with tempfile.TemporaryDirectory(prefix="eucg-cli-") as project:
            for arguments in (["pr-check", "--strict", "--json"], ["--help"]):
                for name, target in targets.items():
                    with self.subTest(arguments=arguments, target=name), target() as stdout:
                        result = self.project_cli(project, *arguments, stdout=stdout)
                        self.assertEqual(result.returncode, 2)
                        self.assertEqual(result.stderr, b"eu-compliance-guard: io-failed: output failed\n")

    def test_text_the_console_cannot_encode_is_escaped(self):
        from eu_compliance_guard import authoring
        with tempfile.TemporaryDirectory(prefix="eucg-cli-") as folder:
            project = Path(folder) / "shop"
            (project / "légal").mkdir(parents=True)
            (project / "légal/wéb.py").write_text(
                'def landing(response, visitor_id):\n    response.set_cookie("_analytics", visitor_id, max_age=395)\n')
            declarations = authoring.init(project / ".eu-compliance-guard/declarations.json", "shop", synthetic=True)
            data = json.loads(declarations.read_text())
            data["scope"]["roles"] = [{"id": "fact-cookie-lifetime", "revision": 0, "value": None, "basis": "unknown",
                                       "key": "Analytics cookie lifetime (Größe)", "evidence_ids": [],
                                       "owner": "Jürgen Ölmann", "observed_at": "2026-11-04T00:00:00Z",
                                       "conflicts": []}]
            declarations.write_text(json.dumps(data, ensure_ascii=False))
            ground = self.project_cli(project, "ground", encoding="ascii")
            self.assertEqual((ground.returncode, ground.stderr), (0, b""))
            self.assertIn(b"(Gr\\xf6\\xdfe)", ground.stdout)
            applied = self.project_cli(project, "ground", "--apply", "fact-cookie-lifetime=légal/wéb.py:2",
                                       encoding="ascii")
            self.assertEqual((applied.returncode, applied.stderr), (0, b""))
            self.assertIn(b"pinned to l\\xe9gal/w\\xe9b.py:2", applied.stdout)
            self.assertEqual(json.loads(declarations.read_text())["scope"]["roles"][0]["basis"], "observed")
            diff = ("diff --git a/légal/wéb.py b/légal/wéb.py\n--- a/légal/wéb.py\n"
                    "+++ b/légal/wéb.py\n@@ -2,0 +3 @@\n+set_cookie('größe', analytics)\n").encode()
            for style in ([], ["--markdown"]):
                with self.subTest(style=style):
                    result = self.project_cli(project, "pr-check", *style, stdin=diff, encoding="ascii")
                    self.assertEqual((result.returncode, result.stderr), (0, b""))
                    self.assertIn(b"l\\xe9gal/w\\xe9b.py", result.stdout)

    def test_real_private_fixture_runs_no_overwrite_and_evidence_secrecy(self):
        self.assertIsNotNone(importlib.util.find_spec("eu_compliance_guard.revalidation"),
                             "workflow must be ready before integration acceptance")
        secret = b"RAW-EVIDENCE-SECRET-SENTINEL"
        with tempfile.TemporaryDirectory(prefix="eucg-cli-") as parent:
            parent = Path(parent)
            assets = parent / "revalidation-synthetic"
            assets.mkdir()
            (assets / "source.txt").write_bytes((FIXTURE_PATH.parent / FIXTURE["sources"][0]["file"]["path"]).read_bytes())
            (assets / "evidence.txt").write_bytes(secret)
            payload = deepcopy(FIXTURE)
            payload["evidence"][0]["evidence"]["digest"] = m.content_digest(secret)
            declaration = parent / "declarations.json"
            declaration.write_text(json.dumps(payload))
            original_input = declaration.read_bytes()
            first, second = parent / "run-001", parent / "run-002"
            result = self.package_cli("revalidate", "--input", declaration, "--output", first, "--offline")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("processing state partial", result.stdout)
            bundle = m.parse_record(m.RevalidationBundle, (first / "bundle.json").read_bytes())
            self.assertEqual(bundle.run.state, "partial")
            self.assertEqual(len(bundle.family_screenings), 11)
            self.assertEqual({item.requirement.id: item.state for item in bundle.requirement_assessments},
                             {"requirement-example": "supported", "requirement-unmapped": "unresolved"})
            marker = m.parse_record(m.RunCompletion, (first / "complete.json").read_bytes())
            self.assertEqual(marker.run_id, bundle.run.id)
            for file in marker.files:
                self.assertEqual(m.content_digest((first / file.path).read_bytes()), file.digest)
            self.assertEqual(first.stat().st_mode & 0o777, 0o700)
            saved = {path.relative_to(first): path.read_bytes() for path in first.rglob("*") if path.is_file()}
            for path in saved:
                self.assertEqual((first / path).stat().st_mode & 0o777, 0o600)
            self.assertNotIn(secret, (first / "report.md").read_bytes())
            self.assertNotIn(secret.decode(), result.stdout + result.stderr)
            collision = self.package_cli("revalidate", "--input", declaration, "--output", first)
            self.assertEqual(collision.returncode, 2)
            self.assertNotIn(str(parent), collision.stderr)
            another = self.package_cli("revalidate", "--input", declaration, "--output", second)
            self.assertEqual(another.returncode, 0, another.stderr)
            next_bundle = m.parse_record(m.RevalidationBundle, (second / "bundle.json").read_bytes())
            self.assertNotEqual(next_bundle.run.id, bundle.run.id)
            self.assertEqual(saved, {path.relative_to(first): path.read_bytes() for path in first.rglob("*") if path.is_file()})
            self.assertEqual(declaration.read_bytes(), original_input)


if __name__ == "__main__":
    unittest.main()
