# Submission checklist: what was asked vs. what is included

This maps every requirement in the assignment brief ([docs/RAG_Chatbot_Assignment_Brief.docx](docs/RAG_Chatbot_Assignment_Brief.docx)) to where it is delivered in this repository.

**Use case:** Nykaa (Beauty & Personal Care). **embellish** is a product-discovery assistant for shoppers on a beauty store. It answers questions about brands, prices, discounts, ratings, shades and stock, using only the store's catalogue, and says so when the answer isn't there.

Status key: ✅ done · ➕ done, beyond what was asked · ⚠️ done with a caveat (explained)

---

## 1–2. Problem statement and use case

| Asked | Status | Where |
|---|---|---|
| Choose one industry and company | ✅ | Beauty & Personal Care → Nykaa |
| A realistic user and a clear purpose | ✅ | Online beauty shoppers. Purpose: product discovery, comparison and price/offer questions without invented facts. [README.md](README.md), demo script under "A 5-minute demo" |

## 3. Dataset

| Asked | Status | Where |
|---|---|---|
| Dataset from Kaggle or another credible public source | ✅ | `nyka_popular_brands_products_2022_10_16.csv`: a public scrape of nykaa.com brand listing pages, taken 2022-10-16. 3,663 rows, 25 brands. Source described in [DATA_NOTES.md](DATA_NOTES.md) |
| A meaningful **description** column per record | ⚠️ | The raw CSV has none. A description is composed for every product from its own fields (brand, type, price, MRP, discount, rating, stock, tags, claims in the title) by a fixed template, so it adds no invented facts. Code: [rag/clean.py](rag/clean.py) `describe`, [rag/enrich.py](rag/enrich.py). Output: [data/products_clean.csv](data/products_clean.csv) |
| Useful fields (name, category, brand, price, features…) | ✅ | Title, brand, product type (63 types), category (11), shade/variant, price, MRP, discount %, rating, rating count, stock, tags, claims (e.g. "SPF 50", "Waterproof"), suitable-for, combo flag |
| Clean data; remove duplicate, empty, irrelevant records | ✅ | 3,663 → 3,652 rows: one repeated `product_id` dropped, 10 duplicate listings merged. Steps and counts in [DATA_NOTES.md](DATA_NOTES.md) |
| Track source and assumptions | ✅ | [DATA_NOTES.md](DATA_NOTES.md): stock, zero ratings, discount formula, tags, what the assistant can and cannot answer |
| Enough content for meaningful retrieval (or ≥50 synthetic records) | ✅ | 3,652 real records; no synthetic data used |

## 4. What to build

| Asked | Status | Where |
|---|---|---|
| Prepare and load the dataset | ✅ | [rag/clean.py](rag/clean.py), [scripts/build_index.py](scripts/build_index.py) |
| Chunking strategy, with chunk size / overlap explained | ✅ | One product = one chunk (~60–110 tokens), no overlap: records are short and atomic, and splitting would separate a price from its product. README → "How it works" |
| Embeddings in a vector store | ✅ | `BAAI/bge-small-en-v1.5` (384-d, local via fastembed) in a persistent Chroma collection (cosine). [rag/index.py](rag/index.py) |
| Retrieval of relevant chunks | ✅ | Hybrid dense + BM25, reciprocal rank fusion, cross-encoder rerank (`ms-marco-MiniLM-L-6-v2`), exact metadata filters. [rag/retrieve.py](rag/retrieve.py) |
| Retrieved context + question → LLM → grounded answer | ✅ | OpenAI `gpt-5.4-mini`, streamed; every product cited as `[P:id]`. [rag/generate.py](rag/generate.py), [rag/prompts.py](rag/prompts.py). Claude supported via `LLM_PROVIDER=anthropic` |
| Simple **Streamlit** UI with chat input and visible responses | ✅ ➕ | [streamlit_app.py](streamlit_app.py). Chat on the left. The right pane shows how the question was read, the sub-queries, every retrieved product with its relevance score, stage timings and the grounding check. A live slider changes the confidence threshold |
| Fallback when the dataset can't answer | ✅ | Three layers: an off-topic gate before retrieval, a confidence gate on the rerank score (τ = −2.0), and an output check that withholds any answer whose products or numbers can't be traced to the records. [rag/guard.py](rag/guard.py), [rag/pipeline.py](rag/pipeline.py) |
| Short pipeline explanation (data → chunking → embeddings → vector store → retrieval → LLM → answer) | ✅ | README → "How it works" (diagram and decision table) |
| Custom frontend (not required) | ➕ | Next.js storefront with the embellish chat widget, voice input and read-aloud. [web/](web/), API in [api/main.py](api/main.py) |

