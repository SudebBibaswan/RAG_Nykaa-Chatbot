"""Hybrid retrieval: metadata filters -> dense (Chroma) + BM25 -> RRF -> cross-encoder rerank.

Ranking and counting questions ("cheapest", "top rated", "how many") are answered over the
filtered table directly, so the numbers are exact rather than whatever similarity search
happened to return.
"""
from __future__ import annotations

import re
from functools import lru_cache

import numpy as np
import pandas as pd
from fastembed.rerank.cross_encoder import TextCrossEncoder

from . import clean, config, index
from .schemas import Aggregate, Analysis, Filters, Record, Retrieval, SubQuery


# ---------------------------------------------------------------- data
@lru_cache(maxsize=1)
def table() -> pd.DataFrame:
    df = clean.load_clean()
    df["_title_l"] = df.title.str.lower()
    df["_type_l"] = df.product_type.str.lower()
    df["_brand_n"] = df.brand.map(_norm)
    # name + parsed claims, normalised, for keyword filters ("paraben free" matches
    # "Paraben and Sulphate Free" through the parsed claim "Paraben free")
    df["_search_n"] = (df.title + " " + df.claims.map(" ".join) + " " + df.variant).map(_norm)
    return df.set_index("product_id", drop=False)


@lru_cache(maxsize=1)
def reranker() -> TextCrossEncoder:
    return TextCrossEncoder(config.RERANK_MODEL)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


BRAND_ALIASES = {
    "loreal": "L'Oreal Paris", "lorealparis": "L'Oreal Paris", "maybelline": "Maybelline New York",
    "nyx": "NYX Professional Makeup", "lakme": "Lakme", "lotus": "Lotus Herbals", "faces": "Faces Canada",
    "kay": "Kay Beauty", "kaybeauty": "Kay Beauty", "huda": "Huda Beauty", "facesshop": "The Face Shop",
    "thefaceshop": "The Face Shop", "faceshop": "The Face Shop", "nykaa": "Nykaa Cosmetics",
}


def resolve_brands(names: list[str]) -> list[str]:
    df = table()
    known = sorted(df.brand.unique())
    out: list[str] = []
    for name in names:
        n = _norm(name)
        if not n:
            continue
        hits = [b for b in known if _norm(b) == n]
        if not hits and n in BRAND_ALIASES:
            hits = [BRAND_ALIASES[n]]
        if not hits:
            hits = [b for b in known if n in _norm(b) or _norm(b) in n]
        # "nykaa" alone means all Nykaa house brands
        if n == "nykaa":
            hits = [b for b in known if b.lower().startswith("nykaa")]
        for h in hits:
            if h not in out:
                out.append(h)
    return out


TYPE_SYNONYMS = {
    "lipsticks": "lipstick", "lip colour": "lipstick", "lip color": "lipstick", "sunscreens": "sunscreen",
    "sun screen": "sunscreen", "sunblock": "sunscreen", "facewash": "face wash", "face washes": "face wash",
    "moisturizer": "moisturi", "moisturiser": "moisturi", "moisturizers": "moisturi", "shampoos": "shampoo",
    "nail polish": "nail", "nail paint": "nail", "nail enamel": "nail", "eye liner": "eyeliner",
    "kohl": "kajal", "perfume": "fragrance", "deo": "deodorant", "body wash": "body wash",
    "lip balms": "lip balm", "serums": "serum", "foundations": "foundation", "palettes": "palette",
    "eyeshadow": "eyeshadow", "eye shadow": "eyeshadow", "conditioners": "conditioner", "masks": "mask",
}


def _type_mask(df: pd.DataFrame, term: str) -> pd.Series:
    t = TYPE_SYNONYMS.get(term.lower().strip(), term.lower().strip())
    t = t[:-1] if t.endswith("s") and len(t) > 4 and t not in {"lips", "lashes"} else t
    return df._type_l.str.contains(t, regex=False) | df._title_l.str.contains(t, regex=False)


