export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Product = {
  product_id: string;
  brand: string;
  title: string;
  base_name: string;
  variant: string;
  product_type: string;
  category: string;
  price: number;
  mrp: number;
  discount_pct: number;
  rating: number;
  rating_count: number;
  tags: string[];
  claims: string[];
  suitable_for: string[];
  in_stock: boolean;
  is_combo: boolean;
  image_url: string;
  product_url: string;
  description: string;
};

export type RetrievedRecord = Product & {
  score: number | null;
  rrf: number | null;
  matched: string[];
};

export type Aggregate = {
  label: string;
  matching_products: number;
  min_price: number | null;
  max_price: number | null;
  brands: string[];
};

export type Facet = { name: string; count: number };

export type Home = {
  bestsellers: Product[];
  new: Product[];
  deals: Product[];
  top_rated: Product[];
  by_category: Record<string, Product[]>;
};

export type ProductPage = { product: Product; variants: Product[]; similar: Product[] };

export type ProductList = { total: number; page: number; pages: number; items: Product[] };

export type Facets = {
  brands: Facet[];
  categories: Facet[];
  types: Facet[];
  price: { min: number; max: number };
};

export class ApiDown extends Error {}

/** Server-side fetch to the Python API. Uncached: callers sit behind <Suspense>. */
export async function api<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, { cache: "no-store" });
  } catch {
    throw new ApiDown(`Can't reach the catalogue API at ${API}. Start it with: uvicorn api.main:app --port 8000`);
  }
  if (res.status === 404) throw new Error("not-found");
  if (!res.ok) throw new Error(`API ${res.status} for ${path}`);
  return res.json() as Promise<T>;
}
