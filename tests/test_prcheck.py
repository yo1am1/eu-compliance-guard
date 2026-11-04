"""PR touchpoint screening on synthetic diffs; nothing is fetched or executed."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from eu_compliance_guard import models as m, prcheck as p
from eu_compliance_guard.__main__ import main

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/revalidation-synthetic.json"
DIFF = """diff --git a/app/news.py b/app/news.py
new file mode 100644
--- /dev/null
+++ b/app/news.py
@@ -0,0 +1,3 @@
+def join(email, birth_date):
+    send_newsletter(email, "marketing `rm -rf`")
+x = 1
diff --git a/app/old.py b/app/old.py
--- a/app/old.py
+++ b/app/old.py
@@ -10,2 +10,3 @@ def keep():
 unchanged = True
+cookie = request.cookies.get("analytics")
 tail = 0
diff --git a/node_modules/lib/index.js b/node_modules/lib/index.js
--- a/node_modules/lib/index.js
+++ b/node_modules/lib/index.js
@@ -1 +1 @@
+const consent = cookie
diff --git a/gone.py b/gone.py
deleted file mode 100644
--- a/gone.py
+++ /dev/null
@@ -1 +0,0 @@
-health = 1
"""


class PRCheckTests(unittest.TestCase):
    def test_diff_parsing_tracks_new_line_numbers_and_every_touched_path(self):
        added, touched = p.parse_diff(DIFF)
        self.assertEqual(added["app/news.py"][0], (1, "def join(email, birth_date):"))
        self.assertEqual(added["app/old.py"], [(11, 'cookie = request.cookies.get("analytics")')])
        self.assertEqual(touched, {"app/news.py", "app/old.py", "node_modules/lib/index.js", "gone.py"})

    def test_touchpoints_without_declarations(self):
        report = p.pr_check(DIFF)
        concepts = {item["concept"]: item for item in report["touchpoints"]}
        self.assertEqual(set(concepts), {"personal_data", "marketing", "tracking"})
        self.assertEqual(concepts["tracking"]["examples"], ['app/old.py:11  cookie = request.cookies.get("analytics")'])
        self.assertIn("eprivacy", concepts["tracking"]["families"])
        self.assertFalse(report["declarations"])
        self.assertEqual(report["attention"], 3)
        markdown = p.format_markdown(report)
        self.assertIn("no declarations", markdown)
        self.assertNotIn("`rm -rf`", markdown)  # backticks in diff text cannot break out of code spans
        self.assertIn("not a legal conclusion or a compliance verdict", markdown)

    def test_declared_concepts_pinned_evidence_and_requirement_origins(self):
        payload = json.loads(FIXTURE.read_bytes())
        payload["requirements"][0]["statement"] = "FICTIONAL: honour cookie choices before analytics run."
        declared = m.RevalidationInput.model_validate(payload)
        evidence_path = declared.evidence[0].path
        origin = next((item.origin.path for item in declared.requirements if item.origin), None)
        diff = DIFF + f"""diff --git a/.eu-compliance-guard/{evidence_path} b/.eu-compliance-guard/{evidence_path}
