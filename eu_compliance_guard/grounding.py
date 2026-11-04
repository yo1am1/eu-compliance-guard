"""Ground declared facts in project files with a local, explainable index.

No embeddings, model or network: Okapi BM25 over identifier-split tokens of the text files under
the declarations' files root, with a curated lexicon of legal concepts that expands each query.
Every candidate is a file:line with the file's digest. Grounding finds where code shows a
technical fact; it never decides what the law requires, and organisational facts (lawful basis,
establishment, roles, size, sector) are never observable from code.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat

from . import models as m, revalidation as r

MAX_FILES = 2000
MAX_FILE_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
SKIP_DIRS = {".git", ".hg", ".svn", ".eu-compliance-guard", "node_modules", ".venv", "venv", "env", "__pycache__",
             "dist", "build", "target", ".next", ".nuxt", ".tox", ".mypy_cache", ".pytest_cache", "vendor", "coverage"}
TEXT_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".go", ".rb", ".java", ".kt", ".php", ".cs", ".rs",
                 ".swift", ".scala", ".html", ".htm", ".vue", ".svelte", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
                 ".md", ".txt", ".sql", ".tf", ".sh", ".graphql", ".proto", ".xml", ".properties", ".env.example"}
TEXT_NAMES = {"Dockerfile", "Procfile", "Makefile"}

# Concept -> terms that suggest it in code. Observable concepts describe technical behaviour.
CONCEPTS = {
    "personal_data": ("Personal data fields", {"email", "phone", "address", "name", "surname", "birth", "birthday",
                      "dob", "gender", "ip", "location", "geolocation", "user", "profile", "account", "customer"}),
    "special_category": ("Health or other special-category data", {"health", "weight", "height", "bmi", "medical",
                         "diagnosis", "biometric", "heart", "pregnancy", "religion", "ethnicity", "sexual", "disability"}),
    "children": ("Age and children", {"age", "birth", "dob", "minor", "child", "children", "parental", "kid", "teen"}),
    "tracking": ("Cookies and tracking", {"cookie", "cookies", "localstorage", "sessionstorage", "analytics", "tracking",
                 "tracker", "pixel", "gtag", "ga", "segment", "mixpanel", "amplitude", "hotjar", "fingerprint"}),
    "consent": ("Consent capture", {"consent", "opt", "optin", "checkbox", "banner", "cmp", "agree", "accept"}),
    "marketing": ("Marketing communications", {"newsletter", "marketing", "campaign", "unsubscribe", "mailchimp",
                  "sendgrid", "promo", "promotion"}),
    "ai": ("AI and model calls", {"llm", "openai", "anthropic", "gpt", "claude", "completion", "complete", "prompt",
           "embedding", "model", "chatbot", "inference"}),
    "third_party": ("Third parties and transfers", {"api", "requests", "fetch", "axios", "webhook", "stripe", "twilio",
                    "s3", "bucket", "upload", "vendor", "processor", "endpoint"}),
    "retention": ("Retention and deletion", {"delete", "deletion", "purge", "ttl", "expire", "expiry", "retention",
                  "retain", "days", "max", "remove"}),
    "subscription": ("Subscriptions and pricing", {"subscription", "subscribe", "renew", "auto", "cancel",
                     "cancellation", "refund", "trial", "price", "billing", "plan", "checkout", "withdrawal"}),
    "security": ("Security of processing", {"password", "hash", "bcrypt", "argon", "encrypt", "encryption", "token",
                 "secret", "tls", "auth", "session", "mfa"}),
    "accessibility": ("Accessibility", {"aria", "alt", "tabindex", "role", "label", "contrast", "a11y"}),
}
# Organisational facts are owner decisions or legal positions; code can never show them.
# Words naming organisational or legal judgements that code cannot show (whole words, any case).
NOT_OBSERVABLE_WORDS = frozenset({
    "lawful", "legal", "legitimate", "establishment", "establishments", "controller", "controllers",
    "processor", "processors", "role", "roles", "enterprise", "size", "sizes", "sector", "sectors",
    "dpia", "contract", "contracts", "policy", "policies", "notice", "notices"})


def _key_words(text: str) -> set[str]:
    return set("".join(char.lower() if char.isalnum() else " " for char in text).split())


def not_observable(scope: m.Scope) -> frozenset[str]:
    """Ids of facts only a person can confirm: every lawful basis and size or sector fact, and any
    fact whose key names an organisational or legal judgement."""
    ids = {fact.id for fact in scope.size_and_sector}
    ids.update(activity.lawful_basis.id for activity in scope.activities)
    ids.update(fact.id for fact in m.scope_facts(scope) if _key_words(fact.key) & NOT_OBSERVABLE_WORDS)
    return frozenset(ids)


STOPWORDS = {"the", "and", "for", "with", "this", "that", "from", "are", "is", "of", "to", "in", "on", "by", "as", "or",
             "be", "if", "it", "at", "an", "a", "def", "return", "self", "none", "true", "false", "const", "let", "var",
             "function", "import", "public", "private", "class", "new", "not", "known", "unknown", "assumed"}


def tokens(text: str) -> list[str]:
    """Identifier-aware tokens: snake_case, camelCase and digits split; lower-cased."""
    words = re.findall(r"[A-Za-z][a-z]+|[A-Z]+(?![a-z])|[a-z]+|\d+", re.sub(r"[_\-./]", " ", text))
    return [word.lower() for word in words if len(word) > 1 and word.lower() not in STOPWORDS]


@dataclass
class Line:
    path: str
    number: int
    text: str
    terms: Counter


@dataclass
class Index:
    root: Path
    lines: list[Line] = field(default_factory=list)
    digests: dict[str, str] = field(default_factory=dict)
    document_frequency: Counter = field(default_factory=Counter)
    skipped: int = 0  # unreadable, unexaminable, binary or over-limit files, and folders that could not be listed

    @property
    def average_length(self) -> float:
        return sum(sum(line.terms.values()) for line in self.lines) / max(1, len(self.lines))


def _is_text(path: Path) -> bool:
    return path.name in TEXT_NAMES or "".join(path.suffixes[-2:]) in TEXT_SUFFIXES or path.suffix in TEXT_SUFFIXES


def build_index(root: Path, exclude: frozenset[str] = frozenset()) -> Index:
    """Read text files below root without following symlinks; bounded by file count and bytes."""
    index = Index(root=root)
    total = 0

    def unreadable(_error: OSError) -> None:
        # A folder that cannot be listed is not covered by the index: count it, never drop it silently.
        index.skipped += 1

    for directory, folders, files in os.walk(root, onerror=unreadable, followlinks=False):
        folders[:] = sorted(name for name in folders if name not in SKIP_DIRS and not name.startswith("."))
        for name in sorted(files):
            path = Path(directory) / name
            if not _is_text(path) or path.relative_to(root).as_posix() in exclude:
                continue
            try:
                info = os.lstat(path)
            except OSError:
                index.skipped += 1  # listed but not examinable, e.g. in a folder without search permission
                continue
            if not stat.S_ISREG(info.st_mode):  # symlinks, devices and sockets are never read
                continue
            if len(index.digests) >= MAX_FILES or total >= MAX_TOTAL_BYTES:
                index.skipped += 1
                continue
            raw = _read_capped(path)
            if raw is None or b"\0" in raw[:4096]:
                index.skipped += 1
                continue
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                index.skipped += 1
                continue
            total += len(raw)
            relative = path.relative_to(root).as_posix()
            index.digests[relative] = m.content_digest(raw)
            for number, content in enumerate(_lines(text), 1):
                terms = Counter(tokens(content))
                if terms:
                    index.lines.append(Line(relative, number, content.strip()[:200], terms))
                    index.document_frequency.update(set(terms))
    return index


def expand(query: list[str]) -> dict[str, float]:
    """Query terms weighted 1.0, plus 0.4 for the vocabulary of every concept the query touches."""
    weights = {term: 1.0 for term in query}
    for _, vocabulary in CONCEPTS.values():
        if vocabulary & set(query):
            for term in vocabulary:
                weights.setdefault(term, 0.4)
    return weights


def concepts_of(terms) -> list[str]:
    return [key for key, (_, vocabulary) in CONCEPTS.items() if vocabulary & set(terms)]


def search(index: Index, query: list[str], top: int = 3, k1: float = 1.2, b: float = 0.75) -> list[dict]:
    weights = expand(query)
    count, average = len(index.lines), index.average_length
    scored = []
    for line in index.lines:
        score, length = 0.0, sum(line.terms.values())
        for term, weight in weights.items():
            frequency = line.terms.get(term)
            if frequency:
                idf = math.log(1 + (count - index.document_frequency[term] + 0.5) / (index.document_frequency[term] + 0.5))
                score += weight * idf * frequency * (k1 + 1) / (frequency + k1 * (1 - b + b * length / average))
        # A line sharing only concept vocabulary (gtag for "tracking") qualifies at its lower weight:
        # the same relatedness test apply uses, so every candidate can be pinned.
        if score > 0:
            scored.append((score, line))
    scored.sort(key=lambda item: (-item[0], item[1].path, item[1].number))
    return [{"location": f"{line.path}:{line.number}", "score": round(score, 2), "concepts": concepts_of(line.terms),
             "snippet": line.text, "digest": index.digests[line.path]} for score, line in scored[:top]]


def _read_capped(path: Path) -> bytes | None:
    """At most MAX_FILE_BYTES of a regular file, never followed through a symlink; None when larger."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError:
        return None
    with os.fdopen(fd, "rb") as handle:
        raw = handle.read(MAX_FILE_BYTES + 1)
    return None if len(raw) > MAX_FILE_BYTES else raw


