"""Post-generation grounding check.

An answer passes only if:
- every cited [P:id] is one of the retrieved records,
- it cites at least one product (unless it is the fallback, or it is answering from an aggregate),
- every rupee amount, percentage and x.x/5 rating it states can be traced to the cited
  records, the aggregates, simple price differences between them, or the user's own question.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import config
from .schemas import Aggregate, Record

CITE_RE = re.compile(r"\[P:(\d+)\]")
RUPEE_RE = re.compile(r"(?:₹|\brs\b\.?|\binr\b)\s?(\d[\d,]*(?:\.\d+)?)", re.I)
PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s?%")
RATING_RE = re.compile(r"(\d(?:\.\d)?)\s?(?:/\s?5|out of 5|stars?|★)", re.I)


@dataclass
class Verdict:
    ok: bool
    is_fallback: bool = False
    cited: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def _allowed_numbers(records: list[Record], aggregates: list[Aggregate], question: str):
    money, pct, rating = set(), set(), set()
    prices = []
    for r in records:
        money |= {r.price, r.mrp, r.mrp - r.price}
        prices.append(r.price)
        pct.add(float(r.discount_pct))
        rating.add(round(r.rating, 1))
    ratings = [round(r.rating, 1) for r in records]
    for i, a in enumerate(ratings):  # "rated 0.1 higher"
        for b in ratings[i + 1 :]:
            rating.add(round(abs(a - b), 1))
    for i, a in enumerate(records):  # "5% more off"
        for b in records[i + 1 :]:
            pct.add(float(abs(a.discount_pct - b.discount_pct)))
    for a in aggregates:
        if a.min_price is not None:
            money |= {a.min_price, a.max_price}
    for i, a in enumerate(prices):
        for b in prices[i + 1 :]:
            money.add(abs(a - b))
    if len(prices) > 1:
        money.add(sum(prices))  # "both together cost ..."
    for m in RUPEE_RE.finditer(question):
        money.add(_num(m.group(1)))
    # bare numbers too: "under 500" is often echoed back as "under ₹500"
    for m in re.finditer(r"\d[\d,]*(?:\.\d+)?", question):
        money.add(_num(m.group(0)))
        pct.add(_num(m.group(0)))
    for m in PCT_RE.finditer(question):
        pct.add(_num(m.group(1)))
    for m in re.finditer(r"\d(?:\.\d)?", question):
        rating.add(float(m.group(0)))
    return money, pct, rating


def is_fallback(answer: str) -> bool:
    a = answer.strip().strip('"')
    return a.startswith(config.FALLBACK[:60]) or a.startswith(config.OUT_OF_SCOPE[:60])


def check(answer: str, records: list[Record], aggregates: list[Aggregate], question: str = "") -> Verdict:
    if is_fallback(answer):
        return Verdict(ok=True, is_fallback=True)

    ids = {r.product_id for r in records}
    cited = list(dict.fromkeys(CITE_RE.findall(answer)))
    problems = [f"cites P:{c}, which was not retrieved" for c in cited if c not in ids]

    if not cited and not aggregates:
        problems.append("names no cited product")

    money, pct, rating = _allowed_numbers(records, aggregates, question)
    for m in RUPEE_RE.finditer(answer):
        v = _num(m.group(1))
        if not any(abs(v - x) < 0.51 for x in money):
            problems.append(f"₹{m.group(1)} is not in the records")
    for m in PCT_RE.finditer(answer):
        v = _num(m.group(1))
        if not any(abs(v - x) < 0.51 for x in pct):
            problems.append(f"{m.group(0)} is not in the records")
    for m in RATING_RE.finditer(answer):
        v = _num(m.group(1))
        if v != 5 and not any(abs(v - x) < 0.051 for x in rating):
            problems.append(f"rating {m.group(1)} is not in the records")

    return Verdict(ok=not problems, cited=cited, problems=problems)