--- a/.eu-compliance-guard/{evidence_path}
+++ b/.eu-compliance-guard/{evidence_path}
@@ -1 +1 @@
+changed
"""
        report = p.pr_check(diff, declared)
        concepts = {item["concept"]: item for item in report["touchpoints"]}
        self.assertTrue(concepts["tracking"]["declared"])
        self.assertFalse(concepts["marketing"]["declared"])
        self.assertEqual([item["path"] for item in report["pinned_evidence"]], [f".eu-compliance-guard/{evidence_path}"])
        if origin is None:
            self.assertEqual(report["requirements_in_changed_files"], [])

    def test_paths_cannot_break_out_of_code_spans(self):
        diff = ("--- /dev/null\n+++ b/app/a`<img src=https://evil.example/p.png> [x](https://evil.example) @someone`.py\n"
                "@@ -0,0 +1 @@\n+cookie = analytics()\n")
        markdown = p.format_markdown(p.pr_check(diff))
        for line in markdown.splitlines():
            if "evil" in line:
                self.assertEqual(line.count("`"), 2, line)
        self.assertTrue(markdown.startswith(p.MARKER))

    def test_broad_words_alone_do_not_count_as_mentioned(self):
        payload = json.loads(FIXTURE.read_bytes())
        payload["requirements"][0]["statement"] = "FICTIONAL: the user model and the api are documented."
        report = p.pr_check("--- /dev/null\n+++ b/a.py\n@@ -0,0 +1 @@\n+reply = openai.complete(prompt)\n",
                            m.RevalidationInput.model_validate(payload))
        [ai] = [item for item in report["touchpoints"] if item["concept"] == "ai"]
        self.assertFalse(ai["declared"])

    def test_hunk_lines_that_look_like_headers_stay_hunk_lines(self):
        diff = ("diff --git a/db/m.sql b/db/m.sql\n--- a/db/m.sql\n+++ b/db/m.sql\n@@ -1,2 +1,3 @@\n"
                "--- keep consent records 30 days\n+++ counter\n+the user must give consent via the cookie banner\n"
                " select 1;\n")
        added, touched = p.parse_diff(diff)
        self.assertEqual(touched, {"db/m.sql"})
        self.assertEqual(added["db/m.sql"], [(1, "++ counter"), (2, "the user must give consent via the cookie banner")])

    def test_quoted_paths_and_form_feeds(self):
        diff = ('--- /dev/null\n+++ "b/src/gr\\303\\266\\303\\237e.py"\n@@ -0,0 +1,3 @@\n'
                "+x = 1\x0c y = 2\n+z = 3\n+store_health_consent_cookie()\n")
        added, touched = p.parse_diff(diff)
        self.assertEqual(touched, {"src/größe.py"})
        self.assertEqual(added["src/größe.py"][2][0], 3)
        self.assertTrue(p.pr_check(diff)["touchpoints"])

    def test_two_ordinary_terms_count_as_mentioned_even_with_strong_terms_defined(self):
        payload = json.loads(FIXTURE.read_bytes())
        payload["requirements"][0]["statement"] = "FICTIONAL: we store the customer email and birth year."
        report = p.pr_check("--- /dev/null\n+++ b/a.py\n@@ -0,0 +1 @@\n+def join(email, birth_date): pass\n",
                            m.RevalidationInput.model_validate(payload))
        [personal] = [item for item in report["touchpoints"] if item["concept"] == "personal_data"]
        self.assertTrue(personal["declared"])

    def test_renames_binaries_and_mode_changes_count_as_touched(self):
        diff = ("diff --git a/src/old name.py b/src/old name.py\nold mode 100644\nnew mode 100755\n"
                "diff --git a/ev.txt b/ev2.txt\nsimilarity index 100%\nrename from ev.txt\nrename to ev2.txt\n"
                "diff --git a/logo.png b/logo.png\nBinary files a/logo.png and b/logo.png differ\n"
                'diff --git "a/gr\\303\\266\\303\\237e.py" "b/gr\\303\\266\\303\\237e.py"\nold mode 100644\nnew mode 100755\n')
        _, touched = p.parse_diff(diff)
        self.assertEqual(touched, {"src/old name.py", "ev.txt", "ev2.txt", "logo.png", "größe.py"})

    def test_empty_diff_is_not_a_clean_bill(self):
        report = p.pr_check("")
        self.assertEqual(report["attention"], 0)
        self.assertIn("not a clean bill", p.format_markdown(report))

    def test_cli_reads_a_file_and_strict_mode_signals_attention(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pr.diff"
            path.write_text(DIFF)
            missing = str(Path(folder) / "none.json")
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(["pr-check", "--diff", str(path), "--input", missing, "--json"]), 0)
            self.assertEqual(json.loads(out.getvalue())["attention"], 3)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["pr-check", "--diff", str(path), "--input", missing, "--strict"]), 1)
            bad = Path(folder) / "bad.json"
            bad.write_text("{")
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                self.assertEqual(main(["pr-check", "--diff", str(path), "--input", str(bad)]), 2)
            self.assertTrue(err.getvalue().startswith("eu-compliance-guard: "))
            self.assertNotIn("{", err.getvalue())


if __name__ == "__main__":
    unittest.main()
