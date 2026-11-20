"""HTML builders for the console. Every value from data or the model is escaped."""
from __future__ import annotations

import os
import re
from html import escape

STORE = os.getenv("STOREFRONT_URL", "http://localhost:3000")
REFUSED = {"fallback", "out_of_scope", "withheld"}


def img(url: str, size: int = 120) -> str:
    return escape(re.sub(r"tr:h-\d+,w-\d+", f"tr:h-{size},w-{size}", url or ""), quote=True)


def inr(x: float | None) -> str:
    if x is None:
        return "–"
    s = f"{x:,.0f}"
    # Indian grouping: 1,23,456
    n = f"{int(round(x))}"
    if len(n) > 3:
        head, tail = n[:-3], n[-3:]
        head = re.sub(r"(\d)(?=(\d{2})+$)", r"\1,", head)
        s = f"{head},{tail}"
    return f"₹{s}"


def short(title: str, brand: str) -> str:
    return title[len(brand):].strip(" -") if title.startswith(brand) else title


# ------------------------------------------------------------------ answer text
def _inline(text: str, recs: dict) -> str:
    def cite(m: re.Match) -> str:
        pid = m.group(1)
        r = recs.get(pid)
        thumb = f'<img src="{img(r["image_url"], 60)}" alt="">' if r else ""
        title = escape(r["title"], quote=True) if r else f"Product {pid}"
        return f'<a class="cite" href="{STORE}/p/{pid}" target="_blank" rel="noopener" title="{title}">{thumb}P:{pid}</a>'

    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"\[P:(\d+)\]", cite, text)


def answer_body(text: str, records: list[dict], streaming: bool = False) -> str:
    recs = {r["product_id"]: r for r in records}
    out, items = [], []
    for raw in escape(text).split("\n"):
        line = raw.rstrip()
        m = re.match(r"^\s*(?:[-•*]|\d+[.)])\s+(.*)$", line)
        if m:
            items.append(f"<li>{_inline(m.group(1), recs)}</li>")
            continue
        if items:
            out.append("<ul>" + "".join(items) + "</ul>")
            items = []
        if line.strip():
            out.append(f"<p>{_inline(line, recs)}</p>")
    if items:
        out.append("<ul>" + "".join(items) + "</ul>")
    html = "".join(out) or "<p></p>"
    if streaming:
        html = re.sub(r"</(p|ul)>$", r'<span class="caret"></span></\1>', html)
    return html


def product_cards(records: list[dict]) -> str:
    cards = []
    for r in records:
        off = f'<s>{inr(r["mrp"])}</s><em>{r["discount_pct"]}% off</em>' if r["discount_pct"] else ""
        cards.append(
            f'<a class="card" href="{STORE}/p/{escape(r["product_id"])}" target="_blank" rel="noopener">'
            f'<img src="{img(r["image_url"], 140)}" alt="">'
            f'<div><div class="t">{escape(short(r["title"], r["brand"]))}</div>'
            f'<div class="p">{inr(r["price"])}{off}</div></div></a>'
        )
    return f'<div class="cards">{"".join(cards)}</div>' if cards else ""


def user_msg(text: str) -> str:
    return f'<div class="msg-user"><p>{escape(text)}</p></div>'


def bot_msg(turn: dict, selected: bool = False) -> str:
    status = turn.get("status", "streaming")
    ev = turn.get("events", {})
    records = ev.get("sources", {}).get("records", [])
    text = turn.get("answer", "")
    if status in REFUSED:
        head = {
            "out_of_scope": "That's outside what I can help with",
            "withheld": "I couldn't verify that answer",
        }.get(status, "Not in my catalogue")
        body = (
            "I drafted an answer, but some details didn't match the product records, so I've held it back rather than risk being wrong."
            if status == "withheld"
            else escape(text)
        )
        inner = f'<div class="refusal"><b>{head}</b><span>{body}</span></div>'
    elif status == "error":
        inner = f'<p style="color:var(--rani-deep)">{escape(text)}</p>'
    elif status == "retrieval_only":
        lines = text.split("\n")
        inner = (
            '<div class="note">Answer writing is unavailable right now, so these are the closest matches from the catalogue.</div>'
            + answer_body("\n".join(lines[1:]), records)
        )
    elif status == "streaming" and not text:
        stage = "Searching the catalogue" if "analysis" in ev else "Reading your question"
        if "sources" in ev:
            stage = f'Found {len(records)} products, writing the answer'
        inner = f'<p style="color:var(--mauve)">{stage}<span class="caret"></span></p>'
    else:
        inner = answer_body(text, records, streaming=status == "streaming")

    cited_ids = ev.get("final", {}).get("cited") or []
    shown = [r for r in records if r["product_id"] in cited_ids] or (records[:5] if status == "retrieval_only" else [])
    cards = product_cards(shown) if status != "streaming" else ""
    return (
        f'<div class="msg-bot{" selected" if selected else ""}"><div class="av"></div><div class="body">'
        f'<div class="name">embellish</div>{inner}{cards}</div></div>'
    )


