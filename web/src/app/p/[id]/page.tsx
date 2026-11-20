import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import ProductImage from "@/components/ProductImage";
import ProductRail from "@/components/ProductRail";
import { Price, Rating } from "@/components/ProductCard";
import { AddToBag, AskAbout } from "@/components/product/ProductActions";
import { api, ApiDown, type ProductPage } from "@/lib/api";
import { inr } from "@/lib/format";

async function Detail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let data: ProductPage;
  try {
    data = await api<ProductPage>(`/api/products/${encodeURIComponent(id)}`);
  } catch (e) {
    if (e instanceof Error && e.message === "not-found") notFound();
    return <p className="rounded-3xl border border-dashed border-rani/50 bg-white p-6">{e instanceof ApiDown ? e.message : "The catalogue API returned an error."}</p>;
  }
  const { product: p, variants, similar } = data;

  return (
    <>
      <nav aria-label="Breadcrumb" className="text-[13px] text-mauve">
        <Link href="/shop" className="hover:text-rani">Shop</Link>
        <span className="mx-2">/</span>
        <Link href={`/shop?category=${encodeURIComponent(p.category)}`} className="hover:text-rani">{p.category}</Link>
        <span className="mx-2">/</span>
        <Link href={`/shop?brand=${encodeURIComponent(p.brand)}`} className="hover:text-rani">{p.brand}</Link>
      </nav>

      <div className="mt-6 grid gap-10 md:grid-cols-[1fr_1.05fr] lg:gap-16">
        <div className="md:sticky md:top-[150px] md:self-start">
          <div className="overflow-hidden rounded-[28px] bg-white">
            <ProductImage src={p.image_url} alt={p.title} brand={p.brand} size={700} className="aspect-square w-full p-8" />
          </div>
        </div>

        <div>
          <Link href={`/shop?brand=${encodeURIComponent(p.brand)}`} className="text-[14px] text-rani hover:underline">
            {p.brand}
          </Link>
          <h1 className="display mt-2 text-[clamp(32px,3.6vw,50px)] leading-[1.04]">{p.title}</h1>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Rating rating={p.rating} n={p.rating_count} size="md" />
            {p.tags.map((t) => (
              <span key={t} className="rounded-full bg-petal px-2.5 py-0.5 text-[12px] text-rani-deep">{t}</span>
            ))}
          </div>

          <div className="mt-6">
            <Price p={p} size="lg" />
            <p className="mt-1 text-[13px] text-mauve">
              {p.discount_pct > 0 ? `MRP ${inr(p.mrp)}, you save ${inr(p.mrp - p.price)}. ` : "Sold at MRP. "}
              Listed price on 16 Oct 2022.
            </p>
            <p className={`mt-2 text-[14px] ${p.in_stock ? "text-ok" : "text-mauve"}`}>
              {p.in_stock ? "In stock" : "Not marked as in stock in this snapshot"}
            </p>
          </div>

          <div className="mt-6">
            <AddToBag p={p} />
          </div>

          {variants.length > 0 && (
            <div className="mt-8">
              <p className="text-[14px] font-semibold">Other shades and variants ({variants.length})</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {variants.map((v) => (
                  <Link
                    key={v.product_id}
                    href={`/p/${v.product_id}`}
                    className="rounded-full border border-line bg-white px-3 py-1.5 text-[13px] text-kohl-soft hover:border-rani hover:text-rani"
                  >
                    {v.variant || v.title.replace(p.base_name, "").replace(/^[\s-]+/, "") || "Variant"}
                    <span className="ml-1.5 text-mauve">{inr(v.price)}</span>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {(p.claims.length > 0 || p.suitable_for.length > 0) && (
            <div className="mt-8">
              <p className="text-[14px] font-semibold">Stated in the product name</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {[...p.claims, ...p.suitable_for].map((c) => (
                  <span key={c} className="rounded-full bg-white px-3 py-1 text-[13px] text-kohl-soft ring-1 ring-line">{c}</span>
                ))}
              </div>
            </div>
          )}

          <div className="mt-8">
            <AskAbout p={p} />
          </div>

          <div className="mt-8 border-t border-line pt-6">
            <p className="text-[14px] font-semibold">From the catalogue</p>
            <p className="mt-2 max-w-[62ch] text-[14.5px] leading-relaxed text-kohl-soft">{p.description}</p>
            <p className="mt-3 text-[13px] text-mauve">
              {p.product_type} in {p.category}. Catalogue ID {p.product_id}.
            </p>
          </div>
        </div>
      </div>

      {similar.length > 0 && (
        <section className="mt-24">
          <h2 className="display mb-16 text-[clamp(32px,4vw,50px)]">More {p.product_type.toLowerCase()}s at a similar price</h2>
          <ProductRail products={similar} label="Similar products" />
        </section>
      )}
    </>
  );
}

function DetailSkeleton() {
  return (
    <div className="mt-10 grid gap-10 md:grid-cols-2" aria-busy>
      <div className="aspect-square rounded-[28px] bg-white" />
      <div className="space-y-4">
        <div className="h-4 w-24 rounded bg-blush/60" />
        <div className="h-12 w-4/5 rounded-xl bg-blush/60" />
        <div className="h-8 w-40 rounded-xl bg-blush/60" />
      </div>
    </div>
  );
}

export default function ProductRoute(props: PageProps<"/p/[id]">) {
  return (
    <div className="mx-auto max-w-[1320px] px-4 pt-8 sm:px-6">
      <Suspense fallback={<DetailSkeleton />}>
        <Detail params={props.params} />
      </Suspense>
    </div>
  );
}