def _declarations(path: Path) -> tuple[m.RevalidationInput, Path]:
    # Absolute first: the parent of a bare "declarations.json" is the current directory, not "..".
    path = Path(os.path.abspath(path))
    declared = r.load_input(path)
    root = path.parent.parent if declared.files_root == "project" else path.parent
    return declared, Path(os.path.realpath(root))


def _own_files(path, root: Path) -> frozenset[str]:
    """The declarations file, relative to the files root, when it lies inside it."""
    try:
        return frozenset({Path(os.path.realpath(path)).relative_to(root).as_posix()})
    except ValueError:
        return frozenset()


def _lines(text: str) -> list[str]:
    """Split on newlines only, so numbers match editors and git; form feeds stay inside a line."""
    lines = [line[:-1] if line.endswith("\r") else line for line in text.split("\n")]
    return lines[:-1] if lines and lines[-1] == "" else lines


def _fact_query(fact: m.Fact) -> list[str]:
    # An unknown value (None) adds no "null" term to the query.
    value = "" if fact.value is None else fact.value if isinstance(fact.value, str) else json.dumps(fact.value)
    return tokens(f"{fact.key} {value}")


def _current_evidence(path: Path, declared: m.RevalidationInput) -> frozenset[str]:
    """Ids of declared evidence whose file still has its pinned digest, read as a run reads it:
    from the files root, never through a symlink."""
    current = set()
    try:
        with r._parent(Path(os.path.abspath(path))) as (parent_fd, _), r.files_root(declared, parent_fd) as root_fd:
            for selected in declared.evidence:
                if selected.path is None or selected.evidence.availability != "available":
                    continue
                try:
                    observed = r._read_file(root_fd, selected.path, limit=r.MAX_FILE_BYTES, retain=False)
                except r.RevalidationError:
                    continue  # too large to verify, so not current
                if observed.availability == "available" and observed.digest == selected.evidence.digest:
                    current.add(selected.evidence.id)
    except OSError:
        raise r.RevalidationError("unsafe-path") from None
    return frozenset(current)


