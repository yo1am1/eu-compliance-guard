"""Project graph: static parsing of a fictional multi-file project; nothing is imported or run."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from typing import get_args

from pydantic import ValidationError

from eu_compliance_guard import authoring as a, graph as g, grounding, models as m
from eu_compliance_guard.__main__ import main
from eu_compliance_guard.notice import LEGAL_NOTICE

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/eval/graph-project"


def named(graph: m.ProjectGraph) -> dict[str, str]:
    return {node.id: f"{node.path}::{node.name}" for node in graph.nodes}


def calls(graph: m.ProjectGraph) -> set[tuple[str, str, str]]:
    names = named(graph)
    return {(edge.provenance, names[edge.source], names[edge.target]) for edge in graph.edges if edge.kind == "calls"}


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="eucg-graph-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "project"
        shutil.copytree(FIXTURE, self.root)

    def test_concepts_match_the_grounding_vocabulary(self):
        self.assertEqual(set(get_args(m.GraphConcept)), set(grounding.CONCEPTS))

    def test_calls_resolve_like_python_and_ambiguity_is_labelled(self):
        graph = g.build_graph(self.root)
        self.assertEqual((graph.files, graph.parsed, graph.skipped), (9, 8, 1))  # broken.py does not parse
        found = calls(graph)
        for expected in [("extracted", "app/coach.py::plan_meals", "app/llm.py::ask_model"),
                         ("extracted", "app/coach.py::plan_meals", "app/models.py::load_member"),
                         ("extracted", "app/analytics.py::track", "app/storage.py::save"),
                         ("extracted", "app/billing.py::renew", "app/billing.py::save"),
                         ("ambiguous", "app/jobs.py::nightly", "app/storage.py::save"),
                         ("ambiguous", "app/jobs.py::nightly", "app/billing.py::save")]:
            self.assertIn(expected, found)
        self.assertNotIn(("ambiguous", "app/analytics.py::track", "app/billing.py::save"), found)
        names = named(graph)
        imports = {(names[edge.source], names[edge.target]) for edge in graph.edges if edge.kind == "imports"}
        self.assertIn(("app/coach.py::app/coach.py", "app/llm.py::app/llm.py"), imports)  # relative import
        self.assertIn(("app/analytics.py::app/analytics.py", "app/storage.py::app/storage.py"), imports)
        concepts = {f"{node.path}::{node.name}": node.concepts for node in graph.nodes}
        self.assertEqual(concepts["app/llm.py::ask_model"], ["ai"])
        self.assertIn("tracking", concepts["app/analytics.py::track"])

    def test_graph_is_byte_identical_wherever_the_project_lives(self):
        first = g.to_json(g.build_graph(self.root))
        self.assertEqual(g.to_json(g.build_graph(self.root)), first)
        moved = Path(self.temporary.name) / "elsewhere"
        shutil.copytree(self.root, moved)
        self.assertEqual(g.to_json(g.build_graph(moved)), first)
        self.assertEqual(m.parse_record(m.ProjectGraph, first), g.build_graph(self.root))

    def test_project_code_is_never_run_and_links_and_dependencies_are_never_read(self):
        marker = Path(self.temporary.name) / "RAN"
        (self.root / "app/side_effect.py").write_text(f"open({str(marker)!r}, 'w').write('x')\nimport os\nos.system('true')\n")
        (self.root / "app/linked.py").symlink_to(self.root / "app/coach.py")
        (self.root / "node_modules/pkg").mkdir(parents=True)
        (self.root / "node_modules/pkg/index.py").write_text("def hidden():\n    pass\n")
        graph = g.build_graph(self.root)
        self.assertFalse(marker.exists())
        paths = {node.path for node in graph.nodes}
        self.assertIn("app/side_effect.py", paths)
        self.assertNotIn("app/linked.py", paths)
        self.assertFalse(any(path.startswith("node_modules") for path in paths))

    def test_flows_run_from_data_to_the_first_sink_with_every_hop_located(self):
        flows = g.flows(g.build_graph(self.root))
        self.assertEqual([g.describe_flow(flow) for flow in flows],
                         ["special_category → ai: app/coach.py:5 plan_meals → app/llm.py:1 ask_model (extracted)"])
        self.assertTrue(g.covers(flows[0], {"app/llm.py:2"}))  # inside ask_model's lines
        self.assertFalse(g.covers(flows[0], {"app/llm.py:5", "app/coach.py:1"}))

    def test_ground_shows_paths_and_a_pinned_line_covers_its_flow(self):
        declarations = a.init(self.root / ".eu-compliance-guard/declarations.json", "demo", synthetic=True)
        data = json.loads(declarations.read_text())
        data["scope"]["roles"] = [{"id": "fact-weight-llm", "revision": 0, "key": "Member weight is sent to the model",
                                   "value": True, "basis": "assumed", "evidence_ids": [], "owner": "Fictional owner",
                                   "observed_at": "2026-11-05T00:00:00Z", "conflicts": []}]
        declarations.write_text(json.dumps(data))
        report = grounding.ground(declarations)
        top = report["facts"][0]["candidates"][0]
        self.assertEqual(top["location"], "app/coach.py:7")
        self.assertEqual([hop["name"] for hop in top["path"]], ["plan_meals", "ask_model"])
        self.assertEqual([flow["covered"] for flow in report["flows"]], [False])
        self.assertIn("data flows no fact covers", grounding.format_ground(report))
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(["ground", "--input", str(declarations), "--apply", "fact-weight-llm=app/coach.py:7"]), 0)
        report = grounding.ground(declarations)
        self.assertEqual([flow["covered"] for flow in report["flows"]], [True])
        self.assertNotIn("data flows no fact covers", grounding.format_ground(report))

    def test_pr_check_names_the_flows_a_diff_changes_and_the_facts_on_them(self):
        declarations = a.init(self.root / ".eu-compliance-guard/declarations.json", "demo", synthetic=True)
        data = json.loads(declarations.read_text())
        data["scope"]["roles"] = [{"id": "fact-weight-llm", "revision": 0, "key": "Member weight is sent to the model",
                                   "value": True, "basis": "assumed", "evidence_ids": [], "owner": "Fictional owner",
                                   "observed_at": "2026-11-05T00:00:00Z", "conflicts": []}]
        declarations.write_text(json.dumps(data))
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(["ground", "--input", str(declarations), "--apply", "fact-weight-llm=app/coach.py:7"]), 0)
        diff = self.root / "change.diff"

        def check(text: str) -> dict:
            diff.write_text(text)
            stdout = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                self.assertIn(main(["pr-check", "--diff", str(diff), "--input", str(declarations), "--json"]), (0, 1))
            return json.loads(stdout.getvalue())

        report = check("diff --git a/app/llm.py b/app/llm.py\n--- a/app/llm.py\n+++ b/app/llm.py\n"
                       "@@ -2,0 +2,1 @@\n+    prompt = prompt.strip()\n")
        self.assertEqual(report["flows"], [{"flow": "special_category → ai: app/coach.py:5 plan_meals → app/llm.py:1 ask_model (extracted)",
                                            "changed": ["app/llm.py:2"], "facts": ["fact-weight-llm"]}])
        self.assertGreaterEqual(report["attention"], 1)
        report = check("diff --git a/app/billing.py b/app/billing.py\n--- a/app/billing.py\n+++ b/app/billing.py\n"
                       "@@ -2,0 +2,1 @@\n+    pass\n")
        self.assertEqual(report["flows"], [])
        self.assertTrue(report["graph"])

    def test_the_contract_rejects_dangling_or_unsorted_edges(self):
        graph = g.build_graph(self.root)
        data = graph.model_dump(mode="json")
        data["edges"][0]["target"] = "node-missing"
        with self.assertRaises(ValidationError):
            m.ProjectGraph.model_validate(data)
        data = graph.model_dump(mode="json")
        data["nodes"].reverse()
        with self.assertRaises(ValidationError):
            m.ProjectGraph.model_validate(data)

    def test_cli_maps_the_files_root_without_the_declarations(self):
        declarations = a.init(self.root / ".eu-compliance-guard/declarations.json", "demo", synthetic=True)
        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            self.assertEqual(main(["graph", "--input", str(declarations), "--json"]), 0)
        graph = m.parse_record(m.ProjectGraph, stdout.getvalue())
        self.assertNotIn(".eu-compliance-guard", json.dumps([node.path for node in graph.nodes]))
        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            self.assertEqual(main(["graph", "--input", str(declarations)]), 0)
        self.assertIn("possible paths", stdout.getvalue())
        self.assertTrue(stdout.getvalue().rstrip().endswith(LEGAL_NOTICE))
        stderr = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            self.assertEqual(main(["graph", "--input", str(self.root / "missing.json")]), 2)
        self.assertIn(": graph failed", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
