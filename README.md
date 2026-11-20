# Glossary, with embellish

A Nykaa-style beauty storefront with **embellish**, a retrieval-augmented shopping assistant that answers only from the product catalogue, and says so when the answer isn't there. You can ask by voice and have answers read aloud.

The same pipeline powers the **embellish console** in Streamlit (the assignment's required UI). It shows each answer the way a shopper sees it, next to how it was made: how the question was read, what was searched, every product retrieved with its relevance score, and whether every fact in the answer checks out.

**Assignment:** RAG chatbot, Beauty & Personal Care → Nykaa. [SUBMISSION.md](SUBMISSION.md) maps every requirement in the brief ([docs/RAG_Chatbot_Assignment_Brief.docx](docs/RAG_Chatbot_Assignment_Brief.docx)) to where it is delivered.

## Run it

You need Python 3.12 (via `uv`) and Node 20 or later. The search indexes are not committed, so step 1 builds them.

```bash
git clone https://github.com/Nisarg004/RAG_Nykaa.git && cd RAG_Nykaa
cp .env.example .env                        # then add OPENAI_API_KEY; without it the app runs in retrieval-only mode

# 1. Backend: install, build the indexes (about a minute), start the API
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python scripts/build_index.py
.venv/bin/uvicorn api.main:app --port 8000

# 2. Storefront (second terminal)
cd web && npm install && npm run dev        # http://localhost:3000

# 3. Streamlit console: the assignment's UI (third terminal)
.venv/bin/streamlit run streamlit_app.py    # http://localhost:8501
```

### The AI provider

Answers are written by OpenAI. `.env` holds `OPENAI_API_KEY` (never commit it; it's in `.gitignore`). Restart the API and Streamlit after changing it.

| Job | Model | Why |
|---|---|---|
| Write the answer | `gpt-5.4-mini` | Cheaper and fast; 100% judged faithfulness on the golden set, about 3–5 s per answer |
| Score answers in the eval | `gpt-5.5` | A stronger model judges the writer's faithfulness |
| Read the question | `gpt-5.4-mini`, no reasoning | Correct filters and sub-queries in about 1.6 s |
| Read answers aloud | `gpt-4o-mini-tts` | Natural voice; the browser voice is the fallback |
| Transcribe spoken questions | `gpt-4o-mini-transcribe` | Used by the console's mic and `/api/voice/stt` |

Claude still works: set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY`.

**If the account runs out of credits** (or the key is rejected), nothing breaks. After the first failed call, embellish pauses answer writing for 10 minutes and answers in retrieval-only mode: it shows the closest catalogue products, and the question reader falls back to rules. The console's sidebar says so. Voice output falls back to the browser's speech synthesis. Spoken questions in the console need credits, while the storefront's mic uses the browser's own recognition in Chrome and Edge.

## How it works

```
CSV → clean + enrich → 3,652 product records ─┬→ Chroma (bge-small embeddings)
                                              ├→ BM25 keyword index
                                              └→ pandas table (exact filters, sorts, counts)

question → analyse (gpt-5.4-mini structured output: scope, rewrite, sub-queries, filters, operation)
         → hybrid retrieval per sub-query: dense + BM25 → reciprocal rank fusion → cross-encoder rerank
           (rank and count questions are computed exactly over the filtered table)
         → confidence gate → grounded answer (gpt-5.4-mini, streamed, every product cited)
         → citation and number check → answer, or a clear "not in my catalogue"
```

| Stage | Choice | Why |
|---|---|---|
| Data | 3,663 rows → 3,652 after removing duplicates; a description column composed from real fields only | The CSV has no description; composing one from its own fields adds no invented facts. See `DATA_NOTES.md` |
| Chunking | One product = one chunk (~60–110 tokens), no overlap | Records are short and atomic; splitting would separate a price from its product |
| Embeddings | `BAAI/bge-small-en-v1.5`, 384-d, local via fastembed (ONNX) | Free, fast on a laptop, strong on short English text |
| Vector store | Chroma, persistent, cosine | Simple, supports metadata filters, no server to run |
| Hybrid retrieval | Dense top 30 + BM25 top 30, merged with reciprocal rank fusion | Titles are full of exact tokens (shade codes, "SPF 50", brand names) that keyword search catches and embeddings blur |
| Query decomposition | The analyzer model splits comparisons and multi-part questions into up to 3 sub-queries, each with its own filters | Both optional enhancements from the brief, hybrid and decomposition, are implemented |
| Rerank | `ms-marco-MiniLM-L-6-v2` cross-encoder, keep top 8 | Gives a relevance score usable as a refusal threshold |
| Generation | OpenAI `gpt-5.4-mini`, streamed | Grounded, cited answers in 3–5 s; Claude is a one-line switch |

### Guardrails

1. **Scope gate.** Off-topic questions are refused before retrieval. Questions about a product that ask for something the catalogue lacks (ingredients, safety) are answered in part: embellish says the detail isn't listed, then gives what is.
2. **Confidence gate.** If the best rerank score is below τ = −2.0 (set from the eval sweep), or the filters match nothing, the fallback is returned without calling the model.
3. **Grounded prompt.** Only the supplied records may be used. Every product must be cited as `[P:id]`. Ingredients, usage and medical claims are not allowed.
4. **Output check.** Every cited id must have been retrieved, and every ₹ amount, percentage and x.x/5 rating must trace back to the records (or to simple differences between them, or the shopper's own numbers). Otherwise the draft is withheld.

## Evaluation

```bash
.venv/bin/pytest -q                          # 25 deterministic tests, no key needed
.venv/bin/python eval/run_eval.py --no-llm   # retrieval + guardrails → eval/report_retrieval_only.md
.venv/bin/python eval/run_eval.py            # with credits: adds guard pass rate and LLM-judged faithfulness → eval/report.md
```

On the 34-question golden set:

| Run | Retrieval hit | Unanswerable refused | False refusals | Faithfulness (judged) |
|---|---|---|---|---|
| Retrieval only | 100% (24/24) | 100% (8/8) | 0% | n/a |
| OpenAI (`gpt-5.4-mini` writer, `gpt-5.5` judge) | 100% (24/24) | 100% (8/8) | 0% (0/24) | 100% (26/26) |

The guard withheld no answers in this run. An earlier `gpt-5.5` run had one false refusal (the guard rejecting "rated 0.1 higher", a true difference between two ratings); that is now allowed and unit-tested. Full results are in `eval/report.md`. These are development-set numbers, because the set was used to find and fix bugs. `eval/FAILURE_ANALYSIS.md` documents nine real failures and their fixes.

**Response time.** Typical answers take 3–6 s: about 1.6 s to read the question, under 0.25 s for retrieval, and the rest writing the answer. OpenAI occasionally takes 15–25 s on a single call.

## A 5-minute demo

1. **Problem (about 1 min).** Shoppers on a beauty site ask product questions; a general chatbot invents ingredients and prices. embellish answers only from the 3,652-product Nykaa catalogue snapshot and cites every product.
2. **Demo (3–4 min), on the storefront:**
   - *Factual:* "What's the rating of Kay Beauty Waterproof 24 Hour Kajal?" Point out the citation chips and product cards.
   - *Comparison:* "Compare Maybelline Fit Me foundation and Lakme 9to5 primer". Open **Why this answer** to show the two sub-queries, the hybrid hits and the rerank scores.
   - *Exact ranking:* "Cheapest SPF 50 sunscreen". It is computed over the table, not guessed.
   - *Unanswerable:* "What are the ingredients in Lakme 9to5 primer?" then "Who won the cricket world cup?" Show the "not in my catalogue" state.
   - *Voice:* tap the mic, ask "Best rated Lakme lipstick under 500", and turn on read-aloud.
   - Then switch to the Streamlit console and ask the comparison again. The right-hand pane shows the five steps (read, search, gate, write, verify) light up with timings, the two sub-queries, the products read with their relevance bars, and the grounding check. Drag the confidence slider to show refusals changing live.
3. **Q&A (1–2 min).** `DATA_NOTES.md`, the decision table above and `eval/FAILURE_ANALYSIS.md` cover the likely questions.

## Files

```
rag/            pipeline: clean, enrich, index, retrieve, analyze, prompts, generate, guard, llm, pipeline, config
scripts/        build_index.py
api/main.py     FastAPI: /api/chat (server-sent events), products, facets, home, OpenAI voice
streamlit_app.py  the embellish console
ui/             console styles, WebGL orb and HTML renderers
.streamlit/     console theme
eval/           golden.jsonl, run_eval.py, reports, FAILURE_ANALYSIS.md
tests/          unit tests
web/            Next.js 16 storefront and the embellish widget
data/           products_clean.csv (cleaned, with descriptions); index/ is built locally
docs/           the assignment brief
SUBMISSION.md   requirement-by-requirement checklist against the brief
DATA_NOTES.md   dataset source, cleaning steps and assumptions
```
