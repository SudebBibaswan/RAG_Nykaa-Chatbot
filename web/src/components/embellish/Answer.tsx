"use client";

import Link from "next/link";
import { Fragment, type ReactNode } from "react";
import type { RetrievedRecord } from "@/lib/api";
import { img } from "@/lib/format";

/** Citation marker: a tiny product thumbnail that links to the product page. */
function Cite({ id, rec }: { id: string; rec?: RetrievedRecord }) {
  return (
    <Link
      href={`/p/${id}`}
      title={rec ? rec.title : `Product ${id}`}
      className="mx-0.5 inline-flex h-[1.35em] translate-y-[0.2em] items-center gap-1 rounded-full border border-line bg-white pl-0.5 pr-1.5 align-baseline text-[11px] font-semibold text-rani no-underline transition-colors hover:border-rani"
    >
      {rec ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={img(rec.image_url, 60)} alt="" className="h-[1.05em] w-[1.05em] rounded-full bg-petal object-cover" />
      ) : (
        <span className="h-[1.05em] w-[1.05em] rounded-full bg-petal" />
      )}
      <span className="sr-only">Source: {rec ? rec.title : id}</span>
      <span aria-hidden>{rec ? "↗" : id}</span>
    </Link>
  );
}

function inline(text: string, recs: Record<string, RetrievedRecord>, key: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /\[P:(\d+)\]|\*\*(.+?)\*\*/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    if (m[1]) out.push(<Cite key={`${key}-c${i++}`} id={m[1]} rec={recs[m[1]]} />);
    else out.push(<strong key={`${key}-b${i++}`} className="font-semibold text-kohl">{m[2]}</strong>);
    last = re.lastIndex;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

/** Minimal, safe renderer for the answer's markdown subset: paragraphs, bullets, bold, citations. */
export default function Answer({ text, records, streaming }: { text: string; records: RetrievedRecord[]; streaming?: boolean }) {
  const recs = Object.fromEntries(records.map((r) => [r.product_id, r]));
  const lines = text.split("\n");
  const blocks: ReactNode[] = [];
  let list: string[] = [];
  const flush = (k: string) => {
    if (list.length) {
      blocks.push(
        <ul key={k} className="my-2 space-y-1.5">
          {list.map((l, i) => (
            <li key={i} className="relative pl-4 before:absolute before:left-0 before:top-[0.62em] before:h-1.5 before:w-1.5 before:rounded-full before:bg-rani/70">
              {inline(l, recs, `${k}-${i}`)}
            </li>
          ))}
        </ul>,
      );
      list = [];
    }
  };
  lines.forEach((raw, i) => {
    const l = raw.trimEnd();
    const bullet = l.match(/^\s*(?:[-•*]|\d+[.)])\s+(.*)$/);
    if (bullet) {
      list.push(bullet[1]);
      return;
    }
    flush(`ul${i}`);
    if (l.trim()) blocks.push(<p key={`p${i}`} className="my-1.5">{inline(l, recs, `p${i}`)}</p>);
  });
  flush("ul-end");
  return (
    <div className={streaming ? "caret [&>*:last-child]:inline" : undefined}>
      {blocks.length ? blocks.map((b, i) => <Fragment key={i}>{b}</Fragment>) : null}
    </div>
  );
}
