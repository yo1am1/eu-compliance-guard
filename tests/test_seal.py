"""The run log: a sealed run that changes, or a rewritten log, is detected."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from eu_compliance_guard import models as m, revalidation as r, seal
from eu_compliance_guard.__main__ import main

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/revalidation-synthetic.json"


def cli(*args):
    out = io.StringIO()
    with redirect_stdout(out), redirect_stderr(io.StringIO()):
        code = main([str(arg) for arg in args])
    return code, out.getvalue()


class SealTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="eucg-seal-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)
        shutil.copytree(FIXTURE.parent / "revalidation-synthetic", self.root / "revalidation-synthetic")
        self.input = self.root / "declarations.json"
        self.input.write_bytes(FIXTURE.read_bytes())
        self.state = self.root / "state/eu-compliance-guard/project-example"
        self.state.mkdir(parents=True, mode=0o700)
        patcher = mock.patch.dict(os.environ, {"XDG_STATE_HOME": str(self.root / "state")})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.log = self.root / "runs.log"

    def run_named(self, name: str) -> Path:
        r.run(self.input, self.state / name)
        return self.state / name

    def test_sealed_runs_form_a_chain_and_sealing_again_changes_nothing(self):
        self.run_named("run-1")
        code, out = cli("seal", "--input", self.input)
        self.assertEqual(code, 0, out)
        self.assertIn("sealed as entry 1", out)
        first = self.log.read_bytes()
        self.assertEqual(cli("seal", "--input", self.input)[1].count("was already sealed"), 1)
        self.assertEqual(self.log.read_bytes(), first)
        second = self.run_named("run-2")
        self.assertEqual(cli("seal", "--input", self.input, "--run", second)[0], 0)
        entries = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual([entry["seq"] for entry in entries], [1, 2])
        self.assertEqual(entries[1]["previous"], m.content_digest(self.log.read_bytes().splitlines()[0]))
        code, out = cli("seal", "--check", "--input", self.input)
        self.assertEqual(code, 0, out)
        self.assertEqual(out.count("run intact"), 2)
        self.assertIn("commit runs.log to Git", out)

    def test_a_report_rewritten_with_new_checksums_is_detected(self):
        run = self.run_named("run-1")
        self.assertEqual(cli("seal", "--input", self.input)[0], 0)
        shutil.copytree(run, self.root / "copy")
        # What the run's own checksums cannot catch: rewrite the report, then recompute the marker.
        report = run / "report.md"
        os.chmod(report, 0o600)
        report.write_text(report.read_text() + "\nCOMPLIANT\n")
        marker = json.loads((run / "complete.json").read_text())
        for item in marker["files"]:
            if item["path"] == "report.md":
                item["digest"] = m.content_digest(report.read_bytes())
        os.chmod(run / "complete.json", 0o600)
        (run / "complete.json").write_text(json.dumps(marker))
        from eu_compliance_guard.view import verify_run
        verify_run(run)  # the run still verifies against its own, recomputed checksums
        code, out = cli("seal", "--check", "--input", self.input, "--json")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["entries"][0]["run"], "changed")
        self.assertEqual(cli("seal", "--input", self.input)[0], 2)  # and it cannot be sealed again under the same id
        # An untouched copy of the run in another folder does not hide the change.
        shutil.move(self.root / "copy", self.state / "run-9")
        code, out = cli("seal", "--check", "--input", self.input, "--json")
        self.assertEqual((code, json.loads(out)["entries"][0]["run"]), (1, "changed"))
        shutil.rmtree(run)
        code, out = cli("seal", "--check", "--input", self.input, "--json")
        self.assertEqual((code, json.loads(out)["entries"][0]["run"]), (0, "intact"))

    def test_a_rewritten_or_reordered_log_breaks_the_chain(self):
        self.run_named("run-1")
        self.run_named("run-2")
        for name in ("run-1", "run-2"):
            self.assertEqual(cli("seal", "--input", self.input, "--run", self.state / name)[0], 0)
        lines = self.log.read_text().splitlines()
        edited = json.loads(lines[0])
        edited["marker"] = "sha256:" + "0" * 64
        self.log.write_text(json.dumps(edited, sort_keys=True) + "\n" + lines[1] + "\n")
        report = seal.check(self.input, self.state)
        self.assertEqual([item["chain"] for item in report["entries"]], [True, False])
        self.assertFalse(report["ok"])
        self.log.write_text(lines[1] + "\n")  # the first entry dropped
        self.assertFalse(seal.check(self.input, self.state)["ok"])
        self.log.write_text("not json\n")
        self.assertEqual(cli("seal", "--check", "--input", self.input)[0], 2)

    def test_runs_that_are_absent_or_unsealed_are_named_not_failed(self):
        run = self.run_named("run-1")
        self.assertEqual(cli("seal", "--input", self.input)[0], 0)
        self.run_named("run-2")
        shutil.rmtree(run)
        code, out = cli("seal", "--check", "--input", self.input)
        self.assertEqual(code, 0, out)
        self.assertIn("run not on this machine (not compared)", out)
        self.assertIn("Not sealed: ", out)
        self.assertEqual(cli("seal", "--check", "--input", self.root / "missing.json")[0], 2)

    def test_only_this_projects_intact_runs_are_sealed(self):
        self.assertEqual(cli("seal", "--input", self.input)[0], 2)  # no run yet
        self.run_named("run-1")
        other = self.root / "other/declarations.json"
        other.parent.mkdir()
        other.write_text(FIXTURE.read_text().replace("project-example", "project-other"))
        with self.assertRaises(seal.SealError) as raised:
            seal.seal(other, self.state / "run-1")
        self.assertEqual(raised.exception.code, "wrong-project")

    @unittest.skipUnless(shutil.which("ssh-keygen"), "ssh-keygen is required")
    def test_a_signed_entry_verifies_only_for_its_signer(self):
        key = self.root / "key"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "fictional", "-f", str(key)], check=True)
        allowed = self.root / "allowed"
        allowed.write_text("reviewer@example.invalid " + (self.root / "key.pub").read_text())
        self.run_named("run-1")
        self.assertEqual(cli("seal", "--input", self.input, "--key", key, "--principal", "reviewer@example.invalid")[0], 0)
        unverified = cli("seal", "--check", "--input", self.input)[1]
        self.assertIn("signed (not verified: give --allowed-signers)", unverified)
        self.assertNotIn("reviewer@example.invalid", unverified)  # a name nobody verified is not shown as the signer
        code, out = cli("seal", "--check", "--input", self.input, "--allowed-signers", allowed)
        self.assertEqual(code, 0, out)
        self.assertIn("signature of reviewer@example.invalid valid", out)
        stranger = self.root / "stranger"
        stranger.write_text("someone@example.invalid " + (self.root / "key.pub").read_text())
        code, out = cli("seal", "--check", "--input", self.input, "--allowed-signers", stranger)
        self.assertEqual(code, 1)
        self.assertIn("signature INVALID", out)
        self.assertEqual(cli("seal", "--input", self.input, "--key", key)[0], 0)  # already sealed: nothing to sign
        self.run_named("run-2")
        self.assertEqual(cli("seal", "--input", self.input, "--key", key)[0], 2)  # a key needs a principal
        # An entry without a signature is named when signatures are checked, and only then.
        self.assertEqual(cli("seal", "--input", self.input)[0], 0)
        code, out = cli("seal", "--check", "--input", self.input, "--allowed-signers", allowed)
        self.assertEqual((code, out.count("; NOT signed")), (0, 1))
        self.assertNotIn("NOT signed", cli("seal", "--check", "--input", self.input)[1])


if __name__ == "__main__":
    unittest.main()
