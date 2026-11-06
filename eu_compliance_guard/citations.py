"""Citation guard (2.0 bolt 018): check agent-written text against the retained official text.

Every "Article N" the text cites must exist in an act the latest run retained, and every
quotation must appear in an article word for word (ignoring case, whitespace and the style of
quotation marks). A quotation is checked against the article cited just before it, so a real
sentence attributed to the wrong article is reported too. A citation followed by an act's
name or number ("Article 17 GDPR", "Article 5(3) of the ePrivacy Directive", "Article 99 of
Regulation (EU) 2016/679") is checked in that act only. Passing this check shows only that
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


# Common names of acts, by the CELEX number of the act as first published. A citation followed by
# one of these names, or by the act's number ("Regulation (EU) 2016/679"), is checked in that act.
KNOWN_ACTS = {
    "32016R0679": ("GDPR", "General Data Protection Regulation"),
    "32024R1689": ("AI Act", "Artificial Intelligence Act"),
    "32002L0058": ("ePrivacy Directive", "ePrivacy", "Directive on privacy and electronic communications"),
    "32022R2065": ("DSA", "Digital Services Act"),
    "32022R1925": ("DMA", "Digital Markets Act"),
    "32023R2854": ("Data Act",),
    "32022L2555": ("NIS2", "NIS 2 Directive"),
    "32024R2847": ("CRA", "Cyber Resilience Act"),
    "32019L0882": ("European Accessibility Act", "EAA"),
    "32011L0083": ("Consumer Rights Directive",),
    "32018R1725": ("EUDPR",),
}
ACT_WINDOW = 120  # characters after a citation in which an act's name is looked for


def _tokens(text: str) -> list[str]:
    return "".join(char.lower() if char.isalnum() else " " for char in text).split()


def act_names(targets) -> dict[str, list[list[str]]]:
    """Name token sequences per source target: its id, its CELEX number and the act's common names."""
    from .sources import celex_version
    names: dict[str, list[list[str]]] = {}
    declared = set()
    for target in targets:
        found = [_tokens(target.id)]
        version = celex_version(target.intended_identifier, target.intended_url)
        if version:
            celex = version["celex"].split("-", 1)[0]
            base = "3" + celex[1:] if celex[0] == "0" else celex
            year, number = base[1:5], base[6:].lstrip("0") if len(base) > 6 else ""
            if number and base[5] in "RLD":
                found.append([year, number])
            found += [_tokens(name) for name in KNOWN_ACTS.get(base, ())]
            declared.add(base)
        names[target.id] = [item for item in found if item]
    # A well-known act the project did not declare is still recognised, so "Article 5 of the DSA" is
    # never checked against another act's Article 5.
    for base, known in KNOWN_ACTS.items():
        if base not in declared:
            names[f"{known[0]} (not declared)"] = [_tokens(name) for name in known] + [[base[1:5], base[6:].lstrip("0")]]
    return names


def _names_act(window: str, names: dict[str, list[list[str]]]) -> str | None:
    """The act whose name appears first in the window, if any."""
    words = _tokens(window)
    best = None
    for act, sequences in names.items():
        for sequence in sequences:
            for at in range(len(words) - len(sequence) + 1):
                if words[at:at + len(sequence)] == sequence:
                    if best is None or at < best[0]:
                        best = (at, act)
                    break
    return best[1] if best else None


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


def _window(text: str, position: int, starts: list[int]) -> str:
    """The text after a citation, up to the next citation, the end of the sentence or ACT_WINDOW characters."""
    following = [start for start in starts if start > position]
    end = min([position + ACT_WINDOW, *following[:1]])
    window = text[position:end]
    for stop in (". ", ";", "\n\n"):
        at = window.find(stop, 12)  # "Art. 5" is not the end of a sentence
        if at != -1:
            window = window[:at]
    return window


def check(text: str, catalogue: dict[str, dict[str, dict]], names: dict[str, list[list[str]]] | None = None) -> dict:
    """Citations and quotations against the retained acts. With `names` (see act_names), a citation
    followed by an act's name or number is checked in that act only."""
    text = text[:MAX_TEXT]
    names = names or {}
    normal = {(source, key): _normal(item["title"] + " " + item["text"])
              for source, acts in catalogue.items() for key, item in acts.items()}
    cited = _citations(text)
    starts = sorted({position for position, _ in cited})
    named = [(position, key, _names_act(_window(text, position, starts), names) if names else None)
             for position, key in cited]
    citations = []
    for _, key, act in named:
        if any(item["article"] == key and item["act"] == act for item in citations):
            continue
        if act is not None and act not in catalogue:
            citations.append({"article": key, "act": act, "found_in": [], "ok": False, "reason": "act-not-retained"})
            continue
        acts = [act] if act is not None and key in catalogue[act] else [] if act is not None else \
            sorted(source for source, items in catalogue.items() if key in items)
        citations.append({"article": key, "act": act, "found_in": acts, "ok": bool(acts)})
    quotations = []
    for position, quoted in _quotes(text):
        needle = _normal(quoted)
        matches = sorted(f"{source} {key}" for (source, key), body in normal.items() if needle in body)
        before = [(key, act) for at, key, act in named if at < position]
        attributed, attributed_act = before[-1] if before else (None, None)
        expected = None if attributed is None else f"{attributed_act} {attributed}" if attributed_act else attributed
        ok = bool(matches) and (expected is None or any(match == expected or (attributed_act is None and
                                                                              match.endswith(" " + attributed))
                                                        for match in matches))
        shown = " ".join(quoted.split())
        quotations.append({"quote": shown if len(shown) <= 200 else shown[:197] + "...", "attributed_to": expected,
                           "found_in": matches, "ok": ok})
    return {"acts": sorted(catalogue), "citations": citations, "quotations": quotations,
            "ok": all(item["ok"] for item in citations + quotations)}


def format_check(report: dict) -> str:
    if not report["acts"]:
        return "No retained official text in the latest run: nothing can be checked. Run revalidate with sources first."
    lines = []
    for item in report["citations"]:
        cited = f"{item['article']} of {item['act']}" if item.get("act") else item["article"]
        if item["ok"]:
            lines.append(f"- {cited}: exists in {', '.join(item['found_in'])}")
        elif item.get("reason") == "act-not-retained":
            lines.append(f"- {cited}: NOT CHECKED, the latest run retained no text of {item['act']}")
        else:
            lines.append(f"- {cited}: NOT FOUND in " + (item["act"] if item.get("act") else "any retained act"))
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
