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

from bisect import bisect_left, bisect_right

from . import articles, jurisdictions as _jurisdictions

OPEN, CLOSE = "\"“„«", "\"”“»"  # “ closes a German „quotation“
MIN_QUOTE_WORDS = 3  # shorter quotations are usually defined terms, which are not checked
MAX_TEXT = 1_000_000


def _normal(text: str) -> str:
    table = {ord(c): "'" for c in "‘’‚‛"} | {ord(c): '"' for c in "“”„‟«»"}
    return " ".join(text.translate(table).split()).casefold()


# Common names of acts, per jurisdiction (jurisdictions.py). A citation followed by one of these
# names, or by an EU act's number ("Regulation (EU) 2016/679"), is checked in that act.
KNOWN_ACTS = _jurisdictions.EU.known_acts
ACT_WINDOW = 120  # characters after a citation in which an act's name is looked for


def _tokens(text: str) -> list[str]:
    return "".join(char.lower() if char.isalnum() else " " for char in text).split()


def act_names(targets) -> dict[str, list[list[str]]]:
    """Name token sequences per source target: its id, its EU act number and the act's common names."""
    names: dict[str, list[list[str]]] = {}
    declared = set()
    for target in targets:
        found = [_tokens(target.id)]
        version = _jurisdictions.version(target.intended_identifier, target.intended_url)
        if version and version["jurisdiction"] == "UK":
            found += [_tokens(name) for name in _jurisdictions.UK.known_acts.get(version["id"], ())]
            declared.add(version["id"])
        elif version:
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
    for identity, known in _jurisdictions.UK.known_acts.items():
        if identity not in declared:
            names[f"{known[0]} (not declared)"] = [_tokens(name) for name in known]
    return names


INSTRUMENTS = {"Regulation", "Regulations", "Directive", "Decision", "Act", "Code", "Convention", "Treaty", "Order"}
UNRECOGNISED = "an act not recognised"


def _cites_other_act(window: str) -> bool:
    """'Article 9 of the Product Liability Directive', 'Article 4 of Directive (EU) 2019/770': the
    citation names an instrument ("of" within its first words, then a capitalised Regulation,
    Directive, Act, ...) that no declared or known act matched. 'of this Regulation' is not one."""
    words = [word.strip(PUNCTUATION) for word in window.split()][:14]
    if "of" not in words[1:5]:
        return False
    following = words[words.index("of", 1) + 1:]
    for index, word in enumerate(following[:10]):
        if word in INSTRUMENTS:
            return not (index and following[index - 1].lower() in ("this", "that", "the same"))
    return False


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


# Words that cite provisions: singular ones cite one, plural ones a list ("Sections 5 and 6").
CITING = {"article": ("Article", False), "art.": ("Article", False), "art": ("Article", False),
          "articles": ("Article", True), "arts.": ("Article", True),
          "section": ("Section", False), "s.": ("Section", False), "sections": ("Section", True), "ss.": ("Section", True),
          "regulation": ("Regulation", False), "reg.": ("Regulation", False), "regulations": ("Regulation", True),
          "regs.": ("Regulation", True)}
PUNCTUATION = "(),;:.'\"“”"
# Marks that may open a citing word in prose or Markdown: "(Article 5)", "**Art. 5**", "[Article 5]".
LEADING = "([{*_`'\"“‘«„"


def _citations(text: str) -> list[tuple[int, str]]:
    """(position, key) for each 'Article N', 'Art. N', 'section 170', 's. 170', 'regulation 6',
    'reg. 6' or plural list ('Articles N and M') in the text."""
    found, words, position = [], [], 0
    for word in text.split():
        position = text.index(word, position)
        head, dot, rest = word.lstrip(LEADING).partition(".")
        if dot and rest[:1].isdecimal() and (head + dot).lower() in CITING:
            words += [(position, head + dot), (position, rest)]  # "Art.17" reads as "Art. 17"
        else:
            words.append((position, word))
        position += len(word)
    for index, (position, word) in enumerate(words):
        lowered = word.lstrip(LEADING).lower()
        if lowered not in CITING:
            continue
        name, plural = CITING[lowered]
        for _, following in words[index + 1:index + 8]:
            # A plural may name both ends of a range: "Articles 15–22".
            parts = following.replace("–", "-").split("-") if plural else [following]
            keys = [] if following[:1] == "(" else [
                key for part in parts if (key := articles.article_key(f"{name} {part.strip(PUNCTUATION)}"))]
            if not keys:
                if following.lower() in ("and", "or", "to", "&"):
                    continue
                break
            found += [(position, key) for key in keys]
            if not following.endswith(",") and not plural:
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
    at = bisect_right(starts, position)  # starts are sorted: binary search keeps long texts linear
    end = min(position + ACT_WINDOW, starts[at]) if at < len(starts) else position + ACT_WINDOW
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
    named = []
    for position, key in cited:
        window = _window(text, position, starts)
        act = _names_act(window, names) if names else None
        named.append((position, key, UNRECOGNISED if act is None and _cites_other_act(window) else act))
    citations = []
    for _, key, act in named:
        if any(item["article"] == key and item["act"] == act for item in citations):
            continue
        if act == UNRECOGNISED:
            citations.append({"article": key, "act": act, "found_in": [], "ok": False, "reason": "act-not-recognised"})
            continue
        if act is not None and act not in catalogue:
            citations.append({"article": key, "act": act, "found_in": [], "ok": False, "reason": "act-not-retained"})
            continue
        acts = [act] if act is not None and key in catalogue[act] else [] if act is not None else \
            sorted(source for source, items in catalogue.items() if key in items)
        citations.append({"article": key, "act": act, "found_in": acts, "ok": bool(acts)})
    quotations = []
    positions = [at for at, _, _ in named]  # in text order
    for position, quoted in _quotes(text):
        needle = _normal(quoted)
        matches = sorted(f"{source} {key}" for (source, key), body in normal.items() if needle in body)
        last = bisect_left(positions, position) - 1
        attributed, attributed_act = (named[last][1], named[last][2]) if last >= 0 else (None, None)
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
        elif item.get("reason") == "act-not-recognised":
            lines.append(f"- {item['article']}: NOT CHECKED, it cites an act the tool does not recognise; "
                         "declare that act as a source target to check it")
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
