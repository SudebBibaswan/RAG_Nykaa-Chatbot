"use client";

import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";
import { ChevronDown, Plus, SearchX, ShieldCheck, Volume2 } from "lucide-react";
import { useState } from "react";
import { useCart } from "@/lib/cart";
import type { RetrievedRecord } from "@/lib/api";
import { img, inr, shortTitle } from "@/lib/format";
import Answer from "./Answer";
import { useEmbellish, type Msg } from "./store";

const REFUSED = new Set(["fallback", "out_of_scope", "withheld"]);

function Progress({ m }: { m: Msg }) {
  const steps = [
    { label: "Reading your question", done: !!m.analysis },
    { label: m.records ? `Found ${m.records.length} matching products` : "Searching the catalogue", done: !!m.records },
    { label: "Writing the answer", done: !!m.text },
  ];
  const active = steps.findIndex((s) => !s.done);
  return (
    <ol className="space-y-1.5 text-[13px] text-mauve" aria-live="polite">
      {steps.map((s, i) => (
        <li key={s.label} className={`flex items-center gap-2 ${i > active && active !== -1 ? "opacity-40" : ""}`}>
          <span
            className={`h-2 w-2 rounded-full ${s.done ? "bg-rani" : i === active ? "animate-pulse bg-marigold" : "bg-line"}`}
          />
          {s.label}
        </li>
      ))}
    </ol>
  );
}

function MiniCard({ r }: { r: RetrievedRecord }) {
  const add = useCart((s) => s.add);
  const added = useCart((s) => s.items.some((i) => i.product_id === r.product_id));
  return (
    <div className="flex w-[200px] shrink-0 gap-2.5 rounded-2xl border border-line bg-white p-2">
      <Link href={`/p/${r.product_id}`} className="shrink-0">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={img(r.image_url, 120)} alt="" className="h-14 w-14 rounded-xl bg-petal object-contain" />
      </Link>
      <div className="min-w-0 flex-1">
        <Link href={`/p/${r.product_id}`} className="line-clamp-2 text-[12px] leading-snug text-kohl hover:text-rani">
          {shortTitle(r.title, r.brand)}
        </Link>
        <div className="mt-1 flex items-center justify-between">
          <span className="text-[13px] font-semibold">{inr(r.price)}</span>
          <button
            onClick={() => add(r)}
            aria-label={`Add ${r.title} to bag`}
            className={`grid h-6 w-6 place-items-center rounded-full transition-colors ${added ? "bg-kohl text-white" : "bg-petal text-rani hover:bg-rani hover:text-white"}`}
          >
            <Plus size={14} strokeWidth={2.5} />
          </button>
        </div>
      </div>
    </div>
  );
}

