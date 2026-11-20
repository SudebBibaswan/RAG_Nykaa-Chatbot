"""The full RAG pipeline as a stream of events.

analysis -> sources -> token* -> final

Both the FastAPI server and the Streamlit app consume this generator, so the two UIs
always give the same answer to the same question.
"""
from __future__ import annotations

import logging
import time
from typing import Iterator

from . import config, guard, llm
from .llm import Refusal
from .analyze import analyze
from .generate import stream_answer
from .retrieve import retrieve
from .schemas import Retrieval

log = logging.getLogger(__name__)

SMALLTALK_REPLY = (
    "Hi, I'm embellish. Ask me about anything in our catalogue: find a product, compare two, "
    "get the cheapest or best rated in a category, or check shades, offers and stock."
)

SUGGESTIONS = [
    "Best rated Lakme lipstick under ₹500",
    "Compare Maybelline Fit Me foundation and Lakme 9to5 primer",
    "Sunscreens with SPF 50",
    "How many Biotique shampoos do you have?",
]


def _retrieval_only_answer(r: Retrieval, unsupported: list[str]) -> str:
    lines = [config.NO_KEY]
    if unsupported:
        lines.append(f"(Not in the catalogue: {', '.join(unsupported)}.)")
    for a in r.aggregates:
        if a.matching_products:
            lines.append(
                f"{a.matching_products} matching products, ₹{a.min_price:,.0f} to ₹{a.max_price:,.0f}."
            )
    for rec in r.records[:5]:
        rating = f", {rec.rating:.1f}/5 ({rec.rating_count:,})" if rec.rating_count else ""
        lines.append(f"- {rec.title} [P:{rec.product_id}]: ₹{rec.price:,.0f}{rating}")
    return "\n".join(lines)


def run(question: str, history: list[dict] | None = None) -> Iterator[dict]:
    t0 = time.perf_counter()
    question = question.strip()[:1000]
    analysis, analyzer = analyze(question, history)
    ms = lambda: int((time.perf_counter() - t0) * 1000)  # noqa: E731
    yield {"type": "analysis", "analyzer": analyzer, "analysis": analysis.model_dump(), "ms": ms()}

    def final(status: str, answer: str, **extra) -> dict:
        return {"type": "final", "status": status, "answer": answer,
                "latency_ms": int((time.perf_counter() - t0) * 1000), **extra}

    if analysis.scope == "smalltalk":
        yield final("smalltalk", SMALLTALK_REPLY, suggestions=SUGGESTIONS)
        return
    if analysis.scope == "out_of_scope":
        yield final("out_of_scope", config.OUT_OF_SCOPE, suggestions=SUGGESTIONS)
        return

    r = retrieve(analysis)
    yield {
        "type": "sources",
        "records": [x.model_dump() for x in r.records],
        "aggregates": [a.model_dump() for a in r.aggregates],
        "confident": r.confident,
        "top_score": r.top_score,
        "reason": r.reason,
        "ms": ms(),
    }

    # Confidence gate: weak or empty retrieval never reaches the generator.
    if not r.confident:
        yield final("fallback", config.FALLBACK, reason=r.reason, suggestions=SUGGESTIONS)
        return

    ok, why = llm.available()
    if not ok:
        yield final("retrieval_only", _retrieval_only_answer(r, analysis.unsupported_parts), reason=why)
        return

    parts: list[str] = []
    try:
        for delta in stream_answer(
            analysis.standalone_question, r.records, r.aggregates, analysis.unsupported_parts, history,
            operation=analysis.operation,
        ):
            parts.append(delta)
            yield {"type": "token", "text": delta}
    except Refusal:
        yield final("fallback", config.FALLBACK, reason="model declined", suggestions=SUGGESTIONS)
        return
    except Exception as e:
        if llm.is_account_problem(e) and not parts:
            # quota/auth: degrade to the retrieved products instead of an error
            llm.pause(llm.friendly(e))
            log.warning("LLM unavailable, switching to retrieval-only: %s", e)
            yield final("retrieval_only", _retrieval_only_answer(r, analysis.unsupported_parts), reason=llm.friendly(e))
            return
        log.exception("generation failed")
        yield final("error", "Something went wrong while writing the answer. Please try again.", reason=str(e))
        return

    answer = "".join(parts).strip()
    v = guard.check(answer, r.records, r.aggregates, question)
    if v.is_fallback:
        yield final("fallback", config.FALLBACK, suggestions=SUGGESTIONS)
    elif not v.ok:
        # Output check failed: withhold the drafted answer rather than show unverified facts.
        log.warning("guard withheld answer: %s", v.problems)
        yield final("withheld", config.FALLBACK, problems=v.problems, draft=answer, suggestions=SUGGESTIONS)
    else:
        yield final("answered", answer, cited=v.cited)


def answer(question: str, history: list[dict] | None = None) -> dict:
    """Non-streaming convenience: returns all events folded into one dict."""
    out: dict = {"question": question}
    for ev in run(question, history):
        if ev["type"] == "token":
            continue
        out[ev["type"]] = ev
    return out
