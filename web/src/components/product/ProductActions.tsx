"use client";

import { Check, ShoppingBag } from "lucide-react";
import { useEffect } from "react";
import type { Product } from "@/lib/api";
import { useCart } from "@/lib/cart";
import { inr } from "@/lib/format";
import { useEmbellish } from "../embellish/store";

export function AddToBag({ p }: { p: Product }) {
  const add = useCart((s) => s.add);
  const setOpen = useCart((s) => s.setOpen);
  const inBag = useCart((s) => s.items.find((i) => i.product_id === p.product_id)?.qty ?? 0);
  return (
    <div className="flex flex-wrap gap-3">
      <button
        onClick={() => add(p)}
        className="inline-flex min-w-[200px] items-center justify-center gap-2 rounded-full bg-rani px-6 py-3.5 text-[15px] font-medium text-white transition-colors hover:bg-rani-deep"
      >
        <ShoppingBag size={18} /> {inBag ? "Add another" : "Add to bag"}
      </button>
      {inBag > 0 && (
        <button onClick={() => setOpen(true)} className="inline-flex items-center gap-2 rounded-full border border-kohl px-5 py-3.5 text-[15px]">
          <Check size={17} /> In your bag ({inBag})
        </button>
      )}
    </div>
  );
}

/** Sets the assistant's product context while this page is open. */
export function AskAbout({ p }: { p: Product }) {
  const setContext = useEmbellish((s) => s.setContext);
  const ask = useEmbellish((s) => s.ask);
  useEffect(() => {
    setContext({ id: p.product_id, title: p.title, price: p.price });
    return () => setContext(null);
  }, [p.product_id, p.title, p.price, setContext]);

  const qs = [
    "Is this on offer?",
    p.variant ? "What other shades are there?" : "Are there other sizes or variants?",
    `Show similar products under ${inr(Math.ceil(p.price / 100) * 100)}`,
  ];
  return (
    <div className="rounded-3xl border border-line bg-white p-5">
      <div className="flex items-center gap-3">
        {/* a still miniature of the orb; the live one waits in the corner */}
        <span
          aria-hidden
          className="h-9 w-9 shrink-0 rounded-full"
          style={{ background: "radial-gradient(circle at 34% 30%, #fff2f6 0%, #fdc2d6 18%, #e2185b 52%, #3c0e2e 92%)" }}
        />
        <div>
          <p className="font-semibold">Ask embellish about this product</p>
          <p className="text-[13px] text-mauve">Answers come from the catalogue listing only.</p>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {qs.map((q) => (
          <button key={q} onClick={() => ask(q)} className="rounded-full bg-petal px-3.5 py-1.5 text-[13.5px] text-kohl-soft hover:bg-rani hover:text-white">
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
