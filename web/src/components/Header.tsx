"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Search, ShoppingBag } from "lucide-react";
import { useState, useSyncExternalStore } from "react";
import { useCart } from "@/lib/cart";
import { useEmbellish } from "./embellish/store";

const NAV = [
  { label: "Makeup", href: "/shop?category=Makeup" },
  { label: "Skin", href: "/shop?category=Skin%20Care" },
  { label: "Hair", href: "/shop?category=Hair%20Care" },
  { label: "Bath & Body", href: "/shop?category=Bath%20%26%20Body" },
  { label: "Nails", href: "/shop?category=Nails" },
  { label: "Gift sets", href: "/shop?category=Combos%20%26%20Kits" },
  { label: "Offers", href: "/shop?min_discount=30&sort=discount" },
];

export default function Header() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const items = useCart((s) => s.items);
  const setCartOpen = useCart((s) => s.setOpen);
  const openChat = useEmbellish((s) => s.setOpen);
  const bagCount = items.reduce((n, i) => n + i.qty, 0);

  // the bag lives in localStorage, so only show its count after hydration
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );

  return (
    <header className="sticky top-0 z-40 border-b border-line/80 bg-powder/90 backdrop-blur-md">
      <div className="bg-kohl px-4 py-1.5 text-center text-[12px] text-white/80">
        Prices, offers and stock are from a catalogue snapshot taken on 16 October 2022.
      </div>
      <div className="mx-auto flex max-w-[1320px] items-center gap-4 px-4 py-3 sm:gap-6 sm:px-6">
        <Link href="/" className="display shrink-0 text-[30px] leading-none tracking-[-0.03em] text-kohl" aria-label="Glossary home">
          Glossary<span className="text-rani">.</span>
        </Link>
        <nav aria-label="Categories" className="hidden items-center gap-5 text-[14px] text-kohl-soft lg:flex">
          {NAV.map((n) => (
            <Link key={n.label} href={n.href} className="whitespace-nowrap hover:text-rani">
              {n.label}
            </Link>
          ))}
        </nav>
        <form
          role="search"
          className="ml-auto flex min-w-0 flex-1 items-center gap-2 rounded-full border border-line bg-white px-3.5 py-2 focus-within:border-kohl-soft lg:max-w-[300px]"
          onSubmit={(e) => {
            e.preventDefault();
            if (q.trim()) router.push(`/shop?q=${encodeURIComponent(q.trim())}`);
          }}
        >
          <Search size={16} className="shrink-0 text-mauve" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search products and brands"
            aria-label="Search products and brands"
            className="min-w-0 flex-1 bg-transparent text-[14px] outline-none placeholder:text-mauve/80 focus-visible:outline-none"
          />
        </form>
        <button
          onClick={() => openChat(true)}
          className="hidden shrink-0 rounded-full border border-kohl px-3.5 py-1.5 text-[13.5px] font-medium text-kohl transition-colors hover:bg-kohl hover:text-white md:block"
        >
          Ask embellish
        </button>
        <button onClick={() => setCartOpen(true)} aria-label={`Open bag, ${bagCount} items`} className="relative grid h-10 w-10 shrink-0 place-items-center rounded-full hover:bg-petal">
          <ShoppingBag size={21} />
          {mounted && bagCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 grid h-5 min-w-5 place-items-center rounded-full bg-rani px-1 text-[11px] font-semibold text-white">{bagCount}</span>
          )}
        </button>
      </div>
      <nav aria-label="Categories" className="rail flex gap-5 overflow-x-auto px-4 pb-2.5 text-[13.5px] text-kohl-soft lg:hidden">
        {NAV.map((n) => (
          <Link key={n.label} href={n.href} className="whitespace-nowrap hover:text-rani">
            {n.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
