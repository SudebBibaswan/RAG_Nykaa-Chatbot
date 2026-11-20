"""Central configuration. Every tunable knob of the pipeline lives here.

Values can be overridden with environment variables (see .env.example).
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _env(name: str, default):
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return type(default)(raw)


# ---------- paths ----------
RAW_CSV = ROOT / "nyka_popular_brands_products_2022_10_16.csv"
DATA_DIR = ROOT / "data"
CLEAN_CSV = DATA_DIR / "products_clean.csv"
INDEX_DIR = DATA_DIR / "index"
CHROMA_DIR = INDEX_DIR / "chroma"
BM25_PATH = INDEX_DIR / "bm25.pkl"
SNAPSHOT_DATE = "2022-10-16"

# ---------- models ----------
EMBED_MODEL = _env("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
RERANK_MODEL = _env("RERANK_MODEL", "Xenova/ms-marco-MiniLM-L-6-v2")
COLLECTION = "nykaa_products"


def has_openai() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def has_anthropic() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


# OpenAI by default; Claude when chosen explicitly or when it's the only key present.
LLM_PROVIDER = _env("LLM_PROVIDER", "openai" if has_openai() or not has_anthropic() else "anthropic").lower()
_DEFAULTS = {
    "openai": {"chat": "gpt-5.5", "analyzer": "gpt-5.4-mini", "chat_effort": "low", "analyzer_effort": "none"},
    "anthropic": {"chat": "claude-opus-5-5", "analyzer": "claude-opus-5-5", "chat_effort": "low", "analyzer_effort": "low"},
}[LLM_PROVIDER]
CHAT_MODEL = _env("CHAT_MODEL", _DEFAULTS["chat"])
ANALYZER_MODEL = _env("ANALYZER_MODEL", _DEFAULTS["analyzer"])
CHAT_EFFORT = _env("CHAT_EFFORT", _DEFAULTS["chat_effort"])
ANALYZER_EFFORT = _env("ANALYZER_EFFORT", _DEFAULTS["analyzer_effort"])
COMPARE_EFFORT = _env("COMPARE_EFFORT", "medium")
JUDGE_MODEL = _env("JUDGE_MODEL", CHAT_MODEL)

# voice (OpenAI)
TTS_MODEL = _env("TTS_MODEL", "gpt-4o-mini-tts")
TTS_VOICE = _env("TTS_VOICE", "shimmer")
STT_MODEL = _env("STT_MODEL", "gpt-4o-mini-transcribe")

# ---------- retrieval ----------
DENSE_K = _env("DENSE_K", 30)          # candidates from the vector store per sub-query
BM25_K = _env("BM25_K", 30)            # candidates from keyword search per sub-query
RRF_K = _env("RRF_K", 60)              # reciprocal-rank-fusion constant
RERANK_KEEP = _env("RERANK_KEEP", 8)   # records passed to the generator
MAX_CONTEXT_RECORDS = _env("MAX_CONTEXT_RECORDS", 12)  # after merging sub-queries

# Cross-encoder logit below which we consider retrieval "not confident".
# Set from the eval sweep (eval/run_eval.py), not by feel.
RERANK_THRESHOLD = _env("RERANK_THRESHOLD", -2.0)

# ---------- conversation ----------
HISTORY_TURNS = _env("HISTORY_TURNS", 6)
MAX_ANSWER_TOKENS = _env("MAX_ANSWER_TOKENS", 1200)

# ---------- fixed responses ----------
FALLBACK = (
    "I couldn't find that in our product catalogue, so I'd rather not guess. "
    "I can help with product names, brands, prices, discounts, ratings, shades and availability."
)
OUT_OF_SCOPE = (
    "I'm embellish, the catalogue assistant for this store, so I can only answer questions about "
    "the products we list: brands, prices, offers, ratings, shades and stock."
)
NO_KEY = (
    "Answer writing is unavailable right now (no API key, or the AI account is out of credits). "
    "Here are the closest matching products from the catalogue."
)


def has_llm() -> bool:
    return has_openai() if LLM_PROVIDER == "openai" else has_anthropic()
