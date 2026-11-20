"use client";

import { useState } from "react";
import { img } from "@/lib/format";

/** Product photo with a designed placeholder for 2022 image URLs that no longer resolve. */
export default function ProductImage({
  src,
  alt,
  size = 400,
  className = "",
  brand,
}: {
  src: string;
  alt: string;
  size?: number;
  className?: string;
  brand?: string;
}) {
  const [failed, setFailed] = useState(false);
  if (failed || !src) {
    return (
      <div className={`grid place-items-center bg-petal text-center ${className}`} role="img" aria-label={alt}>
        <span className="display px-4 text-[20px] leading-tight text-rani/60">{brand ?? "Glossary"}</span>
      </div>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={img(src, size)}
      alt={alt}
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
      className={`object-contain ${className}`}
    />
  );
}
