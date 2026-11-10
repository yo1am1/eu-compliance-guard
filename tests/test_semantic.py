"""Optional semantic ranking: off by default, labelled, never able to break word search.

The fusion and labelling are tested with a tiny fake embedder, so they run without the extra.
The real model is tested only where the `semantic` extra is installed and the model is set up.
"""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from eu_compliance_guard import articles, evaluation, semantic
from eu_compliance_guard.__main__ import main

CATALOGUE = {"act": {
    "Article 1": {"title": "Erasure", "text": "The controller shall erase personal data on request."},
    "Article 2": {"title": "Breach notice", "text": "The controller shall notify the authority of a breach."},
    "Article 3": {"title": "Portability", "text": "The data subject may receive the data in a portable format."},
}}
SYNONYMS = {"zap": "erase", "leak": "breach", "export": "portable"}
AXES = ["erase", "breach", "portable"]


def fake_embed(texts):
    """A unit vector over three meanings; here "zap" means "erase", which word search cannot know."""
    vectors = []
    for text in texts:
        words = ["".join(c for c in word.lower() if c.isalpha()) for word in text.split()]
        words = [SYNONYMS.get(word, word) for word in words]
        counts = [float(sum(word.startswith(axis[:5]) for word in words)) for axis in AXES]
        norm = sum(value * value for value in counts) ** 0.5 or 1.0
        vectors.append([value / norm for value in counts])
    return vectors


def hybrid_index():
    keys = [("act", key) for key in CATALOGUE["act"]]
    return articles.ArticleIndex(CATALOGUE, semantic=semantic.SemanticIndex(CATALOGUE, keys, embed=fake_embed))


class FusionTests(unittest.TestCase):
    def setUp(self):
        # Whatever the caller's settings, these tests start with semantic search not turned on.
        home = tempfile.TemporaryDirectory(prefix="eucg-semantic-")
        self.addCleanup(home.cleanup)
        patcher = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": home.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("EUCG_SEMANTIC", None)

    def test_word_search_is_the_default_and_says_so(self):
        index = articles.ArticleIndex(CATALOGUE)
        self.assertEqual(index.method, "words")
        found = index.suggest("erase personal data")
        self.assertEqual((found[0]["article"], found[0]["via"]), ("Article 1", ["words"]))
        self.assertEqual(index.suggest("zap my account"), [])  # no shared word: word search finds nothing

    def test_the_model_finds_what_shares_no_word_and_each_hit_is_labelled(self):
        index = hybrid_index()
        self.assertEqual(index.method, "words+semantic")
        found = index.suggest("zap my account", top=1)
        self.assertEqual((found[0]["article"], found[0]["via"], found[0]["matched"]), ("Article 1", ["semantic"], []))
        both = index.suggest("notify the authority of a breach", top=1)[0]
        self.assertEqual((both["article"], both["via"]), ("Article 2", ["words", "semantic"]))
        self.assertEqual(articles.via_text(both), "word match + semantic match")
        self.assertEqual(index.suggest("zap my account"), index.suggest("zap my account"))  # deterministic

    def test_fusion_orders_by_both_rankings(self):
        self.assertEqual([position for _, position in semantic.fuse([0, 1, 2], [1, 0, 2])], [0, 1, 2])
        self.assertEqual([position for _, position in semantic.fuse([2], [1, 2, 0])], [2, 1, 0])
        self.assertEqual(semantic.fuse([], []), [])

    def test_long_articles_are_embedded_in_windows_led_by_the_title(self):
        parts = semantic.chunks("Title", " ".join(["word"] * (semantic.CHUNK_WORDS + 5)))
        self.assertEqual(len(parts), 2)
        self.assertTrue(all(part.startswith("Title. ") for part in parts))
        self.assertEqual(semantic.chunks("Title", ""), ["Title. "])

    def test_a_failing_model_never_breaks_suggestions(self):
        with mock.patch.object(semantic, "status", return_value={"active": True}), \
                mock.patch.object(semantic, "SemanticIndex", side_effect=RuntimeError("boom")):
            index = articles.ArticleIndex(CATALOGUE)
        self.assertEqual(index.method, "words")
        self.assertEqual(index.suggest("erase personal data")[0]["article"], "Article 1")

    def test_the_report_names_the_method(self):
        from eu_compliance_guard import view
        self.assertIn("Text search suggestion, not a mapping.", view._suggestions("erase data", articles.ArticleIndex(CATALOGUE)))
        html = view._suggestions("zap my account", hybrid_index())
        self.assertIn("semantic match", html)
        self.assertIn("Word and semantic search suggestion (local model bge-small-en-v1.5), not a mapping.", html)


class SwitchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="eucg-semantic-")
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        patcher = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.home / "config"),
                                               "XDG_CACHE_HOME": str(self.home / "cache"), "HOME": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("EUCG_SEMANTIC", None)

    def test_it_is_off_until_the_user_turns_it_on(self):
        self.assertFalse(semantic.wanted())
        config = self.home / "config/eu-compliance-guard"
        config.mkdir(parents=True)
        (config / "config.json").write_text('{"semantic": true}')
        self.assertTrue(semantic.wanted())
        with mock.patch.dict(os.environ, {"EUCG_SEMANTIC": "off"}):
            self.assertFalse(semantic.wanted())  # the environment wins
        (config / "config.json").write_text('{"semantic": "yes"}')
        self.assertFalse(semantic.wanted())
        with mock.patch.dict(os.environ, {"EUCG_SEMANTIC": "on"}):
            self.assertTrue(semantic.wanted())

    def test_turned_on_without_a_model_stays_word_search_and_says_why(self):
        with mock.patch.dict(os.environ, {"EUCG_SEMANTIC": "on"}):
            report = semantic.status()
            self.assertFalse(report["active"])  # this folder holds no model
            self.assertEqual(articles.ArticleIndex(CATALOGUE).method, "words")
            text = semantic.format_status(report)
        self.assertIn("Semantic search: off", text)
        self.assertTrue("not installed" in text or "semantic setup" in text)

    def test_a_model_with_other_bytes_is_never_used(self):
        folder = semantic.cache_dir() / "models" / semantic.SNAPSHOTS / "revision"
        folder.mkdir(parents=True)
        for name in semantic.FILES:
            (folder / name).write_bytes(b"not the pinned model")
        self.assertIsNone(semantic._snapshot())
        with mock.patch.object(semantic, "installed", return_value=True):
            self.assertEqual(semantic.status()["model"], "wrong digest")

    def test_cli_status_runs_without_the_extra(self):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["semantic", "status", "--json"]), 0)
        self.assertFalse(json.loads(out.getvalue())["active"])


@unittest.skipUnless(semantic.status()["installed"] and semantic.status()["model"] == "ready",
                     "needs the semantic extra and `semantic setup`")
class RealModelTests(unittest.TestCase):
    def test_hybrid_never_falls_below_its_floor_on_the_real_gdpr(self):
        floor = json.loads((evaluation.EVAL_DIR / "baseline.json").read_text())["gdpr_hybrid"]
        with mock.patch.dict(os.environ, {"EUCG_SEMANTIC": "on"}):
            first = evaluation.gdpr(semantic=None)
            second = evaluation.gdpr(semantic=None)
        self.assertEqual(first["method"], "words+semantic")
        self.assertGreaterEqual(first["top1"], floor["top1"])
        self.assertGreaterEqual(first["top3"], floor["top3"])
        self.assertEqual(first, second)

    def test_using_the_model_is_offline(self):
        with mock.patch.dict(os.environ, {"EUCG_SEMANTIC": "on"}), mock.patch.object(semantic, "_loaded", None):
            os.environ.pop("HF_HUB_OFFLINE", None)
            index = articles.ArticleIndex(CATALOGUE)
            self.assertEqual(index.method, "words+semantic")
            index.suggest("zap my account")
            self.assertEqual(os.environ.get("HF_HUB_OFFLINE"), "1")  # loading the model forbids hub requests


if __name__ == "__main__":
    unittest.main()
