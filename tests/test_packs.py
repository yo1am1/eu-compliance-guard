"""Obligation packs: built from declarations, SSH-signed, verified and imported without decisions."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from eu_compliance_guard import models as m, packs
from eu_compliance_guard.__main__ import main

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/revalidation-synthetic.json"


def cli(*args):
    stdout = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
        code = main([str(arg) for arg in args])
    return code, stdout.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="eucg-pack-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "source").mkdir()
        (self.root / "target").mkdir()
        self.source = self.root / "source/declarations.json"
        shutil.copy(FIXTURE, self.source)
        self.pack = self.root / "fictional.pack.json"
        data = json.loads(FIXTURE.read_text())
        # The importing project has the same project shape but none of the obligations or targets.
        for key in ("obligations", "source_targets", "sources", "source_reviews", "applicability_decisions",
                    "evidence_reviews", "family_screenings", "evidence"):
            data[key] = []
        for requirement in data["requirements"]:
            requirement["obligation_refs"], requirement["evidence_ids"] = [], []
        self.target = self.root / "target/declarations.json"
        self.target_raw = json.dumps(data, indent=2)
        self.target.write_text(self.target_raw)


class PackTests(Base):
    def test_build_is_deterministic_and_closed(self):
        self.assertEqual(cli("pack", "build", "--input", self.source, "--id", "pack-fictional", "--title", "Fictional",
                             "--output", self.pack)[0], 0)
        first = self.pack.read_bytes()
        pack = m.parse_record(m.ObligationPack, first)
        self.assertEqual([item.id for item in pack.obligations], ["obligation-example", "obligation-unmapped"])
        self.assertEqual([item.id for item in pack.source_targets], ["target-example"])
        self.assertIn("Not legal advice", " ".join(pack.limitations))
        self.assertEqual(packs.to_bytes(packs.build(self.source, "pack-fictional", "Fictional")), first)
        # The project a pack came from already has its obligations: importing it there changes nothing.
        before = self.source.read_bytes()
        result = packs.import_pack(self.source, self.pack, None, unsigned=True)
        self.assertEqual(result["added"], {"source_targets": [], "obligations": []})
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(cli("pack", "build", "--input", self.source, "--id", "p", "--title", "t",
                             "--obligation", "missing", "--output", self.root / "x.json")[0], 2)

    def test_import_adds_obligations_only_and_refuses_conflicts_and_unsigned_packs(self):
        self.assertEqual(cli("pack", "build", "--input", self.source, "--id", "pack-fictional", "--title", "Fictional",
                             "--output", self.pack)[0], 0)
        with self.assertRaises(SystemExit):  # --allowed-signers or --unsigned is required
            cli("pack", "import", self.pack, "--input", self.target)
        self.assertEqual(self.target.read_text(), self.target_raw)
        code, out = cli("pack", "import", self.pack, "--input", self.target, "--unsigned")
        self.assertEqual(code, 0, out)
        self.assertIn("UNSIGNED", out)
        declared = json.loads(self.target.read_text())
        self.assertEqual(len(declared["obligations"]), 2)
        self.assertEqual(declared["applicability_decisions"], [])
        self.assertTrue(all(not item["obligation_refs"] for item in declared["requirements"]))
        again = self.target.read_bytes()
        self.assertEqual(cli("pack", "import", self.pack, "--input", self.target, "--unsigned")[0], 0)
        self.assertEqual(self.target.read_bytes(), again)  # importing twice changes nothing
        changed = json.loads(self.pack.read_text())
        changed["obligations"][0]["conditions"] = ["A different fictional condition."]
        self.pack.write_text(json.dumps(changed))
        self.assertEqual(cli("pack", "import", self.pack, "--input", self.target, "--unsigned")[0], 2)
        self.assertEqual(self.target.read_bytes(), again)


@unittest.skipUnless(shutil.which("ssh-keygen"), "ssh-keygen is required")
class SignedPackTests(Base):
    def test_signed_pack_verifies_and_a_changed_pack_does_not(self):
        key = self.root / "key"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "fictional", "-f", str(key)], check=True)
        allowed = self.root / "allowed_signers"
        allowed.write_text("reviewer@example.invalid " + (self.root / "key.pub").read_text())
        self.assertEqual(cli("pack", "build", "--input", self.source, "--id", "pack-fictional", "--title", "Fictional",
                             "--status", "reviewed", "--output", self.pack)[0], 0)
        self.assertEqual(cli("pack", "verify", self.pack, "--allowed-signers", allowed)[0], 1)  # not signed yet
        self.assertEqual(cli("pack", "sign", self.pack, "--key", key, "--principal", "reviewer@example.invalid")[0], 0)
        code, out = cli("pack", "verify", self.pack, "--allowed-signers", allowed)
        self.assertEqual(code, 0, out)
        self.assertIn("signed by reviewer@example.invalid", out)
        code, out = cli("pack", "import", self.pack, "--input", self.target, "--allowed-signers", allowed)
        self.assertEqual(code, 0, out)
        self.assertIn("signed by reviewer@example.invalid", out)
        self.pack.write_bytes(self.pack.read_bytes().replace(b"Fictional", b"Altered"))
        self.assertEqual(cli("pack", "verify", self.pack, "--allowed-signers", allowed)[0], 1)
        self.target.write_text(self.target_raw)
        self.assertEqual(cli("pack", "import", self.pack, "--input", self.target, "--allowed-signers", allowed)[0], 2)
        self.assertEqual(self.target.read_text(), self.target_raw)


if __name__ == "__main__":
    unittest.main()
