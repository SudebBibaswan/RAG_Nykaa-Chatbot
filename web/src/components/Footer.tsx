import Link from "next/link";

export default function Footer() {
  return (
    <footer className="mt-24 border-t border-line bg-white/60">
      <div className="mx-auto grid max-w-[1320px] gap-10 px-4 py-12 sm:px-6 md:grid-cols-[1.4fr_1fr_1fr]">
        <div>
          <p className="display text-[34px] leading-none">
            Glossary<span className="text-rani">.</span>
          </p>
          <p className="mt-4 max-w-[46ch] text-[13.5px] leading-relaxed text-kohl-soft">
            A student project built to demonstrate retrieval-augmented generation. Product data comes from a public snapshot of
            nykaa.com brand listings taken on 16 October 2022. Glossary is not affiliated with Nykaa, and nothing here can be bought.
          </p>
        </div>
        <nav aria-label="Shop" className="text-[14px]">
          <p className="mb-3 font-semibold">Shop</p>
          <ul className="space-y-2 text-kohl-soft">
            <li><Link className="hover:text-rani" href="/shop?category=Makeup">Makeup</Link></li>
            <li><Link className="hover:text-rani" href="/shop?category=Skin%20Care">Skin care</Link></li>
            <li><Link className="hover:text-rani" href="/shop?category=Hair%20Care">Hair care</Link></li>
            <li><Link className="hover:text-rani" href="/shop?tag=Bestseller">Bestsellers</Link></li>
            <li><Link className="hover:text-rani" href="/shop?min_discount=30&sort=discount">Offers</Link></li>
          </ul>
        </nav>
        <div className="text-[14px]">
          <p className="mb-3 font-semibold">About embellish</p>
          <p className="max-w-[36ch] text-kohl-soft">
            embellish answers questions using only this catalogue: names, brands, prices, discounts, ratings, shades and stock. It
            won&apos;t answer from general knowledge.
          </p>
        </div>
      </div>
    </footer>
  );
}