function Why({ m }: { m: Msg }) {
  const a = m.analysis;
  const maxScore = Math.max(1, ...(m.records ?? []).map((r) => Math.abs(r.score ?? 0)));
  return (
    <div className="mt-2 space-y-3 rounded-2xl bg-powder p-3 text-[12px] leading-relaxed text-kohl-soft">
      {a && (
        <div>
          <p className="font-semibold text-kohl">How I read the question</p>
          <p>
            {a.operation === "lookup" ? "Search" : a.operation === "rank" ? `Rank by ${a.sort_by?.replace("_", " ")}` : a.operation === "count" ? "Count" : "Compare"}
            {a.sub_queries.length > 1 ? `, split into ${a.sub_queries.length} searches` : ""}
            {m.analyzer === "heuristic" ? " (rule-based reader, no API key)" : ""}
          </p>
          {a.sub_queries.map((sq, i) => {
            const f = Object.entries(sq.filters).filter(([, v]) => (Array.isArray(v) ? v.length : v !== null && v !== false));
            return (
              <p key={i} className="mt-1 text-mauve">
                “{sq.text}”{f.length ? `: ${f.map(([k, v]) => `${k.replace(/_/g, " ")} ${Array.isArray(v) ? v.join(", ") : v}`).join("; ")}` : ""}
              </p>
            );
          })}
          {a.unsupported_parts.length > 0 && (
            <p className="mt-1">Not in the catalogue: {a.unsupported_parts.join(", ")}</p>
          )}
        </div>
      )}
      {m.aggregates?.map((g) => (
        <p key={g.label}>
          Exact count from the catalogue: <span className="font-semibold text-kohl">{g.matching_products}</span> products
          {g.matching_products ? `, ${inr(g.min_price!)} to ${inr(g.max_price!)}` : ""}
        </p>
      ))}
      {m.records && m.records.length > 0 && (
        <div>
          <p className="font-semibold text-kohl">Products I read ({m.records.length})</p>
          <ul className="mt-1 space-y-1">
            {m.records.map((r) => (
              <li key={r.product_id} className="flex items-center gap-2">
                <span className="relative h-1.5 w-12 shrink-0 overflow-hidden rounded-full bg-line" title={`relevance ${r.score?.toFixed(2)}`}>
                  <span
                    className={`absolute inset-y-0 left-0 rounded-full ${(r.score ?? 0) >= 0 ? "bg-rani" : "bg-mauve/50"}`}
                    style={{ width: `${Math.max(6, (Math.abs(r.score ?? 0) / maxScore) * 100)}%` }}
                  />
                </span>
                <span className="truncate">{r.title}</span>
                <span className="ml-auto shrink-0 text-[10px] text-mauve">{r.matched.join(" + ")}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {m.reason && <p className="text-mauve">Confidence check: {m.reason}</p>}
      {m.problems && m.problems.length > 0 && (
        <p className="text-rani-deep">Held back because: {m.problems.join("; ")}</p>
      )}
      {m.latencyMs != null && (
        <p className="text-mauve">Answered in {m.latencyMs < 1000 ? `${m.latencyMs} ms` : `${(m.latencyMs / 1000).toFixed(1)} s`}</p>
      )}
    </div>
  );
}

export default function MessageView({ m, onSpeak }: { m: Msg; onSpeak: (m: Msg) => void }) {
  const ask = useEmbellish((s) => s.ask);
  const [why, setWhy] = useState(false);

  if (m.role === "user") {
    return (
      <div className="flex justify-end">
        <p className="max-w-[85%] rounded-[20px] rounded-br-md bg-kohl px-4 py-2.5 text-[14.5px] leading-snug text-white">{m.text}</p>
      </div>
    );
  }

  const refused = m.status && REFUSED.has(m.status);
  const records = m.records ?? [];
  const cited = m.cited?.length
    ? m.cited.map((id) => records.find((r) => r.product_id === id)).filter(Boolean) as RetrievedRecord[]
    : m.status === "retrieval_only"
      ? records.slice(0, 5)
      : [];

  return (
    <div className="text-[14.5px] leading-relaxed text-kohl">
      {m.status === "streaming" && !m.text && <Progress m={m} />}

      {refused ? (
        <div className="rounded-2xl border border-dashed border-rani/50 bg-white/70 p-3.5">
          <div className="flex items-start gap-2.5">
            <SearchX size={18} className="mt-0.5 shrink-0 text-rani" />
            <div>
              <p className="font-semibold">
                {m.status === "out_of_scope" ? "That's outside what I can help with" : m.status === "withheld" ? "I couldn't verify that answer" : "Not in my catalogue"}
              </p>
              <p className="mt-0.5 text-[13.5px] text-kohl-soft">
                {m.status === "withheld"
                  ? "I drafted an answer, but some details didn't match the product records, so I've held it back rather than risk being wrong."
                  : m.text}
              </p>
            </div>
          </div>
        </div>
      ) : m.status === "error" ? (
        <p className="text-rani-deep">{m.text}</p>
      ) : (
        m.text && (
          <>
            {m.status === "retrieval_only" ? (
              <>
                <p className="mb-2 flex items-start gap-2 rounded-xl bg-petal px-3 py-2 text-[12.5px] text-kohl-soft">
                  <ShieldCheck size={15} className="mt-0.5 shrink-0 text-rani" />
                  Answer writing is unavailable right now, so these are the closest matches from the catalogue.
                </p>
                <Answer text={m.text.split("\n").slice(1).join("\n")} records={records} />
              </>
            ) : (
              <Answer text={m.text} records={records} streaming={m.status === "streaming"} />
            )}
          </>
        )
      )}

      {cited.length > 0 && m.status !== "streaming" && (
        <div className="thin-scroll -mx-1 mt-3 flex gap-2 overflow-x-auto px-1 pb-1">
          {cited.map((r) => (
            <MiniCard key={r.product_id} r={r} />
          ))}
        </div>
      )}

      {m.suggestions && m.status !== "streaming" && (refused || m.status === "smalltalk") && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {m.suggestions.map((s) => (
            <button
              key={s}
              onClick={() => ask(s)}
              className="rounded-full border border-line bg-white px-3 py-1.5 text-[12.5px] text-kohl-soft transition-colors hover:border-rani hover:text-rani"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {m.status && m.status !== "streaming" && m.status !== "smalltalk" && (
        <div className="mt-2 flex items-center gap-3 text-[12px] text-mauve">
          {(m.analysis || m.records) && (
            <button onClick={() => setWhy((v) => !v)} className="inline-flex items-center gap-1 hover:text-rani" aria-expanded={why}>
              Why this answer
              <ChevronDown size={14} className={`transition-transform ${why ? "rotate-180" : ""}`} />
            </button>
          )}
          {m.text && m.status !== "error" && (
            <button onClick={() => onSpeak(m)} className="inline-flex items-center gap-1 hover:text-rani" aria-label="Read this answer aloud">
              <Volume2 size={14} /> Listen
            </button>
          )}
        </div>
      )}
      <AnimatePresence initial={false}>
        {why && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <Why m={m} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
