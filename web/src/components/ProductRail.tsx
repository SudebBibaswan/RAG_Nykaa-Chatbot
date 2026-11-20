"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useRef } from "react";
import type { Product } from "@/lib/api";
import ProductCard from "./ProductCard";

export default function ProductRail({ products, label }: { products: Product[]; label: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const by = (dir: number) => ref.current?.scrollBy({ left: dir * ref.current.clientWidth * 0.85, behavior: "smooth" });
  return (
    <div className="relative">
      <div ref={ref} className="rail -mx-4 flex gap-4 overflow-x-auto px-4 pb-2 sm:-mx-6 sm:gap-5 sm:px-6" aria-label={label} role="region">
        {products.map((p) => (
          <ProductCard key={p.product_id} p={p} className="w-[46vw] shrink-0 sm:w-[220px]" />
        ))}
      </div>
      <div className="pointer-events-none absolute -top-14 right-0 hidden gap-2 md:flex">
        <button onClick={() => by(-1)} aria-label={`Scroll ${label} back`} className="pointer-events-auto grid h-10 w-10 place-items-center rounded-full border border-line bg-white hover:border-kohl">
          <ChevronLeft size={18} />
        </button>
        <button onClick={() => by(1)} aria-label={`Scroll ${label} forward`} className="pointer-events-auto grid h-10 w-10 place-items-center rounded-full border border-line bg-white hover:border-kohl">
          <ChevronRight size={18} />
        </button>
      </div>
    </div>
  );
}