def ground(path: str | os.PathLike, top: int = 3) -> dict:
    """Candidate code evidence for each assumed/unknown fact and each fact whose pinned evidence
    changed or is missing (stale), and touchpoints no fact covers."""
    path = Path(path)
    declared, root = _declarations(path)
    index = build_index(root, _own_files(path, root))
    facts = {fact.id: fact for fact in m.scope_facts(declared.scope)}
    current = _current_evidence(path, declared)
    # Only the cited lines of unchanged files are accounted for: the rest of a cited file, and the
    # old line numbers of a changed one, may hold other touchpoints.
    cited = {ref for item in declared.evidence if item.evidence.id in current for ref in item.evidence.source_refs}
    unobservable = not_observable(declared.scope)
    results, covered = [], set()
    terms_at = {f"{line.path}:{line.number}": line.terms for line in index.lines}
    for fact in facts.values():
        stale = any(identity not in current for identity in fact.evidence_ids)
        if fact.basis not in ("assumed", "unknown") and not fact.conflicts and not stale:
            continue
        observable = fact.id not in unobservable
        query = _fact_query(fact)
        candidates = search(index, query, top) if observable else []
        # A candidate found only through concept vocabulary (gtag for a cookie fact) does not show
        # the fact, so it stays listed as a touchpoint no fact covers.
        covered.update(item["location"] for item in candidates if set(query) & set(terms_at[item["location"]]))
        results.append({"fact": fact.id, "key": fact.key, "basis": fact.basis, "observable": observable,
                        "stale": stale, "candidates": candidates,
                        "next": ("pinned evidence changed or is missing; " if stale else "")
                        + ("confirm a candidate with --apply, or ask the owner" if candidates
                           else "ask the owner; code cannot show this" if not observable
                           else "no code evidence found; ask the owner")})
    undeclared, accounted = [], covered | cited
    for key, (label, vocabulary) in CONCEPTS.items():
        hits = [line for line in index.lines if vocabulary & set(line.terms) and len(vocabulary & set(line.terms)) >= 2
                and f"{line.path}:{line.number}" not in accounted]
        if hits:
            undeclared.append({"concept": key, "label": label, "count": len(hits),
                               "examples": [f"{line.path}:{line.number}  {line.text}" for line in hits[:3]]})
    return {"root": str(root), "files": len(index.digests), "skipped": index.skipped, "facts": results,
            "undeclared": undeclared}


