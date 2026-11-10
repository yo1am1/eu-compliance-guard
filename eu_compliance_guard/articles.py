"""Split retained legal-act text into articles and suggest articles for a statement.

Official Journal XHTML marks each article with `oj-ti-art` (number) and `oj-sti-art`
(title); older EUR-Lex HTML uses `ti-art`/`sti-art`. Unmarked pages and plain-text lines
fall back to paragraphs that read "Article N". The text is shown as an unreviewed
candidate next to a declared provision; a suggestion is a search result, never a mapping
or a legal conclusion.
"""
from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser
import itertools
import math

from .grounding import tokens

MAX_ARTICLES = 2000
MAX_ARTICLE_CHARS = 20000
MAX_PARAGRAPHS = 50000
MAX_PAGE_CHARS = 8 * 1024 * 1024
BREAKS = frozenset({"p", "div", "td", "li", "tr", "br", "h1", "h2", "h3", "h4", "table"})
# Code, styling, fallback content and site navigation of a saved page are never legal text.
SKIPPED = frozenset({"script", "style", "noscript", "template", "nav", "footer"})
# Words that describe the project or the task rather than the legal subject matter.
NOISE = frozenset({"code", "app", "py", "ts", "js", "determine", "decide", "whether", "currently", "define", "declare",
                   "document", "put", "place", "give", "provide", "users", "user", "customer", "customers"})

# Plain engineering words -> the vocabulary legal acts use for the same idea.
LEGAL_TERMS = {
    "delete": "erasure erase", "deletion": "erasure erase", "remove": "erasure erase",
    "export": "portability", "download": "portability access",
    "inform": "information transparent", "tell": "information transparent", "notice": "information transparent",
    "privacy": "information transparent", "signup": "information collected", "sign": "information collected",
    "vendor": "processor behalf", "provider": "processor behalf", "supplier": "processor behalf",
    "subprocessor": "processor", "contract": "processor contract", "dpa": "processor contract",
    "kid": "child", "kids": "child", "minor": "child", "minors": "child", "age": "child", "teen": "child",
    "breach": "breach notification", "hack": "breach security", "leak": "breach security",
    "encrypt": "security encryption", "encryption": "security encryption",
    "health": "health special categories", "weight": "health special categories",
    "cookie": "terminal equipment consent", "tracking": "terminal equipment consent",
    "recommend": "profiling automated", "score": "profiling automated", "personalise": "profiling",
    "abroad": "transfers third country", "transfer": "transfers third country",
    "retention": "storage limitation", "keep": "storage limitation", "log": "records processing",
    "parent": "parental responsibility child", "approval": "consent authorised", "approve": "consent authorised",
    "correct": "rectification inaccurate", "wrong": "inaccurate rectification", "incorrect": "inaccurate rectification",
}
TITLE_WEIGHT = 1.0
SUFFIXES = ("ations", "ation", "ings", "ing", "ies", "ed", "es", "s")