# ------------------------------------------------------------------ workings
STAGES = [
    ("read", "Read", "scope, rewrite, split"),
    ("search", "Search", "dense + BM25, fused"),
    ("gate", "Gate", "rerank confidence"),
    ("write", "Write", "grounded, cited"),
    ("verify", "Verify", "ids and numbers"),
]


def stage_states(turn: dict) -> dict[str, tuple[str, str]]:
    """(state, caption) per stage: done | active | skip | fail | todo."""
    ev = turn.get("events", {})
    status = turn.get("status", "streaming")
    an, src, fin = ev.get("analysis"), ev.get("sources"), ev.get("final")
    s: dict[str, tuple[str, str]] = {k: ("todo", "") for k, *_ in STAGES}
    if not an:
        s["read"] = ("active", "reading…")
        return s
    s["read"] = ("done", f'{an.get("ms", 0)} ms, {an["analyzer"]}')
    if an["analysis"]["scope"] != "catalog":
        label = "off-topic" if an["analysis"]["scope"] == "out_of_scope" else "greeting"
        s["read"] = ("fail" if label == "off-topic" else "done", f"{label}, stopped")
        for k in ("search", "gate", "write", "verify"):
            s[k] = ("skip", "not needed")
        return s
    if not src:
        s["search"] = ("active", "searching…")
        return s
    n = len(src["records"])
    s["search"] = ("done", f'{n} product{"" if n == 1 else "s"}, {src.get("ms", 0)} ms')
    if not src["confident"]:
        s["gate"] = ("fail", "too weak, refused")
        s["write"] = s["verify"] = ("skip", "not needed")
        return s
    top = src.get("top_score")
    s["gate"] = ("done", "exact table match" if "table" in (src.get("reason") or "") else f"passed at {top:.2f}" if top is not None else "passed")
    if status == "streaming":
        s["write"] = ("active", "writing…")
        return s
    if status == "retrieval_only":
        s["write"] = ("skip", "model unavailable")
        s["verify"] = ("skip", "nothing to check")
        return s
    if status == "error":
        s["write"] = ("fail", "model error")
        s["verify"] = ("skip", "")
        return s
    s["write"] = ("done", f'{fin.get("latency_ms", 0) / 1000:.1f} s total' if fin else "done")
    if status == "withheld":
        s["verify"] = ("fail", "mismatch, withheld")
    elif status == "fallback":
        s["verify"] = ("done", "model said not found")
    else:
        s["verify"] = ("done", f'{len(fin.get("cited") or [])} cited, all checked' if fin else "checked")
    return s


def rail(turn: dict) -> str:
    st = stage_states(turn)
    parts = []
    for key, label, hint in STAGES:
        state, cap = st[key]
        parts.append(f'<div class="st {state}"><i></i><b>{label}</b><span>{escape(cap or hint)}</span></div>')
    return f'<div class="rail" aria-label="Pipeline progress">{"".join(parts)}</div>'


def _filters(f: dict) -> str:
    chips = []
    for k, v in f.items():
        if v in (None, False, [], ""):
            continue
        label = k.replace("_", " ")
        val = ", ".join(map(str, v)) if isinstance(v, list) else ("yes" if v is True else v)
        chips.append(f'<span class="chip">{escape(label)}: {escape(str(val))}</span>')
    return "".join(chips) or '<span class="chip">no filters, pure semantic search</span>'


def reading(turn: dict) -> str:
    an = turn.get("events", {}).get("analysis")
    if not an:
        return ""
    a = an["analysis"]
    op = {"lookup": "Look up", "compare": "Compare", "rank": "Rank", "count": "Count"}.get(a["operation"], a["operation"])
    if a["operation"] == "rank" and a.get("sort_by"):
        op += " by " + a["sort_by"].replace("_asc", " (low first)").replace("_desc", " (high first)").replace("_", " ")
    if a["scope"] != "catalog":
        why = "no product involved" if a["scope"] == "out_of_scope" else "a greeting"
        return (
            f'<div class="sec"><h4>How I read it</h4><div class="chips"><span class="chip k">Stopped at scope</span>'
            f'<span class="chip">{why}</span><span class="chip">reader: {escape(an["analyzer"])}</span></div></div>'
        )
    head = (
        f'<div class="chips" style="margin-bottom:8px"><span class="chip k">{escape(op)}</span>'
        f'<span class="chip">scope: {escape(a["scope"])}</span><span class="chip">reader: {escape(an["analyzer"])}</span></div>'
    )
    if a["standalone_question"].strip().lower() != turn["q"].strip().lower():
        head += f'<p style="font-size:13px;color:var(--kohl-soft);margin:0 0 8px">Rewritten as “{escape(a["standalone_question"])}”</p>'
    subs = "".join(
        f'<div class="sq"><q>{escape(sq["text"])}</q><div class="chips">{_filters(sq["filters"])}</div></div>' for sq in a["sub_queries"]
    )
    uns = ""
    if a["unsupported_parts"]:
        uns = '<div class="chips" style="margin-top:4px">' + "".join(
            f'<span class="chip warn">not in catalogue: {escape(u)}</span>' for u in a["unsupported_parts"]
        ) + "</div>"
    title = f'How I read it{f" ({len(a["sub_queries"])} searches)" if len(a["sub_queries"]) > 1 else ""}'
    return f'<div class="sec"><h4>{title}</h4>{head}{subs}{uns}</div>'


