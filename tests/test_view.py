"""HTML run view checks on synthetic runs; nothing is opened or fetched."""

from contextlib import redirect_stderr, redirect_stdout
import io
import os
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from eu_compliance_guard import models as m, revalidation as r, scorecard as s, view as v
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
        self.assertEqual(sorted(item.name for item in path.parent.iterdir()),
                         sorted([path.name, "run-20261025T000000Z.scorecard.json", "run-20261025T000000Z.dashboard.html"]))

    def test_article_text_and_suggestions_come_from_retained_source_bytes(self):
        text = ("FICTIONAL SOURCE — SYNTHETIC EXAMPLE ONLY\nArticle 1\nFictional review records\n"
                "The fictional controller shall retain a declared review record & 1 < 2.\n"
                "Article 2\nFictional erasure\nThe fictional controller shall erase an account on request.\n").encode()
        folder = self.root / "revalidation-synthetic"
        (folder / "source.txt").write_bytes(text)
        raw = FIXTURE.read_text().replace("Fictional section 1", "Article 1").replace(
            "sha256:b89f4bb123cc3732e9560553b419757350e5bdab12f0f1f4a8bdc53dfd89f5a0", m.content_digest(text))
        payload = json.loads(raw)
        payload["requirements"][1]["statement"] = "FICTIONAL: users can delete their account."
        self.input.write_text(json.dumps(payload))
        run = self.runs / "run-20261025T000001Z"
        r.run(self.input, run)
        html = v.write_view(run).read_text()
        self.assertIn("<summary>Article 1 — Fictional review records</summary>", html)
        self.assertIn("retain a declared review record &amp; 1 &lt; 2.", html)
        self.assertIn("Unreviewed candidate text", html)
        self.assertRegex(html, r"Articles to read: Article 2 <span class=\"muted\">Fictional erasure")
        self.assertIn("not a mapping", html)
        self.assertNotRegex(html, r"(?i)<script")

    def test_an_excerpt_comes_from_the_pinned_source_not_another_source_of_the_target(self):
        import copy
        folder = self.root / "revalidation-synthetic"
        old = "FICTIONAL SOURCE — SYNTHETIC EXAMPLE ONLY\nArticle 1\nFictional OLD title\nOLD wording.\n".encode()
        new = "FICTIONAL SOURCE — SYNTHETIC EXAMPLE ONLY\nArticle 1\nFictional NEW title\nNEW wording.\n".encode()
        (folder / "old.txt").write_bytes(old)
        (folder / "new.txt").write_bytes(new)
        payload = json.loads(FIXTURE.read_text().replace("Fictional section 1", "Article 1"))
        first = payload["sources"][0]
        first.update(file={"path": "revalidation-synthetic/old.txt", "digest": m.content_digest(old)})
        first["source"].update(content_digest=m.content_digest(old), id="source-old")
        second = copy.deepcopy(first)
        second.update(file={"path": "revalidation-synthetic/new.txt", "digest": m.content_digest(new)})
        second["source"].update(content_digest=m.content_digest(new), id="source-example")
        payload["sources"] = [first, second]
        self.input.write_text(json.dumps(payload))
        run = self.runs / "run-20261025T000002Z"
        r.run(self.input, run)
        html = v.write_view(run).read_text()
        self.assertIn("Article 1 — Fictional NEW title", html)
        self.assertNotIn("OLD wording", html)

    def test_unverified_runs_are_refused(self):
        (self.runs / "run-incomplete").mkdir()
        for target, code in ((self.runs / "missing", "unsafe-path"), (self.runs / "run-incomplete", "incomplete-run")):
            with self.subTest(code=code, target=target.name), self.assertRaises(v.ViewError) as caught:
                v.write_view(target)
            self.assertEqual(caught.exception.code, code)
        previous = os.getcwd()
        os.chdir(self.runs / "run-incomplete")  # An empty run argument must not mean the working directory.
        try:
            with self.assertRaises(v.ViewError) as caught:
                v.write_view("")
            self.assertEqual(caught.exception.code, "unsafe-path")
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                self.assertEqual(main(["view", "--run", ""]), 2)
            self.assertIn("unsafe-path", stderr.getvalue())
        finally:
            os.chdir(previous)
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
        self.assertIn("unsafe-path", stderr.getvalue())
        self.assertNotIn("PRIVATE-SECRET", stderr.getvalue() + stdout.getvalue())

    def test_open_with_a_relative_run_path_uses_an_absolute_uri(self):
        cwd = os.getcwd()
        os.chdir(self.runs)
        try:
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch("webbrowser.open", return_value=True) as opened, redirect_stdout(stdout), redirect_stderr(stderr):
                self.assertEqual(main(["view", "--run", self.run.name, "--open"]), 0)
            with patch("webbrowser.open", side_effect=RuntimeError("no display")), redirect_stdout(stdout), redirect_stderr(stderr):
                self.assertEqual(main(["view", "--run", self.run.name, "--open"]), 0)
        finally:
            os.chdir(cwd)
        self.assertTrue(opened.call_args.args[0].startswith("file:///"))
        self.assertIn("no-browser", stderr.getvalue())

    def test_review_progress_leads_the_view_with_the_score_command_numbers(self):
        from test_scorecard import banned_words
        before = self.snapshot()
        html = v.write_view(self.run).read_text()
        self.assertEqual(self.snapshot(), before)
        start, end = html.index('<section class="progress"'), html.index("</section>")
        section = html[start:end]
        self.assertLess(start, html.index('<div class="cards">'))
        self.assertLess(html.index('<div class="banner">'), start)
        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            self.assertEqual(main(["score", "--run", str(self.run), "--json"]), 0)
        card = m.parse_record(m.Scorecard, json.dumps(json.loads(stdout.getvalue())["scorecard"]))
        for item in card.dimensions:
            label = s.LABELS[item.key]
            self.assertIn(f"{item.done} of {item.total} {s.UNITS[item.key]}", section)
            self.assertIn(f'aria-label="{item.points} of 10 points"', section)
            self.assertIn(label if item.key != "alignment" else label.upper(), section)
        self.assertIn("0 of 11 families screened", section)
        self.assertIn("Record hygiene", section)
        self.assertIn(m.SCORE_NOTICE, section)
        self.assertIn("▶ NEXT</b> Map requirement-unmapped to a candidate obligation", section)
        # The hero, five meter tiles, screening and hygiene each carry the fictional marker.
        self.assertEqual(section.count('<span class="chip fiction">fictional data</span>'), 8)
        self.assertEqual(section.count('class="tile focus"'), 1)
        self.assertEqual(banned_words(section.replace("compliance conclusion", "")), [])
        self.assertNotIn("total", section.replace("not scored", "").replace("no total exists", "").lower())
        for forbidden in ("<script", "<img", "<svg", "<link", "url(", "http://", "https://", "src="):
            self.assertNotIn(forbidden, section.lower())

    def test_view_writes_the_scorecard_json_privately_and_deterministically(self):
        before = self.snapshot()
        html = v.write_view(self.run)
        path = html.with_name("run-20261025T000000Z.scorecard.json")
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        first = path.read_bytes()
        self.assertEqual(m.parse_record(m.Scorecard, first), s.score(self.bundle))
        self.assertEqual(first, s.to_json(s.score(self.bundle)))
        first_html = html.read_bytes()
        v.write_view(self.run)
        self.assertEqual((path.read_bytes(), html.read_bytes()), (first, first_html))
        self.assertEqual(self.snapshot(), before)
        # A planted link is replaced, never followed.
        outside = self.root / "outside.json"
        outside.write_text("keep")
        path.unlink()
        path.symlink_to(outside)
        v.write_view(self.run)
        self.assertFalse(path.is_symlink())
        self.assertEqual((outside.read_text(), path.read_bytes()), ("keep", first))
        self.assertEqual(sorted(item.name for item in path.parent.iterdir()),
                         sorted([html.name, path.name, "run-20261025T000000Z.dashboard.html"]))

    def test_dashboard_is_one_static_private_page_opened_from_the_cli(self):
        dashboard = v.write_view(self.run, dashboard=True)
        self.assertEqual(dashboard.name, "run-20261025T000000Z.dashboard.html")
        self.assertEqual(dashboard.stat().st_mode & 0o777, 0o600)
        page = dashboard.read_text()
        self.assertIn("default-src 'none'", page)
        self.assertNotIn("<script", page.lower())
        self.assertNotIn("http", page.replace("http-equiv", ""))
        self.assertIn('href="run-20261025T000000Z.html"', page)
        self.assertIn(v._review_progress(s.score(self.bundle)), page)
        first = dashboard.read_bytes()
        v.write_view(self.run)
        self.assertEqual(dashboard.read_bytes(), first)
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("webbrowser.open", return_value=True) as opened, redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(main(["view", "--run", str(self.run), "--dashboard", "--open"]), 0)
        self.assertEqual(stdout.getvalue().strip(), str(dashboard))
        opened.assert_called_once_with(dashboard.as_uri())

    def test_review_progress_escapes_declared_text(self):
        payload = json.loads(self.input.read_text())
        payload["obligations"][1]["required_methods"] = ["<b onclick=x>method</b>"]
        self.input.write_text(json.dumps(payload))
        run = self.runs / "run-20261026T000000Z"
        r.run(self.input, run)
        html = v.write_view(run).read_text()
        section = html[html.index('<section class="progress"'):html.index("</section>")]
        self.assertIn("&lt;b onclick=x&gt;method&lt;/b&gt;", section)
        self.assertNotIn("<b onclick", html)

    def test_view_leads_with_owner_questions_and_groups_attention_by_area(self):
        html = v.write_view(self.run).read_text()
        questions = html.index("Questions for the project owner")
        self.assertLess(questions, html.index("What needs attention"))
        unknown = next(fact for fact in m.scope_facts(self.bundle.declarations.scope) if fact.basis == "unknown")
        self.assertIn(f"<td>{unknown.key}</td>", html)
        self.assertIn("<details open><summary>Requirements <span class=\"count\">", html)
        self.assertIn("<details><summary>Legal families to screen <span class=\"count\">11</span>", html)
        self.assertNotRegex(html, r"(?i)<script|https?://")

    def test_comparison_names_change_types_and_obligations_not_raw_digests(self):
        payload = json.loads(self.input.read_text())
        payload["requirements"][0].update(revision=1, statement="FICTIONAL changed requirement")
        self.input.write_text(json.dumps(payload))
        from eu_compliance_guard import revalidation as rv
        successor = rv.run(self.input, self.runs / "run-20261025T000100Z", previous=self.run)
        html = v.render_html(successor)
        self.assertIn('<span class="tag ">changed</span></td><td>requirement</td><td>requirement-example</td>', html)
        self.assertIn("<code>obligation-example</code>", html)
        full = next(item.after for item in successor.comparison.changes if item.after)
        self.assertIn(f'title="{full}"', html)
        self.assertNotIn(f">{full}<", html)

    def test_legal_references_and_retrieval_show_their_source_type(self):
        payload = json.loads(self.input.read_text())
        payload["sources"][0]["source"].update(type="proposal", synthetic=False)
        payload["source_targets"][0]["intended_type"] = "draft_guidance"
        unpinned = dict(payload["obligations"][0]["source_provisions"][0], locator="Fictional section 2")
        unpinned.pop("source_id"), unpinned.pop("revision")
        payload["obligations"][0]["source_provisions"].append(unpinned)
        self.input.write_text(json.dumps(payload))
        bundle = r.run(self.input, self.runs / "run-20261025T000300Z")
        html = v.render_html(bundle)
        obligations = html[html.index("<h2>Candidate obligations</h2>"):html.index("<h2>Official-source retrieval</h2>")]
        self.assertIn("source-example — Fictional section 1 (proposal)", obligations)
        self.assertIn("target-example — Fictional section 2 (draft_guidance)", obligations)
        attempt = m.SourceAttempt.model_validate({
            "id": "attempt-ui", "source_target_id": "target-example", "intended_url": "https://example.invalid/a",
            "publisher": "Fictional fixture authority", "intended_type": "engineering_practice", "language": "en",
            "attempted_at": "2026-10-18T10:00:00Z", "state": "retrieval_failed",
            "failure": {"code": "network-unavailable", "safe_message": "Fictional failure"},
            "retrieval": {"requested_url": "https://example.invalid/a", "redirects": [], "bytes_read": 0,
                          "started_at": "2026-10-18T10:00:00Z", "ended_at": "2026-10-18T10:00:00Z",
                          "comparison": "not_compared"}})
        html = v.render_html(bundle.model_copy(update={"source_attempts": [attempt]}))
        retrieval = html[html.index("<h2>Official-source retrieval</h2>"):]
        self.assertIn("<th scope=\"col\">Type</th>", retrieval)
        self.assertIn("<td>engineering_practice</td>", retrieval)

    def test_a_retrieval_that_needs_review_is_not_styled_as_confirmed(self):
        digest = "sha256:" + "a" * 64
        def attempt(admission):
            return m.SourceAttempt.model_validate({
                "id": f"attempt-{admission}", "source_target_id": "target-example", "intended_url": "https://example.invalid/a",
                "publisher": "Fictional fixture authority", "intended_type": "synthetic_fixture", "language": "en",
                "attempted_at": "2026-10-18T10:00:00Z", "state": "retrieved",
                "retrieved_source": {"id": "source-example", "revision": 0},
                "retrieval": {"requested_url": "https://example.invalid/a", "final_url": "https://example.invalid/a",
                              "redirects": [], "bytes_read": 1, "status": 200, "digest": digest,
                              "artifact_path": "sources/" + "a" * 64 + ".bin", "admission": admission,
                              "admission_reason": "fictional-reason", "started_at": "2026-10-18T10:00:00Z",
                              "ended_at": "2026-10-18T10:00:00Z", "comparison": "same_bytes"}})
        for admission, styled in (("needs_review", False), ("accepted", True)):
            with self.subTest(admission=admission):
                html = v.render_html(self.bundle.model_copy(update={"source_attempts": [attempt(admission)]}))
                retrieval = html[html.index("<h2>Official-source retrieval</h2>"):html.index("<h2>Eleven")]
                self.assertEqual('<span class="tag ok">retrieved</span>' in retrieval, styled)
                self.assertEqual('<span class="tag ok">same_bytes</span>' in retrieval, styled)

    def test_a_removed_historical_obligation_is_named_in_view_and_report(self):
        payload = json.loads(self.input.read_text())
        payload["obligations"] = [item for item in payload["obligations"] if item["id"] != "obligation-unmapped"]
        payload["applicability_decisions"] = [item for item in payload["applicability_decisions"]
                                              if item["obligation"]["id"] != "obligation-unmapped"]
        self.input.write_text(json.dumps(payload))
        successor = r.run(self.input, self.runs / "run-20261025T000200Z", previous=self.run)
        removed = next(item for item in self.bundle.obligation_dispositions if item.obligation_id == "obligation-unmapped")
        overlay = next(item for item in successor.current_assessments if item.obligation_disposition_id == removed.id)
        self.assertEqual(overlay.obligation_id, "obligation-unmapped")
        html = v.render_html(successor)
        table = html[html.index("Historical obligation"):]
        self.assertIn("<td><code>obligation-unmapped</code></td>", table)
        self.assertNotIn(f"<code>{removed.id}</code>", table)
        report = (self.runs / "run-20261025T000200Z" / "report.md").read_text()
        freshness = report[report.index("Historical claim freshness"):report.index("## Declared scope")]
        self.assertIn("- Obligation id: obligation&#45;unmapped\n", freshness)


if __name__ == "__main__":
    unittest.main()