def filter_mask(f: Filters) -> pd.Series:
    df = table()
    m = pd.Series(True, index=df.index)
    if f.brands:
        brands = resolve_brands(f.brands)
        if brands:
            m &= df.brand.isin(brands)
        else:
            m &= False  # a brand we don't carry -> nothing matches
    if f.product_types:
        tm = pd.Series(False, index=df.index)
        for t in f.product_types:
            tm |= _type_mask(df, t)
        m &= tm
    for kw in f.title_keywords:
        k = _norm(kw)
        if k:
            m &= df._search_n.str.contains(k, regex=False)
    if f.price_min is not None:
        m &= df.price >= f.price_min
    if f.price_max is not None:
        m &= df.price <= f.price_max
    if f.min_rating is not None:
        m &= (df.rating >= f.min_rating) & (df.rating_count > 0)
    if f.min_discount_pct is not None:
        m &= df.discount_pct >= f.min_discount_pct
    for tag in f.tags:
        m &= df.tags.map(lambda ts, tag=tag: tag in ts)
    if f.in_stock_only:
        m &= df.in_stock
    if f.combos is True:
        m &= df.is_combo
    elif f.combos is False:
        m &= ~df.is_combo
    return m


# ---------------------------------------------------------------- search
def dense_search(query: str, allowed: set[str] | None, k: int) -> list[str]:
    col = index.collection()
    vec = index.embed_query(query)
    if allowed is None:
        res = col.query(query_embeddings=[vec], n_results=k)
    else:
        if not allowed:
            return []
        res = col.query(
            query_embeddings=[vec],
            n_results=min(k, len(allowed)),
            where={"product_id": {"$in": sorted(allowed)}},
        )
    return res["ids"][0]


def bm25_search(query: str, allowed: set[str] | None, k: int) -> list[str]:
    store = index.bm25()
    toks = index.tokenize(query)
    if not toks:
        return []
    scores = store["bm25"].get_scores(toks)
    ids = store["ids"]
    order = np.argsort(-scores)
    out = []
    for i in order:
        if scores[i] <= 0:
            break
        if allowed is None or ids[i] in allowed:
            out.append(ids[i])
            if len(out) >= k:
                break
    return out


def rrf(rankings: dict[str, list[str]], k: int = config.RRF_K) -> list[tuple[str, float, list[str]]]:
    """Reciprocal rank fusion: score(d) = sum over retrievers of 1 / (k + rank)."""
    scores: dict[str, float] = {}
    found: dict[str, list[str]] = {}
    for name, ids in rankings.items():
        for rank, pid in enumerate(ids, start=1):
            scores[pid] = scores.get(pid, 0.0) + 1.0 / (k + rank)
            found.setdefault(pid, []).append(name)
    return sorted(((p, s, found[p]) for p, s in scores.items()), key=lambda x: -x[1])


def rerank(query: str, pids: list[str]) -> list[tuple[str, float]]:
    if not pids:
        return []
    df = table()
    docs = [index.chunk_text(df.loc[p].to_dict()) for p in pids]
    scores = list(reranker().rerank(query, docs))
    return sorted(zip(pids, map(float, scores)), key=lambda x: -x[1])


def to_record(pid: str, **extra) -> Record:
    r = table().loc[pid].to_dict()
    keep = {k: v for k, v in r.items() if not k.startswith("_") and k in Record.model_fields}
    return Record(**keep, **extra)


def _relaxed(sq: SubQuery) -> SubQuery:
    """Keyword filters are a precision aid; if they empty the result set, drop them and
    let semantic search handle the qualifier instead."""
    if sq.filters.title_keywords and not filter_mask(sq.filters).any():
        return SubQuery(text=sq.text, filters=sq.filters.model_copy(update={"title_keywords": []}))
    return sq


def hybrid(sq: SubQuery, keep: int = config.RERANK_KEEP) -> list[Record]:
    sq = _relaxed(sq)
    mask = filter_mask(sq.filters)
    allowed = None if sq.filters.is_empty() else set(table().index[mask])
    if allowed is not None and not allowed:
        return []
    dense = dense_search(sq.text, allowed, config.DENSE_K)
    sparse = bm25_search(sq.text, allowed, config.BM25_K)
    fused = rrf({"dense": dense, "bm25": sparse})[: max(config.DENSE_K, config.BM25_K)]
    meta = {p: (s, f) for p, s, f in fused}
    ranked = rerank(sq.text, [p for p, _, _ in fused])[:keep]
    return [to_record(p, score=s, rrf=meta[p][0], matched=meta[p][1]) for p, s in ranked]


