import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-[720px] px-4 py-24 text-center">
      <p className="display text-[56px]">Not on our shelves</p>
      <p className="mt-3 text-kohl-soft">This page or product isn&apos;t in the catalogue.</p>
      <Link href="/shop" className="mt-6 inline-block rounded-full bg-kohl px-5 py-2.5 text-white">
        Browse all products
      </Link>
    </div>
  );
}
