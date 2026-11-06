"""Seeded fuzzing of every parser that reads untrusted input: none may crash or hang.

Inputs are random mixes of the tokens these parsers look for, mutated fixtures and random
JSON. Expected refusals (each module's own error type) are fine; any other exception fails.
The seed is fixed, so a failure always reproduces.
"""
import io
import json
from pathlib import Path
import random
import unittest

from eu_compliance_guard import articles, citations, imports, mcp_server, prcheck, sources

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
TOKENS = ["Article", "article", "Art.", "Articles", " ", "\n", '"', "“", "”", "„", "«", "»", "(", ")", "1", "9", "12a",
          "and", ",", "\x00", "‮", "é", "<p>", "</p>", '<p class="oj-ti-art">', '<p class="ti-art">', "&amp;",
          "&#0;", "CHAPTER I", "\r", "\t", "{", "}", "[", "]", "@@ -1 +1 @@", "diff --git a/x b/x", "+++ b/x", "+cookie",
          # legislation.gov.uk markup, so the UK parser is fuzzed too
          "legislation.gov.uk", '<a class="LegAnchorID" id="section-170">', '<span class="LegP1No" id="regulation-6">',
          '<h4 class="LegP1Container">', '<span class="LegP1GroupTitle">', '<div class="LegAnnotations">',
          'id="section-Article-17"', 'id="schedule-1"', "</span>", "</h4>", "</div>", "section 5", "s. 12", "reg. 6"]
KEYS = ["cookies", "beacons", "hosts", "requests", "thirdParty", "runs", "tool", "driver", "results", "ruleId", "message",
        "text", "locations", "physicalLocation", "artifactLocation", "uri", "region", "startLine", "rules", "properties",
        "tags", "localStorage", "secure_connection", "unsafeForms", "name", "id", "level"]
EXPECTED = (imports.ImportFailure, mcp_server.ToolError, prcheck.PRCheckError, sources.RetrievalFailure)
CATALOGUE = {"target": {"Article 1": {"title": "Erasure", "text": "The controller shall erase the data."}}}


class FuzzTests(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(20261106)

    def text(self, size=60):
        return "".join(self.rng.choice(TOKENS) for _ in range(self.rng.randint(0, size)))

    def value(self, depth=0):
        roll = self.rng.random()
        if depth > 3 or roll < 0.3:
            return self.rng.choice([None, True, 0, -1, 1.5, "", self.text(8), [], {}])
        if roll < 0.6:
            return [self.value(depth + 1) for _ in range(self.rng.randint(0, 3))]
        return {self.rng.choice(KEYS): self.value(depth + 1) for _ in range(self.rng.randint(0, 4))}

    def mutate(self, text):
        chars = list(text)
        for _ in range(self.rng.randint(1, 12)):
            at = self.rng.randint(0, len(chars))
            if self.rng.random() < 0.5 and chars:
                del chars[min(at, len(chars) - 1)]
            else:
                chars.insert(at, self.rng.choice(TOKENS))
        return "".join(chars)

    def survives(self, call):
        try:
            call()
        except EXPECTED:
            pass

    def test_parsers_never_crash(self):
        wec = (FIXTURES / "imports/wec-synthetic.json").read_text()
        sarif = (FIXTURES / "imports/sarif-synthetic.json").read_text()
        for _ in range(300):
            text = self.text()
            raw = text.encode("utf-8", "surrogatepass")
            self.survives(lambda: articles.article_key(text))
            self.survives(lambda: articles.parse(raw, "text/plain"))
            self.survives(lambda: articles.parse(raw, "text/html"))
            self.survives(lambda: citations.check(text, CATALOGUE))
            self.survives(lambda: prcheck.pr_check(text))
            self.survives(lambda: imports.summarise(json.dumps(self.value()).encode(), "wec"))
            self.survives(lambda: imports.summarise(json.dumps(self.value()).encode(), "sarif"))
            self.survives(lambda: imports.summarise(self.mutate(wec).encode("utf-8", "surrogatepass"), "wec"))
            self.survives(lambda: imports.summarise(self.mutate(sarif).encode("utf-8", "surrogatepass"), "sarif"))

    def test_the_mcp_server_answers_every_line_and_keeps_running(self):
        lines = [json.dumps(self.value()) for _ in range(150)] + [self.text(30).replace("\n", " ") for _ in range(150)]
        lines += [json.dumps({"jsonrpc": "2.0", "id": self.rng.randint(1, 9), "method": "tools/call",
                              "params": {"name": self.rng.choice(["cite_check", "nope"]), "arguments": self.value()}})
                  for _ in range(50)]
        stdout = io.StringIO()
        self.assertEqual(mcp_server.serve("/nonexistent/declarations.json", io.StringIO("\n".join(lines) + "\n"), stdout), 0)
        for line in stdout.getvalue().splitlines():
            json.loads(line, parse_constant=mcp_server._reject_constant)  # every reply is plain JSON


if __name__ == "__main__":
    unittest.main()