def format_ground(report: dict) -> str:
    lines = [f"indexed {report['files']} files under the files root ({report['skipped']} skipped)"]
    for fact in report["facts"]:
        stale = ", pinned evidence changed or missing" if fact["stale"] else ""
        lines.append(f"\nfact {fact['fact']} ({fact['basis']}{stale}): {fact['key']}")
        if not fact["observable"]:
            lines.append("  organisational: code cannot show this; ask the owner")
        for item in fact["candidates"]:
            lines.append(f"  {item['location']}  score {item['score']}  [{', '.join(item['concepts']) or '-'}]  {item['snippet']}")
        if fact["observable"] and not fact["candidates"]:
            lines.append("  no code evidence found; ask the owner")
    if report["undeclared"]:
        lines.append("\npossible touchpoints no fact covers:")
        for item in report["undeclared"]:
            lines.append(f"  {item['label']} ({item['count']}): " + " | ".join(item["examples"]))
    lines.append("\nCandidates are search results, not findings. Confirm each before --apply; no output is a compliance conclusion.")
    return "\n".join(lines)


def _rewrite_pins(node, changes: dict[str, tuple[int, int]], top: bool = True) -> bool:
    """Move {id, revision} pins inside a record (not the record itself) to the new revisions."""
    changed = False
    if isinstance(node, dict):
        if not top and set(node) == {"id", "revision"} and node["id"] in changes and node["revision"] == changes[node["id"]][0]:
            node["revision"] = changes[node["id"]][1]
            return True
        for value in node.values():
            changed |= _rewrite_pins(value, changes, False)
    elif isinstance(node, list):
        for value in node:
            changed |= _rewrite_pins(value, changes, False)
    return changed


