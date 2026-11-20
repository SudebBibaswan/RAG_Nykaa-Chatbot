"""FastAPI server: the storefront's product API and embellish's chat endpoint.

    .venv/bin/uvicorn api.main:app --port 8000
"""
from __future__ import annotations

import json
import logging
import math
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
from fastapi import FastAPI, File, HTTPException, Query, UploadFile  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse, Response, StreamingResponse  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from rag import config, index, llm, pipeline  # noqa: E402
from rag.retrieve import rerank, table  # noqa: E402

logging.basicConfig(level=logging.INFO)

PUBLIC_COLS = [
    "product_id", "brand", "title", "base_name", "variant", "product_type", "category", "price", "mrp",
    "discount_pct", "rating", "rating_count", "tags", "claims", "suitable_for", "in_stock", "is_combo",
    "image_url", "product_url", "description",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm every model once so the first shopper doesn't wait ~15s.
    table()
    index.collection()
    index.bm25()
    index.embed_query("warm up")
    rerank("warm up", [table().index[0]])
    yield


app = FastAPI(title="embellish API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


def _rows(df: pd.DataFrame) -> list[dict]:
    return json.loads(df[PUBLIC_COLS].to_json(orient="records"))


# ------------------------------------------------------------------ meta
@app.get("/api/health")
def health():
    ok, why = llm.available()
    return {
        "ok": True,
        "llm": ok,
        "llm_provider": config.LLM_PROVIDER,
        "llm_note": why,
        "chat_model": config.CHAT_MODEL if ok else None,
        "products": len(table()),
        "snapshot": config.SNAPSHOT_DATE,
        "voice": {
            "tts": "openai" if llm.voice_available() else "browser",
            "stt": "openai" if llm.voice_available() else "browser",
        },
    }


@app.get("/api/facets")
def facets():
    df = table()
    return {
        "brands": df.brand.value_counts().rename_axis("name").reset_index(name="count").to_dict("records"),
        "categories": df.category.value_counts().rename_axis("name").reset_index(name="count").to_dict("records"),
        "types": df.product_type.value_counts().rename_axis("name").reset_index(name="count").to_dict("records"),
        "price": {"min": float(df.price.min()), "max": float(df.price.max())},
    }


@app.get("/api/home")
def home():
    df = table()
    popular = df[df.rating_count >= 200]

    def top(sub: pd.DataFrame, by: list[str], n: int = 12) -> list[dict]:
        sub = sub.sort_values(by, ascending=False).drop_duplicates("base_name")
        return _rows(sub.head(n))

    return {
        "bestsellers": top(df[df.tags.map(lambda t: "Bestseller" in t)], ["rating_count"]),
        "new": top(df[df.tags.map(lambda t: "New arrival" in t)], ["rating", "rating_count"]),
        "deals": top(popular[popular.discount_pct >= 30], ["discount_pct", "rating_count"]),
        "top_rated": top(df[df.rating_count >= 1000], ["rating", "rating_count"]),
        "by_category": {
            c: top(popular[popular.category == c], ["rating_count"], 10)
            for c in ["Makeup", "Skin Care", "Hair Care", "Bath & Body", "Nails"]
        },
    }


# ------------------------------------------------------------------ products
SortKey = Literal["popular", "price_asc", "price_desc", "rating", "discount", "relevance"]


@app.get("/api/products")
def products(
    q: Optional[str] = None,
    brand: list[str] = Query(default=[]),
    category: list[str] = Query(default=[]),
    type: list[str] = Query(default=[]),
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_rating: Optional[float] = None,
    min_discount: Optional[int] = None,
    tag: Optional[str] = None,
    sort: SortKey = "popular",
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=96),
):
    df = table()
    m = pd.Series(True, index=df.index)
    if brand:
        m &= df.brand.isin(brand)
    if category:
        m &= df.category.isin(category)
    if type:
        m &= df.product_type.isin(type)
    if min_price is not None:
        m &= df.price >= min_price
    if max_price is not None:
        m &= df.price <= max_price
    if min_rating is not None:
        m &= (df.rating >= min_rating) & (df.rating_count > 0)
    if min_discount is not None:
        m &= df.discount_pct >= min_discount
    if tag:
        m &= df.tags.map(lambda t: tag in t)
    sub = df[m]

    if q:
        # storefront search reuses the hybrid retriever's keyword half for speed
        from rag.retrieve import bm25_search, dense_search, rrf
        allowed = set(sub.index)
        fused = rrf({"dense": dense_search(q, allowed, 60), "bm25": bm25_search(q, allowed, 60)})
        ids = [p for p, _, _ in fused]
        sub = sub.loc[ids]
        if sort == "popular":
            sort = "relevance"

    order = {
        "popular": (["rating_count"], [False]),
        "price_asc": (["price"], [True]),
        "price_desc": (["price"], [False]),
        "rating": (["rating", "rating_count"], [False, False]),
        "discount": (["discount_pct", "rating_count"], [False, False]),
    }
    if sort != "relevance":
        cols, asc = order[sort]
        sub = sub.sort_values(cols, ascending=asc)
        if sort in ("popular", "rating"):
            # shades of one product share its rating count; show each product's best shade
            # first, then the remaining shades, so page 1 isn't twelve shades of one lipstick
            rank = sub.groupby(["brand", "base_name"], sort=False).cumcount()
            sub = sub.assign(_v=rank.values).sort_values("_v", kind="stable").drop(columns="_v")

    total = len(sub)
    start = (page - 1) * limit
    return {
        "total": total,
        "page": page,
        "pages": max(1, math.ceil(total / limit)),
        "items": _rows(sub.iloc[start : start + limit]),
    }


@app.get("/api/products/{pid}")
def product(pid: str):
    df = table()
    if pid not in df.index:
        raise HTTPException(404, "product not found")
    row = df.loc[[pid]]
    p = row.iloc[0]
    variants = df[(df.base_name == p.base_name) & (df.brand == p.brand) & (df.product_id != pid)]
    similar = df[(df.product_type == p.product_type) & (df.product_id != pid) & (df.base_name != p.base_name)]
    similar = similar.assign(_d=(similar.price - p.price).abs()).sort_values(["_d"]).head(40)
    similar = similar.sort_values("rating_count", ascending=False).drop_duplicates("base_name").head(10)
    return {
        "product": _rows(row)[0],
        "variants": _rows(variants.sort_values("price").head(24)),
        "similar": _rows(similar),
    }


# ------------------------------------------------------------------ chat
class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[Turn] = Field(default_factory=list, max_length=24)
    product_id: Optional[str] = None  # set when the shopper asks from a product page


@app.post("/api/chat")
def chat(req: ChatRequest):
    history = [t.model_dump() for t in req.history]
    message = req.message
    if req.product_id and req.product_id in table().index:
        # give the analyzer the page context so "is this on sale?" resolves
        title = table().loc[req.product_id].title
        history = history + [
            {"role": "user", "content": f"I'm looking at {title}."},
            {"role": "assistant", "content": f"Sure, ask me anything about {title}."},
        ]

    def events():
        for ev in pipeline.run(message, history):
            yield f"event: {ev['type']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ------------------------------------------------------------------ voice (OpenAI; the browser voice is the fallback)
class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


@app.post("/api/voice/tts")
def tts(req: SpeakRequest):
    if not llm.voice_available():
        return JSONResponse({"configured": False, "detail": "Add OPENAI_API_KEY to enable server voice."}, status_code=501)
    try:
        audio = llm.speech(req.text)
    except Exception as e:  # quota, network: the client falls back to browser speech
        return JSONResponse({"configured": True, "detail": str(e)[:300]}, status_code=503)
    return Response(audio, media_type="audio/mpeg")


@app.post("/api/voice/stt")
async def stt(file: UploadFile = File(...)):
    if not llm.voice_available():
        return JSONResponse({"configured": False, "detail": "Add OPENAI_API_KEY to enable server transcription."}, status_code=501)
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "audio too long")
    try:
        text = llm.transcribe(data, file.filename or "question.webm")
    except Exception as e:
        return JSONResponse({"configured": True, "detail": str(e)[:300]}, status_code=503)
    return {"text": text}
