"use client";

import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import type { Product } from "@/lib/api";
import ProductRail from "../ProductRail";

export default function CategoryTabs({ byCategory }: { byCategory: Record<string, Product[]> }) {
  const cats = Object.keys(byCategory);
  const [active, setActive] = useState(cats[0]);
  return (
    <section className="mx-auto max-w-[1320px] px-4 pt-20 sm:px-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h2 className="display text-[clamp(34px,4.4vw,56px)]">Most loved, by aisle</h2>
      </div>
      <div role="tablist" aria-label="Aisles" className="rail mt-6 flex gap-2 overflow-x-auto">
        {cats.map((c) => (
          <button
            key={c}
            role="tab"
            aria-selected={c === active}
            onClick={() => setActive(c)}
            className={`relative shrink-0 rounded-full px-4 py-2 text-[14px] transition-colors ${c === active ? "text-white" : "text-kohl-soft hover:text-kohl"}`}
          >
            {c === active && <motion.span layoutId="aisle-pill" className="absolute inset-0 rounded-full bg-kohl" transition={{ type: "spring", stiffness: 420, damping: 36 }} />}
            <span className="relative">{c}</span>
          </button>
        ))}
        <Link href={`/shop?category=${encodeURIComponent(active)}`} className="ml-auto shrink-0 self-center whitespace-nowrap text-[14px] text-rani hover:underline">
          See all {active.toLowerCase()}
        </Link>
      </div>
      <div className="mt-16">
        <AnimatePresence mode="wait">
          <motion.div key={active} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
            <ProductRail products={byCategory[active]} label={`Most loved in ${active}`} />
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}