class _Paragraphs(HTMLParser):
    """Flatten a page into (classes, text) paragraphs; text outside <p> joins the next break."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paragraphs: list[tuple[tuple[str, ...], str]] = []
        self.classes: tuple[str, ...] = ()
        self.buffer: list[str] = []
        self.size = 0
        self.skipped = 0  # depth inside SKIPPED elements

    def _flush(self):
        text = _tidy("".join(self.buffer))
        if text and len(self.paragraphs) < MAX_PARAGRAPHS:
            self.paragraphs.append((self.classes, text))
        self.classes, self.buffer = (), []

    def handle_starttag(self, tag, attrs):
        if tag in SKIPPED:
            self.skipped += 1
        if tag in BREAKS:
            self._flush()
            if tag == "p":
                self.classes = tuple((dict(attrs).get("class") or "").split())

    def handle_endtag(self, tag):
        if tag in SKIPPED and self.skipped:
            self.skipped -= 1
        if tag in BREAKS:
            self._flush()

    def handle_data(self, data):
        if not self.skipped and self.size < MAX_PAGE_CHARS:
            self.buffer.append(data)
            self.size += len(data)


def _is_number(classes) -> bool:
    return any(name.endswith("ti-art") and not name.endswith("sti-art") for name in classes)


def _is_title(classes) -> bool:
    return any(name.endswith("sti-art") for name in classes)


def _numeral(word: str) -> bool:
    """'12', 'XIV', or an inserted '10a' / 'IIIa'."""
    if len(word) > 1 and "a" <= word[-1] <= "z":
        word = word[:-1]
    return word.isascii() and (word.isdigit() or not word.strip("IVXLC"))


def _article_number(text: str) -> str | None:
    """'Article 5' -> '5', 'Article 10a' -> '10a'; any other paragraph is not an article heading.

    "Article 6(1) applies" is a reference, and "‘Article 6a" is another act's article quoted by an amendment.
    """
    words = text.split()
    if len(words) != 2 or words[0].lower() != "article":
        return None
    number = words[1]
    digits = number[:-1] if len(number) > 1 and number[-1].isascii() and number[-1].isalpha() else number
    return number if digits.isascii() and digits.isdigit() else None


# An amending act quotes the text it inserts: "‘ANNEX IIIa" or "‘CHAPTER IIa" stays in the amending article.
OPENING_QUOTES = ("‘", "“", "\"", "'", "«", "„")


def _is_end(classes, text: str) -> bool:
    """An annex heading or "Done at …" closes the last article.

    Upper-case "ANNEX" headings only: body text such as "Annex III shall apply" stays in its article.
    """
    if text.startswith(OPENING_QUOTES):
        return False
    if any(name.endswith("doc-ti") for name in classes) or text[:7] == "Done at" and not text[7:8].isalnum():
        return True
    words = text.split()
    return words[:1] == ["ANNEX"] and (len(words) == 1 or len(words) == 2 and _numeral(words[1]))


# Headings of the divisions above articles: "CHAPTER III", "Section 2", "TITLE IIa", "PART 1".
DIVISIONS = frozenset({"CHAPTER", "Chapter", "TITLE", "Title", "PART", "Part", "SECTION", "Section"})


def _is_division(classes, text: str, marked: bool) -> bool:
    """A chapter, title, part or section heading closes the article before it.

    Marked pages say so by class (`oj-ti-section-1`, consolidated `title-division-1`); elsewhere the
    paragraph must read just like "CHAPTER III". The division's own name then falls outside any article.
    """
    if text.startswith(OPENING_QUOTES):
        return False
    if any("ti-section-" in name or name.startswith("title-division") for name in classes):
        return True
    words = text.split()
    return not marked and len(words) == 2 and words[0] in DIVISIONS and _numeral(words[1])


def _follows(number: str, previous: str | None) -> bool:
    """'2' follows '1', and '1a' or '1b' follows '1': the next heading of the same enacting terms."""
    def split(value: str) -> tuple[int, str]:
        letter = value[-1] if value[-1].isalpha() else ""
        return int(value[:len(value) - len(letter)]), letter

    if previous is None:
        return False
    (count, letter), (last, last_letter) = split(number), split(previous)
    return count == last + 1 and not letter or count == last and letter > last_letter


def _segment(paragraphs) -> dict[str, dict]:
    """Class-marked articles when the page has them, else paragraphs that read exactly "Article N".

    Only a paragraph that is just "Article N" opens an article. A marked heading that is not, such as
    an amendment's quoted "‘Article 6a", stays text of the amending article. An annex heading or
    closing formula after article text ends the enacting terms unless the very next article heading
    continues their numbering: a later correlation table or annexed agreement, which repeats or
    jumps numbers, opens nothing. A number seen twice (a contents list, then the body) keeps the
    occurrence with the most text, the first one on a tie.
    """
    marked = any(_is_number(classes) for classes, _ in paragraphs)
    found: dict[str, dict] = {}
    current = previous = repeat = None  # repeat: the key a later occurrence of a number may take over
    expect_title = wrote = ended = final = False
    for classes, text in paragraphs:
        if _is_end(classes, text):
            current, expect_title, ended = None, False, ended or wrote  # annexes belong to no article
            continue
        if _is_division(classes, text, marked):
            current, expect_title = None, False  # nor do chapter and section headings
            continue
        number = _article_number(text) if _is_number(classes) or not marked else None
        if number is not None:
            key = f"Article {number}"
            current = None
            if ended and not final:
                # The first heading after an end decides: the next number means the end was a stray marker.
                ended = key in found or not _follows(number, previous)
                final = ended
            repeat = key if key in found else None
            if not final and (repeat or len(found) < MAX_ARTICLES):
                current = {"title": "", "text": ""}
                found.setdefault(key, current)
                previous = number
            expect_title = True
            continue
        if current is None:
            continue
        if expect_title and (_is_title(classes) if marked else len(text) <= 200 and not text[0].isdigit()):
            current["title"] = text
        elif len(current["text"]) < MAX_ARTICLE_CHARS:
            current["text"] += " " + text
            wrote = True
            if repeat is not None and len(current["text"]) > len(found[repeat]["text"]):
                found[repeat] = current  # keep only the best occurrence, so repeats cost no memory
        expect_title = False
    return found


# legislation.gov.uk XHTML (2.2): a provision starts at an element whose id names it
# ("section-170", "regulation-6", "section-Article-17" or "article-17"); its title is in a
# `LegP1GroupTitle` element just before or after. Amendment notes, extent labels and footnote
# markers are not the provision's text.
UK_SKIPPED_CLASSES = frozenset({"LegAnnotations", "LegCommentaryItem", "LegExtentRestriction", "LegCommentaryLink",
                                "LegChangeDelimiter", "LegP1No", "LegFootnoteRef", "LegAnchorID", "LegClearPblock"})
UK_TITLE_CLASSES = frozenset({"LegP1GroupTitle", "LegP1GroupTitleFirst"})
UK_ENDS = ("schedule-", "part-", "chapter-", "crossheading-", "signature", "annex-")
VOID = frozenset({"br", "img", "hr", "meta", "link", "input", "col", "area", "base", "wbr", "source"})


def _uk_provision(identity: str) -> str | None:
    """'section-170' -> 'Section 170', 'regulation-6' -> 'Regulation 6', 'section-Article-17' or
    'article-17' -> 'Article 17'; sub-paragraph ids ('regulation-6-2-a') are not provisions."""
    parts = identity.split("-")
    if len(parts) == 3 and parts[0] == "section" and parts[1] == "Article":
        parts = ["article", parts[2]]
    if len(parts) != 2 or parts[0] not in ("section", "regulation", "article"):
        return None
    return article_key(f"{parts[0]} {parts[1]}") if parts[1][:1].isdecimal() else None


def _ends_provisions(identity: str) -> bool:
    """'schedule-1', 'part-2', 'annex-I' and the like start a division that is not a provision."""
    for prefix in UK_ENDS:
        if identity.startswith(prefix):
            return "-" not in identity[len(prefix):]
    return False


class _LegislationUk(HTMLParser):
    """Provisions of one legislation.gov.uk XHTML page, in order, with their titles and text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.found: dict[str, dict] = {}
        self.current: str | None = None
        self.stack: list[tuple[str, bool, bool]] = []  # tag, skipping, in a title
        self.open: dict[str, list[int]] = {}  # tag -> stack positions where it is open, so end tags are found in O(1)
        self.pending_title: list[str] = []
        self.title_parts: list[str] | None = None
        self.size = 0

    def _skipping(self) -> bool:
        return bool(self.stack) and self.stack[-1][1]

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        identity = values.get("id") or ""
        if _ends_provisions(identity):
            self.current = None  # a schedule, part or annex begins: no provision continues into it
        key = _uk_provision(identity) if identity else None
        if key and key not in self.found and len(self.found) < MAX_ARTICLES:
            self.current = key
            self.found[key] = {"title": " ".join(" ".join(self.pending_title).split()), "text": []}
            self.pending_title = []
        in_title = bool(classes & UK_TITLE_CLASSES) or (bool(self.stack) and self.stack[-1][2])
        if classes & UK_TITLE_CLASSES and not (self.stack and self.stack[-1][2]):
            self.title_parts = []
        skipping = self._skipping() or bool(classes & UK_SKIPPED_CLASSES) or tag in SKIPPED
        if tag not in VOID:
            self.open.setdefault(tag, []).append(len(self.stack))
            self.stack.append((tag, skipping, in_title))
        if self.current and not skipping and not in_title and (tag in BREAKS or "LegRHS" in classes):
            # A paragraph, or the text column beside a number label: "(1) It is", never "(1)It is".
            self.found[self.current]["text"].append("\n" if tag in BREAKS else " ")

    def handle_endtag(self, tag):
        positions = self.open.get(tag)
        if not positions:
            return  # an end tag with no open start tag is ignored
        index = positions[-1]
        closing_title = self.stack[index][2] and (index == 0 or not self.stack[index - 1][2])
        for name, _, _ in self.stack[index:]:
            self.open[name].pop()  # each closed tag is the last open one of its name
        del self.stack[index:]
        if closing_title and self.title_parts is not None:
            title = " ".join(" ".join(self.title_parts).split())
            self.title_parts = None
            item = self.found.get(self.current) if self.current else None
            # A title right after the anchor names this provision. Any other title starts the
            # next provision: the current one ends, and the title waits for the next anchor.
            if item is not None and not item["title"] and not "".join(item["text"]).strip():
                item["title"] = title
            else:
                self.pending_title = [title]
                self.current = None

    def handle_data(self, data):
        if self._skipping():
            return
        self.size += len(data)
        if self.size > MAX_PAGE_CHARS:
            raise ValueError("page too large")
        if self.stack and self.stack[-1][2]:
            if self.title_parts is not None:
                self.title_parts.append(data)
            return
        if self.current:
            self.found[self.current]["text"].append(data)
        elif data.strip():
            # Text before any anchor belongs to a provision without one (a prospective insertion,
            # for example): its title must not be given to the next provision.
            self.pending_title = []


