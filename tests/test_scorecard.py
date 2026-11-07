"""Review-progress scorecard on synthetic runs: points per meter, never a total or a verdict."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from eu_compliance_guard.notice import LEGAL_NOTICE
from eu_compliance_guard import history as h, models as m, revalidation as r, scorecard as s
from eu_compliance_guard.__main__ import main

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/revalidation-synthetic.json"
SCORECARD_FIXTURE = ROOT / "fixtures/scorecard-synthetic.json"
STAMP = "2026-11-04T00:00:00Z"
BANNED = ("compliant", "compliance score", "certified", "approved", "safe to", "risk score", "grade", "healthy",
          "violation")


def assemble(payload: dict, root: Path = FIXTURE.parent) -> m.RevalidationBundle:
    """A deterministic run of ``payload`` whose files resolve under ``root`` (fixed time and ids)."""
    with tempfile.TemporaryDirectory(prefix="eucg-score-input-") as folder:
        path = Path(folder) / "input.json"
        path.write_text(json.dumps(payload))
        declared = r.load_input(path)
    with r._parent(root / "input.json") as (fd, _):
        observations = r._observe(declared, fd, r.time.monotonic() + 300)
    return r.assemble(declared, observations, input_digest=m.content_digest(json.dumps(payload).encode()),
                      timestamp=STAMP, run_id="run-synthetic", manifest_id="manifest-synthetic")


def synthetic_scorecard() -> bytes:
    """The scorecard of the synthetic fixture, as `view` writes it; the band tests read it."""
    payload = json.loads(FIXTURE.read_bytes())
    declared = r.load_input(FIXTURE)
    with r._parent(FIXTURE) as (fd, _):
        observations = r._observe(declared, fd, r.time.monotonic() + 300)
    bundle = r.assemble(declared, observations, input_digest=m.content_digest(FIXTURE.read_bytes()),
                        timestamp=STAMP, run_id="run-synthetic", manifest_id="manifest-synthetic")
    assert bundle.declarations.model_dump() == m.RevalidationInput.model_validate(payload).model_dump()
    return s.to_json(s.score(bundle))


def banned_words(text: str) -> list[str]:
    lowered = text.replace(m.SCORE_NOTICE, "").lower()
    words = "".join(char if char.isalpha() else " " for char in lowered).split()
    return [word for word in BANNED if word in lowered] + [word for word in ("pass", "passed") if word in words]


def points(card: m.Scorecard) -> list[int | None]:
    return [item.points for item in card.dimensions]


def dimension(card: m.Scorecard, key: str) -> m.ScoreDimension:
    return next(item for item in card.dimensions if item.key == key)


class PointsRuleTests(unittest.TestCase):
    def test_points_are_integer_with_none_and_all_reserved(self):
        for done, total, expected in ((0, 0, None), (0, 3, 0), (1, 3, 3), (2, 3, 6), (3, 3, 10), (1, 11, 1),
                                      (10, 11, 9), (11, 11, 10), (1, 200, 1), (199, 200, 9)):
            with self.subTest(done=done, total=total):
                self.assertEqual(m.review_points(done, total), expected)

    def test_raise_hint_names_the_fewest_items_that_raise_the_points(self):
        self.assertEqual(m.raise_hint(1, 3), (3, 1))
        self.assertEqual(m.raise_hint(0, 0), (None, None))
        self.assertEqual(m.raise_hint(3, 3), (None, None))
        self.assertEqual(m.raise_hint(1, 200), (1, 39))
        self.assertEqual(m.raise_hint(199, 200), (1, 1))
        for total in range(1, 60):
            for done in range(total):
                gained, more = m.raise_hint(done, total)
                self.assertEqual(m.review_points(done + more, total) - m.review_points(done, total), gained)
                if more > 1:
                    self.assertEqual(m.review_points(done + more - 1, total), m.review_points(done, total))


class ScorecardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="eucg-score-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)
        (self.root / "revalidation-synthetic").mkdir()
        for name in ("source.txt", "evidence.txt"):
            (self.root / "revalidation-synthetic" / name).write_bytes((FIXTURE.parent / "revalidation-synthetic" / name).read_bytes())
        self.payload = json.loads(FIXTURE.read_bytes())

    def card(self, previous=None) -> m.Scorecard:
        return s.score(assemble(self.payload, self.root), previous)

    def test_synthetic_fixture_golden_values_and_next_step(self):
        card = self.card()
        self.assertEqual(points(card), [5, 10, 3, 5, 5, 5])
        self.assertEqual(card.status, "in_review")
        self.assertTrue(card.synthetic)
        self.assertIsNone(dimension(card, "alignment").ceiling)
        self.assertEqual((card.next_step.kind, card.next_step.subject, card.next_step.focus),
                         ("mapping", "requirement-unmapped", "mapping"))
        self.assertEqual((card.screening.screened, card.screening.total), (0, 11))
        self.assertEqual([(item.key, item.done, item.total) for item in card.hygiene],
                         [("requirements_located", 0, 2), ("evidence_referenced", 1, 2), ("origins_unchanged", 0, 0)])
        alignment = dimension(card, "alignment")
        self.assertEqual([(item.id, item.reasons) for item in alignment.open_items], [("requirement-unmapped", ["no_mapping"])])
        self.assertEqual((alignment.raise_points, alignment.raise_by), (5, 1))
        facts = dimension(card, "facts")
        self.assertEqual([item.id for item in facts.open_items], ["fact-assumed", "fact-unknown"])
        self.assertEqual(card.assessed_days_before_run, 17)
        self.assertEqual(card.notice, s.NOTICE)

    def test_same_run_gives_byte_identical_output_without_clock_or_environment(self):
        bundle = assemble(self.payload, self.root)

        def refuse(*args, **kwargs):
            raise AssertionError("scoring read the clock")
        with patch.object(time, "time", refuse), patch.object(time, "monotonic", refuse), \
                patch.object(time, "time_ns", refuse), patch.dict(os.environ, {}, clear=True):
            first, second = s.to_json(s.score(bundle)), s.to_json(s.score(bundle))
        self.assertEqual(first, second)
        self.assertEqual(s.format_text(s.score(bundle)), s.format_text(s.score(bundle)))
        self.assertEqual(m.parse_record(m.Scorecard, first), s.score(bundle))

    def test_fixture_file_matches_the_synthetic_run(self):
        # The band tests read this file; it must stay what `view` would write.
        current = synthetic_scorecard()
        if os.environ.get("EUCG_UPDATE_FIXTURES") == "1":
            SCORECARD_FIXTURE.write_bytes(current)
        self.assertEqual(SCORECARD_FIXTURE.read_bytes(), current,
                         "fixtures/scorecard-synthetic.json is stale; rerun with EUCG_UPDATE_FIXTURES=1")

    def test_no_total_or_average_exists_in_the_contract(self):
        fields = set(m.Scorecard.model_fields) | set(m.ScoreDimension.model_fields)
        for word in ("total_points", "sum", "average", "mean", "overall"):
            self.assertFalse([name for name in fields if word in name], word)
        self.assertEqual(len(m.SCORE_KEYS), 6)
        self.assertNotIn("screening", m.SCORE_KEYS)

    def test_technical_methods_set_a_ceiling_and_name_the_tool_limit(self):
        self.payload["obligations"][0]["required_methods"] = ["document", "technical"]
        card = self.card()
        alignment = dimension(card, "alignment")
        self.assertEqual(alignment.points, 0)
        self.assertEqual((alignment.ceiling.points, alignment.ceiling.technical, alignment.ceiling.unconfirmed_sources),
                         (5, 1, 0))
        self.assertIn("technical checks this workflow never runs", s.format_text(card))
        self.assertIn(m.ScoreCount(key="technical_not_run", count=1), dimension(card, "reviews").counts)

    def test_an_offline_real_source_sets_a_ceiling_with_the_fetch_hint(self):
        source, target = self.payload["sources"][0]["source"], self.payload["source_targets"][0]
        source["synthetic"] = False
        for record in (source, target):
            record["type" if record is source else "intended_type"] = "eu_act"
        card = self.card()
        alignment = dimension(card, "alignment")
        self.assertEqual((alignment.ceiling.points, alignment.ceiling.unconfirmed_sources), (5, 1))
        self.assertIn("revalidate --fetch-official", s.format_text(card))
        law = dimension(card, "law_text")
        self.assertEqual(law.points, 0)
        self.assertIn(m.ScoreCount(key="sources_confirmable_by_fetch", count=1), law.counts)
        self.assertEqual(law.reasons, [m.ScoreCount(key="source_review_open", count=2)])

    def test_unmapped_methodless_and_not_applicable_duties_are_blockers_not_ceilings(self):
        self.payload["obligations"][0]["required_methods"] = []
        self.payload["evidence_reviews"] = []
        card = self.card()
        self.assertIsNone(dimension(card, "alignment").ceiling)
        reasons = {item.id: item.reasons for item in dimension(card, "alignment").open_items}
        self.assertEqual(reasons["requirement-unmapped"], ["no_mapping"])
        self.assertIn("no_methods", reasons["requirement-example"])
        self.payload = json.loads(FIXTURE.read_bytes())
        self.payload["applicability_decisions"][0]["applicability"] = "not_applicable"
        reasons = {item.id: item.reasons for item in dimension(self.card(), "alignment").open_items}
        self.assertEqual(reasons["requirement-example"], ["mapped_not_applicable"])
        decisions = dimension(self.card(), "decisions")
        self.assertIn(m.ScoreCount(key="not_applicable", count=1), decisions.counts)

    def test_settling_a_fact_raises_facts(self):
        before = dimension(self.card(), "facts")
        next(item for item in self.payload["scope"]["roles"] if item["id"] == "fact-assumed")["basis"] = "declared"
        after = dimension(self.card(), "facts")
        self.assertEqual((before.points, after.points), (3, 6))
        route = {item.id: item.reasons for item in after.open_items}
        self.assertEqual(route, {"fact-unknown": ["unknown", "ask_owner"]})

    def test_changed_evidence_lowers_facts_and_reviews_and_needs_attention(self):
        next(item for item in self.payload["scope"]["roles"] if item["id"] == "fact-declared")["evidence_ids"] = ["evidence-example"]
        before = self.card()
        (self.root / "revalidation-synthetic/evidence.txt").write_bytes(b"changed after the declaration")
        after = self.card()
        self.assertLess(dimension(after, "facts").points, dimension(before, "facts").points)
        self.assertLess(dimension(after, "reviews").points, dimension(before, "reviews").points)
        self.assertEqual(after.status, "needs_attention")
        self.assertEqual([item.key for item in after.attention], ["evidence_changed"])
        self.assertIn(m.ScoreCount(key="evidence_ready", count=1), dimension(before, "reviews").counts)
        self.assertNotIn("evidence_ready", [item.key for item in dimension(after, "reviews").counts])

    def test_a_recorded_insufficient_review_needs_attention_and_is_named_neutrally(self):
        self.payload["evidence_reviews"][0]["state"] = "insufficient"
        card = self.card()
        self.assertEqual(card.status, "needs_attention")
        self.assertEqual(card.attention, [m.ScoreAttentionCount(key="reviewer_recorded_insufficient", count=2)])
        self.assertIn("a reviewer recorded insufficient evidence ×2", s.format_text(card))

    def test_a_changed_predecessor_dependency_asks_for_re_review_and_a_parent_trend(self):
        state = self.root / "state"
        state.mkdir(mode=0o700)
        path = self.root / "input.json"
        path.write_text(json.dumps(self.payload))
        prior = r.run(path, state / "run-a")
        self.payload["requirements"][0].update(revision=1, statement="FICTIONAL changed requirement")
        path.write_text(json.dumps(self.payload))
        successor = r.run(path, state / "run-b", previous=state / "run-a")
        card = s.score(successor, prior)
        self.assertEqual(card.status, "needs_attention")
        self.assertIn("re_review_after_change", [item.key for item in card.attention])
        reasons = {item.id: item.reasons for item in dimension(card, "alignment").open_items}
        self.assertIn("renew_after_change", reasons["requirement-example"])
        self.assertEqual(dimension(card, "decisions").open_items[0].reasons, ["renew_after_change"])
        self.assertTrue(card.trend.comparable)
        alignment = card.trend.deltas[0]
        self.assertEqual((alignment.points_before, alignment.points_after), (5, 0))
        # The trend is display only: the status is the same with and without it.
        self.assertEqual(s.score(successor).status, card.status)
        self.assertEqual(s.score(successor).model_copy(update={"trend": card.trend}), card)
        unrelated = s.score(prior, successor)
        self.assertEqual((unrelated.trend.comparable, unrelated.trend.reason, unrelated.trend.deltas), (False, "not_parent", []))
        self.assertEqual(unrelated.status, s.score(prior).status)
        self.assertIn("Trend unavailable", s.format_text(unrelated))

    def test_every_shared_phrase_maps_to_a_named_blocker(self):
        phrases = [r.NO_MAPPING_GAP, r.FACT_PINS_MISSING_GAP, r.FACT_OPEN_GAP, r.FACT_EVIDENCE_GAP, r.REQUIREMENT_EVIDENCE_GAP,
                   r.REQUIREMENT_ORIGIN_GAP, r.METHODS_OPEN_GAP, r.MAPPED_NOT_APPLICABLE_GAP, h.RENEW_REQUIREMENT_GAP]
        self.assertEqual(sorted(phrases), sorted(s.REQUIREMENT_BLOCKERS))
        self.assertNotIn("other", s.REQUIREMENT_BLOCKERS.values())
        self.assertEqual(set(s.TAG_LABELS), set(m.SCORE_TAGS))
        self.assertEqual(set(s.LABELS), set(m.SCORE_KEYS))
        self.assertLessEqual(set(r.PIN_GAPS) | {"overlay_open"}, set(m.SCORE_TAGS))

    def test_declarations_without_requirements_are_incomplete(self):
        self.payload["requirements"] = []
        self.payload["evidence_reviews"] = []
        card = self.card()
        self.assertEqual(card.status, "declarations_incomplete")
        self.assertIsNone(dimension(card, "alignment").points)
        self.assertIn("not scored: nothing declared", s.format_text(card))

    def test_rendered_words_avoid_verdict_vocabulary(self):
        texts = [s.format_text(self.card())]
        self.payload["evidence_reviews"][0]["state"] = "insufficient"
        self.payload["obligations"][0]["required_methods"] = ["document", "technical"]
        texts.append(s.format_text(self.card()))
        labels = [*s.TAG_LABELS.values(), *s.LABELS.values(), *s.UNITS.values(), *s.HOW_TO_RAISE.values(),
                  *s.STATUS_LABELS.values(), *s.ATTENTION_LABELS.values(), *s.HYGIENE_LABELS.values()]
        for text in [*texts, *labels]:
            self.assertEqual(banned_words(text), [], text)

    def test_maxima_stay_within_contract_bounds(self):
        requirement = deepcopy(self.payload["requirements"][1])
        obligation = deepcopy(self.payload["obligations"][1])
        self.payload["requirements"] = [{**requirement, "id": f"requirement-{index:03}"} for index in range(200)]
        self.payload["obligations"] = [{**obligation, "id": f"obligation-{index:03}"} for index in range(200)]
        self.payload["applicability_decisions"] = []
        self.payload["evidence_reviews"] = []
        card = self.card()
        for item in card.dimensions:
            self.assertLessEqual(len(item.open_items), m.MAX_OPEN_ITEMS)
        alignment = dimension(card, "alignment")
        self.assertEqual((alignment.done, alignment.total, alignment.open_total, len(alignment.open_items)), (0, 200, 200, 50))
        self.assertEqual(alignment.open_items[0].id, "requirement-000")
        self.assertEqual(m.parse_record(m.Scorecard, s.to_json(card)), card)

    def test_the_contract_refuses_inconsistent_cards(self):
        payload = json.loads(s.to_json(self.card()))
        for change in (
            lambda card: card["dimensions"][0].update(points=6),
            lambda card: card["dimensions"][0].update(done=3),
            lambda card: card["dimensions"].reverse(),
            lambda card: card["dimensions"][0].update(raise_by=2),
            lambda card: card.update(notice="A compliance score."),
            lambda card: card.update(status="steps_closed"),
            lambda card: card.update(status="needs_attention"),
            lambda card: card.update(total=30),
            lambda card: card["next_step"].update(focus="facts"),
            lambda card: card["dimensions"][1].update(ceiling={"points": 5, "technical": 1, "unconfirmed_sources": 0}),
            lambda card: card["dimensions"][2]["open_items"].reverse(),
        ):
            broken = deepcopy(payload)
            change(broken)
            with self.subTest(change=change), self.assertRaises(ValidationError):
                m.parse_record(m.Scorecard, json.dumps(broken))


class ScoreCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="eucg-score-cli-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)
        (self.root / "revalidation-synthetic").mkdir()
        for name in ("source.txt", "evidence.txt"):
            (self.root / "revalidation-synthetic" / name).write_bytes((FIXTURE.parent / "revalidation-synthetic" / name).read_bytes())
        self.input = self.root / "input.json"
        self.input.write_text(FIXTURE.read_text())
        self.state = self.root / "state"
        self.state.mkdir(mode=0o700)

    def cli(self, *argv, state=None):
        out, err = io.StringIO(), io.StringIO()
        with patch("eu_compliance_guard.authoring.state_dir", return_value=state or self.state), \
                redirect_stdout(out), redirect_stderr(err):
            code = main(["score", *argv])
        return code, out.getvalue(), err.getvalue()

    def test_text_and_json_describe_the_newest_run_and_exit_zero_whatever_the_points(self):
        r.run(self.input, self.state / "run-20261025T000000Z")
        newer = r.run(self.input, self.state / "run-20261026T000000Z")
        code, out, err = self.cli()
        self.assertEqual((code, err), (0, ""))
        self.assertIn(f"run {newer.run.id}", out)
        self.assertIn("Alignment  ■■■■■□□□□□  5/10  1 of 2 requirements supported  +5 pts: close 1 more", out)
        self.assertIn("Screening: 0 of 11 families screened (not scored)", out)
        self.assertTrue(out.startswith("FICTIONAL DATA"))
        self.assertTrue(out.rstrip().endswith(m.SCORE_NOTICE + "\n" + LEGAL_NOTICE))
        self.assertEqual(banned_words(out), [])
        code, out, err = self.cli("--json", "--top", "2")
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["run"], str(self.state / "run-20261026T000000Z"))
        card = m.parse_record(m.Scorecard, json.dumps(result["scorecard"]))
        self.assertEqual(points(card), [5, 10, 3, 5, 5, 5])
        self.assertEqual(len(result["steps"]), 2)
        self.assertEqual(result["steps"][0]["kind"], card.next_step.kind)

    def test_against_a_run_that_is_not_the_parent_gives_no_deltas_and_no_error(self):
        older = self.state / "run-20261025T000000Z"
        r.run(self.input, older)
        newer = self.state / "run-20261026T000000Z"
        r.run(self.input, newer)
        code, out, err = self.cli("--run", str(newer), "--against", str(older), "--json")
        self.assertEqual((code, err), (0, ""))
        trend = json.loads(out)["scorecard"]["trend"]
        self.assertEqual((trend["comparable"], trend["reason"], trend["deltas"]), (False, "not_parent", []))
        child = self.state / "run-20261027T000000Z"
        r.run(self.input, child, previous=newer)
        code, out, _ = self.cli("--run", str(child), "--against", str(newer))
        self.assertEqual(code, 0)
        self.assertIn("Since ", out)
        self.assertIn("Alignment 5/10 → 5/10", out)

    def test_missing_and_corrupt_runs_fail_with_fixed_codes(self):
        empty = self.root / "empty"
        empty.mkdir()
        self.assertEqual(self.cli(state=empty), (2, "", "eu-compliance-guard: no-run: score failed\n"))
        run = self.state / "run-20261025T000000Z"
        r.run(self.input, run)
        (run / "report.md").write_text("tampered")
        code, out, err = self.cli("--run", str(run))
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(err, "eu-compliance-guard: corrupt-run: score failed\n")
        code, out, err = self.cli("--run", str(self.root / "nowhere"), "--json")
        self.assertEqual((code, out), (2, ""))
        self.assertTrue(err.startswith("eu-compliance-guard: ") and err.endswith(": score failed\n"))
        self.assertNotIn(str(self.root), err)
        with self.assertRaises(SystemExit) as caught, redirect_stderr(io.StringIO()):
            main(["score", "--top", "0"])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
