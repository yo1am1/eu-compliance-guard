"""Search quality on a fixed, versioned synthetic evaluation set (`make eval`).

Article search and code grounding are scored by top-1 and top-3 hits against expected answers.
The set is fictional: it measures ranking changes, not legal correctness. A search change ships
with its before/after numbers, and `fixtures/eval/baseline.json` holds the current floor.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

from . import articles, graph, grounding, models as m

EVAL_DIR = Path(__file__).resolve().parents[1] / "fixtures/eval"


def _hits(found: list[str], expected: list[str]) -> tuple[int, int]:
    return int(bool(found[:1]) and found[0] in expected), int(any(item in expected for item in found[:3]))


def _ground_cases(project: Path, facts: list[dict]) -> dict:
    code = grounding.build_index(project)
    top1 = top3 = 0
    misses = []
    for case in facts:
        fact = m.Fact(id="fact-eval", revision=0, key=case["key"], value=case["value"], basis="assumed",
                      evidence_ids=[], owner="Fictional owner", observed_at="2026-11-05T00:00:00Z", conflicts=[])
        found = [item["location"] for item in grounding.search(code, grounding._fact_query(fact), 3)]
        one, three = _hits(found, case["expected"])
        top1, top3 = top1 + one, top3 + three
        if not three:
            misses.append(case["key"])
    return {"cases": len(facts), "top1": top1, "top3": top3, "misses": misses}


def gdpr(directory: Path = EVAL_DIR, semantic=False) -> dict:
    """Ranking on the real GDPR text: word search (semantic=False), or the hybrid when the optional
    model is on and ready (semantic=None). Returns the method actually used."""
    import gzip
    spec = json.loads((directory / "gdpr-v1.json").read_text(encoding="utf-8"))
    act = articles.parse(gzip.decompress((directory / spec["act"]["path"]).read_bytes()), "text/html")
    index = articles.ArticleIndex({spec["act"]["target"]: act}, semantic=semantic)
    top1 = top3 = 0
    misses = []
    for case in spec["cases"]:
        found = [item["article"] for item in index.suggest(case["statement"], top=3)]
        one, three = _hits(found, case["expected"])
        top1, top3 = top1 + one, top3 + three
        if not three:
            misses.append(case["statement"])
    return {"method": index.method, "cases": len(spec["cases"]), "top1": top1, "top3": top3, "misses": misses}


def evaluate(directory: Path = EVAL_DIR) -> dict:
    spec = json.loads((directory / "search-v1.json").read_text(encoding="utf-8"))
    act = articles.parse((directory / spec["act"]["path"]).read_bytes(), "text/plain")
    index = articles.ArticleIndex({spec["act"]["target"]: act}, semantic=False)  # the floor is word search
    result = {"version": spec["version"], "articles": len(act)}
    for split, cases in spec["articles"].items():
        top1 = top3 = 0
        misses = []
        for case in cases:
            found = [item["article"] for item in index.suggest(case["statement"], top=3)]
            one, three = _hits(found, case["expected"])
            top1, top3 = top1 + one, top3 + three
            if not three:
                misses.append(case["statement"])
        result[f"articles_{split}"] = {"cases": len(cases), "top1": top1, "top3": top3, "misses": misses}
    code = grounding.build_index(directory / spec["grounding"]["project"])
    top1 = top3 = 0
    misses = []
    for case in spec["grounding"]["facts"]:
        fact = m.Fact(id="fact-eval", revision=0, key=case["key"], value=case["value"], basis="assumed",
                      evidence_ids=[], owner="Fictional owner", observed_at="2026-11-05T00:00:00Z", conflicts=[])
        found = [item["location"] for item in grounding.search(code, grounding._fact_query(fact), 3)]
        one, three = _hits(found, case["expected"])
        top1, top3 = top1 + one, top3 + three
        if not three:
            misses.append(case["key"])
    result["grounding"] = {"cases": len(spec["grounding"]["facts"]), "top1": top1, "top3": top3, "misses": misses}
    result["graph_grounding"] = _ground_cases(directory / spec["graph_grounding"]["project"], spec["graph_grounding"]["facts"])
    found = {(flow["hops"][0]["location"], flow["hops"][-1]["location"])
             for flow in graph.flows(graph.build_graph(directory / spec["flows"]["project"]))}
    expected = {tuple(item) for item in spec["flows"]["expected"]}
    result["flows"] = {"expected": len(expected), "found": len(found & expected), "unexpected": sorted(found - expected)}
    result["gdpr_words"] = gdpr(directory)
    return result


def format_result(result: dict) -> str:
    lines = [f"Search evaluation v{result['version']} (synthetic sets and the real GDPR text; ranking quality, "
             "not legal correctness)"]
    for name in ("articles_tune", "articles_held_out", "grounding", "graph_grounding", "gdpr_words", "gdpr_hybrid"):
        if name not in result:
            continue
        item = result[name]
        lines.append(f"{name:<18} top-1 {item['top1']:>2}/{item['cases']}  top-3 {item['top3']:>2}/{item['cases']}")
        lines += [f"  miss: {miss}" for miss in item["misses"]]
    flows = result["flows"]
    lines.append(f"{'flows':<18} found {flows['found']}/{flows['expected']}  unexpected {len(flows['unexpected'])}")
    lines += [f"  unexpected: {start} → {end}" for start, end in flows["unexpected"]]
    return "\n".join(lines)


if __name__ == "__main__":
    outcome = evaluate()
    hybrid = gdpr(semantic=None)  # measured only when the optional model is on and ready
    if hybrid["method"] != "words":
        outcome["gdpr_hybrid"] = hybrid
    print(format_result(outcome))
    sys.exit(0)
