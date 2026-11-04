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
import math
import re

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


def _segment(paragraphs) -> dict[str, dict]:
    """Class-marked articles when the page has them, else paragraphs that read exactly "Article N".

    Only a paragraph that is just "Article N" opens an article. A marked heading that is not, such as
    an amendment's quoted "‘Article 6a", stays text of the amending article. The first annex heading
    or closing formula after article text ends the enacting terms: an "Article N" in a later
    correlation table opens nothing. A number seen twice (a contents list, then the body) keeps the
    occurrence with the most text, the first one on a tie.
    """
    marked = any(_is_number(classes) for classes, _ in paragraphs)
    found: dict[str, list[dict]] = {}
    current = None
    expect_title = wrote = ended = False
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
            if not ended and (key in found or len(found) < MAX_ARTICLES):
                current = {"title": "", "text": ""}
                found.setdefault(key, []).append(current)
            expect_title = True
            continue
        if current is None:
            continue
        if expect_title and (_is_title(classes) if marked else len(text) <= 200 and not text[0].isdigit()):
            current["title"] = text
        elif len(current["text"]) < MAX_ARTICLE_CHARS:
            current["text"] += " " + text
            wrote = True
        expect_title = False
    return {key: max(occurrences, key=lambda item: len(item["text"])) for key, occurrences in found.items()}


def _tidy(text: str) -> str:
    return " ".join(text.split())


def parse(content: bytes, media_type: str) -> dict[str, dict]:
    """Map "Article N" to {"title", "text"}; empty when the format is not supported."""
    try:
        text = content.decode("utf-8-sig")  # a leading byte order mark is not part of the first line
    except UnicodeDecodeError:
        return {}
    media_type = media_type.lower()  # media types are case-insensitive; admission accepts any case
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
        paragraphs = [((), line) for line in map(_tidy, text.splitlines()) if line]
    else:
        return {}
    return {key: {"title": item["title"], "text": _tidy(item["text"])[:MAX_ARTICLE_CHARS]}
            for key, item in _segment(paragraphs).items()}


def article_key(locator: str) -> str | None:
    """'Article 9(2)(a)', 'Art. 9' or 'article 9' -> 'Article 9'."""
    match = re.match(r"^\s*(?:Article|Art\.?)\s*(\d+[a-z]?)", locator, re.I)
    return f"Article {match.group(1)}" if match else None


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


def _query(statement: str) -> dict[str, float]:
    """Statement terms at 1.0 plus their legal-vocabulary counterparts at 0.8, all stemmed."""
    query = [term for term in tokens(re.sub(r"\(code:[^)]*\)", " ", statement)) if term not in NOISE]
    weights: dict[str, float] = {}
    for term in query:
        weights[_stem(term)] = 1.0
    for term in query:
        for legal in (LEGAL_TERMS.get(term) or INFLECTED_TERMS.get(term, "")).split():
            weights[_stem(legal)] = max(weights.get(_stem(legal), 0.0), 0.8)
    return weights


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

    def __init__(self, catalogue: dict[str, dict[str, dict]]):
        self.catalogue = catalogue
        self.keys = [(source, key) for source, articles in catalogue.items() for key in articles]
        self.text = _Field([catalogue[s][k]["text"] for s, k in self.keys], b=0.75)
        self.title = _Field([catalogue[s][k]["title"] for s, k in self.keys], b=0.3)

    def suggest(self, statement: str, top: int = 3) -> list[dict]:
        """BM25 over the text plus a boosted BM25 over the title."""
        if not self.keys:
            return []
        weights = _query(statement)
        scored = sorted(((t + TITLE_WEIGHT * h, s, k) for t, h, (s, k)
                         in zip(self.text.scores(weights), self.title.scores(weights), self.keys) if t + h > 0),
                        key=lambda item: (-item[0], item[1], item[2]))
        return [{"source": source, "article": key, "title": self.catalogue[source][key]["title"], "score": round(score, 2)}
                for score, source, key in scored[:top]]


def suggest(statement: str, catalogue: dict[str, dict[str, dict]], top: int = 3) -> list[dict]:
    """One-off search; build an ArticleIndex to search many statements."""
    return ArticleIndex(catalogue).suggest(statement, top)