def retrieved(turn: dict) -> str:
    src = turn.get("events", {}).get("sources")
    if not src:
        return ""
    cited = set(turn.get("events", {}).get("final", {}).get("cited") or [])
    aggs = "".join(
        f'<div class="agg"><strong>{a["matching_products"]}</strong><span>products match “{escape(a["label"])}” exactly'
        + (f', from {inr(a["min_price"])} to {inr(a["max_price"])}' if a["matching_products"] else "")
        + "</span></div>"
        for a in src.get("aggregates", [])
    )
    recs = src.get("records", [])
    if not recs:
        return f'<div class="sec"><h4>What I found</h4>{aggs}<div class="verdict neutral">No product matched the filters.</div></div>'
    peak = max(1.0, max(abs(r["score"] or 0) for r in recs))
    rows = []
    for r in recs:
        sc = r["score"] or 0.0
        pct = max(6, abs(sc) / peak * 100)
        rating = f'{r["rating"]:.1f}★' if r["rating_count"] else "no ratings"
        by = " + ".join(r["matched"])
        rows.append(
            f'<div class="rec{" cited" if r["product_id"] in cited else ""}">'
            f'<img src="{img(r["image_url"], 80)}" alt="">'
            f'<div><div class="t">{escape(r["title"])}</div>'
            f'<div class="m"><span class="bar{" neg" if sc < 0 else ""}" title="relevance {sc:.2f}"><i style="width:{pct:.0f}%"></i></span>'
            f'<span>{sc:+.2f}</span><span>{inr(r["price"])}</span><span>{rating}</span>'
            + ('<span class="tag">cited</span>' if r["product_id"] in cited else "")
            + f'</div></div><div class="by">{escape(by)}</div></div>'
        )
    return f'<div class="sec"><h4>What I found ({len(recs)} products read)</h4>{aggs}{"".join(rows)}</div>'


def verdict(turn: dict) -> str:
    ev = turn.get("events", {})
    fin, src = ev.get("final"), ev.get("sources")
    status = turn.get("status")
    if not fin or status == "streaming":
        return ""
    if status == "answered":
        n = len(fin.get("cited") or [])
        html = f'<div class="verdict ok"><span class="ic">✓</span><span>Every one of the {n} cited products was in the retrieved set, and every price, discount and rating in the answer matches the records.</span></div>'
    elif status == "withheld":
        probs = "; ".join(escape(p) for p in fin.get("problems", []))
        html = f'<div class="verdict bad"><span class="ic">!</span><span>Draft withheld. {probs}</span></div>'
    elif status == "out_of_scope":
        html = '<div class="verdict neutral"><span class="ic">◌</span><span>Stopped at the scope check: no product was involved, so nothing was searched.</span></div>'
    elif status == "fallback":
        reason = escape(fin.get("reason") or (src or {}).get("reason") or "the records didn't answer it")
        html = f'<div class="verdict neutral"><span class="ic">◌</span><span>Refused instead of guessing: {reason}.</span></div>'
    elif status == "retrieval_only":
        why = escape((fin.get("reason") or "no API key")[:180])
        html = f'<div class="verdict neutral"><span class="ic">◌</span><span>Answer writing was skipped ({why}). The products shown come straight from retrieval.</span></div>'
    elif status == "smalltalk":
        return ""
    else:
        html = f'<div class="verdict bad"><span class="ic">!</span><span>{escape(fin.get("reason") or "error")[:240]}</span></div>'
    return f'<div class="sec"><h4>Grounding check</h4>{html}</div>'


def workings(turn: dict) -> str:
    return rail(turn) + reading(turn) + retrieved(turn) + verdict(turn)


def how_it_works(n_products: int, model: str, analyzer: str, tau: float) -> str:
    steps = [
        ("Clean the catalogue", f"3,663 scraped Nykaa rows become {n_products:,} products. A description is composed from each row's own fields, so nothing is invented."),
        ("One product, one chunk", "Each record is 60–110 tokens and self-contained, so it is never split. No overlap is needed."),
        ("Embed locally", "bge-small-en-v1.5 turns every chunk into a 384-number vector, on this laptop, with no API."),
        ("Store twice", "Vectors go into Chroma for meaning; the same text goes into a BM25 index for exact words like “SPF 50”."),
        ("Read the question", f"{analyzer} sorts it into scope, filters and up to three sub-questions."),
        ("Search, fuse, rerank", f"Both indexes search each sub-question; results are fused and a cross-encoder rescores them. Below {tau:+.1f}, embellish refuses."),
        ("Write and verify", f"{model} answers only from the retrieved records and cites each one. Any id or number that doesn't match withholds the answer."),
    ]
    items = "".join(f"<li><div></div><div><b>{escape(t)}</b><span>{escape(d)}</span></div></li>" for t, d in steps)
    return f'<ol class="how">{items}</ol>'.replace("<li><div></div>", "<li>")
