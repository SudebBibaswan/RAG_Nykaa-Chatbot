# Failure analysis

These failures were found while building and evaluating embellish (1–5 in retrieval-only mode, 6–9 with OpenAI generation). Each was reproduced, diagnosed and either fixed or left with a planned improvement. The question IDs refer to `eval/golden.jsonl`.

A caution about the scores: the golden set was used to find and fix bugs, so the retrieval-only results (100% hit rate, 100% refusal accuracy, 0% false refusals) are scores on a development set, not a held-out test. A fresh set of questions written by someone else on the team would give a fairer number.

---

## 1. A multi-part question retrieved only one of its two products (M4)

**Question:** "Find me a Biotique SPF 50 cream and a Biotique face wash"

**What happened:** The context held eight Biotique face washes and no SPF 50 cream. The rule-based analyzer only splits a question into sub-queries when every part names a product type it recognises, and "cream" on its own was not in its vocabulary (only "face cream", "night cream" and so on). The question stayed as one query. That query had both "face wash" and "SPF 50" as filters, and no product matches both, so the keyword filter was relaxed and the face washes won.

**Fix applied:** Added "cream" to the product vocabulary. The question now splits into two sub-queries, each retrieved separately.

**Better fix:** This is why decomposition is done by the LLM analyzer when a key is set. A rule list will always miss some phrasings; the LLM analyzer returns one sub-query per product without needing a vocabulary. The rule-based version is only a fallback.

## 2. "Discount" was read as a counting question

**Question:** "waterproof mascara with big discount"

**What happened:** The analyzer chose the `count` operation, because the regex for counting questions (`how many|number of|count`) matched the "count" inside "dis**count**". The shopper got a product count instead of the mascaras ranked by discount.

**Fix applied:** Word boundaries on the pattern (`\bcount\b`), plus a rule that maps "big/best/biggest discount" to ranking by discount. A unit test (`test_discount_is_not_count`) guards it.

**Lesson:** Substring matching on user text is fragile. The structured LLM analyzer avoids this class of bug.

## 3. A foundation was labelled as a lipstick

**Product:** "Maybelline New York Super Stay Matte Ink Liquid Foundation"

**What happened:** The rule-based product taxonomy matches the first pattern that fits. The rule for "Matte Ink" (a lipstick line) came before the foundation rule, so this foundation was typed as a lipstick and would have shown up in "best rated lipstick" answers.

**Fix applied:** The "ink" rule now excludes titles that contain "foundation". A unit test covers both the lipstick and the foundation.

**Better fix:** Ordered keyword rules are cheap and transparent, but they cannot see product lines. With a richer dataset (a category column from the source site), the type would come from the data rather than from parsing titles. 128 of 3,652 products (3.5%) still have the type "Other" and are found only through their title text.

## 4. An unknown brand returned another brand's products

**Question:** "Dior lipstick" (Dior is not in the catalogue)

**What happened:** In retrieval-only mode, the rule-based analyzer only recognised the 25 brands in the catalogue, so "Dior" was dropped and the search ran as "lipstick". A Nykaa lipstick scored 2.31 on the reranker, above the threshold, and would have been presented as an answer to a Dior question.

**Fix applied:** The LLM analyzer is told to keep unknown brand names in the brand filter. A brand filter that matches nothing returns zero products, which triggers the fallback. The rule-based mode now has a list of common brands the store doesn't carry.

**Lesson:** The confidence threshold alone isn't enough. Semantic similarity between "Dior lipstick" and "Nykaa lipstick" is genuinely high, so an exact filter has to catch it.

## 5. The confidence threshold has a narrow margin

**What we measured** (top cross-encoder score per question):

| Question | Should | Top score |
|---|---|---|
| What is your return policy? | refuse | −11.23 |
| best laptop under 50000 | refuse | −10.59 |
| Who is the CEO of Nykaa? | refuse | **−2.42** |
| red lipstick for a wedding | answer | **−1.24** |
| face wash under 200 | answer | −0.81 |

**What happened:** "Who is the CEO of Nykaa?" scores close to real questions because "Nykaa" appears in hundreds of product names. At the starting threshold of −4.0 it passed the gate. The sweep in `eval/report_retrieval_only.md` showed that −2.0 refuses it while still answering every answerable question, so τ is now −2.0.

