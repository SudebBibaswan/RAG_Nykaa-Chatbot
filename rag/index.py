"""Build and load the two retrieval indexes.

Chunking: one product = one chunk. Each record is ~60-110 tokens and atomic (a price
only means something next to its product), so splitting would break facts apart and
overlap would just duplicate them.

- Dense: bge-small-en-v1.5 embeddings (fastembed / ONNX, local) in a persistent Chroma
  collection with cosine distance and filterable metadata.
- Sparse: BM25 over a normalised token stream of the same text, pickled to disk.
"""
from __future__ import annotations

import pickle
import re
from functools import lru_cache

import chromadb
import pandas as pd
from fastembed import TextEmbedding
from rank_bm25 import BM25Okapi

from . import config

TOKEN_RE = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")
STOP = {"the", "a", "an", "and", "or", "of", "for", "with", "in", "to", "is", "from", "by", "on", "this", "it"}


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower().replace("'", "")) if t not in STOP]


def chunk_text(r: dict) -> str:
    """The text that gets embedded: title first (most signal), then the description."""
    return f"{r['title']}\n{r['description']}"


def metadata(r: dict) -> dict:
    return {
        "product_id": r["product_id"],
        "brand": r["brand"],
        "product_type": r["product_type"],
        "category": r["category"],
        "price": float(r["price"]),
        "mrp": float(r["mrp"]),
        "discount_pct": int(r["discount_pct"]),
        "rating": float(r["rating"]),
        "rating_count": int(r["rating_count"]),
        "in_stock": bool(r["in_stock"]),
        "is_combo": bool(r["is_combo"]),
        "tags": "|".join(r["tags"]),
    }


@lru_cache(maxsize=1)
def embedder() -> TextEmbedding:
    return TextEmbedding(config.EMBED_MODEL)


def embed_query(q: str) -> list[float]:
    # bge models expect this instruction prefix on queries (not on passages)
    return next(embedder().query_embed([q])).tolist()


def build(df: pd.DataFrame) -> dict:
    config.INDEX_DIR.mkdir(parents=True, exist_ok=True)
    rows = df.to_dict("records")
    texts = [chunk_text(r) for r in rows]
    ids = [r["product_id"] for r in rows]

    # dense
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    try:
        client.delete_collection(config.COLLECTION)
    except Exception:
        pass
    col = client.create_collection(config.COLLECTION, metadata={"hnsw:space": "cosine"})
    vectors = [v.tolist() for v in embedder().passage_embed(texts, batch_size=128)]
    for i in range(0, len(ids), 1000):
        col.add(
            ids=ids[i : i + 1000],
            embeddings=vectors[i : i + 1000],
            documents=texts[i : i + 1000],
            metadatas=[metadata(r) for r in rows[i : i + 1000]],
        )

    # sparse
    bm25 = BM25Okapi([tokenize(t) for t in texts])
    with open(config.BM25_PATH, "wb") as f:
        pickle.dump({"bm25": bm25, "ids": ids}, f)

    return {"chunks": len(ids), "dim": len(vectors[0]), "collection_count": col.count()}


@lru_cache(maxsize=1)
def collection():
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    return client.get_collection(config.COLLECTION)


@lru_cache(maxsize=1)
def bm25():
    with open(config.BM25_PATH, "rb") as f:
        return pickle.load(f)
