"""Draft starter packs: built from the official texts, unreviewed, importable without decisions."""
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from eu_compliance_guard import models as m, packs
from eu_compliance_guard.__main__ import main
from eu_compliance_guard.notice import LEGAL_NOTICE

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/revalidation-synthetic.json"


def builder():
    spec = importlib.util.spec_from_file_location("build_starter_packs", ROOT / "scripts/build_starter_packs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cli(*args):
    stdout = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
        code = main([str(arg) for arg in args])
    return code, stdout.getvalue()


class StarterPackTests(unittest.TestCase):
    def test_shipped_packs_match_a_fresh_build_from_the_official_texts(self):
        build = builder()
        shipped = sorted(path.name for path in packs.STARTERS.glob("*.pack.json"))
        self.assertEqual(shipped, sorted(f"eu-{name}.pack.json" for name in build.PACKS))
        for name in build.PACKS:
            self.assertEqual((packs.STARTERS / f"eu-{name}.pack.json").read_bytes(), packs.to_bytes(build.build(name)), name)

    def test_every_pack_is_a_labelled_draft_pinning_real_articles(self):
        for item in packs.starters():
            pack, _ = packs.load(item["path"])
            self.assertEqual(pack.status, "draft")
            self.assertIn(LEGAL_NOTICE, pack.limitations)
            self.assertTrue(any("reviewed by no one" in text for text in pack.limitations))
            locked = {article.key for entry in pack.law for article in entry.articles}
            for obligation in pack.obligations:
                self.assertTrue(obligation.limitations and obligation.conditions, obligation.id)
                for pin in obligation.source_provisions:
                    from eu_compliance_guard.articles import article_key
                    self.assertIn(article_key(pin.locator), locked, (obligation.id, pin.locator))

    def test_all_packs_import_together_without_any_decision(self):
        with tempfile.TemporaryDirectory(prefix="eucg-starter-") as folder:
            target = Path(folder) / "declarations.json"
            shutil.copy(FIXTURE, target)
            before = json.loads(target.read_text())
            for item in packs.starters():
                code, out = cli("pack", "import", item["path"], "--input", target, "--unsigned")
                self.assertEqual(code, 0, out)
                self.assertIn("UNSIGNED", out)
            after = json.loads(target.read_text())
            m.parse_record(m.RevalidationInput, target.read_bytes())
            self.assertEqual(len(after["obligations"]) - len(before["obligations"]), sum(i["obligations"] for i in packs.starters()))
            self.assertEqual(after["applicability_decisions"], before["applicability_decisions"])
            self.assertEqual([r["obligation_refs"] for r in after["requirements"]], [r["obligation_refs"] for r in before["requirements"]])
        code, out = cli("pack", "starters")
        self.assertEqual(code, 0)
        self.assertIn("pack-eu-gdpr-core", out)
        self.assertIn("reviewed by no one", out)


if __name__ == "__main__":
    unittest.main()
