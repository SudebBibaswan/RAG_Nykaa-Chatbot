"use client";

import { ArrowUp } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useEmbellish } from "../embellish/store";

const QUESTIONS = [
  "Which Kay Beauty kajal is waterproof?",
  "Cheapest SPF 50 sunscreen",
  "Best rated Lakme lipstick under ₹500",
  "Compare NYX and Huda Beauty palettes",
  "Paraben free shampoo for dry hair",
];

const BULBS = 18;

export default function Hero({ total }: { total: number }) {
  const slot = useRef<HTMLDivElement>(null);
  const setHeroSlot = useEmbellish((s) => s.setHeroSlot);
  const setOpen = useEmbellish((s) => s.setOpen);
  const ask = useEmbellish((s) => s.ask);
  const [q, setQ] = useState("");
  const [hint, setHint] = useState(0);

  useEffect(() => {
    setHeroSlot(slot.current);
    return () => setHeroSlot(null);
  }, [setHeroSlot]);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const id = setInterval(() => setHint((h) => (h + 1) % QUESTIONS.length), 3200);
    return () => clearInterval(id);
  }, []);

  return (
    <section className="relative overflow-hidden">
      <div className="mx-auto grid max-w-[1320px] items-center gap-10 px-4 pb-16 pt-10 sm:px-6 md:grid-cols-[1.15fr_1fr] md:pb-24 md:pt-16">
        <div>
          <h1 className="display max-w-[12ch] text-[clamp(48px,7.4vw,108px)]">Ask the beauty counter anything.</h1>
          <p className="mt-6 max-w-[48ch] text-[17px] leading-relaxed text-kohl-soft">
            embellish knows all {total.toLocaleString("en-IN")} products on our shelves, from Lakme kajal to Huda Beauty palettes. Ask
            about prices, offers, shades or ratings, and it answers from the catalogue, never from guesswork.
          </p>
          <form
            className="mt-8 flex max-w-[560px] items-center gap-2 rounded-full border border-kohl/15 bg-white p-1.5 pl-5 shadow-[0_12px_40px_-18px_rgba(60,14,46,0.35)] focus-within:border-kohl/40"
            onSubmit={(e) => {
              e.preventDefault();
              if (q.trim()) {
                ask(q);
                setQ("");
              } else setOpen(true);
            }}
          >
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={QUESTIONS[hint]}
              aria-label="Ask embellish a question"
              className="min-w-0 flex-1 bg-transparent py-2.5 text-[16px] outline-none placeholder:text-mauve/80 focus-visible:outline-none"
            />
            <button type="submit" className="flex shrink-0 items-center gap-2 rounded-full bg-rani px-5 py-3 text-[15px] font-medium text-white transition-colors hover:bg-rani-deep">
              Ask
              <ArrowUp size={16} strokeWidth={2.4} className="rotate-45" />
            </button>
          </form>
          <div className="mt-4 flex flex-wrap gap-2">
            {QUESTIONS.slice(0, 3).map((s) => (
              <button key={s} onClick={() => ask(s)} className="rounded-full border border-line bg-white/70 px-3 py-1.5 text-[13px] text-kohl-soft hover:border-rani hover:text-rani">
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* the vanity mirror: bulbs light in sequence once, then embellish sits inside */}
        <div className="relative mx-auto hidden aspect-square w-full max-w-[460px] md:block">
          <div className="absolute inset-[6%] rounded-full border border-kohl/10 bg-[radial-gradient(circle_at_50%_40%,#ffffff_0%,#fdeaf0_55%,#f6dfe7_100%)]" />
          {Array.from({ length: BULBS }).map((_, i) => {
            const a = (i / BULBS) * Math.PI * 2 - Math.PI / 2;
            return (
              <span
                key={i}
                aria-hidden
                className="bulb absolute h-3 w-3 rounded-full bg-marigold shadow-[0_0_14px_4px_rgba(240,162,59,0.45)]"
                style={{
                  left: `calc(50% + ${Math.cos(a) * 47}% - 6px)`,
                  top: `calc(50% + ${Math.sin(a) * 47}% - 6px)`,
                  animationDelay: `${200 + i * 55}ms`,
                }}
              />
            );
          })}
          <div ref={slot} className="absolute left-1/2 top-1/2 aspect-square w-[58%] -translate-x-1/2 -translate-y-1/2" aria-hidden />
          <p className="absolute inset-x-0 bottom-[13%] text-center text-[13px] text-mauve">Tap embellish to start</p>
        </div>
      </div>
    </section>
  );
}
