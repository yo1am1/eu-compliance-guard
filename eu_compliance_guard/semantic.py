"""Optional semantic search for article suggestions (2.6): a small local embedding model.

Off unless the user turns it on (`EUCG_SEMANTIC=on`, or `"semantic": true` in
`~/.config/eu-compliance-guard/config.json`), the `semantic` extra is installed, and the model
has been downloaded once with `semantic setup` and matches its pinned digests. When on, article
suggestions merge the word-search ranking with the model's ranking (reciprocal rank fusion).
It only orders suggestions for a person to read; it never maps, decides or scores anything.

The model is BAAI/bge-small-en-v1.5 (MIT), in the ONNX build fastembed uses. It runs locally;
nothing is sent anywhere. Using it never touches the network: only `setup` downloads, from
huggingface.co. Similarities are rounded before ranking, so tiny floating-point differences
between machines do not reorder results.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from .errors import CodedError

MODEL = "BAAI/bge-small-en-v1.5"
MODEL_LABEL = "bge-small-en-v1.5"
SNAPSHOTS = "models--Qdrant--bge-small-en-v1.5-onnx-Q/snapshots"
# sha256 of each file of the pinned build; a model that differs is never loaded.
FILES = {
    "model_optimized.onnx": "51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431",
    "tokenizer.json": "d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66",
    "config.json": "13582bcf2effc85b7bf3d3f5532e686bc1c9ce86bb009d10f0ec33cbe92299dd",
    "special_tokens_map.json": "5d5b662e421ea9fac075174bb0688ee0d9431699900b90662acd44b2a350503a",
    "tokenizer_config.json": "0b29c7bfc889e53b36d9dd3e686dd4300f6525110eaa98c76a5dafceb2029f53",
}
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
CHUNK_WORDS = 180  # an article is embedded in windows of this many words, each led by its title
MAX_CHUNKS = 5000  # above this the index stays word-only
MAX_MODEL_BYTES = 128 * 1024 * 1024
RRF_K = 60
NEAR = 10  # a hit is labelled with each ranking that has it this near the top
DECIMALS = 4


class SemanticError(CodedError):
    pass


def _home(variable: str, fallback: str) -> Path:
    configured = os.environ.get(variable, "")
    return Path(configured) if os.path.isabs(configured) else Path.home() / fallback


def cache_dir() -> Path:
    return _home("XDG_CACHE_HOME", ".cache") / "eu-compliance-guard"


def wanted() -> bool:
    """Whether the user turned semantic search on: the environment wins over the config file."""
    choice = os.environ.get("EUCG_SEMANTIC", "").strip().lower()
    if choice in ("on", "off"):
        return choice == "on"
    try:
        config = json.loads((_home("XDG_CONFIG_HOME", ".config") / "eu-compliance-guard/config.json").read_text(encoding="utf-8"))
        return isinstance(config, dict) and config.get("semantic") is True
    except (OSError, ValueError):
        return False


def installed() -> bool:
    import importlib.util
    return importlib.util.find_spec("fastembed") is not None and importlib.util.find_spec("numpy") is not None


def _snapshot() -> Path | None:
    """The downloaded snapshot whose every file matches its pinned digest, if any."""
    root = cache_dir() / "models" / SNAPSHOTS
    try:
        candidates = sorted(path for path in root.iterdir() if path.is_dir())
    except OSError:
        return None
    for folder in candidates:
        try:
            if all(_digest(folder / name) == digest for name, digest in FILES.items()):
                return folder
        except OSError:
            continue
    return None


def _digest(path: Path) -> str:
    if path.stat().st_size > MAX_MODEL_BYTES:
        raise OSError("too large")
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def status() -> dict:
    model = "not checked"
    if installed():
        model = "ready" if _snapshot() is not None else (
            "wrong digest" if (cache_dir() / "models" / SNAPSHOTS).is_dir() else "not downloaded")
    on = wanted()
    return {"wanted": on, "installed": installed(), "model": model, "name": MODEL,
            "digest": "sha256:" + FILES["model_optimized.onnx"],
            "active": on and installed() and model == "ready"}


def format_status(report: dict) -> str:
    lines = [f"Semantic search: {'on' if report['active'] else 'off'} (optional; article suggestions only)."]
    if not report["wanted"]:
        lines.append('Not turned on: set EUCG_SEMANTIC=on, or "semantic": true in ~/.config/eu-compliance-guard/config.json.')
    if not report["installed"]:
        lines.append("The `semantic` extra is not installed: run the CLI with `uv run --extra semantic …`, "
                     "or `pip install 'eu-compliance-guard[semantic]'`.")
    elif report["model"] != "ready":
        lines.append(f"Model {report['name']}: {report['model']}. `semantic setup` downloads it once from huggingface.co "
                     "(about 67 MB) and checks its digests.")
    else:
        lines.append(f"Model {report['name']} is ready ({report['digest'][:19]}…); it runs locally and offline.")
    lines.append("It only orders articles to read; word search still runs, and nothing is mapped or decided.")
    return "\n".join(lines)


def setup() -> dict:
    """Download the pinned model once (network: huggingface.co) and verify its digests."""
    if not installed():
        raise SemanticError("semantic-not-installed")
    if _snapshot() is None:
        folder = cache_dir() / "models"
        folder.mkdir(mode=0o700, parents=True, exist_ok=True)
        from fastembed import TextEmbedding
        try:
            TextEmbedding(MODEL, cache_dir=str(folder), lazy_load=True)
        except Exception:
            raise SemanticError("model-download-failed") from None
        if _snapshot() is None:
            raise SemanticError("model-digest-mismatch")
    return status()


class _Model:
    """The pinned model, loaded from local files only."""

    def __init__(self):
        if _snapshot() is None:
            raise SemanticError("model-not-ready")
        os.environ.setdefault("HF_HUB_OFFLINE", "1")  # using the model never touches the network
        from fastembed import TextEmbedding
        self.model = TextEmbedding(MODEL, cache_dir=str(cache_dir() / "models"), local_files_only=True)

    def __call__(self, texts: list[str]):
        import numpy
        return numpy.array(list(self.model.embed(texts)), dtype=numpy.float32)


_loaded: _Model | None = None


def _model() -> _Model:
    global _loaded
    if _loaded is None:
        _loaded = _Model()
    return _loaded


def chunks(title: str, text: str) -> list[str]:
    words = text.split()
    return [f"{title}. " + " ".join(words[start:start + CHUNK_WORDS]) for start in range(0, max(len(words), 1), CHUNK_WORDS)]


def _dot(matrix, vector) -> list[float]:
    if hasattr(matrix, "dot"):
        return [float(value) for value in matrix.dot(vector)]
    return [sum(a * b for a, b in zip(row, vector)) for row in matrix]


class SemanticIndex:
    """Embeddings of every article of an ArticleIndex; `embed` maps texts to unit vectors."""

    def __init__(self, catalogue: dict[str, dict[str, dict]], keys: list[tuple[str, str]], embed=None):
        self.owner, texts = [], []
        for position, (source, key) in enumerate(keys):
            item = catalogue[source][key]
            for chunk in chunks(item["title"], item["text"]):
                self.owner.append(position)
                texts.append(chunk)
        if len(texts) > MAX_CHUNKS:
            raise SemanticError("too-many-articles")
        self.count = len(keys)
        self.embed = embed or _model()
        self.matrix = self._cached(texts) if embed is None else self.embed(texts)

    def _cached(self, texts: list[str]):
        """Embeddings are kept per (model, texts) under the cache folder: an act is embedded once."""
        import numpy
        name = hashlib.sha256(json.dumps([FILES, CHUNK_WORDS, texts], ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        folder = cache_dir() / "embeddings"
        path = folder / f"{name}.npy"
        try:
            matrix = numpy.load(path, allow_pickle=False)
            if matrix.shape[0] == len(texts) and matrix.dtype == numpy.float32:
                return matrix
        except (OSError, ValueError):
            pass
        matrix = self.embed(texts)
        try:
            folder.mkdir(mode=0o700, parents=True, exist_ok=True)
            temporary = folder / f".{name}.{os.getpid()}.tmp"
            with open(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), "wb") as handle:
                numpy.save(handle, matrix, allow_pickle=False)
            os.replace(temporary, path)
        except OSError:
            pass  # the cache is an optimisation only
        return matrix

    def scores(self, statement: str) -> list[float]:
        """Per article, its best window's similarity to the statement, rounded."""
        query = self.embed([QUERY_PREFIX + statement])[0]
        best = [-1.0] * self.count
        for position, value in zip(self.owner, _dot(self.matrix, query)):
            if value > best[position]:
                best[position] = value
        return [round(value, DECIMALS) for value in best]


def fuse(word_rank: list[int], semantic_rank: list[int]) -> list[tuple[float, int]]:
    """Reciprocal rank fusion of two rankings of article positions: (score, position), best first."""
    score: dict[int, float] = {}
    for ranking in (word_rank, semantic_rank):
        for place, position in enumerate(ranking):
            score[position] = score.get(position, 0.0) + 1.0 / (RRF_K + place + 1)
    return sorted(((round(value, 6), position) for position, value in score.items()), key=lambda item: (-item[0], item[1]))
