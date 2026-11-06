"""Signed decisions, the citation guard and the MCP server: offline, with a real throwaway SSH key."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from eu_compliance_guard import citations, mcp_server, models as m, revalidation as r, signing
from eu_compliance_guard.__main__ import main

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/revalidation-synthetic.json"
OLD_DIGEST = "sha256:b89f4bb123cc3732e9560553b419757350e5bdab12f0f1f4a8bdc53dfd89f5a0"
ACT = ("FICTIONAL SOURCE — SYNTHETIC EXAMPLE ONLY\nArticle 1\nFictional review records\n"
       "The fictional controller shall retain a review record.\n"
       "Article 2\nFictional erasure\nThe fictional controller shall erase an account on request.\n")
CATALOGUE = {"target-example": {
    "Article 1": {"title": "Fictional review records", "text": "The fictional controller shall retain a review record."},
    "Article 2": {"title": "Fictional erasure", "text": "The fictional controller shall erase an account on request."}}}


def cli(*args, stdin: str | None = None):
    stdout = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
        code = main([str(arg) for arg in args])
    return code, stdout.getvalue()


class Project(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="eucg-sign-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)
        (self.root / "revalidation-synthetic").mkdir()
        (self.root / "revalidation-synthetic/evidence.txt").write_bytes((FIXTURE.parent / "revalidation-synthetic/evidence.txt").read_bytes())
        (self.root / "revalidation-synthetic/source.txt").write_bytes(ACT.encode())
        self.raw = FIXTURE.read_text().replace("Fictional section 1", "Article 1").replace(OLD_DIGEST, m.content_digest(ACT.encode()))
        self.input = self.root / "declarations.json"
        self.input.write_text(self.raw)
        (self.root / "state").mkdir(mode=0o700)
        self.run = self.root / "state/run-1"
        r.run(self.input, self.run)


@unittest.skipUnless(shutil.which("ssh-keygen"), "ssh-keygen is required")
class SigningTests(Project):
    def setUp(self):
        super().setUp()
        self.key = self.root / "key"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "fictional", "-f", str(self.key)], check=True)
        self.allowed = self.root / "allowed_signers"
        self.allowed.write_text("reviewer@example.invalid " + (self.root / "key.pub").read_text())
        self.assertEqual(cli("lock", "--input", self.input, "--run", self.run)[0], 0)

    def sign(self):
        return cli("sign", "--decision", "decision-example", "--input", self.input, "--key", self.key,
                   "--principal", "reviewer@example.invalid")

    def test_a_signed_decision_verifies_and_reports_what_changed_since(self):
        code, out = self.sign()
        self.assertEqual(code, 0, out)
        self.assertNotIn("No eu-law.lock", out)
        stored = json.loads((self.root / "signatures/decision-example.json").read_text())
        self.assertEqual(stored["payload"]["law"][0]["article"], "Article 1")
        self.assertTrue(stored["payload"]["law"][0]["digest"].startswith("sha256:"))
        self.assertEqual(stored["payload"]["evidence"][0]["id"], "evidence-example")
        code, out = cli("verify", "--input", self.input, "--allowed-signers", self.allowed)
        self.assertEqual(code, 0, out)
        self.assertIn("decision, law and evidence unchanged", out)
        # The decision's rationale changes: the signature stays valid but no longer covers it.
        self.input.write_text(self.raw.replace("Fictional reviewer", "Another fictional reviewer"))
        code, out = cli("verify", "--input", self.input, "--allowed-signers", self.allowed, "--json")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)[0]["signature"], "valid")
        self.assertEqual(json.loads(out)[0]["changed"], ["decision"])

    def test_signing_without_a_lock_says_no_article_text_is_pinned(self):
        (self.root / "eu-law.lock").unlink()
        code, out = self.sign()
        self.assertEqual(code, 0, out)
        self.assertIn("No eu-law.lock was found", out)
        stored = json.loads((self.root / "signatures/decision-example.json").read_text())
        self.assertIsNone(stored["payload"]["law"][0]["digest"])

    def test_a_tampered_record_or_an_unknown_signer_is_invalid(self):
        self.assertEqual(self.sign()[0], 0)
        stranger = self.root / "allowed_other"
        stranger.write_text("someone@example.invalid " + (self.root / "key.pub").read_text())
        code, out = cli("verify", "--input", self.input, "--allowed-signers", stranger, "--json")
        self.assertEqual((code, json.loads(out)[0]["signature"]), (1, "invalid"))
        path = self.root / "signatures/decision-example.json"
        stored = json.loads(path.read_text())
        stored["payload"]["decision"]["applicability"] = "not_applicable"
        path.write_text(json.dumps(stored))
        code, out = cli("verify", "--input", self.input, "--allowed-signers", self.allowed, "--json")
        self.assertEqual((code, json.loads(out)[0]["signature"]), (1, "invalid"))

    def test_only_a_reviewed_decision_with_a_plain_principal_is_signed(self):
        self.assertEqual(cli("sign", "--decision", "missing", "--input", self.input, "--key", self.key,
                             "--principal", "reviewer@example.invalid")[0], 2)
        self.assertEqual(cli("sign", "--decision", "decision-example", "--input", self.input, "--key", self.key,
                             "--principal", "two words")[0], 2)
        self.assertFalse((self.root / "signatures").exists())


class CitationTests(Project):
    def test_citations_and_quotations_are_checked_against_the_cited_article(self):
        text = ('Article 1 requires that "the fictional controller shall retain a review record". '
                'Article 2 says “the fictional controller shall retain a  review\nrecord”. See Articles 2 and 9.')
        report = citations.check(text, CATALOGUE)
        self.assertEqual([(item["article"], item["ok"]) for item in report["citations"]],
                         [("Article 1", True), ("Article 2", True), ("Article 9", False)])
        self.assertEqual([(item["attributed_to"], item["ok"]) for item in report["quotations"]],
                         [("Article 1", True), ("Article 2", False)])
        self.assertIn("attributed to Article 2, but it is in target-example Article 1", citations.format_check(report))
        self.assertTrue(citations.check('Article 2: "erase an account on request".', CATALOGUE)["ok"])
        self.assertFalse(citations.check('Article 2: "erase every account at once".', CATALOGUE)["ok"])

    def test_cli_reads_the_latest_run_and_fails_on_a_wrong_citation(self):
        good, bad = self.root / "good.md", self.root / "bad.md"
        good.write_text('Article 1: "shall retain a review record".')
        bad.write_text("Article 7 applies.")
        self.assertEqual(cli("cite-check", good, "--input", self.input, "--run", self.run)[0], 0)
        code, out = cli("cite-check", bad, "--input", self.input, "--run", self.run)
        self.assertEqual(code, 1)
        self.assertIn("Article 7: NOT FOUND", out)


class McpTests(Project):
    def serve(self, *messages) -> list[dict]:
        stdin = io.StringIO("".join(json.dumps(item) + "\n" for item in messages) + "not json\n")
        stdout = io.StringIO()
        original = mcp_server._latest
        mcp_server._latest = lambda declarations: (None, CATALOGUE)
        self.addCleanup(setattr, mcp_server, "_latest", original)
        self.assertEqual(mcp_server.serve(str(self.input), stdin, stdout), 0)
        return [json.loads(line) for line in stdout.getvalue().splitlines()]

    def test_initialize_list_and_call_tools(self):
        responses = self.serve(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "cite_check", "arguments": {"text": "Article 9 applies."}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
             "params": {"name": "article_search", "arguments": {"query": "erase an account", "top": 1}}},
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "article_search", "arguments": {}}},
            {"jsonrpc": "2.0", "id": 6, "method": "unknown"})
        self.assertEqual([item.get("id") for item in responses], [1, 2, 3, 4, 5, 6, None])
        self.assertEqual(responses[0]["result"]["serverInfo"]["name"], "eu-compliance-guard")
        self.assertEqual([tool["name"] for tool in responses[1]["result"]["tools"]], ["cite_check", "article_search", "ground", "pr_check", "next_steps"])
        self.assertFalse(responses[2]["result"]["structuredContent"]["ok"])
        self.assertIn("Not legal advice", responses[2]["result"]["content"][0]["text"])
        self.assertEqual(responses[3]["result"]["structuredContent"]["results"][0]["article"], "Article 2")
        self.assertTrue(responses[4]["result"]["isError"])
        self.assertEqual(responses[5]["error"]["code"], -32601)
        self.assertEqual(responses[6]["error"]["code"], -32700)

    def test_hostile_messages_get_an_error_and_never_stop_the_server(self):
        stdin = io.StringIO("[" * 100000 + "]" * 100000 + "\n"
                            '{"jsonrpc":"2.0","id":NaN,"method":"ping"}\n'
                            '{"jsonrpc":"2.0","id":{"a":1},"method":"ping"}\n'
                            '{"jsonrpc":"2.0","id":true,"method":"ping"}\n'
                            '{"jsonrpc":"2.0","id":7,"method":"ping"}\n')
        stdout = io.StringIO()
        self.assertEqual(mcp_server.serve(str(self.input), stdin, stdout), 0)
        responses = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual([(item["id"], item.get("error", {}).get("code")) for item in responses],
                         [(None, -32700), (None, -32700), (None, -32600), (None, -32600), (7, None)])

    def test_tools_read_the_real_project_and_latest_run(self):
        import os
        from unittest import mock
        from eu_compliance_guard import authoring
        with mock.patch.dict(os.environ, {"XDG_STATE_HOME": str(self.root / "xdg")}):
            r.run(self.input, authoring.state_dir(self.input) / "run-latest")
            declarations = str(self.input)
            text, report = mcp_server.call(declarations, "cite_check", {"text": 'Article 2: "erase an account on request".'})
            self.assertTrue(report["ok"], text)
            _, steps = mcp_server.call(declarations, "next_steps", {"top": 2})
            self.assertLessEqual(len(steps["steps"]), 2)
            _, grounded = mcp_server.call(declarations, "ground", {})
            self.assertIsInstance(grounded, dict)
            diff = ("diff --git a/app/signup.py b/app/signup.py\n--- a/app/signup.py\n+++ b/app/signup.py\n"
                    "@@ -1 +1,2 @@\n x = 1\n+analytics_cookie = set_tracking_cookie(user.email)\n")
            text, screened = mcp_server.call(declarations, "pr_check", {"diff": diff})
            self.assertIn("attention", screened)
            with self.assertRaises(mcp_server.ToolError):
                mcp_server.call(declarations, "pr_check", {"diff": "  "})


if __name__ == "__main__":
    unittest.main()
