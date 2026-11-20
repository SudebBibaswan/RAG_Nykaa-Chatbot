"use client";

import { ReactLenis } from "lenis/react";
import type { ReactNode } from "react";

// Read once on the client; Lenis options aren't rendered, so this can't cause a hydration mismatch.
const reduce = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export default function SmoothScroll({ children }: { children: ReactNode }) {
  return (
    <ReactLenis root options={{ lerp: reduce ? 1 : 0.12, smoothWheel: !reduce }}>
      {children}
    </ReactLenis>
  );
}
