"""Deterministic tests: no API key needed. Run with `.venv/bin/pytest -q`."""
import pandas as pd
import pytest

from rag import clean, config, enrich, guard
from rag.analyze import heuristic_analyze
from rag.retrieve import filter_mask, resolve_brands, retrieve, rrf, table
from rag.schemas import Aggregate, Filters, Record


# ------------------------------------------------------------- cleaning / enrichment
def test_clean_counts_and_descriptions():
    df = clean.load_clean()
    assert len(df) == 3652
    assert df.product_id.is_unique
    assert (df.description.str.len() > 50).all()


def test_description_uses_only_record_facts():
    df = clean.load_clean()
    r = df.iloc[0].to_dict()
    d = r["description"]
    assert f"₹{r['price']:,.0f}" in d
    assert r["brand"] in d


@pytest.mark.parametrize(
    "title,ptype",
    [
        ("Maybelline New York Super Stay Matte Ink Liquid Foundation", "Foundation / BB-CC"),
        ("Maybelline New York Super Stay Matte Ink Liquid Lipstick - Lover", "Lipstick"),
        ("Lakme 9 to 5 Primer + Matte Lip Color - Red Coat", "Combo / Gift Set"),
        ("Kay Beauty Gel Eye Pencil - Blue", "Eye Pencil"),
        ("Biotique Bio Kelp Protein Shampoo", "Shampoo"),
        ("NIVEA Body Lotion for Dry Skin, Shea Smooth", "Body Lotion"),
    ],
)
def test_product_type(title, ptype):
    assert enrich.product_type(title)[0] == ptype


def test_claims_and_variant():
    t = "Nykaa Naturals Onion & Fenugreek Hair Growth Paraben and Sulphate Free Shampoo"
    c = enrich.claims(t)
    assert "Paraben free" in c and "Sulphate free" in c and "Hair growth" in c
    assert enrich.claims("Lotus Safe Sun SPF 50 Gel")[0] == "SPF 50"
    assert enrich.variant("Kay Beauty Gel Eye Pencil - Blue", "Kay Beauty") == "Blue"
    assert enrich.discount_pct(75, 100) == 25 and enrich.discount_pct(100, 100) == 0


# ------------------------------------------------------------- retrieval
def test_rrf_rewards_agreement():
    fused = rrf({"dense": ["a", "b", "c"], "bm25": ["b", "d"]})
    assert fused[0][0] == "b"
    assert set(fused[0][2]) == {"dense", "bm25"}


def test_brand_resolution():
    assert resolve_brands(["loreal"]) == ["L'Oreal Paris"]
    assert resolve_brands(["maybelline"]) == ["Maybelline New York"]
    assert resolve_brands(["Dior"]) == []


def test_filters_are_exact():
    f = Filters(brands=["Lakme"], product_types=["lipstick"], price_max=300)
    sub = table()[filter_mask(f)]
    assert len(sub) > 0
    assert (sub.brand == "Lakme").all() and (sub.price <= 300).all()
    assert sub.title.str.lower().str.contains("lip").all()


def test_unknown_brand_falls_back():
    r = retrieve(heuristic_analyze("Dior lipstick"))
    assert not r.confident and not r.records


def test_rank_cheapest_is_exact():
    r = retrieve(heuristic_analyze("cheapest Maybelline mascara"))
    sub = table()[filter_mask(Filters(brands=["Maybelline New York"], product_types=["mascara"]))]
    assert r.records[0].price == sub.price.min()


def test_count_is_exact():
    r = retrieve(heuristic_analyze("How many Biotique shampoos do you have?"))
    sub = table()[filter_mask(Filters(brands=["Biotique"], product_types=["shampoo"]))]
    assert r.aggregates[0].matching_products == len(sub)


def test_off_topic_is_rejected():
    assert heuristic_analyze("who won the cricket world cup").scope == "out_of_scope"
    r = retrieve(heuristic_analyze("best laptop under 50000"))
    assert not r.confident


def test_unsupported_parts_flagged():
    a = heuristic_analyze("what are the ingredients of Lakme 9to5 primer")
    assert "ingredients" in a.unsupported_parts


def test_discount_is_not_count():
    a = heuristic_analyze("waterproof mascara with big discount")
    assert a.operation == "rank" and a.sort_by == "discount"


# ------------------------------------------------------------- guard
def _rec(pid="1", price=299.0, mrp=399.0, rating=4.3) -> Record:
    return Record(
        product_id=pid, brand="Lakme", title="Lakme Test Lipstick", product_type="Lipstick", category="Makeup",
        price=price, mrp=mrp, discount_pct=25, rating=rating, rating_count=100, in_stock=True, is_combo=False,
        image_url="", product_url="", description="",
    )


def test_guard_passes_grounded_answer():
    v = guard.check("Lakme Test Lipstick [P:1] is listed at ₹299 (25% off ₹399), rated 4.3/5.", [_rec()], [])
    assert v.ok, v.problems


def test_guard_rejects_invented_price_and_id():
    v = guard.check("Lakme Test Lipstick [P:1] costs ₹249. Also try [P:999].", [_rec()], [])
    assert not v.ok
    assert any("249" in p for p in v.problems) and any("999" in p for p in v.problems)


def test_guard_allows_price_difference_and_question_numbers():
    recs = [_rec("1", 299), _rec("2", 349)]
    v = guard.check("[P:1] is ₹50 cheaper than [P:2], both under ₹400.", recs, [], "anything under ₹400?")
    assert v.ok, v.problems


def test_guard_requires_citation():
    assert not guard.check("You should try a nice red lipstick.", [_rec()], []).ok


def test_guard_accepts_fallback_and_aggregate():
    assert guard.check(config.FALLBACK, [], []).is_fallback
    agg = Aggregate(label="x", matching_products=30, min_price=126, max_price=509)
    assert guard.check("We have 30 Biotique shampoos, from ₹126 to ₹509.", [_rec()], [agg]).ok


def test_guard_allows_rating_difference_and_bare_question_numbers():
    recs = [_rec("1", 299, rating=4.5), _rec("2", 349, rating=4.4)]
    assert guard.check("[P:1] is rated 0.1 higher than [P:2], both under ₹500.", recs, [], "lipstick under 500").ok


def test_rupee_pattern_ignores_words_ending_in_rs():
    # "colours, " used to match as "Rs ," and crash the number check
    found = [m.group(1) for m in guard.RUPEE_RE.finditer("Available in 3 colours, from ₹1,234 or Rs. 99 (INR 50).")]
    assert found == ["1,234", "99", "50"]
    assert guard.check("It comes in two colours, both lovely.", [], [], "").problems == ["names no cited product"]