def _is_legislation_uk(text: str) -> bool:
    head = text[:200000]
    return "legislation.gov.uk" in head and "LegP1" in text


def _tidy(text: str) -> str:
    return " ".join(text.split())


def parse(content: bytes, media_type: str) -> dict[str, dict]:
    """Map "Article N" to {"title", "text"}; empty when the format is not supported."""
    try:
        text = content.decode("utf-8-sig")  # a leading byte order mark is not part of the first line
    except UnicodeDecodeError:
        return {}
    media_type = media_type.lower()  # media types are case-insensitive; admission accepts any case
    if media_type in ("text/html", "application/xhtml+xml") and _is_legislation_uk(text):
        uk = _LegislationUk()
        try:
            uk.feed(text)
            uk.close()
        except (AssertionError, ValueError):
            return {}
        return {key: {"title": item["title"], "text": _tidy("".join(item["text"]))[:MAX_ARTICLE_CHARS]}
                for key, item in uk.found.items() if "".join(item["text"]).strip()}
    if media_type in ("text/html", "application/xhtml+xml"):
        parser = _Paragraphs()
        try:
            parser.feed(text)
            parser.close()
        except (AssertionError, ValueError):
            return {}
        parser._flush()
        paragraphs = parser.paragraphs
    elif media_type == "text/plain":
        # Each non-blank line is a paragraph of an unmarked page, so both follow the same rules.
        lines = (line for line in map(_tidy, text.splitlines()) if line)
        paragraphs = [((), line) for line in itertools.islice(lines, MAX_PARAGRAPHS)]
    else:
        return {}
    return {key: {"title": item["title"], "text": _tidy(item["text"])[:MAX_ARTICLE_CHARS]}
            for key, item in _segment(paragraphs).items()}


