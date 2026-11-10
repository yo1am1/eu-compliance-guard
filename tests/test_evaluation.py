"""The synthetic search evaluation runs offline, deterministically, and never falls below its floor."""
import json
import unittest

from eu_compliance_guard import evaluation as e


class EvaluationTests(unittest.TestCase):
    def test_every_article_of_the_fictional_act_is_parsed(self):
        self.assertEqual(e.evaluate()["articles"], 28)

    def test_scores_never_fall_below_the_recorded_baseline(self):
        result = e.evaluate()
        floor = json.loads((e.EVAL_DIR / "baseline.json").read_text())
        for name in ("articles_tune", "articles_held_out", "grounding", "graph_grounding", "gdpr_words"):
            for metric in ("top1", "top3"):
                self.assertGreaterEqual(result[name][metric], floor[name][metric], f"{name} {metric}")
        self.assertGreaterEqual(result["flows"]["found"], floor["flows"]["found"])
        self.assertLessEqual(len(result["flows"]["unexpected"]), floor["flows"]["unexpected_max"])

    def test_evaluation_is_deterministic_and_says_what_it_measures(self):
        first = e.evaluate()
        self.assertEqual(e.evaluate(), first)
        self.assertIn("not legal correctness", e.format_result(first))


if __name__ == "__main__":
    unittest.main()