**Why it's still a risk:** The gap between −2.42 and −1.24 is about one point. A slightly different off-topic question that mentions a brand could pass, and a vague but legitimate question could be refused.

**Mitigation in place:** The threshold is the second of four guards. With an LLM reading the question, the scope check labels the CEO question out of scope before retrieval (confirmed with gpt-5.4-mini).runs. After generation, the citation and number check withholds any answer that cites a product not retrieved or a price not in the records.

**Planned improvement:** Calibrate τ on a larger set of real shopper questions, or use the score margin between the first and second results instead of an absolute cut-off.

---

The failures below appeared once answers were written by OpenAI (`gpt-5.5`, with `gpt-5.4-mini` reading questions).

## 6. The guard withheld correct answers (M2, R3)

**Questions:** "Show me a waterproof mascara under 500…", "best rated matte lipstick under 500"

**What happened:** Both answers were right, but said "under ₹500". The output check allowed a rupee amount from the shopper's question only when the question itself had a ₹ sign. "500" without one didn't count, so the guard called ₹500 invented and withheld both answers. This is a false positive in the safety layer: it made embellish refuse questions it had answered correctly.

**Fix applied:** Any number in the shopper's question may be echoed back as a price or percentage. Unit-tested.

## 7. A true comparison was withheld (C1)

**Question:** "Compare Maybelline Fit Me foundation and Lakme 9to5 primer"

**What happened:** The answer said one product was "rated 0.1 higher". The check traced ratings only to individual records, not to differences between them, so it withheld a correct answer.

**Fix applied:** Differences between any two ratings and any two discounts in the context are allowed, as price differences already were. Unit-tested. Rules 6 and 7 together show the trade-off in a strict number check: every allowance needs to be deliberate, or correct answers get blocked.

## 8. The model said "cheaper" when two prices were equal (C3)

**Question:** "Which is cheaper, Biotique Bio Kelp shampoo or Biotique Neem shampoo?"

**What happened:** Both products are ₹329. The answer listed both prices correctly, then opened with "Biotique Bio Kelp is cheaper". The LLM judge caught it. The output check could not, because every individual number in the answer was correct. Only the comparison was wrong.

**Fix applied:** The prompt now tells the model to compare the numbers before calling one product cheaper, better rated or more discounted, and to say so when they're equal. Comparison and ranking questions also get medium reasoning effort instead of low. The rerun answered correctly.

**Lesson:** Number checks catch invented facts, not wrong reasoning about real ones. That's why the evaluation also uses an LLM judge.

## 9. The question reader sometimes called an ingredients question off-topic

**Question:** "What are the ingredients in Lakme 9to5 primer?"

**What happened:** Across repeated runs, `gpt-5.4-mini` usually marked this as a catalogue question with an unsupported part (ingredients). Once, it marked it off-topic, and the shopper got a blanket refusal instead of "Ingredients aren't listed, but here are the products, prices and ratings."

**Fix applied:** The reader's prompt now says a question about a product stays in scope even when it asks for something the catalogue lacks. "Off-topic" is reserved for questions with no product at all.

## Evaluation-harness bugs found on the way

Two failures in the first OpenAI run were bugs in the evaluation, not the assistant. Both are fixed in `eval/run_eval.py`:

- The partial-answer check looked for "isn't in the catalogue" with a straight apostrophe; the model writes a curly one ("isn’t"), and sometimes "aren’t".
- The LLM judge saw the product records but not the exact-count block, so it called a correct "30 Biotique shampoos" unfaithful.

## Account and operations

The OpenAI account ran out of credits during evaluation. Every call then returned `429 – no credits remaining`, and each question waited about 17 seconds through retries before failing. That's now handled. The first quota or key error pauses answer writing for 10 minutes, and the app answers immediately in retrieval-only mode, so a live demo can't hang on a billing problem.

---

## Known limitations (not bugs)

- **Variant crowding.** Shade variants of one product (for example 12 shades of one lipstick) can fill the context and push out other products. For a "show me shades" question that's right; for "recommend a lipstick" it reduces variety. Improvement: keep at most two records per product name unless the question asks about shades.
- **No product knowledge beyond the name.** Ingredients, how to use, benefits and suitability are not in the dataset, so embellish declines them. This is deliberate. Improvement: add a dataset with real product descriptions.
- **The snapshot is from 2022-10-16.** Prices and stock are historical, and the assistant says "listed at" rather than promising current prices.
