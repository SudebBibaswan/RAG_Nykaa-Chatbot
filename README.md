# RAG_Nykaa-Chatbot
Nykaa product RAG chatbot: hybrid retrieval (dense + BM25), cross-encoder reranking and cited, guard-checked answers, with a Next.js storefront, FastAPI backend and Streamlit console.
# RAG Nykaa: a grounded beauty shopping assistant

A retrieval-augmented chatbot for a Nykaa-style beauty storefront. It answers shopper questions **only from a 3,652-product Nykaa catalogue snapshot**, cites every product it mentions, and says so plainly when the answer isn't in the data.

The assistant, called **embellish**, ships in two interfaces that share one pipeline:

- **Storefront** (Next.js): a browsable shop with an embellish chat widget, citation chips, product cards and optional voice input and read-aloud.
- **Console** (Streamlit): the same answers shown next to how they were made: how the question was read, what was searched, every retrieved product with its relevance score, and whether each fact in the answer checks out.

## Features

- **Hybrid retrieval**: dense embeddings plus BM25 keyword search, merged with reciprocal rank fusion, then reranked by a cross-encoder.
- **Query decomposition**: comparisons and multi-part questions are split into up to three sub-queries, each with its own filters.
- **Exact answers where exactness matters**: "cheapest SPF 50 sunscreen" or "how many Lakme lipsticks" is computed over the product table, not guessed by the model.
- **Four guardrails**: scope gate, confidence gate, grounded prompt, and an output check that verifies every cited product, price, percentage and rating.
- **Honest refusals**: ingredients, usage, safety, delivery and returns aren't in the data, so embellish says so instead of inventing them.
- **Works without an API key**: with no key (or no credits) it falls back to retrieval-only mode and shows the closest catalogue products.
- **Voice**: speech-to-text for questions and text-to-speech for answers.
- **Evaluation harness**: a 34-question golden set, an automated runner and a documented failure analysis.

## Architecture

```
CSV → clean + enrich → 3,652 product records ─┬→ Chroma (bge-small embeddings)
                                              ├→ BM25 keyword index
                                              └→ pandas table (exact filters, sorts, counts)

question → analyse (scope, rewrite, sub-queries, filters, operation)
         → hybrid retrieval per sub-query: dense + BM25 → reciprocal rank fusion → cross-encoder rerank
           (rank and count questions are computed exactly over the filtered table)
         → confidence gate → grounded answer (streamed, every product cited)
         → citation and number check → answer, or a clear "not in my catalogue"
```

| Stage | Choice | Why |
|---|---|---|
| Data | 3,663 rows → 3,652 after de-duplication; descriptions composed from real fields only | The CSV has no description column; a fixed template adds no invented facts |
| Chunking | One product = one chunk (~60–110 tokens), no overlap | Records are short and atomic; splitting would separate a price from its product |
| Embeddings | `BAAI/bge-small-en-v1.5` (384-d, local, ONNX via fastembed) | Free, fast on a laptop, strong on short English text |
| Vector store | Chroma, persistent, cosine | Simple, supports metadata filters, no server to run |
| Keyword search | BM25 (`rank-bm25`) | Titles are full of exact tokens (shade codes, "SPF 50", brand names) that embeddings blur |
| Rerank | `ms-marco-MiniLM-L-6-v2` cross-encoder, keep top 8 | Gives a relevance score usable as a refusal threshold |
| Generation | OpenAI (default) or Anthropic, streamed | Switch with `LLM_PROVIDER` |

### Guardrails

1. **Scope gate**: off-topic questions are refused before retrieval.
2. **Confidence gate**: if the best rerank score is below τ = −2.0, or the filters match nothing, a fallback is returned without calling the model.
3. **Grounded prompt**: only the supplied records may be used, and every product must be cited as `[P:id]`.
4. **Output check**: every cited id must have been retrieved, and every ₹ amount, percentage and rating must trace back to the records. Otherwise the draft is withheld.

## Tech stack

| Layer | Tools |
|---|---|
| Backend | Python, FastAPI, Uvicorn, pandas, Pydantic |
| Retrieval | ChromaDB, fastembed, rank-bm25 |
| LLM | OpenAI or Anthropic (configurable) |
| Console | Streamlit |
| Storefront | Next.js, TypeScript |
| Testing | pytest, custom eval runner |

