"""Law lockfile and change impact: offline, deterministic, from runs' retained official text."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from eu_compliance_guard import lawlock, models as m, revalidation as r
from eu_compliance_guard.__main__ import main

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/revalidation-synthetic.json"
OLD_DIGEST = "sha256:b89f4bb123cc3732e9560553b419757350e5bdab12f0f1f4a8bdc53dfd89f5a0"


def act(article_1: str) -> bytes:
    return ("FICTIONAL SOURCE — SYNTHETIC EXAMPLE ONLY\nArticle 1\nFictional review records\n" + article_1 + "\n"
            "Article 2\nFictional erasure\nThe fictional controller shall erase an account on request.\n").encode()


class LawLockTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="eucg-lock-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)
        (self.root / "revalidation-synthetic").mkdir()
        (self.root / "revalidation-synthetic/evidence.txt").write_bytes((FIXTURE.parent / "revalidation-synthetic/evidence.txt").read_bytes())
        self.input = self.root / "declarations.json"
        (self.root / "state").mkdir(mode=0o700)

    def run_with(self, text: bytes, name: str) -> Path:
        (self.root / "revalidation-synthetic/source.txt").write_bytes(text)
        raw = FIXTURE.read_text().replace("Fictional section 1", "Article 1").replace(OLD_DIGEST, m.content_digest(text))
        self.input.write_text(raw)
        r.run(self.input, self.root / "state" / name)
        return self.root / "state" / name

    def cli(self, *args):
        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            code = main([str(arg) for arg in args])
        return code, stdout.getvalue()

    def test_lock_records_versions_and_article_digests_deterministically(self):
        run = self.run_with(act("The fictional controller shall retain a review record."), "run-1")
        lock = lawlock.build(run)
        self.assertEqual([item.target_id for item in lock.entries], ["target-example"])
        self.assertEqual([item.key for item in lock.entries[0].articles], ["Article 1", "Article 2"])
        self.assertEqual(lawlock.to_bytes(lawlock.build(run)), lawlock.to_bytes(lock))
        code, out = self.cli("lock", "--input", self.input, "--run", run)
        self.assertEqual(code, 0)
        self.assertIn("2 article(s) locked", out)
        path = self.root / "eu-law.lock"
        self.assertEqual(lawlock.read(path), lock)
        self.assertEqual(path.read_bytes(), lawlock.to_bytes(lock))

    def test_impact_lists_changed_articles_and_only_the_records_citing_them(self):
        first = self.run_with(act("The fictional controller shall retain a review record."), "run-1")
        self.assertEqual(self.cli("lock", "--input", self.input, "--run", first)[0], 0)
        same = self.run_with(act("The fictional controller shall retain a review record."), "run-2")
        code, out = self.cli("impact", "--input", self.input, "--run", same, "--strict")
        self.assertEqual(code, 0)
        self.assertIn("No locked article changed", out)
        changed = self.run_with(act("The fictional controller shall retain a review record for five years."), "run-3")
        code, out = self.cli("impact", "--input", self.input, "--run", changed, "--json", "--strict")
        self.assertEqual(code, 1)
        report = json.loads(out)
        self.assertEqual(report["changes"], [{"target": "target-example", "version_before": None, "version_after": None,
                                              "changed": ["Article 1"], "added": [], "removed": []}])
        self.assertEqual([item["obligation"] for item in report["obligations"]], ["obligation-example", "obligation-unmapped"])
        self.assertIn("requirement-example", report["requirements_to_review"])
        self.assertTrue(report["decisions_to_review"])
        text = lawlock.format_impact(report)
        self.assertIn("changed Article 1", text)
        self.assertIn("Nothing was reopened or decided", text)

    def test_a_missing_lock_or_a_linked_lockfile_fails_safely(self):
        run = self.run_with(act("Text."), "run-1")
        code, _ = self.cli("impact", "--input", self.input, "--run", run)
        self.assertEqual(code, 2)
        target = self.root / "elsewhere.lock"
        target.write_text("keep")
        (self.root / "eu-law.lock").symlink_to(target)
        code, _ = self.cli("lock", "--input", self.input, "--run", run)
        self.assertEqual(code, 2)
        self.assertEqual(target.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
