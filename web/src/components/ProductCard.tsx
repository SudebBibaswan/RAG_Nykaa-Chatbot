"use client";

import Link from "next/link";
import { Check, Plus, Star } from "lucide-react";
import type { Product } from "@/lib/api";
import { useCart } from "@/lib/cart";
import { count, inr, shortTitle } from "@/lib/format";
import ProductImage from "./ProductImage";

export function Rating({ rating, n, size = "sm" }: { rating: number; n: number; size?: "sm" | "md" }) {
  if (!n) return <span className="text-[12px] text-mauve">No ratings yet</span>;
  return (
    <span className={`inline-flex items-center gap-1 ${size === "md" ? "text-[14px]" : "text-[12px]"} text-kohl-soft`}>
      <span className="inline-flex items-center gap-0.5 rounded-md bg-kohl px-1.5 py-0.5 font-semibold text-white">
        {rating.toFixed(1)}
        <Star size={size === "md" ? 12 : 10} fill="currentColor" strokeWidth={0} />
      </span>
      <span className="text-mauve">{count(n)} ratings</span>
    </span>
  );
}

export function Price({ p, size = "sm" }: { p: Pick<Product, "price" | "mrp" | "discount_pct">; size?: "sm" | "lg" }) {
  return (
    <span className="inline-flex flex-wrap items-baseline gap-x-2">
      <span className={size === "lg" ? "text-[28px] font-semibold" : "text-[15px] font-semibold"}>{inr(p.price)}</span>
      {p.discount_pct > 0 && (
        <>
          <span className={`${size === "lg" ? "text-[16px]" : "text-[12.5px]"} text-mauve line-through`}>{inr(p.mrp)}</span>
          <span className={`${size === "lg" ? "text-[16px]" : "text-[12.5px]"} font-semibold text-rani`}>{p.discount_pct}% off</span>
        </>
      )}
    </span>
  );
}

export default function ProductCard({ p, className = "" }: { p: Product; className?: string }) {
  const add = useCart((s) => s.add);
  const inBag = useCart((s) => s.items.some((i) => i.product_id === p.product_id));
  const tag = p.tags[0];

  return (
    <article className={`group relative flex flex-col ${className}`}>
      <Link href={`/p/${p.product_id}`} className="relative block overflow-hidden rounded-[18px] bg-white">
        <ProductImage
          src={p.image_url}
          alt={p.title}
          brand={p.brand}
          className="aspect-square w-full p-4 transition-transform duration-500 ease-out group-hover:scale-[1.04]"
        />
        {tag && (
          <span className={`absolute left-3 top-3 rounded-full px-2 py-0.5 text-[11px] font-medium ${tag === "New arrival" ? "bg-marigold/90 text-kohl" : "bg-petal text-rani-deep"}`}>
            {tag}
          </span>
        )}
        {!p.in_stock && (
          <span className="absolute bottom-3 left-3 rounded-full bg-white/90 px-2 py-0.5 text-[11px] text-mauve">Not marked in stock</span>
        )}
      </Link>
      <button
        onClick={() => add(p)}
        aria-label={inBag ? `Add another ${p.title} to bag` : `Add ${p.title} to bag`}
        className={`absolute right-3 top-3 grid h-9 w-9 place-items-center rounded-full shadow-sm transition-all sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100 ${
          inBag ? "bg-kohl text-white sm:opacity-100" : "bg-white text-kohl hover:bg-rani hover:text-white"
        }`}
      >
        {inBag ? <Check size={16} strokeWidth={2.5} /> : <Plus size={17} strokeWidth={2.5} />}
      </button>
      <div className="mt-3 flex flex-1 flex-col gap-1 px-0.5">
        <p className="text-[12px] text-mauve">{p.brand}</p>
        <Link href={`/p/${p.product_id}`} className="line-clamp-2 text-[14px] leading-snug text-kohl hover:text-rani">
          {shortTitle(p.title, p.brand)}
        </Link>
        <div className="mt-auto space-y-1 pt-1">
          <Rating rating={p.rating} n={p.rating_count} />
          <div>
            <Price p={p} />
          </div>
        </div>
      </div>
    </article>
  );
}