# ---------------------------------------------------------------- operations
SORTS = {
    "price_asc": (["price", "rating_count"], [True, False]),
    "price_desc": (["price", "rating_count"], [False, False]),
    "rating": (["rating", "rating_count"], [False, False]),
    "popularity": (["rating_count", "rating"], [False, False]),
    "discount": (["discount_pct", "rating_count"], [False, False]),
}


def _aggregate(label: str, sub: pd.DataFrame) -> Aggregate:
    return Aggregate(
        label=label,
        matching_products=int(len(sub)),
        min_price=float(sub.price.min()) if len(sub) else None,
        max_price=float(sub.price.max()) if len(sub) else None,
        brands=sorted(sub.brand.unique().tolist())[:12],
    )


def _table_op(sq: SubQuery, sort_by: str | None, n: int) -> tuple[list[Record], Aggregate]:
    """Rank/count straight off the filtered table. Used when the sub-query is fully expressed by filters."""
    df = table()
    sq = _relaxed(sq)
    sub = df[filter_mask(sq.filters)]
    if sort_by == "rating":
        # a 5.0 from 2 ratings shouldn't beat 4.6 from 20,000: require a minimum sample
        rated = sub[sub.rating_count >= 50]
        cols, asc = SORTS["rating"]
        sub_sorted = (rated if len(rated) >= n else sub).sort_values(cols, ascending=asc)
    elif sort_by:
        cols, asc = SORTS[sort_by]
        sub_sorted = sub.sort_values(cols, ascending=asc)
    else:
        sub_sorted = sub.sort_values(["rating_count"], ascending=False)
    recs = [to_record(p, matched=["table"]) for p in sub_sorted.product_id.head(n)]
    return recs, _aggregate(sq.text, sub)


def _is_structural(sq: SubQuery) -> bool:
    """True when the filters capture the whole sub-query, so semantic search adds nothing."""
    f = sq.filters
    return bool(f.brands or f.product_types or f.tags or f.title_keywords or f.price_max or f.price_min or f.min_rating)


def retrieve(a: Analysis) -> Retrieval:
    subs = a.sub_queries or [SubQuery(text=a.standalone_question)]
    records: dict[str, Record] = {}
    aggregates: list[Aggregate] = []
    top = None

    for sq in subs[:3]:
        if a.operation in ("rank", "count") and _is_structural(sq):
            recs, agg = _table_op(sq, a.sort_by, n=config.RERANK_KEEP)
            aggregates.append(agg)
            # score table results with the cross-encoder too, so the confidence gate still applies
            scored = dict(rerank(sq.text, [r.product_id for r in recs]))
            for r in recs:
                r.score = scored.get(r.product_id)
        else:
            keep = 4 if a.operation == "compare" else config.RERANK_KEEP
            recs = hybrid(sq, keep=keep)
            if a.operation in ("rank", "count") and recs:
                cols, asc = SORTS.get(a.sort_by or "popularity")
                recs.sort(key=lambda r: tuple((getattr(r, c) if asc[i] else -getattr(r, c)) for i, c in enumerate(cols)))
        for r in recs:
            if r.product_id not in records:
                records[r.product_id] = r
        if recs:
            best = max((r.score for r in recs if r.score is not None), default=None)
            if best is not None:
                top = best if top is None else max(top, best)

    out = list(records.values())[: config.MAX_CONTEXT_RECORDS]
    if not out:
        return Retrieval(records=[], aggregates=aggregates, confident=False, reason="no products match the filters")

    table_backed = any(agg.matching_products > 0 for agg in aggregates)
    confident = table_backed or (top is not None and top >= config.RERANK_THRESHOLD)
    reason = "table match" if table_backed else (
        f"best rerank score {top:.2f} {'>=' if confident else '<'} threshold {config.RERANK_THRESHOLD}"
    )
    return Retrieval(records=out, aggregates=aggregates, top_score=top, confident=confident, reason=reason)
