"""Regular expressions: only short anchored validators remain, and the parsers that replaced the
old patterns behave exactly like them. The old patterns live here, in tests only, as the oracle."""
import ast
from pathlib import Path
import random
import re
import unittest

from eu_compliance_guard import articles, grounding, prcheck, revalidation

ROOT = Path(__file__).resolve().parents[1]
# (file, name): the only regexes allowed in shipped Python. Each is an anchored fullmatch
# validator of one short, bounded value, with no nested quantifiers.
ALLOWED = {
    ("eu_compliance_guard/authoring.py", "ID"),
    ("eu_compliance_guard/sources.py", "LANGUAGE"),
    ("eu_compliance_guard/sources.py", "_MEDIA"),
    ("eu_compliance_guard/sources.py", "_CHARSET"),
    ("hooks/eucg_session.py", "SAFE"),
    ("hooks/eucg_session.py", "PROJECT_ID"),
}
ALPHABET = "aZ09 _-./:<>=\"'()\n\r\té١²AbCdEfHTMLlangcode!?x"


def regex_uses(path: Path) -> set[tuple[str, str]]:
    """Every `re.<call>` in a module, named by the module-level assignment that holds it ('?' if none)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    name = path.relative_to(ROOT).as_posix()
    found, named_calls = set(), set()

    def is_re(call) -> bool:
        return (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Name) and call.func.value.id == "re")

    for node in tree.body:
        if isinstance(node, ast.Assign) and is_re(node.value) and isinstance(node.targets[0], ast.Name):
            found.add((name, node.targets[0].id))
            named_calls.add(id(node.value))
    for node in ast.walk(tree):
        if is_re(node) and id(node) not in named_calls:
            found.add((name, "?"))
    return found


def samples(seed: int, count: int = 4000, size: int = 24):
    rng = random.Random(seed)
    return ["".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, size))) for _ in range(count)]


class RegexPolicyTests(unittest.TestCase):
    def test_only_allowed_validators_use_regular_expressions(self):
        files = [*ROOT.glob("eu_compliance_guard/*.py"), *ROOT.glob("hooks/*.py"), *ROOT.glob("scripts/*.py")]
        uses = set().union(*(regex_uses(path) for path in files))
        self.assertLessEqual(uses, ALLOWED, "new regex: replace it with explicit parsing, or justify an anchored validator")

    def test_band_code_has_no_regex_beyond_its_validators(self):
        for path in ROOT.glob("hooks/band/*.ts*"):
            if path.name.endswith(".test.tsx"):
                continue
            text = path.read_text(encoding="utf-8")
            for call in ("new RegExp", ".replace(/", ".match(/", ".split(/", ".search(/"):
                self.assertFalse(call in text, f"{path.name} uses {call}")


class EquivalenceTests(unittest.TestCase):
    def test_identifier_words(self):
        old = re.compile(r"[A-Za-z][a-z]+|[A-Z]+(?![a-z])|[a-z]+|\d+")
        for text in samples(1) + ["setCookie_maxAge2", "HTTPServer", "parseXMLHttp", "ID", "aB", "x1y22"]:
            self.assertEqual(grounding._words(text), old.findall(re.sub(r"[_\-./]", " ", text)), text)

    def test_article_key(self):
        def old(locator):
            match = re.match(r"^\s*(?:Article|Art\.?)\s*(\d+[a-z]?)", locator, re.I)
            return f"Article {match.group(1)}" if match else None
        cases = ["Article 9(2)(a)", "Art. 9", "article 9", "ART 5a", " Article  12B", "Articles 3", "Art.", "Arts 4", "Article x"]
        rng = random.Random(2)
        cases += [rng.choice(["Article", "Art.", "Art", "art", "ARTICLE", "Artic"]) + rng.choice(["", " ", "  "])
                  + rng.choice(["", "5", "12", "١", "3a", "3A", "3é", "7("]) for _ in range(3000)]
        for locator in cases:
            self.assertEqual(articles.article_key(locator), old(locator), locator)

    def test_code_spans(self):
        old = re.compile(r"\(code:[^)]*\)")
        for text in samples(3) + ["Keep (code: a1) data (code:x)", "(code: open", "a(code:)b"]:
            self.assertEqual(articles._without_code_spans(text), old.sub(" ", text), text)

    def test_markdown_code_and_snippets(self):
        for text in samples(4):
            self.assertEqual(prcheck._code(text), re.sub(r"[\r\n]+", " ", text.replace("`", "'")), text)
            self.assertEqual(" ".join(text.replace("`", "'").split()), re.sub(r"\s+", " ", text.replace("`", "'")).strip())

    def test_title_words(self):
        old = re.compile(r"\b(?:login|log in|sign in|challenge|error|403|404|503)\b")
        words = ("login", "log in", "sign in", "challenge", "error", "403", "404", "503")
        rng = random.Random(5)
        cases = ["terrorist attack", "2021/2403", "error 503", "please log in", "signin", "errors", "sign in_x", "_error"]
        cases += ["".join(rng.choice(["error", "log", " ", "in", "_", "4", "403", "x", "/", "sign", "é"]) for _ in range(6))
                  for _ in range(4000)]
        for title in cases:
            self.assertEqual(any(revalidation._has_word(title, word) for word in words), bool(old.search(title)), title)

    def test_markup_detection(self):
        old = re.compile(r"<\s*(?:!doctype|\?xml|[a-z][\w:-]*(?:\s|>|/))", re.I)
        rng = random.Random(6)
        cases = ["<p>x</p>", "a < b", "<!DOCTYPE html>", "< ?xml", "<a", "<a:b-c d", "x<3", "<_a>", "<é>"]
        cases += ["".join(rng.choice(["<", " ", "a", "B", ":", "-", ">", "/", "!doctype", "?xml", "1", "é", "\n"])
                          for _ in range(7)) for _ in range(4000)]
        for text in cases:
            self.assertEqual(revalidation._looks_like_markup(text), bool(old.search(text)), text)

    def test_html_language(self):
        old = re.compile(rb"<html\b[^>]{0,2048}?\blang\s*=\s*[\"']?([A-Za-z]{1,8})", re.I)
        rng = random.Random(7)
        parts = [b"<html", b"<HTML", b" ", b"lang", b"LANG", b"=", b"\"", b"'", b"en", b"de-AT", b">", b"x",
                 b"xml:", b"_", b"\n", b"<htmlx", b"data-lang", b"fr"]
        cases = [b'<html lang="en">', b"<html xml:lang='de'>", b"<html data-lang=fr lang=it>", b"<htmlx lang=en>",
                 b"<html>" + b"x" * 10 + b" lang=en", b"<html " + b"a" * 2050 + b" lang=en>", b"<html lang =  EN>"]
        cases += [b"".join(rng.choice(parts) for _ in range(rng.randint(1, 10))) for _ in range(6000)]
        for head in cases:
            match = old.search(head)
            self.assertEqual(revalidation._html_lang(head), match.group(1).decode().lower() if match else None, head)


if __name__ == "__main__":
    unittest.main()
