"""Same inputs, same bytes: the whole pipeline is run in fresh interpreters under different hash
seeds, time zones and locales, with only the run's clock and ids fixed, and every output compared."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = r'''
import contextlib, datetime as real, hashlib, io, json, shutil, sys
from pathlib import Path
from unittest import mock
from eu_compliance_guard import revalidation as r
from eu_compliance_guard.__main__ import main

work, fixture = Path(sys.argv[1]), Path(sys.argv[2])
shutil.copytree(fixture.parent / "revalidation-synthetic", work / "revalidation-synthetic")
(work / "input.json").write_bytes(fixture.read_bytes())
(work / "state").mkdir(mode=0o700)
(work / "change.diff").write_text("diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -0,0 +1,2 @@\n"
                                  "+set_cookie(email, max_age=395)\n+llm.complete(user['weight_kg'])\n")
run = work / "state/run-20261105T000000Z"

class Clock(real.datetime):
    @classmethod
    def now(cls, tz=None):
        return real.datetime(2026, 11, 5, 8, 19, 1, tzinfo=real.timezone.utc)

ids = iter(range(10, 99))
digests = {}
def cli(name, *args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        main([str(arg) for arg in args])
    digests[name] = hashlib.sha256(out.getvalue().replace(str(work), "<work>").encode()).hexdigest()

with mock.patch.object(r, "datetime", Clock), mock.patch.object(r, "uuid4", lambda: mock.Mock(hex=f"{next(ids):032x}")):
    cli("revalidate", "revalidate", "--input", work / "input.json", "--output", run, "--offline")
for path in sorted(run.rglob("*")):
    if path.is_file():
        digests[path.relative_to(work).as_posix()] = hashlib.sha256(path.read_bytes().replace(str(work).encode(), b"<work>")).hexdigest()
for name, args in {"check": ("check", "--input", work / "input.json"), "check-json": ("check", "--input", work / "input.json", "--json"),
                   "next": ("next", "--run", run), "next-json": ("next", "--run", run, "--json"),
                   "score": ("score", "--run", run), "score-json": ("score", "--run", run, "--json"),
                   "ground": ("ground", "--input", work / "input.json"), "ground-json": ("ground", "--input", work / "input.json", "--json"),
                   "pr": ("pr-check", "--diff", work / "change.diff", "--input", work / "input.json"),
                   "pr-md": ("pr-check", "--diff", work / "change.diff", "--input", work / "input.json", "--markdown"),
                   "pr-json": ("pr-check", "--diff", work / "change.diff", "--input", work / "input.json", "--json"),
                   "view": ("view", "--run", run)}.items():
    cli(name, *args)
for path in sorted((work / "state/views").iterdir()):
    digests[path.name] = hashlib.sha256(path.read_bytes().replace(str(work).encode(), b"<work>")).hexdigest()
print(json.dumps(digests, sort_keys=True))
'''
ENVIRONMENTS = [{"PYTHONHASHSEED": "1", "TZ": "UTC", "LC_ALL": "C"},
                {"PYTHONHASHSEED": "2", "TZ": "Asia/Tokyo", "LC_ALL": "C.UTF-8"},
                {"PYTHONHASHSEED": "3", "TZ": "America/Los_Angeles", "LC_ALL": "C.UTF-8", "LANG": "de_DE.UTF-8"}]


class DeterminismTests(unittest.TestCase):
    def test_outputs_are_byte_identical_across_hash_seeds_time_zones_and_locales(self):
        results = []
        for extra in ENVIRONMENTS:
            with tempfile.TemporaryDirectory(prefix="eucg-determinism-") as work:
                Path(work).chmod(0o700)
                env = {key: value for key, value in os.environ.items() if not key.startswith(("PYTHON", "LC_", "LANG", "TZ"))}
                env.update(extra, PYTHONPATH=str(ROOT))
                done = subprocess.run([sys.executable, "-c", PIPELINE, work, ROOT / "fixtures/revalidation-synthetic.json"],
                                      capture_output=True, text=True, env=env, cwd=work, timeout=120)
                self.assertEqual(done.returncode, 0, done.stderr[-2000:])
                results.append(json.loads(done.stdout))
        self.assertGreater(len(results[0]), 15)
        for other in results[1:]:
            different = sorted(name for name in results[0] if results[0][name] != other.get(name))
            self.assertEqual(different, [], "outputs differ between environments")
            self.assertEqual(set(other), set(results[0]))


if __name__ == "__main__":
    unittest.main()