# Provision words and their canonical names: EU articles, UK sections (Acts) and regulations
# (statutory instruments). A locator names one provision, so plurals are not keys; the citation
# guard expands "Articles 5 and 6" itself.
PROVISION_WORDS = (("article", "Article"), ("art.", "Article"), ("art", "Article"), ("section", "Section"),
                   ("s.", "Section"), ("regulation", "Regulation"), ("reg.", "Regulation"))


def article_key(locator: str) -> str | None:
    """A provision's canonical key: 'Article 9(2)(a)', 'Art. 9' -> 'Article 9'; 'section 170(1)',
    's. 170' -> 'Section 170'; 'regulation 6', 'reg. 6' -> 'Regulation 6'. An act's own number is
    never a provision: 'Regulation 2016/679' and 'Regulation (EU) 2016/679' give None."""
    rest = locator.lstrip()
    for prefix, name in PROVISION_WORDS:
        if rest[:len(prefix)].lower() == prefix:
            rest = rest[len(prefix):].lstrip()
            break
    else:
        return None
    digits = 0
    while digits < len(rest) and rest[digits].isdecimal():
        digits += 1
    if not digits:
        return None
    after = rest[digits:]
    if after[:1] == "/":
        return None  # 2016/679 is an act number
    suffix = after[:1]
    letters = suffix if suffix.isascii() and suffix.isalpha() else ""
    if letters and name != "Article":
        letters = letters.upper()  # UK insertions are capital letters: section 16A
    return f"{name} {rest[:digits]}{letters}"


