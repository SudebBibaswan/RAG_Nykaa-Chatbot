import Link from "next/link";
import { Suspense } from "react";
import CategoryTabs from "@/components/home/CategoryTabs";
import Hero from "@/components/home/Hero";
import ProductRail from "@/components/ProductRail";
import { api, ApiDown, type Facets, type Home } from "@/lib/api";

function Shelf({ title, note, href, children }: { title: string; note?: string; href?: string; children: React.ReactNode }) {
  return (
    <section className="mx-auto max-w-[1320px] px-4 pt-20 sm:px-6">
      <div className="mb-16 flex flex-wrap items-end justify-between gap-x-6 gap-y-2 pr-0 md:pr-28">
        <div>
          <h2 className="display text-[clamp(34px,4.4vw,56px)]">{title}</h2>
          {note && <p className="mt-2 text-[14px] text-mauve">{note}</p>}
        </div>
        {href && (
          <Link href={href} className="text-[14px] text-rani hover:underline">
            See all
          </Link>
        )}
      </div>
      {children}
    </section>
  );
}

function ShelfSkeleton() {
  return (
    <div className="mx-auto max-w-[1320px] px-4 pt-20 sm:px-6" aria-busy>
      <div className="h-12 w-72 rounded-xl bg-blush/60" />
      <div className="mt-16 flex gap-5 overflow-hidden">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="w-[220px] shrink-0">
            <div className="aspect-square rounded-[18px] bg-white" />
            <div className="mt-3 h-3 w-20 rounded bg-blush/60" />
            <div className="mt-2 h-3 w-40 rounded bg-blush/60" />
          </div>
        ))}
      </div>
    </div>
  );
}

function ApiNotice({ error }: { error: unknown }) {
  return (
    <div className="mx-auto mt-16 max-w-[1320px] px-4 sm:px-6">
      <div className="rounded-3xl border border-dashed border-rani/50 bg-white p-6">
        <p className="font-semibold">The catalogue isn&apos;t loading</p>
        <p className="mt-1 text-[14px] text-kohl-soft">
          {error instanceof ApiDown ? error.message : "The catalogue API returned an error. Check the API terminal for details."}
        </p>
      </div>
    </div>
  );
}

async function HeroWithCount() {
  let total = 3652;
  try {
    total = (await api<{ products: number }>("/api/health")).products;
  } catch {}
  return <Hero total={total} />;
}

async function Brands() {
  const f = await api<Facets>("/api/facets");
  const max = Math.max(...f.brands.map((b) => b.count));
  const brands = f.brands.filter((b) => b.count >= 5);
  return (
    <section className="mx-auto max-w-[1320px] px-4 pt-6 sm:px-6">
      <h2 className="sr-only">Brands</h2>
      <p className="text-[14px] text-mauve">{brands.length} brands on the shelves, sized by how many of their products we carry</p>
      <ul className="mt-4 flex flex-wrap items-baseline gap-x-6 gap-y-1">
        {brands.map((b) => (
          <li key={b.name}>
            <Link
              href={`/shop?brand=${encodeURIComponent(b.name)}`}
              className="display text-kohl transition-colors hover:text-rani"
              style={{ fontSize: `${18 + Math.sqrt(b.count / max) * 30}px` }}
            >
              {b.name}
            </Link>
            <span className="ml-1 align-super text-[11px] text-mauve">{b.count}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

async function Shelves() {
  let home: Home;
  try {
    home = await api<Home>("/api/home");
  } catch (e) {
    return <ApiNotice error={e} />;
  }
  return (
    <>
      <Suspense fallback={null}>
        <Brands />
      </Suspense>
      <CategoryTabs byCategory={home.by_category} />
      <Shelf title="Biggest offers" note="30% or more off MRP, on products with 200+ ratings" href="/shop?min_discount=30&sort=discount">
        <ProductRail products={home.deals} label="Biggest offers" />
      </Shelf>
      <HowItAnswers />
      <Shelf title="Bestsellers" href="/shop?tag=Bestseller">
        <ProductRail products={home.bestsellers} label="Bestsellers" />
      </Shelf>
      <Shelf title="Top rated" note="Rated by at least 1,000 shoppers" href="/shop?sort=rating&min_rating=4.5">
        <ProductRail products={home.top_rated} label="Top rated" />
      </Shelf>
      {home.new.length > 0 && (
        <Shelf title="New arrivals" href="/shop?tag=New%20arrival">
          <ProductRail products={home.new} label="New arrivals" />
        </Shelf>
      )}
    </>
  );
}

function HowItAnswers() {
  const points = [
    {
      title: "Only from the catalogue",
      body: "Every answer is built from the product records on this site. Nothing comes from the wider internet.",
    },
    {
      title: "Every product cited",
      body: "Each product embellish mentions links to its page, so you can check the price and rating yourself.",
    },
    {
      title: "Says when it doesn't know",
      body: "Ingredients, delivery and returns aren't in the catalogue, so it tells you that instead of guessing.",
    },
  ];
  return (
    <section className="mt-24 bg-kohl text-white">
      <div className="mx-auto grid max-w-[1320px] gap-12 px-4 py-20 sm:px-6 md:grid-cols-[1fr_1.6fr]">
        <h2 className="display max-w-[11ch] text-[clamp(38px,5vw,68px)]">How embellish answers</h2>
        <ul className="grid gap-10 sm:grid-cols-3 sm:gap-8">
          {points.map((p) => (
            <li key={p.title}>
              <span aria-hidden className="mb-4 block h-2.5 w-2.5 rounded-full bg-marigold shadow-[0_0_12px_3px_rgba(240,162,59,0.5)]" />
              <p className="text-[18px] font-semibold">{p.title}</p>
              <p className="mt-2 text-[14.5px] leading-relaxed text-white/70">{p.body}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

export default function Page() {
  return (
    <>
      <Suspense fallback={<Hero total={3652} />}>
        <HeroWithCount />
      </Suspense>
      <Suspense fallback={<ShelfSkeleton />}>
        <Shelves />
      </Suspense>
    </>
  );
}
