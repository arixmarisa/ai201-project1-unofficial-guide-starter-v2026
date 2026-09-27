"""
Stages 3 and 4 of the pipeline: embedding chunks and retrieving them.

Three things in here are worth knowing about, because they'd quietly break the
rest of the project if they were wrong:

1. The Chroma collection is created with cosine distance, explicitly. Chroma
   defaults to squared L2, and the 0.6 threshold the course uses is calibrated
   against cosine. Getting this wrong makes every distance number meaningless.

2. `search` returns the distance alongside each chunk. Milestone 4 has you
   compare distances, so they have to be visible.

3. The embedding model is the one Chroma bundles, not one loaded through
   `sentence-transformers`. It is the same model — `all-MiniLM-L6-v2`, 384
   dimensions — but it arrives as an ONNX build from Chroma's own CDN, so the
   install needs neither PyTorch nor a reachable Hugging Face. See `_embedder`.

Unit 2 improvement:
Retrieval now combines semantic similarity with BM25 keyword retrieval using
Reciprocal Rank Fusion (RRF). The original cosine distance is preserved on each
result so the existing relevance gate can still use the same 0.6 threshold.
"""

import os
import re
import shutil
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

# Must be set BEFORE chromadb is imported. Without it, some Chroma versions
# print "Failed to send telemetry event ..." on every single call — which looks
# exactly like a real error, isn't one, and cost a previous cohort a lot of
# confused help-channel messages.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb  # noqa: E402

import config
from chunker import Chunk


@dataclass
class Result:
    """One retrieved chunk and how far it was from the question."""

    text: str
    source: str
    label: str
    distance: float   # LOWER IS BETTER. 0.3 is close, 0.9 is unrelated.
    produced_by: str


_model = None

# The model Chroma bundles. Anything else in config.EMBEDDING_MODEL means
# "fetch that one from Hugging Face instead" — see `_embedder`.
BUNDLED_MODEL = "all-MiniLM-L6-v2"


class _OnnxEmbedder:
    """
    Chroma's built-in embedder, wrapped to look like the other two.

    Chroma's embedding functions are called directly and hand back numpy
    arrays. The rest of this file wants `.encode(texts)`, so the adapter lives
    here rather than making every caller care which embedder it got.
    """

    def __init__(self):
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

        self._ef = ONNXMiniLM_L6_V2()

    def encode(self, texts, show_progress_bar: bool = False):
        return [vector.tolist() for vector in self._ef(list(texts))]


