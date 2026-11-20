"""Evaluate the pipeline on eval/golden.jsonl and write eval/report.md.

    .venv/bin/python eval/run_eval.py            # full run (uses Claude if a key is set)
    .venv/bin/python eval/run_eval.py --no-llm   # retrieval + guardrails only

Metrics
- retrieval hit rate: every expected item appears in the retrieved context
- exactness: cheapest = true minimum, counts = true count (computed from the table)
- refusal accuracy: unanswerable questions end in a refusal
- partial handling: questions with an unsupported part flag that part
- false-refusal rate: answerable questions that were wrongly refused
- with Claude: guard pass rate and an LLM-judged faithfulness score
Then a sweep of the rerank threshold over the recorded scores.
"""
from __future__ import annotations

import argparse
import re
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pydantic import BaseModel  # noqa: E402

from rag import config, pipeline  # noqa: E402
from rag.retrieve import filter_mask, table  # noqa: E402
from rag.schemas import Filters  # noqa: E402

REFUSED = {"fallback", "out_of_scope", "withheld"}
PARTIAL_MARKERS = ["isn't in", "is not in", "not in the catalogue", "not in our catalogue", "doesn't include",
                   "don't have", "do not have", "not listed", "can't tell", "cannot tell", "not available in",
                   "no information", "don't list", "doesn't list", "isn't listed"]


class Judgement(BaseModel):
    faithful: bool
    reason: str


def judge(question: str, answer: str, records: list[dict], aggregates: list[dict]) -> Judgement | None:
    from rag import llm
    from rag.prompts import format_record
    from rag.schemas import Record

    from rag.prompts import format_aggregate
    from rag.schemas import Aggregate

    ctx = "\n\n".join([format_aggregate(Aggregate(**a)) for a in aggregates] + [format_record(Record(**r)) for r in records])
    return llm.structured(
        "You check whether a shopping assistant's answer is grounded in the product records it was given.",
        f"<records>\n{ctx}\n</records>\n<question>{question}</question>\n<answer>{answer}</answer>\n\n"
        "Is every factual claim in the answer supported by the records? Ignore tone and wording. "
        "faithful=false if the answer states any fact (price, rating, ingredient, benefit, stock, "
        "suitability) not present in the records.",
        Judgement,
        model=config.JUDGE_MODEL,
        effort="low",
    )


def titles_hit(groups: list[list[str]], records: list[dict]) -> bool:
    ts = [r["title"].lower() for r in records]
    return all(any(all(term in t for term in g) for t in ts) for g in groups)


def run(use_llm: bool) -> list[dict]:
    if not use_llm:
        for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY"):
            os.environ.pop(k, None)
    items = [json.loads(line) for line in (ROOT / "eval/golden.jsonl").read_text().splitlines() if line.strip()]
    df = table()
    results = []
    for it in items:
        t0 = time.perf_counter()
        out = pipeline.answer(it["q"])
        fin = out["final"]
        src = out.get("sources", {})
        recs = src.get("records", [])
        an = out["analysis"]["analysis"]
        res = {
            **it,
            "status": fin["status"],
            "answer": fin["answer"],
            "analyzer": out["analysis"]["analyzer"],
            "top_score": src.get("top_score"),
            "table_backed": any(a["matching_products"] > 0 for a in src.get("aggregates", [])),
            "n_records": len(recs),
            "unsupported": an.get("unsupported_parts", []),
            "problems": fin.get("problems", []),
            "reason": fin.get("reason", ""),
            "secs": round(time.perf_counter() - t0, 2),
        }
        checks = []
        if "hits" in it:
            checks.append(titles_hit(it["hits"], recs))
        if "first_min" in it:
            sub = df[filter_mask(Filters(**it["first_min"]))]
            checks.append(bool(recs) and recs[0]["price"] == sub.price.min())
        if "count" in it:
            sub = df[filter_mask(Filters(**it["count"]))]
            aggs = src.get("aggregates", [])
            checks.append(bool(aggs) and aggs[0]["matching_products"] == len(sub))
        res["retrieval_ok"] = all(checks) if checks else None

        if it["expect"] == "refuse":
            res["behaviour_ok"] = fin["status"] in REFUSED
        elif it["expect"] == "partial":
            text = fin["answer"].lower().replace("\u2019", "'")
            res["behaviour_ok"] = bool(res["unsupported"]) and (
                fin["status"] in REFUSED or fin["status"] == "retrieval_only"
                or any(m in text for m in PARTIAL_MARKERS)
                or re.search(r"(n't|not) (in|included in|listed in|available in|part of) (the|our|this) catalogue", text) is not None
            )
        else:
            res["behaviour_ok"] = fin["status"] not in REFUSED and fin["status"] != "error"

        if use_llm and fin["status"] == "answered":
            try:
                j = judge(it["q"], fin["answer"], recs, src.get("aggregates", []))
                res["faithful"], res["judge_reason"] = (j.faithful, j.reason) if j else (None, "")
            except Exception as e:  # judge failure shouldn't sink the run
                res["faithful"], res["judge_reason"] = None, f"judge error: {e}"
        results.append(res)
        mark = "✓" if res["behaviour_ok"] and res["retrieval_ok"] is not False else "✗"
        print(f"{mark} {it['id']:4} {fin['status']:15} {res['secs']:5}s  {it['q'][:70]}")
    return results


