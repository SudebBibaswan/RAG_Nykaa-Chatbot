"use client";

import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";
import { Minus, Plus, Trash2, X } from "lucide-react";
import { useEffect } from "react";
import { useCart } from "@/lib/cart";
import { inr, shortTitle } from "@/lib/format";
import ProductImage from "./ProductImage";

export default function CartDrawer() {
  const { items, open, setOpen, setQty, remove } = useCart();
  const total = items.reduce((s, i) => s + i.price * i.qty, 0);
  const saved = items.reduce((s, i) => s + (i.mrp - i.price) * i.qty, 0);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setOpen]);

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="fixed inset-0 z-[70] bg-kohl/30"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setOpen(false)}
          />
          <motion.aside
            role="dialog"
            aria-label="Your bag"
            className="fixed inset-y-0 right-0 z-[71] flex w-full max-w-[420px] flex-col bg-powder"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 380, damping: 38 }}
          >
            <div className="flex items-center justify-between border-b border-line px-5 py-4">
              <p className="display text-[28px]">Your bag</p>
              <button onClick={() => setOpen(false)} aria-label="Close bag" className="grid h-9 w-9 place-items-center rounded-full hover:bg-petal">
                <X size={20} />
              </button>
            </div>
            <div className="thin-scroll flex-1 overflow-y-auto px-5 py-4" data-lenis-prevent>
              {items.length === 0 ? (
                <div className="pt-10 text-center">
                  <p className="text-[15px] text-kohl-soft">Your bag is empty.</p>
                  <Link href="/shop" onClick={() => setOpen(false)} className="mt-3 inline-block rounded-full bg-kohl px-5 py-2.5 text-[14px] text-white">
                    Browse products
                  </Link>
                </div>
              ) : (
                <ul className="space-y-4">
                  {items.map((i) => (
                    <li key={i.product_id} className="flex gap-3">
                      <ProductImage src={i.image_url} alt={i.title} brand={i.brand} size={160} className="h-20 w-20 shrink-0 rounded-2xl bg-white p-1.5" />
                      <div className="min-w-0 flex-1">
                        <p className="text-[12px] text-mauve">{i.brand}</p>
                        <Link href={`/p/${i.product_id}`} onClick={() => setOpen(false)} className="line-clamp-2 text-[14px] leading-snug hover:text-rani">
                          {shortTitle(i.title, i.brand)}
                        </Link>
                        <div className="mt-2 flex items-center gap-3">
                          <div className="flex items-center rounded-full border border-line bg-white">
                            <button onClick={() => setQty(i.product_id, i.qty - 1)} aria-label="Decrease quantity" className="grid h-7 w-7 place-items-center">
                              <Minus size={13} />
                            </button>
                            <span className="w-5 text-center text-[13px]" aria-live="polite">{i.qty}</span>
                            <button onClick={() => setQty(i.product_id, i.qty + 1)} aria-label="Increase quantity" className="grid h-7 w-7 place-items-center">
                              <Plus size={13} />
                            </button>
                          </div>
                          <span className="text-[14px] font-semibold">{inr(i.price * i.qty)}</span>
                          <button onClick={() => remove(i.product_id)} aria-label={`Remove ${i.title}`} className="ml-auto text-mauve hover:text-rani">
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            {items.length > 0 && (
              <div className="border-t border-line px-5 py-4">
                <div className="flex justify-between text-[15px]">
                  <span>Total</span>
                  <span className="font-semibold">{inr(total)}</span>
                </div>
                {saved > 0 && <p className="mt-0.5 text-right text-[13px] text-rani">You save {inr(saved)} on MRP</p>}
                <button disabled className="mt-4 w-full cursor-not-allowed rounded-full bg-kohl/40 py-3 text-[14.5px] text-white">
                  Checkout isn&apos;t part of this demo
                </button>
              </div>
            )}
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
