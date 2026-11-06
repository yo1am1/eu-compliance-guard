"""Citation guard (2.0 bolt 018): check agent-written text against the retained official text.

Every "Article N" the text cites must exist in an act the latest run retained, and every
quotation must appear in an article word for word (ignoring case, whitespace and the style of
quotation marks). A quotation is checked against the article cited just before it, so a real
sentence attributed to the wrong article is reported too. Passing this check shows only that
the citations and quotations match the retained text; it says nothing about their meaning.
"""
from __future__ import annotations

from . import articles

OPEN, CLOSE = "\"“„«", "\"”“»"  # “ closes a German „quotation“
MIN_QUOTE_WORDS = 3  # shorter quotations are usually defined terms, which are not checked
MAX_TEXT = 1_000_000


def _normal(text: str) -> str:
    table = {ord(c): "'" for c in "‘’‚‛"} | {ord(c): '"' for c in "“”„‟«»"}
    return " ".join(text.translate(table).split()).casefold()


def _citations(text: str) -> list[tuple[int, str]]:
    """(position, 'Article N') for each 'Article N', 'Art. N' or 'Articles N and M' in the text."""
    found, words, position = [], [], 0
    for word in text.split():
        position = text.index(word, position)
        words.append((position, word))
        position += len(word)
    for index, (position, word) in enumerate(words):
        lowered = word.lower()
        if lowered not in ("article", "articles", "art.", "art", "arts."):
            continue
        for _, following in words[index + 1:index + 8]:
            key = articles.article_key("Article " + following.strip("(),;:.'\"“”"))
            if key is None:
                if following.lower() in ("and", "or", "to", "&"):
                    continue
                break
            found.append((position, key))
            if not following.endswith(",") and lowered in ("article", "art.", "art"):
                break
    return found


def _quotes(text: str) -> list[tuple[int, str]]:
    found, start = [], None
    for position, char in enumerate(text):
        if start is None and char in OPEN:
            start = position
        elif start is not None and char in CLOSE:
            quoted = text[start + 1:position]
            if len(quoted.split()) >= MIN_QUOTE_WORDS:
                found.append((start, quoted))
            start = None
        elif start is not None and char == "\n" and text[position + 1:position + 2] == "\n":
            start = None  # a quotation never spans paragraphs; an unmatched mark is ignored
    return found


def check(text: str, catalogue: dict[str, dict[str, dict]]) -> dict:
    text = text[:MAX_TEXT]
    normal = {(source, key): _normal(item["title"] + " " + item["text"])
              for source, acts in catalogue.items() for key, item in acts.items()}
    cited = _citations(text)
    citations = []
    for _, key in cited:
        acts = sorted(source for source, items in catalogue.items() if key in items)
        if not any(item["article"] == key for item in citations):
            citations.append({"article": key, "found_in": acts, "ok": bool(acts)})
    quotations = []
    for position, quoted in _quotes(text):
        needle = _normal(quoted)
        matches = sorted(f"{source} {key}" for (source, key), body in normal.items() if needle in body)
        before = [key for at, key in cited if at < position]
        attributed = before[-1] if before else None
        ok = bool(matches) and (attributed is None or any(match.endswith(" " + attributed) for match in matches))
        shown = " ".join(quoted.split())
        quotations.append({"quote": shown if len(shown) <= 200 else shown[:197] + "...", "attributed_to": attributed,
                           "found_in": matches, "ok": ok})
    return {"acts": sorted(catalogue), "citations": citations, "quotations": quotations,
            "ok": all(item["ok"] for item in citations + quotations)}


def format_check(report: dict) -> str:
    if not report["acts"]:
        return "No retained official text in the latest run: nothing can be checked. Run revalidate with sources first."
    lines = []
    for item in report["citations"]:
        lines.append(f"- {item['article']}: " + (f"exists in {', '.join(item['found_in'])}" if item["ok"]
                                                  else "NOT FOUND in any retained act"))
    for item in report["quotations"]:
        if item["ok"]:
            lines.append(f"- quotation \"{item['quote']}\": verbatim in {', '.join(item['found_in'])}")
        elif item["found_in"]:
            lines.append(f"- quotation \"{item['quote']}\": attributed to {item['attributed_to']}, "
                         f"but it is in {', '.join(item['found_in'])}")
        else:
            lines.append(f"- quotation \"{item['quote']}\": NOT FOUND verbatim in any retained article")
    if not lines:
        lines.append("No article citation or quotation found in the text.")
    lines.append(f"{'All' if report['ok'] else 'Not all'} citations and quotations match the retained text of "
                 f"{', '.join(report['acts'])}. This checks wording only, not legal meaning.")
    return "\n".join(lines)
