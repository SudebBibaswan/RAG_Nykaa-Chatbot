"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Product } from "./api";

export type CartItem = Pick<Product, "product_id" | "title" | "brand" | "price" | "mrp" | "image_url"> & { qty: number };

type CartState = {
  items: CartItem[];
  open: boolean;
  lastAdded: string | null;
  add: (p: CartItem | Product) => void;
  setQty: (id: string, qty: number) => void;
  remove: (id: string) => void;
  setOpen: (open: boolean) => void;
};

export const useCart = create<CartState>()(
  persist(
    (set) => ({
      items: [],
      open: false,
      lastAdded: null,
      add: (p) =>
        set((s) => {
          const existing = s.items.find((i) => i.product_id === p.product_id);
          const items = existing
            ? s.items.map((i) => (i.product_id === p.product_id ? { ...i, qty: i.qty + 1 } : i))
            : [
                ...s.items,
                {
                  product_id: p.product_id,
                  title: p.title,
                  brand: p.brand,
                  price: p.price,
                  mrp: p.mrp,
                  image_url: p.image_url,
                  qty: 1,
                },
              ];
          return { items, lastAdded: p.product_id };
        }),
      setQty: (id, qty) =>
        set((s) => ({
          items: qty <= 0 ? s.items.filter((i) => i.product_id !== id) : s.items.map((i) => (i.product_id === id ? { ...i, qty } : i)),
        })),
      remove: (id) => set((s) => ({ items: s.items.filter((i) => i.product_id !== id) })),
      setOpen: (open) => set({ open }),
    }),
    { name: "glossary-bag", partialize: (s) => ({ items: s.items }) },
  ),
);