def _sentence_transformer(name: str):
    """
    The escape hatch: any model that isn't the bundled one.

    Unit 1's "try a second embedding model" stretch option comes through here,
    and so does anything you set `EMBEDDING_MODEL` to. This path *does* need
    `sentence-transformers` and a reachable Hugging Face.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            f"config.EMBEDDING_MODEL is set to {name!r}, which isn't the model "
            f"Chroma bundles ({BUNDLED_MODEL!r}), so it has to be downloaded "
            f"from Hugging Face.\n"
            f"Install the optional dependency first:\n"
            f"    pip install 'sentence-transformers>=3.4,<3.5'\n"
            f"Or set EMBEDDING_MODEL back to {BUNDLED_MODEL!r}."
        ) from exc

    return SentenceTransformer(name)


def _embedder():
    """
    Load the embedding model once and keep it.

    First call is slow — it downloads about 80 MB.
    """
    global _model

    if _model is not None:
        return _model

    # Used only by this repo's own smoke test, which runs where no model can be
    # downloaded at all. Never set this yourself.
    if os.getenv("AI201_FAKE_EMBEDDINGS") == "1":
        from _smoke_embedder import FakeEmbedder

        _model = FakeEmbedder()
    elif config.EMBEDDING_MODEL == BUNDLED_MODEL:
        _model = _OnnxEmbedder()
    else:
        _model = _sentence_transformer(config.EMBEDDING_MODEL)

    return _model


def embed(texts: list[str]) -> list[list[float]]:
    """Turn text into vectors. Runs on your machine, costs no API quota."""
    vectors = _embedder().encode(texts, show_progress_bar=False)

    # sentence-transformers and the smoke stand-in return something with a
    # .tolist(); _OnnxEmbedder has already done that conversion itself.
    return vectors.tolist() if hasattr(vectors, "tolist") else vectors


def _client():
    return chromadb.PersistentClient(
        path=str(config.CHROMA_DIR),
        settings=chromadb.config.Settings(anonymized_telemetry=False),
    )


def build_index(
    chunks: list[Chunk],
    corpus: str | None = None,
    variant: str = "default",
) -> int:
    """
    Embed every chunk and store it.

    `variant` lets you keep more than one index of the same corpus at the same
    time. In unit 2, when you compare two chunking strategies, index the second
    one as variant="v2" and you can query both instead of deleting the first
    and starting over.
    """
    name = config.collection_name(corpus, variant)
    client = _client()

    try:
        client.delete_collection(name)
    except Exception:
        pass

    collection = client.create_collection(
        name=name,
        # ⚠️ Do not remove. Chroma defaults to squared L2, and every distance
        # number in this course assumes cosine.
        metadata={"hnsw:space": "cosine"},
    )

    batch = 256
    for start in range(0, len(chunks), batch):
        window = chunks[start : start + batch]
        collection.add(
            ids=[f"{c.source}#{c.index}" for c in window],
            documents=[c.text for c in window],
            embeddings=embed([c.text for c in window]),
            metadatas=[
                {
                    "source": c.source,
                    "index": c.index,
                    "produced_by": c.produced_by,
                }
                for c in window
            ],
        )

    return len(chunks)


def _tokenize(text: str) -> list[str]:
    """Simple lowercase tokenizer used for BM25 keyword retrieval."""
    return re.findall(r"\b\w+\b", text.lower())


def search(
    question: str,
    top_k: int | None = None,
    corpus: str | None = None,
    variant: str = "default",
    source: str | None = None,
) -> list[Result]:
    """
    Retrieve chunks using hybrid semantic + BM25 search.

    Semantic retrieval finds chunks with similar meaning.
    BM25 adds keyword matching for exact words, names, and numbers.

    The two rankings are combined using Reciprocal Rank Fusion (RRF).

    Each returned Result keeps its original cosine distance so the relevance
    gate can continue using the existing threshold.
    """
    top_k = top_k or config.TOP_K
    name = config.collection_name(corpus, variant)

    try:
        collection = _client().get_collection(name)
    except Exception as exc:
        raise RuntimeError(
            f"No index called '{name}'. Run `python app.py index` first."
        ) from exc

    # Keep metadata filtering working with hybrid retrieval.
    where = {"source": source} if source else None

    if where:
        stored = collection.get(
            where=where,
            include=["documents", "metadatas"],
        )
    else:
        stored = collection.get(
            include=["documents", "metadatas"],
        )

    ids = stored["ids"]
    documents = stored["documents"]

    if not ids:
        return []

    # ---------------------------------------------------------
    # 1. Semantic retrieval
    # ---------------------------------------------------------
    query_options = {
        "query_embeddings": embed([question]),
        # Retrieve all matching chunks so semantic and BM25 ranking can be
        # combined over the same candidate set.
        "n_results": len(ids),
    }

    if where:
        query_options["where"] = where

    semantic_raw = collection.query(**query_options)

    semantic_ids = semantic_raw["ids"][0]
    semantic_docs = semantic_raw["documents"][0]
    semantic_metas = semantic_raw["metadatas"][0]
    semantic_distances = semantic_raw["distances"][0]

    results_by_id: dict[str, Result] = {}

    for chunk_id, text, meta, distance in zip(
        semantic_ids,
        semantic_docs,
        semantic_metas,
        semantic_distances,
    ):
        results_by_id[chunk_id] = Result(
            text=text,
            source=str(meta.get("source", "unknown")),
            label=f"{meta.get('source', 'unknown')}#{meta.get('index', 0)}",
            distance=float(distance),
            produced_by=str(meta.get("produced_by", "unknown")),
        )

    # ---------------------------------------------------------
    # 2. BM25 keyword retrieval
    # ---------------------------------------------------------
    tokenized_documents = [_tokenize(text) for text in documents]
    tokenized_question = _tokenize(question)

    bm25 = BM25Okapi(tokenized_documents)
    bm25_scores = bm25.get_scores(tokenized_question)

    bm25_ranked = sorted(
        zip(ids, bm25_scores),
        key=lambda item: item[1],
        reverse=True,
    )

    # ---------------------------------------------------------
    # 3. Reciprocal Rank Fusion
    # ---------------------------------------------------------
    #
    # Semantic search remains the primary retrieval method.
    # BM25 helps boost chunks containing exact terms, names, and numbers.
    #
    # RRF is useful because cosine distances and BM25 scores are not directly
    # comparable; it combines their rankings instead of raw score values.
    fusion_scores: dict[str, float] = {}

    semantic_weight = 0.65
    bm25_weight = 0.35
    rrf_k = 60

    for rank, chunk_id in enumerate(semantic_ids, start=1):
        fusion_scores[chunk_id] = (
            fusion_scores.get(chunk_id, 0.0)
            + semantic_weight / (rrf_k + rank)
        )

    for rank, (chunk_id, bm25_score) in enumerate(bm25_ranked, start=1):
        # Ignore zero-score BM25 results so arbitrary ordering among chunks with
        # no matching keywords does not affect the hybrid ranking.
        if bm25_score <= 0:
            continue

        fusion_scores[chunk_id] = (
            fusion_scores.get(chunk_id, 0.0)
            + bm25_weight / (rrf_k + rank)
        )

    ranked_ids = sorted(
        fusion_scores,
        key=fusion_scores.get,
        reverse=True,
    )

    return [
        results_by_id[chunk_id]
        for chunk_id in ranked_ids[:top_k]
        if chunk_id in results_by_id
    ]


def index_exists(corpus: str | None = None, variant: str = "default") -> bool:
    """
    Is there an index here to search, without searching it?

    `serve.py`'s health check asks this. It deliberately does not embed
    anything: loading the embedding model takes 80 MB and a few seconds, and a
    health check that heavy is a health check nobody can afford to call.
    """
    try:
        collection = _client().get_collection(
            config.collection_name(corpus, variant)
        )
        return collection.count() > 0
    except Exception:
        return False


def reset():
    """Delete every index. Occasionally the fastest way out of a mess."""
    if config.CHROMA_DIR.exists():
        shutil.rmtree(config.CHROMA_DIR)