def _bump_pins(data, kinds: dict[str, tuple[int, int]]) -> None:
    """Move every pin to the new revisions and raise the revision of each record whose pins moved.

    A record that pins a changed record has changed too, so its own revision rises and the
    records pinning it follow, until nothing moves (`check --previous` then accepts the file).
    """
    changes = dict(kinds)
    while True:
        moved = {}
        for name, items in data.items():
            if name == "scope" or not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict) and _rewrite_pins(item, changes) and isinstance(item.get("revision"), int) \
                        and isinstance(item.get("id"), str) and item["id"] not in changes:
                    moved[item["id"]] = (item["revision"], item["revision"] + 1)
                    item["revision"] += 1
        if not moved:
            return
        changes.update(moved)


def code_evidence_id(relative: str) -> str:
    """The evidence id `ground --apply` gives the code file at `relative` (one record per path)."""
    return "evidence-code-" + hashlib.sha256(relative.encode()).hexdigest()[:16]


def _cited(node, identity: str, skip) -> bool:
    """Whether any value outside the record `skip` names the identifier."""
    if node is skip:
        return False
    if isinstance(node, dict):
        return any(_cited(value, identity, skip) for value in node.values())
    if isinstance(node, list):
        return any(_cited(value, identity, skip) for value in node)
    return node == identity


