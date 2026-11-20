"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import { SlidersHorizontal, X } from "lucide-react";
import { useState, useTransition } from "react";
import type { Facets } from "@/lib/api";

const PRICES = [
  { label: "Under ₹250", max: 250 },
  { label: "₹250 to ₹499", min: 250, max: 499 },
  { label: "₹500 to ₹999", min: 500, max: 999 },
  { label: "₹1,000 to ₹1,999", min: 1000, max: 1999 },
  { label: "₹2,000 and above", min: 2000 },
];

export function useQueryUpdate() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [pending, start] = useTransition();
  const update = (fn: (p: URLSearchParams) => void) => {
    const next = new URLSearchParams(params.toString());
    fn(next);
    next.delete("page");
    start(() => router.push(`${pathname}?${next.toString()}`, { scroll: false }));
  };
  return { params, update, pending };
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-line py-5 first:border-t-0 first:pt-0">
      <fieldset>
        <legend className="mb-3 text-[14px] font-semibold">{title}</legend>
        {children}
      </fieldset>
    </div>
  );
}

function Check({ checked, onChange, label, n }: { checked: boolean; onChange: () => void; label: string; n?: number }) {
  return (
    <label className="flex cursor-pointer items-center gap-2.5 py-1 text-[14px] text-kohl-soft hover:text-kohl">
      <input type="checkbox" checked={checked} onChange={onChange} className="h-4 w-4 accent-[var(--rani)]" />
      <span className="flex-1">{label}</span>
      {n != null && <span className="text-[12px] text-mauve">{n}</span>}
    </label>
  );
}

function Panel({ facets }: { facets: Facets }) {
  const { params, update } = useQueryUpdate();
  const [showAll, setShowAll] = useState(false);
  const brands = params.getAll("brand");
  const cats = params.getAll("category");
  const toggle = (key: string, v: string) =>
    update((p) => {
      const cur = p.getAll(key);
      p.delete(key);
      (cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v]).forEach((x) => p.append(key, x));
    });
  const priceKey = `${params.get("min_price") ?? ""}-${params.get("max_price") ?? ""}`;
  const brandList = showAll ? facets.brands : facets.brands.slice(0, 10);

  return (
    <div>
      <Group title="Category">
        {facets.categories.map((c) => (
          <Check key={c.name} label={c.name} n={c.count} checked={cats.includes(c.name)} onChange={() => toggle("category", c.name)} />
        ))}
      </Group>
      <Group title="Brand">
        {brandList.map((b) => (
          <Check key={b.name} label={b.name} n={b.count} checked={brands.includes(b.name)} onChange={() => toggle("brand", b.name)} />
        ))}
        {facets.brands.length > 10 && (
          <button onClick={() => setShowAll((v) => !v)} className="mt-1 text-[13px] text-rani hover:underline">
            {showAll ? "Show fewer brands" : `Show all ${facets.brands.length} brands`}
          </button>
        )}
      </Group>
      <Group title="Price">
        {PRICES.map((p) => {
          const key = `${p.min ?? ""}-${p.max ?? ""}`;
          return (
            <label key={key} className="flex cursor-pointer items-center gap-2.5 py-1 text-[14px] text-kohl-soft hover:text-kohl">
              <input
                type="radio"
                name="price"
                checked={priceKey === key}
                onChange={() =>
                  update((q) => {
                    q.delete("min_price");
                    q.delete("max_price");
                    if (p.min) q.set("min_price", String(p.min));
                    if (p.max) q.set("max_price", String(p.max));
                  })
                }
                className="h-4 w-4 accent-[var(--rani)]"
              />
              {p.label}
            </label>
          );
        })}
      </Group>
      <Group title="Customer rating">
        {[4.5, 4, 3.5].map((r) => (
          <label key={r} className="flex cursor-pointer items-center gap-2.5 py-1 text-[14px] text-kohl-soft hover:text-kohl">
            <input
              type="radio"
              name="rating"
              checked={params.get("min_rating") === String(r)}
              onChange={() => update((q) => q.set("min_rating", String(r)))}
              className="h-4 w-4 accent-[var(--rani)]"
            />
            {r} and above
          </label>
        ))}
      </Group>
      <Group title="Discount">
        {[10, 20, 30, 40].map((d) => (
          <label key={d} className="flex cursor-pointer items-center gap-2.5 py-1 text-[14px] text-kohl-soft hover:text-kohl">
            <input
              type="radio"
              name="discount"
              checked={params.get("min_discount") === String(d)}
              onChange={() => update((q) => q.set("min_discount", String(d)))}
              className="h-4 w-4 accent-[var(--rani)]"
            />
            {d}% off or more
          </label>
        ))}
      </Group>
    </div>
  );
}

