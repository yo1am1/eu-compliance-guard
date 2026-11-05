"""Every human-readable output ends with the legal notice; JSON stays machine data."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from eu_compliance_guard.__main__ import main
from eu_compliance_guard.notice import LEGAL_NOTICE

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/revalidation-synthetic.json"
DIFF = "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -0,0 +1 @@\n+set_cookie(email)\n"


class LegalNoticeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="eucg-notice-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)
        shutil.copytree(FIXTURE.parent / "revalidation-synthetic", self.root / "revalidation-synthetic")
        self.input = self.root / "input.json"
        self.input.write_bytes(FIXTURE.read_bytes())
        (self.root / "state").mkdir(mode=0o700)
        self.run = self.root / "state/run-20261105T000000Z"
        (self.root / "change.diff").write_text(DIFF)

    def cli(self, *args) -> str:
        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            main([str(arg) for arg in args])
        return stdout.getvalue()

    def test_text_markdown_and_html_end_with_the_notice(self):
        outputs = {"revalidate": self.cli("revalidate", "--input", self.input, "--output", self.run, "--offline")}
        outputs["check"] = self.cli("check", "--input", self.input)
        outputs["next"] = self.cli("next", "--run", self.run)
        outputs["score"] = self.cli("score", "--run", self.run)
        outputs["ground"] = self.cli("ground", "--input", self.input)
        outputs["pr-check"] = self.cli("pr-check", "--diff", self.root / "change.diff", "--input", self.input)
        outputs["pr-check --markdown"] = self.cli("pr-check", "--diff", self.root / "change.diff", "--input", self.input, "--markdown")
        for name, text in outputs.items():
            self.assertTrue(text.rstrip().endswith(LEGAL_NOTICE), name)
        self.assertIn(LEGAL_NOTICE, (self.run / "report.md").read_text())
        view = Path(self.cli("view", "--run", self.run).strip())
        self.assertIn(LEGAL_NOTICE, view.read_text())
        self.assertIn(LEGAL_NOTICE, view.with_name(self.run.name + ".dashboard.html").read_text())

    def test_json_outputs_stay_parseable(self):
        self.cli("revalidate", "--input", self.input, "--output", self.run, "--offline")
        for args in (("next", "--run", self.run, "--json"), ("score", "--run", self.run, "--json"),
                     ("check", "--input", self.input, "--json")):
            json.loads(self.cli(*args))


if __name__ == "__main__":
    unittest.main()
