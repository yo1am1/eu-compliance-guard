"""files.write_bytes: a replaced project file keeps the privacy its owner gave it."""
import os
from pathlib import Path
import tempfile
import unittest

from eu_compliance_guard import files


class WriteBytesTests(unittest.TestCase):
    def test_a_replaced_file_never_gains_permission_bits(self):
        with tempfile.TemporaryDirectory(prefix="eucg-files-") as folder:
            previous = os.umask(0o022)
            self.addCleanup(os.umask, previous)
            path = Path(folder) / "ropa.md"
            files.write_bytes(path, b"first")
            self.assertEqual(path.stat().st_mode & 0o777, 0o644)
            path.chmod(0o600)  # the owner makes an export private, then exports again
            files.write_bytes(path, b"second")
            self.assertEqual((path.read_bytes(), path.stat().st_mode & 0o777), (b"second", 0o600))
            path.chmod(0o666)
            files.write_bytes(path, b"third", mode=0o600)  # and a private kind of file is never widened either
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(os.listdir(folder), ["ropa.md"])


if __name__ == "__main__":
    unittest.main()