def sweep(results: list[dict]) -> list[dict]:
    """Replay the confidence gate at different thresholds using recorded rerank scores."""
    rows = []
    for tau in [-8, -6, -5, -4, -3, -2, -1, 0, 1, 2]:
        refuse_ok = false_refuse = n_ref = n_ans = 0
        for r in results:
            if r["status"] in ("out_of_scope", "smalltalk") or r["expect"] == "partial":
                continue
            gated = (not r["table_backed"]) and (r["top_score"] is None or r["top_score"] < tau)
            refused = gated or r["status"] in REFUSED and r["top_score"] is None
            if r["expect"] == "refuse":
                n_ref += 1
                refuse_ok += refused
            else:
                n_ans += 1
                false_refuse += refused
        rows.append({"tau": tau, "refusal_acc": refuse_ok / max(n_ref, 1), "false_refusal": false_refuse / max(n_ans, 1),
                     "n_refuse_items_reaching_gate": n_ref})
    return rows


def pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def report(results: list[dict], sw: list[dict], use_llm: bool) -> str:
    ans = [r for r in results if r["expect"] == "answer"]
    ref = [r for r in results if r["expect"] == "refuse"]
    par = [r for r in results if r["expect"] == "partial"]
    ret = [r for r in ans if r["retrieval_ok"] is not None]
    lines = [
        "# embellish evaluation report",
        "",
        f"Mode: **{config.LLM_PROVIDER + ' (' + config.CHAT_MODEL + ', analyzer ' + config.ANALYZER_MODEL + ')' if use_llm else 'retrieval-only (no API key, heuristic analyzer)'}**  ",
        f"Questions: {len(results)} ({len(ans)} answerable, {len(par)} partly answerable, {len(ref)} unanswerable)  ",
        f"Rerank threshold τ = {config.RERANK_THRESHOLD}",
        "",
        "## Summary",
        "",
        "| Metric | Result |",
        "|---|---|",
        f"| Retrieval hit rate (expected products in context, incl. exact cheapest/count) | {pct(sum(r['retrieval_ok'] for r in ret) / len(ret))} ({sum(r['retrieval_ok'] for r in ret)}/{len(ret)}) |",
        f"| Refusal accuracy on unanswerable questions | {pct(sum(r['behaviour_ok'] for r in ref) / len(ref))} ({sum(r['behaviour_ok'] for r in ref)}/{len(ref)}) |",
        f"| Unsupported part flagged on partly answerable questions | {pct(sum(r['behaviour_ok'] for r in par) / len(par))} ({sum(r['behaviour_ok'] for r in par)}/{len(par)}) |",
        f"| False-refusal rate on answerable questions | {pct(sum(not r['behaviour_ok'] for r in ans) / len(ans))} ({sum(not r['behaviour_ok'] for r in ans)}/{len(ans)}) |",
    ]
    if use_llm:
        answered = [r for r in results if r["status"] == "answered"]
        judged = [r for r in answered if r.get("faithful") is not None]
        withheld = [r for r in results if r["status"] == "withheld"]
        lines += [
            f"| Answers withheld by the citation/number guard | {len(withheld)} |",
            f"| LLM-judged faithfulness of shown answers | {pct(sum(r['faithful'] for r in judged) / max(len(judged), 1))} ({sum(r['faithful'] for r in judged)}/{len(judged)}) |",
        ]
    groups = sorted({r["group"] for r in results})
    lines += ["", "## By question group", "", "| Group | Correct behaviour | Retrieval hit |", "|---|---|---|"]
    for g in groups:
        rs = [r for r in results if r["group"] == g]
        rt = [r for r in rs if r["retrieval_ok"] is not None]
        lines.append(
            f"| {g} | {sum(r['behaviour_ok'] for r in rs)}/{len(rs)} | "
            + (f"{sum(r['retrieval_ok'] for r in rt)}/{len(rt)}" if rt else "–") + " |"
        )
    lines += [
        "",
        "## Threshold sweep",
        "",
        "Replays the confidence gate over the recorded top rerank scores (questions already stopped by the scope "
        "gate are excluded, since they never reach retrieval).",
        "",
        "| τ | Refusal accuracy (gate-reaching unanswerables) | False-refusal rate |",
        "|---|---|---|",
    ]
    for s in sw:
        lines.append(f"| {s['tau']} | {pct(s['refusal_acc'])} (n={s['n_refuse_items_reaching_gate']}) | {pct(s['false_refusal'])} |")
    lines += ["", "## Every question", "", "| ID | Question | Status | Top score | Behaviour | Retrieval |", "|---|---|---|---|---|---|"]
    for r in results:
        sc = "–" if r["top_score"] is None else f"{r['top_score']:.2f}"
        rt = "–" if r["retrieval_ok"] is None else ("✓" if r["retrieval_ok"] else "✗")
        lines.append(f"| {r['id']} | {r['q']} | {r['status']} | {sc} | {'✓' if r['behaviour_ok'] else '✗'} | {rt} |")
    fails = [r for r in results if not r["behaviour_ok"] or r["retrieval_ok"] is False or r.get("faithful") is False]
    lines += ["", "## Failures in this run", ""]
    if not fails:
        lines.append("None.")
    for r in fails:
        lines += [f"**{r['id']} – {r['q']}**  ", f"status `{r['status']}`, top score {r['top_score']}, unsupported {r['unsupported']}  ",
                  f"answer: {r['answer'][:300]}  "]
        if r.get("judge_reason"):
            lines.append(f"judge: {r['judge_reason']}  ")
        if r["problems"]:
            lines.append(f"guard: {r['problems']}  ")
        lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true")
    args = ap.parse_args()
    use_llm = config.has_llm() and not args.no_llm
    results = run(use_llm)
    sw = sweep(results)
    suffix = "" if use_llm else "_retrieval_only"
    (ROOT / f"eval/report{suffix}.md").write_text(report(results, sw, use_llm))
    (ROOT / f"eval/results{suffix}.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nwrote eval/report{suffix}.md")
