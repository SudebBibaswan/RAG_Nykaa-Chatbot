"use client";

import { useEmbellish } from "../embellish/store";

/** A quiet prompt above the grid that turns the current listing into a question. */
export default function AskAboutResults({ title }: { title: string }) {
  const ask = useEmbellish((s) => s.ask);
  const subject = title.startsWith("Results for") ? title.replace("Results for ", "") : title.toLowerCase();
  const questions = [`Best rated ${subject}`, `Cheapest ${subject} with good ratings`];
  return (
    <div className="mb-8 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-2xl bg-petal/70 px-4 py-3 text-[14px]">
      <span className="text-kohl-soft">Can&apos;t decide? Ask embellish:</span>
      {questions.map((q) => (
        <button key={q} onClick={() => ask(q)} className="rounded-full bg-white px-3 py-1 text-[13px] text-rani ring-1 ring-line hover:ring-rani">
          {q}
        </button>
      ))}
    </div>
  );
}
