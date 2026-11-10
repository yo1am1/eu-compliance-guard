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


def _score(cases: list[tuple[str, list[str]]], search) -> dict:
    """Top-1 and top-3 hits of `search(label)` (a ranked list) against each case's expected answers."""
    top1 = top3 = 0
    misses = []
    for label, expected in cases:
        found = search(label)
        top1 += bool(found[:1]) and found[0] in expected
        hit = any(item in expected for item in found[:3])
        top3 += hit
        if not hit:
            misses.append(label)
    return {"cases": len(cases), "top1": top1, "top3": top3, "misses": misses}


def _articles(index: articles.ArticleIndex, cases: list[dict]) -> dict:
    return _score([(case["statement"], case["expected"]) for case in cases],
                  lambda statement: [item["article"] for item in index.suggest(statement, top=3)])


def _grounding(project: Path, facts: list[dict]) -> dict:
    code = grounding.build_index(project)
    values = {case["key"]: case["value"] for case in facts}

    def search(key: str) -> list[str]:
        fact = m.Fact(id="fact-eval", revision=0, key=key, value=values[key], basis="assumed", evidence_ids=[],
                      owner="Fictional owner", observed_at="2026-11-05T00:00:00Z", conflicts=[])
        return [item["location"] for item in grounding.search(code, grounding._fact_query(fact), 3)]
    return _score([(case["key"], case["expected"]) for case in facts], search)


def gdpr(directory: Path = EVAL_DIR, semantic=False) -> dict:
    """Ranking on the real GDPR text: word search (semantic=False), or the hybrid when the optional
    model is on and ready (semantic=None). Returns the method actually used."""
    import gzip
    spec = json.loads((directory / "gdpr-v1.json").read_text(encoding="utf-8"))
    act = articles.parse(gzip.decompress((directory / spec["act"]["path"]).read_bytes()), "text/html")
    index = articles.ArticleIndex({spec["act"]["target"]: act}, semantic=semantic)
    return {"method": index.method, **_articles(index, spec["cases"])}


def evaluate(directory: Path = EVAL_DIR) -> dict:
    spec = json.loads((directory / "search-v1.json").read_text(encoding="utf-8"))
    act = articles.parse((directory / spec["act"]["path"]).read_bytes(), "text/plain")
    index = articles.ArticleIndex({spec["act"]["target"]: act}, semantic=False)  # the floor is word search
    result = {"version": spec["version"], "articles": len(act)}
    for split, cases in spec["articles"].items():
        result[f"articles_{split}"] = _articles(index, cases)
    result["grounding"] = _grounding(directory / spec["grounding"]["project"], spec["grounding"]["facts"])
    result["graph_grounding"] = _grounding(directory / spec["graph_grounding"]["project"], spec["graph_grounding"]["facts"])
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
