# Data notes

## Source

`nyka_popular_brands_products_2022_10_16.csv` is a public scrape of nykaa.com brand listing pages, taken on 2022-10-16. It covers the 17 most-viewed brand pages (25 distinct `brand_name` values, because some listings include sub-brands). It is a historical snapshot: prices, ratings and stock reflect that date, not today.

Raw columns: `brand_name, product_id, image_url, in_stock, mrp, price, product_title, rating, rating_count, tags, product_url, listing_page_name, listing_url, listing_page_no`.

## Cleaning

| Step | Rows |
|---|---|
| Raw | 3,663 |
| Drop the one repeated `product_id` (1162054), keeping the first | 3,662 |
| Merge rows identical in every field a shopper sees (brand, title, price, MRP, rating, rating count), keeping the lowest id | 3,652 |

Rows that share a product URL but differ in title or price are kept: they are shade or size variants on one product page (60 such URLs).

## Assumptions

- **Stock.** `in_stock` is either `True` or blank. Blank (300 rows) is read as "not marked as in stock in this snapshot", not as "out of stock".
- **Ratings.** Rating 0.0 with 0 ratings means "no ratings yet", not a zero-star product. For "best rated" questions, products with fewer than 50 ratings are ranked only if fewer than 8 products have 50 or more, so a 5.0 from two ratings can't beat a 4.6 from 20,000.
- **Discount.** `discount_pct = round((mrp − price) / mrp × 100)`. There are no rows where price exceeds MRP.
- **Tags.** `BESTSELLER`, `FEATURED` and `NEW` become "Bestseller", "Featured" and "New arrival".

## The description column

The dataset has no description column, which the brief requires. Every description is composed from the record's own fields by a fixed template (`rag/clean.py → describe`), so it adds no facts that aren't in the row. Derived fields come from rules over the title (`rag/enrich.py`):

- **product_type / category**: an ordered keyword taxonomy, 63 types in 11 categories. 128 products (3.5%) remain "Other".
- **variant**: the text after the last " - " in a title, when it is short (for example "Kay Beauty Gel Eye Pencil - **Blue**").
- **claims**: phrases literally present in the title, such as "SPF 50", "Paraben free", "Waterproof" or "Vitamin C".
- **suitable_for**: only when the title names it, for example "for Dry Skin".
- **is_combo**: "combo", "duo", "kit", "regime" or " + " in the title.

Example:

> Maybelline New York The Colossal Volum Express Mascara is a mascara from Maybelline New York (Makeup). Price ₹404, down from an MRP of ₹449 (10% off, saving ₹45). Customer rating 4.4 out of 5 from 29,639 ratings. Availability: in stock.

## Consequence for the assistant

embellish can answer on brand, product type, shade, price, MRP, discount, rating, number of ratings, store tags, stock and features stated in a product's name. It declines ingredients, usage, benefits, safety, delivery, returns and payments, because none of that is in the data.

Product images are hotlinked from the 2022 URLs in the dataset; the storefront shows a placeholder if one no longer loads.
