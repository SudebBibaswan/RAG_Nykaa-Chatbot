const inrFmt = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

export const inr = (n: number) => `₹${inrFmt.format(n)}`;

export const count = (n: number) =>
  n >= 100000 ? `${(n / 100000).toFixed(n >= 1000000 ? 0 : 1)}L` : n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k` : `${n}`;

/** The CDN resizes on the fly; ask for the size we actually render. */
export const img = (url: string, size = 400) => url.replace(/tr:h-\d+,w-\d+/, `tr:h-${size},w-${size}`);

/** Shorten "Maybelline New York The Colossal ..." to the part after the brand. */
export const shortTitle = (title: string, brand: string) => {
  const t = title.startsWith(brand) ? title.slice(brand.length).trim() : title;
  return t.length ? t : title;
};
