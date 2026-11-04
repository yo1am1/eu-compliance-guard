"""PR touchpoint screening on synthetic diffs; nothing is fetched or executed."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
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


def _coloured(diff: str) -> str:
    """The diff as `git -c color.ui=always diff` prints it: SGR codes around headers, hunk headers and changes."""
    out = []
    for line in diff.split("\n"):
        if line.startswith(("diff --git ", "new file mode", "deleted file mode", "--- ", "+++ ")):
            out.append(f"\x1b[1m{line}\x1b[m")
        elif line.startswith("@@"):
            fence = line.index(" @@", 2) + 3
            out.append(f"\x1b[36m{line[:fence]}\x1b[m{line[fence:]}")
        elif line[:1] in ("+", "-"):
            colour = "1;32" if line[0] == "+" else "38;5;1"
            out.append(f"\x1b[{colour}m{line[0]}\x1b[m\x1b[{colour}m{line[1:]}\x1b[m")
        else:
            out.append(f"{line}\x1b[m" if line else line)
    return "\n".join(out)


class PRCheckTests(unittest.TestCase):
    def test_diff_parsing_tracks_new_line_numbers_and_every_touched_path(self):
        added, touched, files = p.parse_diff(DIFF)
        self.assertEqual(added["app/news.py"][0], (1, "def join(email, birth_date):"))
        self.assertEqual(added["app/old.py"], [(11, 'cookie = request.cookies.get("analytics")')])
        self.assertEqual(touched, {"app/news.py", "app/old.py", "node_modules/lib/index.js", "gone.py"})
        self.assertEqual(files, 4)

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

    def test_plain_text_says_when_no_declarations_were_read(self):
        text = p.format_text(p.pr_check(DIFF))
        self.assertNotIn("not mentioned in declarations", text)
        self.assertIn("no declarations to compare", text)
        self.assertIn("No declarations file found, so nothing is compared with declarations.", text)
        declared = m.RevalidationInput.model_validate(json.loads(FIXTURE.read_bytes()))
        text = p.format_text(p.pr_check(DIFF, declared))
        self.assertIn("not mentioned in declarations", text)
        self.assertNotIn("No declarations file found", text)

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
        added, touched, _ = p.parse_diff(diff)
        self.assertEqual(touched, {"db/m.sql"})
        self.assertEqual(added["db/m.sql"], [(1, "++ counter"), (2, "the user must give consent via the cookie banner")])

    def test_quoted_paths_and_form_feeds(self):
        diff = ('--- /dev/null\n+++ "b/src/gr\\303\\266\\303\\237e.py"\n@@ -0,0 +1,3 @@\n'
                "+x = 1\x0c y = 2\n+z = 3\n+store_health_consent_cookie()\n")
        added, touched, _ = p.parse_diff(diff)
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
        _, touched, files = p.parse_diff(diff)
        self.assertEqual(touched, {"src/old name.py", "ev.txt", "ev2.txt", "logo.png", "größe.py"})
        self.assertEqual(files, 4)

    def test_renames_count_once_and_headers_never_invent_paths(self):
        rename = "diff --git a/src/app.py b/src/main.py\nsimilarity index 100%\nrename from src/app.py\nrename to src/main.py\n"
        _, touched, files = p.parse_diff(rename)
        self.assertEqual((touched, files), ({"src/app.py", "src/main.py"}, 1))
        self.assertEqual(p.pr_check(rename)["files"], 1)
        # git --stat counts 4 files here. Split at its first " b/", the rename's header would invent
        # "src/x" and "y.py b/src/z.py"; the rename lines name the real paths.
        diff = ('diff --git "a/src/a b/t\\tab.py" "b/src/a b/t\\tab.py"\nnew file mode 100644\n--- /dev/null\n'
                '+++ "b/src/a b/t\\tab.py"\t\n@@ -0,0 +1 @@\n+consent = 1\n'
                'diff --git "a/src/gr\\303\\266\\303\\237e.py" "b/src/gr\\303\\266\\303\\237e.py"\ndeleted file mode 100644\n'
                '--- "a/src/gr\\303\\266\\303\\237e.py"\n+++ /dev/null\n@@ -1 +0,0 @@\n-z\n'
                "diff --git a/src/x b/y.py b/src/z.py\nsimilarity index 90%\nrename from src/x b/y.py\nrename to src/z.py\n"
                "--- a/src/x b/y.py\n+++ b/src/z.py\n@@ -1 +1,2 @@\n z\n+patient_health = 1\n"
                "diff --git a/src/app.py b/src/app_copy.py\nsimilarity index 62%\ncopy from src/app.py\ncopy to src/app_copy.py\n")
        added, touched, files = p.parse_diff(diff)
        self.assertEqual(touched, {"src/a b/t\tab.py", "src/größe.py", "src/x b/y.py", "src/z.py", "src/app.py",
                                   "src/app_copy.py"})
        self.assertEqual(files, 4)
        self.assertEqual(added["src/z.py"], [(2, "patient_health = 1")])
        self.assertEqual(p.pr_check(diff)["files"], 4)
        # The same file changed in several commits (`git log -p`) is one changed file.
        twice = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-x\n+y\n" * 2
        self.assertEqual(p.parse_diff(twice)[2], 1)

    def test_coloured_diffs_parse_like_plain_ones(self):
        coloured = _coloured(DIFF)
        self.assertTrue(coloured.startswith("\x1b[1mdiff --git "))
        self.assertEqual(p.parse_diff(coloured), p.parse_diff(DIFF))
        self.assertEqual(p.pr_check(coloured), p.pr_check(DIFF))

    def test_input_without_any_diff_is_refused_not_reported_empty(self):
        for text in ("hello this is not a diff\nhealth consent cookie\n",
                     "@@ -1 +1 @@\n+store_health_consent_cookie()\n",
                     " src/app.py | 2 +-\n 1 file changed, 1 insertion(+), 1 deletion(-)\n"):
            with self.assertRaises(p.PRCheckError) as caught:
                p.pr_check(text)
            self.assertEqual(caught.exception.code, "invalid-input")
        self.assertEqual(p.pr_check(" \n\n")["files"], 0)  # blank input is an empty diff
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "notes.txt"
            path.write_text("health consent cookie\n")
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = main(["pr-check", "--diff", str(path), "--input", str(Path(folder) / "none.json"), "--strict"])
            self.assertEqual(code, 2)
            self.assertEqual(out.getvalue(), "")
            self.assertEqual(err.getvalue(), "eu-compliance-guard: invalid-input: pr check failed\n")

    def test_combined_merge_diffs_screen_the_lines_the_merge_adds(self):
        # `git show <merge>`: one prefix column per parent; "+" in any column and no "-" is a result line
        # that some parent lacked, "-" lines are gone from the result and do not advance its numbers.
        diff = ("commit 0e1f481\nMerge: a2b5375 ec47063\n\n    merge\n\n"
                "diff --cc app/web.py\nindex c94aa68,b3be3d7..3a45c78\n--- a/app/web.py\n+++ b/app/web.py\n"
                "@@@ -1,5 -1,5 +1,5 @@@ def landing():\n"
                "  def landing():\n"
                "- old_one = 1\n"
                " -old_two = 2\n"
                "--both_gone = 3\n"
                "+ def a(): pass\n"
                " +def b(): pass\n"
                '++def track(): mixpanel.track("health_diagnosis", user.email)\n'
                "  tail = 0\n"
                "@@@ -20,1 -20,1 +20,2 @@@\n"
                "  x = 1\n"
                "++cookie_consent = True\n"
                "diff --combined lib/three.py\n--- a/lib/three.py\n+++ b/lib/three.py\n"
                "@@@@ -1,1 -1,1 -1,1 +1,2 @@@@\n"
                "   keep = 1\n"
                "+++patient_health_record = 1\n")
        added, touched, files = p.parse_diff(diff)
        self.assertEqual(touched, {"app/web.py", "lib/three.py"})
        self.assertEqual(added["app/web.py"], [
            (2, "def a(): pass"), (3, "def b(): pass"),
            (4, 'def track(): mixpanel.track("health_diagnosis", user.email)'), (21, "cookie_consent = True")])
        self.assertEqual(added["lib/three.py"], [(2, "patient_health_record = 1")])
        report = p.pr_check(diff)
        concepts = {item["concept"] for item in report["touchpoints"]}
        self.assertTrue({"special_category", "tracking"} <= concepts, concepts)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "merge.diff"
            path.write_text(diff)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["pr-check", "--diff", str(path), "--input", str(Path(folder) / "none.json"),
                                       "--strict"]), 1)

    def test_lines_a_hunk_cannot_hold_are_refused(self):
        # Word-diff output and broken hunk headers are not unified diffs; dropping their lines would pass --strict.
        for body in ("@@ -1,2 +1,2 @@\n keep = 1\n[-old-]{+cookie_consent = True+}\n",
                     "@@ -1,x +1 @@\n+cookie_consent = True\n",
                     "@@@ -1 -1 +1,2 @@@\n  keep = 1\n+-cookie_consent = True\n"):
            with self.assertRaises(p.PRCheckError) as caught:
                p.parse_diff("diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n" + body)
            self.assertEqual(caught.exception.code, "invalid-input", body)

    def test_empty_diff_is_not_a_clean_bill(self):
        report = p.pr_check("")
        self.assertEqual(report["attention"], 0)
        self.assertIn("not a clean bill", p.format_markdown(report))

    def cli_in(self, folder, *args):
        """Run the CLI with folder as the current directory, where the default declarations path resolves."""
        previous = os.getcwd()
        os.chdir(folder)
        self.addCleanup(os.chdir, previous)
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(list(args))
        os.chdir(previous)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_cli_reads_a_file_and_strict_mode_signals_attention(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pr.diff"
            path.write_text(DIFF)
            code, out, _ = self.cli_in(folder, "pr-check", "--diff", str(path), "--json")
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["attention"], 3)
            self.assertFalse(json.loads(out)["declarations"])
            self.assertEqual(self.cli_in(folder, "pr-check", "--diff", str(path), "--strict")[0], 1)
            bad = Path(folder) / "bad.json"
            bad.write_text("{")
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                self.assertEqual(main(["pr-check", "--diff", str(path), "--input", str(bad)]), 2)
            self.assertTrue(err.getvalue().startswith("eu-compliance-guard: "))
            self.assertNotIn("{", err.getvalue())

    def test_named_or_unreachable_declarations_are_never_skipped(self):
        with tempfile.TemporaryDirectory() as folder:
            diff = Path(folder) / "pr.diff"
            diff.write_text(DIFF)
            # A named --input must exist: a typo cannot turn a --strict failure into a pass.
            code, stdout, stderr = self.cli_in(folder, "pr-check", "--diff", str(diff), "--strict",
                                               "--input", str(Path(folder) / "declaration.json"))
            self.assertEqual((code, stdout), (2, ""))
            self.assertIn("unsafe-path", stderr)
            # Only a clean "no such file" means absent; a folder that cannot be resolved is refused.
            (Path(folder) / ".eu-compliance-guard").symlink_to(".eu-compliance-guard")
            code, stdout, stderr = self.cli_in(folder, "pr-check", "--diff", str(diff), "--strict")
            self.assertEqual((code, stdout), (2, ""))
            self.assertIn("unsafe-path", stderr)

    @unittest.skipIf(os.geteuid() == 0, "root can traverse any folder")
    def test_an_untraversable_declarations_folder_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            diff = Path(folder) / "pr.diff"
            diff.write_text(DIFF)
            state = Path(folder) / ".eu-compliance-guard"
            state.mkdir()
            (state / "declarations.json").write_bytes(FIXTURE.read_bytes())
            state.chmod(0)
            try:
                for named in ([], ["--input", ".eu-compliance-guard/declarations.json"]):
                    code, _, stderr = self.cli_in(folder, "pr-check", "--diff", str(diff), "--strict", *named)
                    self.assertEqual(code, 2)
                    self.assertIn("unsafe-path", stderr)
            finally:
                state.chmod(0o700)


if __name__ == "__main__":
    unittest.main()
