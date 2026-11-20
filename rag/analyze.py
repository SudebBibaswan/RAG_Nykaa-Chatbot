"""Query analysis: scope check, follow-up rewrite, decomposition into sub-queries and filters.

Two implementations with the same output type:
- `llm_analyze` - an LLM with structured output (OpenAI or Claude, via rag.llm)
- `heuristic_analyze` - regex rules (retrieval-only mode, tests, and fallback on API errors)
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache

from . import config, llm, prompts
from .retrieve import BRAND_ALIASES, table
from .schemas import Analysis, Filters, SubQuery

log = logging.getLogger(__name__)


# ------------------------------------------------------------------ heuristic
TYPE_WORDS = [
    "lipstick", "lip balm", "lip gloss", "lip liner", "kajal", "eyeliner", "mascara", "eyeshadow", "palette",
    "foundation", "concealer", "primer", "compact", "blush", "highlighter", "bronzer", "nail polish", "nail",
    "shampoo", "conditioner", "hair oil", "hair mask", "hair colour", "hair color", "sunscreen", "face wash",
    "cleanser", "serum", "moisturiser", "moisturizer", "night cream", "day cream", "face cream", "cream", "toner",
    "sheet mask", "face mask", "scrub", "body lotion", "lotion", "body wash", "shower gel", "soap",
    "deodorant", "perfume", "fragrance", "brush", "lashes", "brow", "kit", "combo", "micellar", "wipes",
]
UNSUPPORTED = {
    r"ingredient|contain|made of|formula": "ingredients",
    r"how (do i|to|should i) (use|apply)|apply it|usage|steps": "how to use",
    r"side effect|allerg|safe (for|during)|pregnan|irritat|rash|doctor|medical": "safety / medical advice",
    r"return|refund|exchange": "returns and refunds",
    r"deliver|shipping|ship |cod\b|cash on": "delivery",
    r"expir|shelf life|manufactur": "expiry / manufacturing",
    r"review(s)? say|what do (people|customers) say": "written reviews",
}
SMALLTALK = re.compile(r"^\s*(hi|hello|hey|thanks|thank you|ok|okay|good (morning|evening)|who are you|what can you do)\b", re.I)
CATALOG_HINTS = re.compile(
    r"price|cost|cheap|expensive|budget|under|below|rupee|₹|rs\.?|offer|discount|deal|sale|rating|rated|review|"
    r"popular|bestseller|best ?seller|new arrival|featured|stock|available|shade|colou?r|variant|product|brand|buy|"
    r"recommend|suggest|show|compare|vs|versus|which|skin|hair|lip|eye|face|makeup|nail|spf|matte|waterproof|"
    r"gift|dark circle|acne|pimple|tan|dandruff|frizz|dry|oily|glow|wrinkle|ageing|aging|pigment|dull",
    re.I,
)


@lru_cache(maxsize=1)
def _brand_patterns() -> list[tuple[re.Pattern, str]]:
    brands = sorted(table().brand.unique(), key=len, reverse=True)
    pats = [(re.compile(r"\b" + re.escape(b.lower()).replace(r"\ ", r"\s*") + r"\b"), b) for b in brands]
    pats += [(re.compile(r"\b" + re.escape(k) + r"\b"), v) for k, v in BRAND_ALIASES.items() if k.isalpha()]
    pats.append((re.compile(r"\bl'?or[eé]al\b"), "L'Oreal Paris"))
    return pats


def _brands_in(text: str) -> list[str]:
    t = text.lower()
    out: list[str] = []
    for rx, b in _brand_patterns():
        if rx.search(t) and b not in out:
            out.append(b)
    # "Nykaa Naturals" also matches the bare "nykaa" alias - keep the most specific one
    if any(b.startswith("Nykaa ") and b != "Nykaa Cosmetics" for b in out) and "Nykaa Cosmetics" in out \
            and not re.search(r"nykaa cosmetics", t):
        out.remove("Nykaa Cosmetics")
    return out


def _types_in(text: str) -> list[str]:
    t = text.lower()
    found = []
    for w in sorted(TYPE_WORDS, key=len, reverse=True):
        if re.search(r"\b" + re.escape(w) + r"s?\b", t) and not any(w in f for f in found):
            found.append(w)
    return found


KEYWORDS = [
    "waterproof", "smudge proof", "smudgeproof", "transfer proof", "matte", "satin", "glossy", "shimmer", "liquid",
    "creme", "gel", "mini", "paraben free", "sulphate free", "vegan", "vitamin c", "niacinamide", "hyaluronic",
    "retinol", "salicylic", "tea tree", "aloe", "onion", "rice water", "charcoal", "anti dandruff", "anti-dandruff",
    "red", "nude", "pink", "black", "brown", "maroon", "coral", "berry", "blue", "green", "gold",
]
NOT_CARRIED = [
    "dior", "mac", "m.a.c", "chanel", "clinique", "estee lauder", "fenty", "mamaearth", "minimalist",
    "cetaphil", "the ordinary", "revlon", "elle 18", "swiss beauty", "dove", "himalaya", "bobbi brown",
    "charlotte tilbury", "rare beauty", "innisfree", "laneige", "garnier", "ponds", "pond's", "forest essentials",
    "kama ayurveda", "biore", "dot & key", "dot and key", "myglamm", "lakme salon",
]


def _keywords_in(text: str) -> list[str]:
    t = text.lower()
    out = []
    if m := re.search(r"spf\s*(\d+)", t):
        out.append(f"spf {m.group(1)}")
    for w in sorted(KEYWORDS, key=len, reverse=True):
        if re.search(r"\b" + re.escape(w) + r"\b", t) and not any(w in o for o in out):
            out.append(w)
    return out


def _filters(text: str) -> Filters:
    t = text.lower().replace(",", "")
    brands = _brands_in(text)
    if not brands:
        brands = [b for b in NOT_CARRIED if re.search(r"\b" + re.escape(b) + r"\b", t)][:1]
    f = Filters(brands=brands, product_types=_types_in(text), title_keywords=_keywords_in(text))
    if m := re.search(r"between\s*(?:₹|rs\.?)?\s*(\d+)\s*(?:and|to|-)\s*(?:₹|rs\.?)?\s*(\d+)", t):
        f.price_min, f.price_max = float(m.group(1)), float(m.group(2))
    elif m := re.search(r"(?:under|below|less than|within|upto|up to|max|<)\s*(?:₹|rs\.?|inr)?\s*(\d{2,5})", t):
        f.price_max = float(m.group(1))
    if m := re.search(r"(?:above|over|more than|at least|>)\s*(?:₹|rs\.?|inr)\s*(\d{2,5})", t):
        f.price_min = float(m.group(1))
    if m := re.search(r"(?:rated|rating)\s*(?:above|over|at least|>=?)?\s*(\d(?:\.\d)?)", t) or \
            re.search(r"(\d(?:\.\d)?)\s*\+?\s*(?:stars?|rating)", t):
        val = float(m.group(1))
        if 1 <= val <= 5:
            f.min_rating = val
    if m := re.search(r"(\d{1,2})\s*%\s*(?:off|discount)", t):
        f.min_discount_pct = int(m.group(1))
    tags = []
    if re.search(r"best ?sell", t):
        tags.append("Bestseller")
    if re.search(r"new (arrival|launch)|newly launched|\bnew\b", t):
        tags.append("New arrival")
    if "featured" in t:
        tags.append("Featured")
    f.tags = tags
    f.in_stock_only = bool(re.search(r"in stock|available now", t))
    if re.search(r"\bcombos?\b|\bsets?\b|\bkits?\b", t):
        f.combos = True
    return f


def heuristic_analyze(question: str, history: list[dict] | None = None) -> Analysis:
    q = question.strip()
    unsupported = [label for rx, label in UNSUPPORTED.items() if re.search(rx, q, re.I)]
    f = _filters(q)
    t = q.lower()

    if SMALLTALK.search(q) and not (f.brands or f.product_types):
        return Analysis(scope="smalltalk", standalone_question=q)
    if not (f.brands or f.product_types or CATALOG_HINTS.search(q) or unsupported):
        return Analysis(scope="out_of_scope", standalone_question=q)

    op, sort_by = "lookup", None
    if re.search(r"cheapest|lowest price|least expensive|most affordable|budget", t):
        op, sort_by = "rank", "price_asc"
    elif re.search(r"most expensive|priciest|costliest|highest price", t):
        op, sort_by = "rank", "price_desc"
    elif re.search(r"(best|top|highest)[- ]rated|best rating|highest rating", t):
        op, sort_by = "rank", "rating"
    elif re.search(r"most popular|most reviewed|most ratings|bestselling|best selling", t):
        op, sort_by = "rank", "popularity"
    elif re.search(r"(biggest|big|best|most|highest|maximum|max) (discount|deal|offer)s?|on sale", t):
        op, sort_by = "rank", "discount"
    elif re.search(r"how many|number of|\bcount\b", t):
        op = "count"
    elif re.search(r"\bvs\.?\b|versus|compare|difference between|better[,:]? .* or ", t):
        op = "compare"

    subs: list[SubQuery] = []
    if op == "compare":
        body = re.sub(r"^.*?(compare|difference between)\s*", "", q, flags=re.I)
        parts = [p.strip(" ?.") for p in re.split(r"\s+(?:vs\.?|versus|and|or|with)\s+|,", body, flags=re.I) if p.strip(" ?.")]
        for p in parts[:3]:
            pf = _filters(p)
            subs.append(SubQuery(text=p, filters=Filters(
                brands=pf.brands, product_types=pf.product_types, title_keywords=pf.title_keywords)))
    elif op == "lookup":
        # multi-part: "a Biotique SPF 50 cream and a Biotique face wash" -> one sub-query per product
        parts = [p.strip(" ?.") for p in re.split(r"\s+and\s+(?:an?\s+|the\s+|some\s+)?", q, flags=re.I)]
        if len(parts) > 1 and all(_types_in(p) for p in parts):
            brand = _brands_in(parts[0])
            for p in parts[:3]:
                pf = _filters(p)
                if not pf.brands and brand:
                    pf.brands = brand
                subs.append(SubQuery(text=p, filters=pf))
    if not subs:
        subs = [SubQuery(text=q, filters=f)]
    elif len(subs) == 1:
        op = "lookup"

    return Analysis(
        scope="catalog", standalone_question=q, operation=op, sort_by=sort_by,
        sub_queries=subs, unsupported_parts=unsupported,
    )


# ------------------------------------------------------------------ Claude
def _history_text(history: list[dict]) -> str:
    turns = history[-config.HISTORY_TURNS * 2 :]
    return "\n".join(f"{t['role']}: {t['content'][:600]}" for t in turns)


def llm_analyze(question: str, history: list[dict] | None = None) -> Analysis:
    df = table()
    system = prompts.analyzer_system(sorted(df.brand.unique()), len(df))
    content = question
    if history:
        content = f"<conversation>\n{_history_text(history)}\n</conversation>\n\n<latest_message>\n{question}\n</latest_message>"
    a = llm.structured(system, content, Analysis, model=config.ANALYZER_MODEL, effort=config.ANALYZER_EFFORT)
    if a is None:
        return Analysis(scope="out_of_scope", standalone_question=question)
    if a.scope == "catalog" and not a.sub_queries:
        a.sub_queries = [SubQuery(text=a.standalone_question)]
    return a


def analyze(question: str, history: list[dict] | None = None) -> tuple[Analysis, str]:
    """Returns the analysis and which analyzer produced it."""
    if llm.available()[0]:
        try:
            return llm_analyze(question, history), config.LLM_PROVIDER
        except Exception as e:  # network/API errors degrade to rules rather than failing the chat
            if llm.is_account_problem(e):
                llm.pause(llm.friendly(e))
            log.warning("LLM analyzer failed, using heuristic: %s", e)
    return heuristic_analyze(question, history), "heuristic"
