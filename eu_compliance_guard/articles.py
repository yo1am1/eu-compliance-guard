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

from .grounding import expand, tokens

MAX_ARTICLES = 2000
MAX_ARTICLE_CHARS = 20000
ARTICLE = re.compile(r"^\s*Article\s+(\d+[a-z]?)\b", re.I)

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
SUFFIXES = ("ations", "ation", "ings", "ing", "ies", "ed", "es", "s")


class _Articles(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.articles: dict[str, dict] = {}
        self.current: dict | None = None
        self.mode = None

    def handle_starttag(self, tag, attrs):
        classes = (dict(attrs).get("class") or "").split()
        if tag == "p" and any(name.endswith("ti-art") and not name.endswith("sti-art") for name in classes):
            self.mode = "number"
            self.current = {"number": "", "title": "", "text": ""}
        elif tag == "p" and any(name.endswith("sti-art") for name in classes) and self.current is not None:
            self.mode = "title"
        elif tag in ("p", "td", "li", "div") and self.current is not None and self.mode is None:
            self.current["text"] += " "

    def handle_endtag(self, tag):
        if tag == "p" and self.mode == "number" and self.current is not None:
            match = ARTICLE.match(self.current["number"])
            if match and len(self.articles) < MAX_ARTICLES:
                self.articles.setdefault(f"Article {match.group(1)}", self.current)
            self.mode = None
        elif tag == "p" and self.mode == "title":
            self.mode = None

    def handle_data(self, data):
        if self.current is None:
            return
        if self.mode == "number":
            self.current["number"] += data
        elif self.mode == "title":
            self.current["title"] += data
        elif len(self.current["text"]) < MAX_ARTICLE_CHARS:
            self.current["text"] += data


def _tidy(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse(content: bytes, media_type: str) -> dict[str, dict]:
    """Map "Article N" to {"title", "text"}; empty when the format is not supported."""
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return {}
    if media_type in ("text/html", "application/xhtml+xml"):
        parser = _Articles()
        try:
            parser.feed(text)
        except (AssertionError, ValueError):
            return {}
        return {key: {"title": _tidy(item["title"]), "text": _tidy(item["text"])[:MAX_ARTICLE_CHARS]}
                for key, item in parser.articles.items()}
    if media_type == "text/plain":
        articles, current = {}, None
        for line in text.splitlines():
            match = ARTICLE.match(line)
            if match and len(articles) < MAX_ARTICLES:
                current = articles.setdefault(f"Article {match.group(1)}", {"title": "", "text": ""})
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


def _query(statement: str) -> dict[str, float]:
    weights: dict[str, float] = {}
    for term, weight in expand(tokens(statement)).items():
        weights[_stem(term)] = max(weights.get(_stem(term), 0.0), weight)
    for term in tokens(statement):
        for legal in LEGAL_TERMS.get(term, "").split():
            weights[_stem(legal)] = max(weights.get(_stem(legal), 0.0), 0.8)
    return weights


def suggest(statement: str, catalogue: dict[str, dict[str, dict]], top: int = 3) -> list[dict]:
    """Rank articles of every retained act for a statement with BM25 over title and text."""
    documents = [(source, key, Counter(_terms(f"{item['title']} {item['title']} {item['text']}")))
                 for source, articles in catalogue.items() for key, item in articles.items()]
    if not documents:
        return []
    frequency = Counter(term for *_, terms in documents for term in set(terms))
    average = sum(sum(terms.values()) for *_, terms in documents) / len(documents)
    weights = _query(statement)
    scored = []
    for source, key, terms in documents:
        length, score = sum(terms.values()), 0.0
        for term, weight in weights.items():
            count = terms.get(term)
            if count:
                idf = math.log(1 + (len(documents) - frequency[term] + 0.5) / (frequency[term] + 0.5))
                score += weight * idf * count * 2.2 / (count + 1.2 * (0.25 + 0.75 * length / average))
        if score > 0:
            scored.append((score, source, key))
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [{"source": source, "article": key, "title": catalogue[source][key]["title"], "score": round(score, 2)}
            for score, source, key in scored[:top]]
