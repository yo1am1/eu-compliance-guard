"""HTML run view checks on synthetic runs; nothing is opened or fetched."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from eu_compliance_guard import models as m, revalidation as r, view as v
from eu_compliance_guard.__main__ import main

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/revalidation-synthetic.json"


class RunViewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="eucg-view-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)
        (self.root / "revalidation-synthetic").mkdir()
        for name in ("source.txt", "evidence.txt"):
            (self.root / "revalidation-synthetic" / name).write_bytes((FIXTURE.parent / "revalidation-synthetic" / name).read_bytes())
        payload = json.loads(FIXTURE.read_bytes())
        payload["requirements"][1]["statement"] = "<script>alert(1)</script> & <img src=x onerror=y>"
        self.input = self.root / "input.json"
        self.input.write_text(json.dumps(payload))
        self.runs = self.root / "state"
        self.runs.mkdir(mode=0o700)
        self.run = self.runs / "run-20261025T000000Z"
        self.bundle = r.run(self.input, self.run)

    def snapshot(self):
        return {path.relative_to(self.run): path.read_bytes() for path in self.run.rglob("*") if path.is_file()}

    def test_view_is_private_escaped_static_and_outside_the_run(self):
        before = self.snapshot()
        path = v.write_view(self.run)
        self.assertEqual(path, self.runs / "views" / "run-20261025T000000Z.html")
        self.assertEqual((path.stat().st_mode & 0o777, path.parent.stat().st_mode & 0o777), (0o600, 0o700))
        self.assertEqual(self.snapshot(), before)
        html = path.read_text()
        self.assertIn(self.bundle.run.id, html)
        self.assertIn("FICTIONAL / SYNTHETIC DATA", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt; &amp; &lt;img src=x", html)
        self.assertNotRegex(html, r"(?i)<script|<img|<link|<iframe|https?://")
        self.assertIn("default-src 'none'", html)
        self.assertIn("no compliance verdict", html)
        for family in m.LEGAL_FAMILIES:
            self.assertIn(f"<td>{family}</td>", html)
        self.assertEqual(len(re.findall(r'<span class="tag [a-z]*">family</span>', html)), 11)
        v.write_view(self.run)  # A later view replaces the derived file.
        self.assertEqual(sorted(item.name for item in path.parent.iterdir()), [path.name])

    def test_unverified_runs_are_refused(self):
        (self.runs / "run-incomplete").mkdir()
        for target, code in ((self.runs / "missing", "incomplete-run"), (self.runs / "run-incomplete", "incomplete-run")):
            with self.subTest(code=code, target=target.name), self.assertRaises(v.ViewError) as caught:
                v.write_view(target)
            self.assertEqual(caught.exception.code, code)
        (self.run / "report.md").chmod(0o600)
        with open(self.run / "report.md", "ab") as handle:
            handle.write(b"tampered")
        with self.assertRaises(v.ViewError) as caught:
            v.write_view(self.run)
        self.assertEqual(caught.exception.code, "corrupt-run")
        self.assertFalse((self.runs / "views").exists())

    def test_public_parent_is_refused(self):
        self.runs.chmod(0o755)
        try:
            with self.assertRaises(v.ViewError) as caught:
                v.write_view(self.run)
        finally:
            self.runs.chmod(0o700)
        self.assertEqual(caught.exception.code, "privacy-unavailable")

    def test_cli_prints_path_opens_file_uri_and_keeps_errors_safe(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("webbrowser.open", return_value=True) as opened, redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(main(["view", "--run", str(self.run), "--open"]), 0)
        path = self.runs / "views" / "run-20261025T000000Z.html"
        self.assertEqual(stdout.getvalue().strip(), str(path))
        opened.assert_called_once_with(path.as_uri())
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("webbrowser.open", return_value=False), redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(main(["view", "--run", str(self.run), "--open"]), 0)
        self.assertIn("no-browser", stderr.getvalue())
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(main(["view", "--run", str(self.runs / "PRIVATE-SECRET")]), 2)
        self.assertIn("incomplete-run", stderr.getvalue())
        self.assertNotIn("PRIVATE-SECRET", stderr.getvalue() + stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
