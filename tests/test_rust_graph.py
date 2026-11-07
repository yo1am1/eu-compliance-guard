"""Rust in the project graph: a hand-written reader on a fictional crate; nothing is compiled or run."""
from pathlib import Path
import shutil
import tempfile
import unittest

from eu_compliance_guard import graph as g, rust_graph as r

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/eval/graph-project-rust"


class TokenizerTests(unittest.TestCase):
    def test_comments_strings_chars_and_lifetimes_never_become_code(self):
        source = ('/* a /* nested */ fn hidden() {} */ // fn also_hidden()\n'
                  'fn real<\'a>(x: &\'a str) { let s = r#"fn fake() { "q" }"#; let c = \'}\'; let b = b"fn x"; '
                  'let e = \'\\n\'; let r#type = 1; }\n')
        idents = [value for kind, value, _ in r.tokenize(source) if kind == "ident"]
        self.assertNotIn("hidden", idents)
        self.assertNotIn("also_hidden", idents)
        self.assertNotIn("fake", idents)
        self.assertIn("type", idents)  # a raw identifier
        result = r.read_file("src/lib.rs", source)
        self.assertEqual([(item["qualname"], item["line"], item["end_line"]) for item in result["items"]], [("real", 2, 2)])

    def test_items_uses_and_calls(self):
        source = ("use crate::db::{save_user, models::User as U, self};\nuse reqwest::Client;\n"
                  "impl<T> Store for Cache<T> where T: Clone { fn put(&self) { save_user(); Self::evict(); } }\n"
                  "impl Account { fn register(&self) { Client::new().post(\"u\").send(); Ok(()); helper::<u8>(); "
                  "println!(\"x\"); } }\n#[cfg(test)]\nmod tests { fn t() { register(); } }\n"
                  "macro_rules! m { () => { fn not_real() {} }; }\ntrait T { fn a(&self); fn b(&self) { self.a(); } }\n")
        result = r.read_file("src/lib.rs", source)
        self.assertEqual([item["qualname"] for item in result["items"]],
                         ["Cache.put", "Account.register", "T", "T.a", "T.b"])
        self.assertEqual(sorted(result["uses"]), [("Client", ["reqwest"], "Client"), ("U", ["crate", "db", "models"], "User"),
                                                  ("db", ["crate", "db"], ""), ("save_user", ["crate", "db"], "save_user")])
        self.assertEqual(result["calls"], [
            ("Cache.put", None, "save_user", 3), ("Cache.put", "Cache", "evict", 3),
            ("Account.register", "Client", "new", 4), ("Account.register", ".", "post", 4),
            ("Account.register", ".", "send", 4), ("Account.register", None, "helper", 4), ("T.b", ".", "a", 8)])

    def test_module_paths(self):
        self.assertEqual(r.module_path("app/src/lib.rs"), ("app", ()))
        self.assertEqual(r.module_path("app/src/main.rs"), ("app", ()))
        self.assertEqual(r.module_path("app/src/db/mod.rs"), ("app", ("db",)))
        self.assertEqual(r.module_path("app/src/db/models.rs"), ("app", ("db", "models")))
        self.assertEqual(r.module_path("app/src/bin/tool.rs"), ("app/src/bin/tool", ()))


class RustGraphTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="eucg-rust-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "crate"
        shutil.copytree(FIXTURE, self.root)

    def calls(self, graph):
        names = {node.id: f"{node.path}::{node.name}" for node in graph.nodes}
        return {(edge.provenance, names[edge.source], names[edge.target]) for edge in graph.edges if edge.kind == "calls"}

    def test_calls_resolve_through_use_and_mod_and_tests_are_left_out(self):
        graph = g.build_graph(self.root)
        self.assertEqual((graph.files, graph.parsed, graph.skipped), (8, 8, 0))
        self.assertEqual(self.calls(graph), {
            ("extracted", "src/analytics.rs::track", "src/analytics.rs::send_event"),
            ("extracted", "src/billing/mod.rs::Subscription.renew", "src/billing/plans.rs::price_for"),
            ("extracted", "src/coach.rs::plan_meals", "src/models.rs::load_member"),
            ("extracted", "src/coach.rs::plan_meals", "src/llm.rs::ask_model")})
        self.assertFalse([node for node in graph.nodes if node.path.startswith("tests/") and node.kind != "file"])
        self.assertFalse([node for node in graph.nodes if "plans" == node.name])  # the #[cfg(test)] module's test

    def test_data_and_external_crates_make_the_flows(self):
        graph = g.build_graph(self.root)
        by_name = {node.name: node for node in graph.nodes}
        self.assertEqual(by_name["plan_meals"].data, ["special_category"])
        self.assertIn("ai", by_name["ask_model"].concepts)  # through the imported async_openai crate
        self.assertIn("third_party", by_name["send_event"].concepts)  # through reqwest
        flows = {(f["hops"][0]["location"], f["hops"][-1]["location"], f["provenance"]) for f in g.flows(graph)}
        self.assertIn(("src/coach.rs:5", "src/llm.rs:4", "extracted"), flows)
        self.assertIn(("src/analytics.rs:4", "src/analytics.rs:8", "extracted"), flows)

    def test_deterministic_and_separate_from_python(self):
        (self.root / "helper.py").write_text("def ask_model(prompt):\n    return prompt\n\n\ndef caller():\n    ask_model('x')\n")
        first = g.build_graph(self.root)
        self.assertEqual(g.build_graph(self.root).model_dump_json(), first.model_dump_json())
        for provenance, source, target in self.calls(first):
            self.assertEqual(source.split("::")[0].endswith(".py"), target.split("::")[0].endswith(".py"), (source, target))


if __name__ == "__main__":
    unittest.main()
