"""Typed contracts shared by the analyzer, retriever, generator and the API."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Filters(BaseModel):
    brands: list[str] = Field(default_factory=list, description="Brand names mentioned, as written by the user")
    product_types: list[str] = Field(
        default_factory=list, description="Product kinds, e.g. 'lipstick', 'shampoo', 'sunscreen', 'kajal'"
    )
    title_keywords: list[str] = Field(
        default_factory=list,
        description="Words that must appear in the product name, e.g. 'waterproof', 'matte', 'red', 'SPF 50', 'paraben free'",
    )
    price_min: Optional[float] = Field(None, description="Lower price bound in rupees")
    price_max: Optional[float] = Field(None, description="Upper price bound in rupees")
    min_rating: Optional[float] = Field(None, description="Minimum customer rating out of 5")
    min_discount_pct: Optional[int] = Field(None, description="Minimum discount percentage")
    tags: list[Literal["Bestseller", "Featured", "New arrival"]] = Field(default_factory=list)
    in_stock_only: bool = False
    combos: Optional[bool] = Field(None, description="True = only combos/sets, False = exclude combos, null = either")

    def is_empty(self) -> bool:
        return self == Filters()


class SubQuery(BaseModel):
    text: str = Field(description="A self-contained search query for one part of the question")
    filters: Filters = Field(default_factory=Filters)


class Analysis(BaseModel):
    scope: Literal["catalog", "smalltalk", "out_of_scope"] = Field(
        description="catalog = about products in the store; smalltalk = greeting/thanks; out_of_scope = anything else"
    )
    standalone_question: str = Field(description="The question rewritten to stand alone, resolving references to earlier turns")
    operation: Literal["lookup", "compare", "rank", "count"] = "lookup"
    sort_by: Optional[Literal["price_asc", "price_desc", "rating", "popularity", "discount"]] = None
    sub_queries: list[SubQuery] = Field(default_factory=list, description="1-3 sub-queries; one per item for comparisons")
    unsupported_parts: list[str] = Field(
        default_factory=list,
        description="Parts of the question the catalogue cannot answer (ingredients, usage, delivery, returns, medical advice)",
    )


class Record(BaseModel):
    product_id: str
    brand: str
    title: str
    product_type: str
    category: str
    variant: str = ""
    price: float
    mrp: float
    discount_pct: int
    rating: float
    rating_count: int
    tags: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)
    suitable_for: list[str] = Field(default_factory=list)
    in_stock: bool
    is_combo: bool
    image_url: str
    product_url: str
    description: str
    score: Optional[float] = None       # cross-encoder relevance
    rrf: Optional[float] = None
    matched: list[str] = Field(default_factory=list)  # which retrievers found it: dense / bm25 / table


class Aggregate(BaseModel):
    """Exact facts computed over the filtered table (not from retrieval)."""
    label: str
    matching_products: int
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    brands: list[str] = Field(default_factory=list)


class Retrieval(BaseModel):
    records: list[Record]
    aggregates: list[Aggregate] = Field(default_factory=list)
    top_score: Optional[float] = None
    confident: bool = False
    reason: str = ""
