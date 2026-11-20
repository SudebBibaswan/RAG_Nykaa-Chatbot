import Link from "next/link";
import { Suspense } from "react";
import ProductCard from "@/components/ProductCard";
import MobileFilters, { ActiveFilters, FilterSidebar, SortSelect } from "@/components/shop/Filters";
import AskAboutResults from "@/components/shop/AskAboutResults";
import { api, ApiDown, type Facets, type ProductList } from "@/lib/api";

export const metadata = { title: "Shop" };

type SP = Record<string, string | string[] | undefined>;

function toQuery(sp: SP, overrides: Record<string, string> = {}) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(sp)) {
    if (v === undefined) continue;
    (Array.isArray(v) ? v : [v]).forEach((x) => q.append(k, x));
  }
  for (const [k, v] of Object.entries(overrides)) q.set(k, v);
  return q;
}

function heading(sp: SP) {
  const one = (k: string) => (Array.isArray(sp[k]) ? (sp[k] as string[])[0] : (sp[k] as string | undefined));
  if (one("q")) return `Results for “${one("q")}”`;
  const brands = ([] as string[]).concat(sp.brand ?? []);
  const cats = ([] as string[]).concat(sp.category ?? []);
  if (brands.length === 1 && !cats.length) return brands[0];
  if (cats.length === 1 && !brands.length) return cats[0];
  if (one("tag")) return `${one("tag")}s`;
  if (one("min_discount")) return "Offers";
  return "All products";
}

async function Results({ searchParams }: { searchParams: Promise<SP> }) {
  const sp = await searchParams;
  let list: ProductList;
  let facets: Facets;
  try {
    [list, facets] = await Promise.all([api<ProductList>(`/api/products?${toQuery(sp).toString()}`), api<Facets>("/api/facets")]);
  } catch (e) {
    return (
      <p className="rounded-3xl border border-dashed border-rani/50 bg-white p-6 text-[14px]">
        {e instanceof ApiDown ? e.message : "The catalogue API returned an error for these filters."}
      </p>
    );
  }
  const title = heading(sp);
  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="display text-[clamp(40px,5.5vw,72px)]">{title}</h1>
          <p className="mt-2 text-[14px] text-mauve">{list.total.toLocaleString("en-IN")} products</p>
        </div>
        <div className="flex items-center gap-3">
          <MobileFilters facets={facets} />
          <SortSelect />
        </div>
      </div>
      <div className="mt-5">
        <ActiveFilters />
      </div>
      <div className="mt-8 flex gap-10">
        <FilterSidebar facets={facets} />
        <div className="min-w-0 flex-1">
          {list.items.length === 0 ? (
            <div className="rounded-3xl bg-white p-8 text-center">
              <p className="text-[16px]">No products match these filters.</p>
              <p className="mt-1 text-[14px] text-kohl-soft">Remove a filter, or ask embellish to look for something similar.</p>
            </div>
          ) : (
            <>
              <AskAboutResults title={title} />
              <div className="grid grid-cols-2 gap-x-4 gap-y-10 sm:grid-cols-3 xl:grid-cols-4">
                {list.items.map((p) => (
                  <ProductCard key={p.product_id} p={p} />
                ))}
              </div>
            </>
          )}
          {list.pages > 1 && (
            <nav aria-label="Pages" className="mt-14 flex items-center justify-center gap-2 text-[14px]">
              {list.page > 1 && (
                <Link href={`/shop?${toQuery(sp, { page: String(list.page - 1) })}`} className="rounded-full border border-line bg-white px-4 py-2 hover:border-kohl">
                  Previous
                </Link>
              )}
              <span className="px-3 text-mauve">
                Page {list.page} of {list.pages}
              </span>
              {list.page < list.pages && (
                <Link href={`/shop?${toQuery(sp, { page: String(list.page + 1) })}`} className="rounded-full border border-line bg-white px-4 py-2 hover:border-kohl">
                  Next
                </Link>
              )}
            </nav>
          )}
        </div>
      </div>
    </>
  );
}

function ResultsSkeleton() {
  return (
    <div aria-busy>
      <div className="h-16 w-80 rounded-xl bg-blush/60" />
      <div className="mt-12 grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="aspect-square rounded-[18px] bg-white" />
        ))}
      </div>
    </div>
  );
}

export default function ShopPage(props: PageProps<"/shop">) {
  return (
    <div className="mx-auto max-w-[1320px] px-4 pt-10 sm:px-6">
      <Suspense fallback={<ResultsSkeleton />}>
        <Results searchParams={props.searchParams} />
      </Suspense>
    </div>
  );
}
