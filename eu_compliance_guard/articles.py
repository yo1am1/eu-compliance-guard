"""Split retained legal-act text into articles and suggest articles for a statement.

Official Journal XHTML marks each article with `oj-ti-art` (number) and `oj-sti-art`
(title); older EUR-Lex HTML uses `ti-art`/`sti-art`. Plain text falls back to lines that
start with "Article N". The text is shown as an unreviewed candidate next to a declared
provision; a suggestion is a search result, never a mapping or a legal conclusion.
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
ARTICLE = re.compile(r"^\s*Article\s+(\d+[a-z]?)\b", re.I)
ARTICLE_ONLY = re.compile(r"^Article\s+(\d+[a-z]?)$", re.I)
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

    def _flush(self):
        text = _tidy("".join(self.buffer))
        if text and len(self.paragraphs) < MAX_PARAGRAPHS:
            self.paragraphs.append((self.classes, text))
        self.classes, self.buffer = (), []

    def handle_starttag(self, tag, attrs):
        if tag in BREAKS:
            self._flush()
            if tag == "p":
                self.classes = tuple((dict(attrs).get("class") or "").split())

    def handle_endtag(self, tag):
        if tag in BREAKS:
            self._flush()

    def handle_data(self, data):
        if self.size < MAX_PAGE_CHARS:
            self.buffer.append(data)
            self.size += len(data)


def _is_number(classes) -> bool:
    return any(name.endswith("ti-art") and not name.endswith("sti-art") for name in classes)


def _is_title(classes) -> bool:
    return any(name.endswith("sti-art") for name in classes)


# Upper-case "ANNEX" headings only: body text such as "Annex III shall apply" stays in its article.
END = re.compile(r"^(?:ANNEX(?:\s+[IVXLC\d]+)?$|Done at\b)")


def _is_end(classes, text: str) -> bool:
    """An annex heading or "Done at …" closes the last article."""
    return any(name.endswith("doc-ti") for name in classes) or bool(END.match(text))


def _segment(paragraphs) -> dict[str, dict]:
    """Class-marked articles when the page has them, else paragraphs that read exactly "Article N"."""
    marked = any(_is_number(classes) for classes, _ in paragraphs)
    found: dict[str, dict] = {}
    current = None
    expect_title = False
    for classes, text in paragraphs:
        if _is_end(classes, text):
            current, expect_title = None, False  # annexes and the closing formula belong to no article
            continue
        match = ARTICLE_ONLY.match(text)
        if (_is_number(classes) if marked else match is not None):
            match = match or ARTICLE.match(text)
            current = None
            if match and len(found) < MAX_ARTICLES and f"Article {match.group(1)}" not in found:
                current = found[f"Article {match.group(1)}"] = {"title": "", "text": ""}
            expect_title = True
            continue
        if current is None:
            continue
        if expect_title and (_is_title(classes) if marked else len(text) <= 200 and not text[0].isdigit()):
            current["title"] = text
        elif len(current["text"]) < MAX_ARTICLE_CHARS:
            current["text"] += " " + text
        expect_title = False
    return found


def _tidy(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse(content: bytes, media_type: str) -> dict[str, dict]:
    """Map "Article N" to {"title", "text"}; empty when the format is not supported."""
    try:
        text = content.decode("utf-8-sig")  # a leading byte order mark is not part of the first line
    except UnicodeDecodeError:
        return {}
    if media_type in ("text/html", "application/xhtml+xml"):
        parser = _Paragraphs()
        try:
            parser.feed(text)
            parser.close()
        except (AssertionError, ValueError):
            return {}
        parser._flush()
        return {key: {"title": item["title"], "text": _tidy(item["text"])[:MAX_ARTICLE_CHARS]}
                for key, item in _segment(parser.paragraphs).items()}
    if media_type == "text/plain":
        articles, current = {}, None
        for line in text.splitlines():
            # Only a line that is just "Article N" opens an article; "Article 6(1) applies" is a reference.
            match = ARTICLE_ONLY.match(line.strip())
            if _is_end((), line.strip()):
                current = None
            elif match:
                # A repeated number (an annex correlation table) never reopens an article.
                key = f"Article {match.group(1)}"
                current = None if key in articles or len(articles) >= MAX_ARTICLES else articles.setdefault(key, {"title": "", "text": ""})
            elif current is not None:
                if not current["title"] and line.strip():
                    current["title"] = _tidy(line)
                elif len(current["text"]) < MAX_ARTICLE_CHARS:
                    current["text"] += " " + line
        return {key: {"title": item["title"], "text": _tidy(item["text"])[:MAX_ARTICLE_CHARS]} for key, item in articles.items()}
    return {}


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