def apply(path: str | os.PathLike, fact_id: str, location: str, now: str | None = None, *,
          write: bool = True) -> m.RevalidationInput:
    """Mark one technical fact observed, pinned to a code line whose terms match the fact.

    Adds (or extends) a code-file evidence record with the file's digest, raises the fact's and
    the scope's revisions and updates every pin to them. The file is rewritten only if the result
    validates; with write=False nothing is written, so a caller can check several pins first.
    """
    path = Path(path)
    declared, root = _declarations(path)
    facts = {fact.id: fact for fact in m.scope_facts(declared.scope)}
    fact = facts.get(fact_id)
    if fact is None:
        raise r.RevalidationError("invalid-input")
    if fact.id in not_observable(declared.scope):
        raise GroundingError("not-observable")
    relative, _, number = location.rpartition(":")
    # ASCII decimal without leading zeros, as ground prints it: str.isdigit() alone also accepts
    # other scripts' digits and superscripts, which would store one line under several refs.
    if not relative or not (number.isascii() and number.isdigit()) or number.startswith("0"):
        raise GroundingError("bad-location")
    try:
        m.SourceFile(path=relative, digest="sha256:" + "0" * 64)
    except ValueError:
        raise GroundingError("bad-location") from None
    if relative in _own_files(path, root):
        raise GroundingError("bad-location")  # the declarations can never be evidence for themselves
    target = root / relative
    if target.is_symlink() or not target.is_file() or os.path.realpath(target) != str(target):
        raise GroundingError("bad-location")
    raw = _read_capped(target)
    if raw is None:
        raise GroundingError("bad-location")
    text_lines = _lines(raw.decode("utf-8", errors="replace"))
    if not 1 <= int(number) <= len(text_lines):
        raise GroundingError("bad-location")
    line_terms = set(tokens(text_lines[int(number) - 1]))
    if not line_terms & set(expand(_fact_query(fact))):
        raise GroundingError("unrelated-line")
    now = now or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    digest = m.content_digest(raw)
    # Code evidence of this fact whose file changed or is gone is replaced by the new pin, so a
    # fact re-pinned to another file stops being stale.
    current = _current_evidence(path, declared)
    outdated = {item.evidence.id for item in declared.evidence
                if item.path and item.evidence.id == code_evidence_id(item.path)
                and item.evidence.id not in current and item.evidence.id in fact.evidence_ids}
    with r._parent(path) as (parent_fd, name):
        observed = r._read_file(parent_fd, name, limit=m.MAX_REQUEST_BYTES, retain=True)
    if observed.availability != "available":
        raise r.RevalidationError("unsafe-path")
    data = json.loads(observed.content)
    evidence_id = code_evidence_id(relative)
    selected = next((item for item in data.setdefault("evidence", []) if item["evidence"]["id"] == evidence_id), None)
    if selected is None:
        selected = {"path": relative, "evidence": {
            "id": evidence_id, "project_id": data["project_id"], "run_id": data["declaration_run_id"],
            "attempt_id": None, "kind": "source_code", "provenance": "observed", "digest": digest, "captured_at": now,
            "manifest_id": data["declaration_manifest_id"], "media_type": "text/plain", "redaction": "safe",
            "availability": "available", "retention_until": None, "source_refs": [], "browser_context": None}}
        data["evidence"].append(selected)
    # One record per file (one digest per path). When the file changed, the other facts pinned to
    # it were confirmed against bytes that no longer exist: they go back to assumed, to be grounded again.
    renewed = selected["evidence"]["digest"] != digest
    selected["evidence"].update(digest=digest, captured_at=now)
    revisions = {fact.id: (fact.revision, fact.revision + 1),
                 declared.scope.id: (declared.scope.revision, declared.scope.revision + 1)}
    scope = data["scope"]
    scope["revision"] += 1
    copies = [*scope.get("roles", []), *scope.get("size_and_sector", [])]
    for activity in scope.get("activities", []):
        copies += [activity["lawful_basis"], *(item for key in ("roles", "recipients", "locations", "stores", "retention")
                                               for item in activity.get(key, []))]
    if renewed:
        selected["evidence"]["source_refs"] = []
        for copy in copies:
            if copy["id"] != fact.id and evidence_id in copy.get("evidence_ids", []):
                old = facts[copy["id"]].revision
                revisions[copy["id"]] = (old, old + 1)
                copy.update(revision=old + 1, basis="assumed",
                            evidence_ids=[item for item in copy["evidence_ids"] if item != evidence_id])
    if location not in selected["evidence"]["source_refs"]:
        selected["evidence"]["source_refs"].append(location)
    for copy in copies:
        if copy["id"] == fact.id:
            copy.update(revision=fact.revision + 1, basis="observed", observed_at=now,
                        evidence_ids=sorted((set(copy.get("evidence_ids", [])) - outdated) | {evidence_id}))
    # A dropped record that nothing else cites any more would only leave an unresolved evidence gap.
    data["evidence"] = [item for item in data["evidence"] if item["evidence"]["id"] not in outdated
                        or item["evidence"]["id"] == evidence_id or _cited(data, item["evidence"]["id"], item)]
    _bump_pins(data, revisions)
    record = m.RevalidationInput.model_validate(data)
    if not write:
        return record
    content = (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    with r._parent(path) as (parent_fd, name):
        _replace(parent_fd, name, content)
    return record


def _replace(parent_fd: int, name: str, content: bytes) -> None:
    """Atomically replace a writable project file, keeping its permission bits.

    Like an editor, a read-only file is refused rather than replaced: os.access for the
    caller, and the owner's write bit, which root's access check ignores.
    """
    info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode):
        raise r.RevalidationError("unsafe-path")
    mode = stat.S_IMODE(info.st_mode) & 0o777
    if not mode & stat.S_IWUSR or not os.access(name, os.W_OK, dir_fd=parent_fd, follow_symlinks=False):
        raise r.RevalidationError("io-failed")
    # Created exclusively without following links, so a planted temp symlink is replaced, never written through.
    temporary = "." + name + ".tmp"
    try:
        os.unlink(temporary, dir_fd=parent_fd)
    except FileNotFoundError:
        pass
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent_fd)
    with os.fdopen(fd, "wb") as handle:
        os.fchmod(fd, mode)
        handle.write(content)
        handle.flush()
        os.fsync(fd)
    os.replace(temporary, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
    os.fsync(parent_fd)


class GroundingError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)