## Getting started

**Prerequisites:** Python 3.12 (via [`uv`](https://docs.astral.sh/uv/)), Node 20 or later, and internet access on first run (the embedding and rerank models are downloaded once).

```bash
git clone https://github.com/<your-username>/RAG_Nykaa.git
cd RAG_Nykaa
cp .env.example .env     # add OPENAI_API_KEY; without it the app runs in retrieval-only mode
```

**1. Backend**

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python scripts/build_index.py     # builds the search indexes, about a minute
.venv/bin/uvicorn api.main:app --port 8000
```

**2. Storefront** (second terminal)

```bash
cd web
npm install
npm run dev          # http://localhost:3000
```

**3. Streamlit console** (third terminal)

```bash
.venv/bin/streamlit run streamlit_app.py     # http://localhost:8501
```

The search indexes aren't committed, so step 1 must build them before the API or console will work.

## Configuration

Copy `.env.example` to `.env`. Never commit `.env`; it is in `.gitignore`.

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `openai` (default) or `anthropic` |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Key for the chosen provider |
| `CHAT_MODEL`, `ANALYZER_MODEL`, `JUDGE_MODEL` | Models for answering, reading the question, and judging the eval |
| `RERANK_THRESHOLD`, `DENSE_K`, `BM25_K`, `RERANK_KEEP` | Retrieval tuning |
| `STOREFRONT_URL`, `CORS_ORIGINS` | Where citation chips link to, and allowed origins |

If the API key is rejected or credits run out, embellish pauses answer writing for 10 minutes and answers in retrieval-only mode. The console sidebar says so.

## API

| Endpoint | Description |
|---|---|
| `GET /api/health` | Service status |
| `GET /api/facets` | Available brands, categories and filters |
| `GET /api/home` | Storefront home content |
| `GET /api/products` | Search and filter products |
| `GET /api/products/{pid}` | One product |
| `POST /api/chat` | Ask embellish a question (server-sent events) |
| `POST /api/voice/tts` | Text to speech |
| `POST /api/voice/stt` | Speech to text |

## Example questions

- *Factual:* "What's the rating of Kay Beauty Waterproof 24 Hour Kajal?"
- *Comparison:* "Compare Maybelline Fit Me foundation and Lakme 9to5 primer"
- *Exact ranking:* "Cheapest SPF 50 sunscreen"
- *Filtered:* "Best rated Lakme lipstick under 500"
- *Unanswerable (refused):* "What are the ingredients in Lakme 9to5 primer?" or "Who won the cricket world cup?"

## Evaluation

```bash
.venv/bin/pytest -q                          # 25 deterministic tests, no key needed
.venv/bin/python eval/run_eval.py --no-llm   # retrieval + guardrails → eval/report_retrieval_only.md
.venv/bin/python eval/run_eval.py            # adds LLM-judged faithfulness → eval/report.md
```

Results on the 34-question golden set:

| Run            | Retrieval hit | Unanswerable refused | False refusals | Faithfulness (judged) |
| -------------- | ------------- | -------------------- | -------------- | --------------------- |
| Retrieval only | 100% (24/24)  | 100% (8/8)           | 0%             | n/a                   |
| With LLM       | 100% (24/24)  | 100% (8/8)           | 0% (0/24)      | 100% (26/26)          |

## Project structure

```
rag/              pipeline: clean, enrich, index, retrieve, analyze, prompts, generate, guard, llm, pipeline, config
scripts/          build_index.py
api/main.py       FastAPI app: chat (SSE), products, facets, home, voice
streamlit_app.py  the embellish console
ui/               console styles, WebGL orb and HTML renderers
.streamlit/       console theme
web/              Next.js storefront and the embellish widget
eval/             golden set, runner, reports, failure analysis
tests/            unit tests
data/             products_clean.csv (index/ is built locally)
docs/             the assignment brief
```

## Limitations

- The catalogue is a 2022 snapshot, so prices, ratings and stock are out of date by design.
- Only fields in the data can be answered. Ingredients, usage, benefits, safety, delivery, returns and payments are declined.
- Product images are hotlinked from 2022 URLs; the storefront shows a placeholder when one no longer loads.
- Typical answers take 3–6 seconds, and an occasional LLM call can take 15–25 seconds.
