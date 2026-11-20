import type { Metadata, Viewport } from "next";
import { Bodoni_Moda, Schibsted_Grotesk } from "next/font/google";
import CartDrawer from "@/components/CartDrawer";
import Embellish from "@/components/embellish/Embellish";
import Footer from "@/components/Footer";
import Header from "@/components/Header";
import SmoothScroll from "@/components/SmoothScroll";
import "./globals.css";

const bodoni = Bodoni_Moda({
  variable: "--font-bodoni",
  subsets: ["latin"],
  axes: ["opsz"],
  style: ["normal", "italic"],
});

const schibsted = Schibsted_Grotesk({
  variable: "--font-schibsted",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: { default: "Glossary · beauty, with embellish", template: "%s · Glossary" },
  description: "A beauty storefront with embellish, an assistant that answers only from the product catalogue.",
};

export const viewport: Viewport = { themeColor: "#fbf4f6" };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en-IN" className={`${bodoni.variable} ${schibsted.variable}`}>
      <body className="flex min-h-dvh flex-col">
        <SmoothScroll>
          <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[80] focus:rounded-full focus:bg-kohl focus:px-4 focus:py-2 focus:text-white">
            Skip to content
          </a>
          <Header />
          <main id="main" className="flex-1">
            {children}
          </main>
          <Footer />
          <CartDrawer />
          <Embellish />
        </SmoothScroll>
      </body>
    </html>
  );
}