## 5. RAG techniques

| Asked | Status | Where |
|---|---|---|
| Working baseline RAG pipeline (mandatory) | ✅ | [rag/pipeline.py](rag/pipeline.py) |
| At least one enhancement: Hybrid RAG | ✅ | Dense top 30 + BM25 top 30, merged with reciprocal rank fusion, then reranked. [rag/retrieve.py](rag/retrieve.py) |
| At least one enhancement: Query decomposition | ✅ | Comparisons and multi-part questions are split into up to 3 sub-queries, each with its own filters and retrieval, and the evidence is combined. [rag/analyze.py](rag/analyze.py) |
| | ➕ | Both enhancements are implemented, plus exact computed answers for "cheapest / best rated / how many" questions |

## 6. Test and evaluate

| Asked | Status | Where |
|---|---|---|
| At least 3–4 test questions across factual, comparison, multi-part, unanswerable | ✅ ➕ | 34 questions: 8 factual, 5 comparison, 5 multi-part, 6 filter/rank/count, 10 unanswerable or partly answerable. [eval/golden.jsonl](eval/golden.jsonl) |
| Check that retrieved chunks contain the needed evidence | ✅ | Retrieval hit rate: 100% (24/24). [eval/report.md](eval/report.md) |
| Evaluate correctness, relevance, faithfulness, unsupported-question handling | ✅ | Correct behaviour 34/34; faithfulness 100% (26/26, judged by `gpt-5.5`); unanswerable refused 100% (8/8); false refusals 0% (0/24); threshold sweep. [eval/report.md](eval/report.md), [eval/run_eval.py](eval/run_eval.py) |
| Document at least two failure cases and how to improve | ✅ ➕ | Nine real failures found during development, each with cause, fix and result, plus known limitations. [eval/FAILURE_ANALYSIS.md](eval/FAILURE_ANALYSIS.md) |
| | ➕ | 25 automated unit tests: [tests/test_pipeline.py](tests/test_pipeline.py) |

## 7. Deliverables

| Asked | Status | Where |
|---|---|---|
| Working Streamlit RAG chatbot | ✅ | `streamlit run streamlit_app.py` (setup in [README.md](README.md)) |
| Live 5-minute presentation | ⚠️ | Delivered live by the group. A timed demo script and suggested questions are in [README.md](README.md) → "A 5-minute demo" |
| Group of 4–5 students | — | Organisational; not part of the code |

## Rubric coverage

| Criterion | Weight | Evidence |
|---|---|---|
| Problem definition and dataset quality | 15% | Sections 1–3 above; [DATA_NOTES.md](DATA_NOTES.md) |
| RAG pipeline: chunking, embeddings, vector store, retrieval, generation | 50% | Sections 4–5; [rag/](rag/) |
| Grounded answers and unsupported questions | 15% | Three-layer fallback, citation and number check; 8/8 refusals, 26/26 faithful |
| Streamlit UI and usability | 10% | [streamlit_app.py](streamlit_app.py) with a pipeline-visibility pane |
| Testing, evaluation and error analysis | 10% | [eval/](eval/), [tests/](tests/) |

## Known caveats

- **Description column.** It is composed from the record's own fields because the source had none. It is honest, but less rich than a hand-written description. Questions about ingredients, usage or safety are declined because that data doesn't exist.
- **Historical snapshot.** Prices, ratings and stock are as of 2022-10-16. Some product image URLs no longer load; the storefront shows a placeholder.
- **Development-set numbers.** The 34 golden questions were also used to find and fix bugs, so the scores are optimistic for unseen questions.
- **Latency.** Typical answers take 3–6 s. Occasional OpenAI-side slowdowns can reach 15–25 s.