def _stem(term: str) -> str:
    for suffix in SUFFIXES:
        if term.endswith(suffix) and len(term) - len(suffix) >= 4:
            return term[: -len(suffix)]
    return term


def _terms(text: str) -> list[str]:
    return [_stem(term) for term in tokens(text)]


def _inflections(word: str) -> set[str]:
    stem = word[:-1] if word.endswith("e") else word
    return {word, word + "s", word + "es", word + "d", word + "ed", stem + "ed", stem + "ing", stem + "ion", stem + "ions"}


# The bridge also answers inflected forms: "deleted", "cookies", "providers", "encrypted".
INFLECTED_TERMS = {form: value for key, value in LEGAL_TERMS.items() for form in _inflections(key)}


def _without_code_spans(text: str) -> str:
    """Replace each '(code: ...)' span with a space; an unclosed span is kept as text."""
    parts, index = [], 0
    while (start := text.find("(code:", index)) != -1:
        end = text.find(")", start + 6)
        if end == -1:
            break
        parts += [text[index:start], " "]
        index = end + 1
    return "".join(parts) + text[index:]


def _explained_query(statement: str) -> dict[str, tuple[float, str]]:
    """Stemmed term -> (weight, origin). Statement terms weigh 1.0 and come from the statement;
    their legal-vocabulary counterparts weigh 0.8 and name the statement word that bridged to them."""
    query = [term for term in tokens(_without_code_spans(statement)) if term not in NOISE]
    terms: dict[str, tuple[float, str]] = {}
    for term in query:
        terms[_stem(term)] = (1.0, "statement")
    for term in query:
        for legal in (LEGAL_TERMS.get(term) or INFLECTED_TERMS.get(term, "")).split():
            terms.setdefault(_stem(legal), (0.8, term))
    return terms


def _query(statement: str) -> dict[str, float]:
    """Statement terms at 1.0 plus their legal-vocabulary counterparts at 0.8, all stemmed."""
    return {term: weight for term, (weight, _) in _explained_query(statement).items()}


class _Field:
    """One field of every article, tokenised once: term counts, lengths and document frequencies."""

    def __init__(self, texts: list[str], b: float):
        self.documents = [Counter(_terms(text)) for text in texts]
        self.lengths = [sum(terms.values()) for terms in self.documents]
        self.frequency = Counter(term for terms in self.documents for term in terms)
        self.average = max(1.0, sum(self.lengths) / max(1, len(self.documents)))
        self.b = b

    def scores(self, weights: dict[str, float], k1: float = 1.2) -> list[float]:
        total = len(self.documents)
        idf = {term: math.log(1 + (total - self.frequency[term] + 0.5) / (self.frequency[term] + 0.5))
               for term in weights if self.frequency[term]}
        result = []
        for terms, length in zip(self.documents, self.lengths):
            score = 0.0
            for term, value in idf.items():
                count = terms.get(term)
                if count:
                    score += weights[term] * value * count * (k1 + 1) / (count + k1 * (1 - self.b + self.b * length / self.average))
            result.append(score)
        return result


