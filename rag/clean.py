"""Load the raw Nykaa snapshot, clean it, enrich it and compose the description column.

Output: data/products_clean.csv - one row per product, which is also one chunk.
Every rule here is documented in DATA_NOTES.md.
"""
from __future__ import annotations

import json

import pandas as pd

from . import config, enrich

TAG_LABELS = {"BESTSELLER": "Bestseller", "FEATURED": "Featured", "NEW": "New arrival"}


def load_raw() -> pd.DataFrame:
    return pd.read_csv(config.RAW_CSV, dtype=str, keep_default_na=False)


def _tags(raw: str) -> list[str]:
    return [TAG_LABELS[t.strip()] for t in raw.split(",") if t.strip() in TAG_LABELS]


def _fmt_inr(x: float) -> str:
    return f"₹{x:,.0f}"


def describe(r: dict) -> str:
    """Compose a natural-language description strictly from the record's own fields."""
    parts = [f"{r['title']} is a {r['product_type'].lower()} from {r['brand']} ({r['category']})."]
    if r["variant"]:
        parts.append(f"Shade / variant: {r['variant']}.")
    if r["size"]:
        parts.append(f"Size stated in title: {r['size']}.")
    if r["discount_pct"] > 0:
        parts.append(
            f"Price {_fmt_inr(r['price'])}, down from an MRP of {_fmt_inr(r['mrp'])} "
            f"({r['discount_pct']}% off, saving {_fmt_inr(r['mrp'] - r['price'])})."
        )
    else:
        parts.append(f"Price {_fmt_inr(r['price'])} (sold at MRP, no discount).")
    if r["rating_count"] > 0:
        parts.append(f"Customer rating {r['rating']:.1f} out of 5 from {r['rating_count']:,} ratings.")
    else:
        parts.append("No customer ratings yet.")
    if r["tags"]:
        parts.append("Store tags: " + ", ".join(r["tags"]) + ".")
    if r["claims"]:
        parts.append("Features stated in the product name: " + ", ".join(r["claims"]) + ".")
    if r["suitable_for"]:
        parts.append("Named as suitable for: " + ", ".join(r["suitable_for"]) + ".")
    if r["is_combo"]:
        parts.append("This listing is a combo / multi-product set.")
    parts.append(
        "Availability: in stock." if r["in_stock"]
        else "Availability: not marked as in stock in this snapshot."
    )
    return " ".join(parts)


def build() -> pd.DataFrame:
    raw = load_raw()
    n_raw = len(raw)

    df = raw.copy()
    for c in df.columns:
        df[c] = df[c].str.strip()
    df = df[(df.product_title != "") & (df.product_id != "")]

    # 1. Exact duplicate product id -> keep first occurrence.
    df = df.drop_duplicates(subset="product_id", keep="first")
    n_after_id = len(df)

    # 2. Rows identical in every user-visible fact are indistinguishable to a shopper;
    #    keep one (the lowest product id) so they don't crowd retrieval results.
    vis = ["brand_name", "product_title", "price", "mrp", "rating", "rating_count"]
    df = df.sort_values("product_id", key=lambda s: s.astype(int)).drop_duplicates(subset=vis, keep="first")
    n_after_vis = len(df)

    records = []
    for row in df.to_dict("records"):
        title = row["product_title"]
        brand = row["brand_name"]
        price = float(row["price"])
        mrp = float(row["mrp"])
        rating_count = int(float(row["rating_count"] or 0))
        rating = float(row["rating"] or 0)
        ptype, cat = enrich.product_type(title)
        var = enrich.variant(title, brand)
        rec = {
            "product_id": row["product_id"],
            "brand": brand,
            "title": title,
            "base_name": enrich.base_name(title, var),
            "variant": var,
            "product_type": ptype,
            "category": cat,
            "price": price,
            "mrp": mrp,
            "discount_pct": enrich.discount_pct(price, mrp),
            "price_band": enrich.price_band(price),
            "rating": rating if rating_count > 0 else 0.0,
            "rating_count": rating_count,
            "tags": _tags(row["tags"]),
            "claims": enrich.claims(title),
            "suitable_for": enrich.suitability(title),
            "size": enrich.size(title),
            "is_combo": ptype == "Combo / Gift Set" or " + " in title,
            "in_stock": row["in_stock"] == "True",
            "image_url": row["image_url"],
            "product_url": row["product_url"],
            "source_listing": row["listing_page_name"],
        }
        rec["description"] = describe(rec)
        records.append(rec)

    out = pd.DataFrame(records)
    out.attrs["stats"] = {
        "raw_rows": n_raw,
        "after_duplicate_id": n_after_id,
        "after_visible_duplicates": n_after_vis,
        "final": len(out),
    }
    return out


def save(df: pd.DataFrame) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    disk = df.copy()
    for c in ("tags", "claims", "suitable_for"):
        disk[c] = disk[c].map(json.dumps)
    disk.to_csv(config.CLEAN_CSV, index=False)


def load_clean() -> pd.DataFrame:
    df = pd.read_csv(config.CLEAN_CSV, dtype={"product_id": str}, keep_default_na=False)
    for c in ("tags", "claims", "suitable_for"):
        df[c] = df[c].map(json.loads)
    for c in ("is_combo", "in_stock"):
        df[c] = df[c].astype(str) == "True"
    return df
