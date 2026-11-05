"""The React dashboard's fixed wording is generated from eu_compliance_guard/scorecard.py, never copied."""

import json
import os
from pathlib import Path
import unittest

from eu_compliance_guard import models as m, scorecard as s

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "frontend/src/dashboard/labels.ts"


def labels_source() -> str:
    def table(name: str, values: dict) -> str:
        rows = "".join(f"  {key}: {json.dumps(value, ensure_ascii=False)},\n" for key, value in values.items())
        return f"export const {name} = {{\n{rows}}} as const\n"
    return ("// Generated from eu_compliance_guard/scorecard.py by tests/test_frontend_dashboard.py\n"
            "// (EUCG_UPDATE_FIXTURES=1). Do not edit: the CLI, HTML view and dashboard share these words.\n"
            f"export const NOTICE = {json.dumps(m.SCORE_NOTICE)}\n"
            f"export const MAX_OPEN_ITEMS = {m.MAX_OPEN_ITEMS}\n"
            + "".join(table(name, getattr(s, name)) for name in (
                "LABELS", "UNITS", "HOW_TO_RAISE", "TAG_LABELS", "STATUS_LABELS", "ATTENTION_LABELS",
                "HYGIENE_LABELS", "STEP_TEXT")))


class DashboardWordingTests(unittest.TestCase):
    def test_labels_are_generated_from_the_scorecard_module(self):
        expected = labels_source()
        if os.environ.get("EUCG_UPDATE_FIXTURES") == "1":
            LABELS.write_text(expected, encoding="utf-8")
        self.assertEqual(LABELS.read_text(encoding="utf-8"), expected,
                         "frontend/src/dashboard/labels.ts is stale; rerun with EUCG_UPDATE_FIXTURES=1")

    def test_the_dashboard_makes_no_request_and_injects_no_html(self):
        sources = [path for path in (ROOT / "frontend").glob("src/**/*") if path.is_file()]
        sources += [ROOT / "frontend/index.html", ROOT / "frontend/vite.config.ts"]
        for path in sources:
            if path.name == "contract.ts":
                continue
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource", "dangerouslySetInnerHTML",
                                  "innerHTML", "http://", "https://", "eval(", "new Function"):
                    self.assertNotIn(forbidden, text)
        page = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
        self.assertIn("connect-src 'none'", page)
        self.assertIn("default-src 'none'", page)


if __name__ == "__main__":
    unittest.main()