class ArticleIndex:
    """Every article of every retained act, indexed once and searched per statement."""

    def __init__(self, catalogue: dict[str, dict[str, dict]], semantic=None):
        """`semantic`: None uses the optional model when the user turned it on and it is ready;
        False is word search only; a SemanticIndex-like object (with `scores`) is used as given."""
        self.catalogue = catalogue
        self.keys = [(source, key) for source, articles in catalogue.items() for key in articles]
        self.text = _Field([catalogue[s][k]["text"] for s, k in self.keys], b=0.75)
        self.title = _Field([catalogue[s][k]["title"] for s, k in self.keys], b=0.3)
        self.semantic = None
        if semantic is None and self.keys:
            from . import semantic as model
            if model.status()["active"]:
                try:
                    self.semantic = model.SemanticIndex(catalogue, self.keys)
                except Exception:  # an optional ranking never breaks a report: word search still answers
                    self.semantic = None
        elif semantic:
            self.semantic = semantic

    @property
    def method(self) -> str:
        return "words+semantic" if self.semantic is not None else "words"

    def suggest(self, statement: str, top: int = 3) -> list[dict]:
        """BM25 over the text plus a boosted BM25 over the title; with the optional model, that
        ranking merged with the model's (reciprocal rank fusion). Each hit says which found it."""
        if not self.keys:
            return []
        explained = _explained_query(statement)
        weights = {term: weight for term, (weight, _) in explained.items()}
        scored = sorted(((t + TITLE_WEIGHT * h, s, k, i) for i, (t, h, (s, k))
                         in enumerate(zip(self.text.scores(weights), self.title.scores(weights), self.keys)) if t + h > 0),
                        key=lambda item: (-item[0], item[1], item[2]))
        if self.semantic is None:
            return [{"source": source, "article": key, "title": self.catalogue[source][key]["title"], "score": round(score, 2),
                     "matched": self._matched(explained, index), "via": ["words"]}
                    for score, source, key, index in scored[:top]]
        from .semantic import NEAR, fuse
        similarity = self.semantic.scores(statement)
        word_rank = [index for _, _, _, index in scored]
        semantic_rank = sorted(range(len(self.keys)), key=lambda index: (-similarity[index], self.keys[index]))
        near_words, near_semantic = set(word_rank[:NEAR]), set(semantic_rank[:NEAR])
        fused = sorted(fuse(word_rank, semantic_rank), key=lambda item: (-item[0], self.keys[item[1]]))
        results = []
        for score, index in fused[:top]:
            source, key = self.keys[index]
            via = [name for name, near in (("words", near_words), ("semantic", near_semantic)) if index in near]
            results.append({"source": source, "article": key, "title": self.catalogue[source][key]["title"], "score": score,
                            "matched": self._matched(explained, index), "via": via or ["words"]})
        return results

    def _matched(self, explained: dict[str, tuple[float, str]], index: int) -> list[dict]:
        """Why an article was suggested: each query term it contains, and where that term came from."""
        present = self.text.documents[index].keys() | self.title.documents[index].keys()
        return [{"term": term, "via": "statement" if origin == "statement" else "legal vocabulary",
                 **({} if origin == "statement" else {"from": origin})}
                for term, (_, origin) in sorted(explained.items()) if term in present]


def suggest(statement: str, catalogue: dict[str, dict[str, dict]], top: int = 3) -> list[dict]:
    """One-off search; build an ArticleIndex to search many statements."""
    return ArticleIndex(catalogue).suggest(statement, top)


VIA = {"words": "word match", "semantic": "semantic match"}


def via_text(item: dict) -> str:
    return " + ".join(VIA[name] for name in item.get("via", ["words"]))