export function ActiveFilters() {
  const { params, update } = useQueryUpdate();
  const chips: { label: string; remove: (p: URLSearchParams) => void }[] = [];
  params.getAll("brand").forEach((b) => chips.push({ label: b, remove: (p) => removeValue(p, "brand", b) }));
  params.getAll("category").forEach((c) => chips.push({ label: c, remove: (p) => removeValue(p, "category", c) }));
  if (params.get("min_price") || params.get("max_price"))
    chips.push({
      label: `₹${params.get("min_price") ?? 0} to ${params.get("max_price") ? "₹" + params.get("max_price") : "any"}`,
      remove: (p) => {
        p.delete("min_price");
        p.delete("max_price");
      },
    });
  if (params.get("min_rating")) chips.push({ label: `${params.get("min_rating")}+ rating`, remove: (p) => p.delete("min_rating") });
  if (params.get("min_discount")) chips.push({ label: `${params.get("min_discount")}%+ off`, remove: (p) => p.delete("min_discount") });
  if (params.get("tag")) chips.push({ label: params.get("tag")!, remove: (p) => p.delete("tag") });
  if (params.get("q")) chips.push({ label: `“${params.get("q")}”`, remove: (p) => p.delete("q") });
  if (!chips.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-2">
      {chips.map((c) => (
        <button key={c.label} onClick={() => update(c.remove)} className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1 text-[13px] text-kohl-soft ring-1 ring-line hover:ring-rani">
          {c.label}
          <X size={13} />
        </button>
      ))}
      <button onClick={() => update((p) => [...p.keys()].forEach((k) => k !== "sort" && p.delete(k)))} className="text-[13px] text-rani hover:underline">
        Clear all
      </button>
    </div>
  );
}

function removeValue(p: URLSearchParams, key: string, v: string) {
  const rest = p.getAll(key).filter((x) => x !== v);
  p.delete(key);
  rest.forEach((x) => p.append(key, x));
}

export function SortSelect() {
  const { params, update } = useQueryUpdate();
  return (
    <label className="flex items-center gap-2 text-[14px] text-kohl-soft">
      Sort by
      <select
        value={params.get("sort") ?? (params.get("q") ? "relevance" : "popular")}
        onChange={(e) => update((p) => p.set("sort", e.target.value))}
        className="rounded-full border border-line bg-white px-3 py-1.5 text-[14px] text-kohl outline-none focus:border-kohl-soft"
      >
        {params.get("q") && <option value="relevance">Relevance</option>}
        <option value="popular">Most rated</option>
        <option value="rating">Customer rating</option>
        <option value="price_asc">Price: low to high</option>
        <option value="price_desc">Price: high to low</option>
        <option value="discount">Discount</option>
      </select>
    </label>
  );
}

export function FilterSidebar({ facets }: { facets: Facets }) {
  return (
    <aside className="hidden w-[250px] shrink-0 lg:block" aria-label="Filters">
      <div className="thin-scroll sticky top-[140px] max-h-[calc(100dvh-160px)] overflow-y-auto pr-2" data-lenis-prevent>
        <Panel facets={facets} />
      </div>
    </aside>
  );
}

export default function MobileFilters({ facets }: { facets: Facets }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button onClick={() => setOpen(true)} className="inline-flex items-center gap-2 rounded-full border border-line bg-white px-4 py-2 text-[14px] lg:hidden">
        <SlidersHorizontal size={15} /> Filters
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            className="fixed inset-0 z-[70] flex flex-col bg-powder lg:hidden"
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", stiffness: 380, damping: 40 }}
          >
            <div className="flex items-center justify-between border-b border-line px-4 py-3">
              <p className="display text-[26px]">Filters</p>
              <button onClick={() => setOpen(false)} aria-label="Close filters" className="grid h-9 w-9 place-items-center rounded-full hover:bg-petal">
                <X size={20} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-4 py-4" data-lenis-prevent>
              <Panel facets={facets} />
            </div>
            <div className="border-t border-line p-4">
              <button onClick={() => setOpen(false)} className="w-full rounded-full bg-kohl py-3 text-white">
                Show products
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
