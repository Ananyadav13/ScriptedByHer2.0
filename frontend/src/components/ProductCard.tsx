import Link from "next/link";
import type { Product } from "@/lib/api";
import { statusMeta } from "@/lib/decisions";

function money(n: number) {
  return "₹" + Math.round(n).toLocaleString("en-IN");
}

// Meesho-style catalog tile: photo, price/MRP, discount, and a Build Trust status pill.
export function ProductCard({ p }: { p: Product }) {
  const discount = p.mrp > p.price ? Math.round((1 - p.price / p.mrp) * 100) : 0;
  const sm = statusMeta(p.status);
  const trusted = p.status === "active";
  return (
    <Link href={`/product/${p.id}`} className="group block">
      <div className="overflow-hidden rounded-xl bg-surface shadow-[0_1px_3px_rgba(28,28,40,0.08)] transition group-hover:shadow-md">
        <div className="relative aspect-square overflow-hidden bg-[#f2f2f7]">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={`/products/${p.id}.jpg`}
            alt={p.title}
            className="h-full w-full object-cover transition group-hover:scale-105"
            loading="lazy"
          />
          <span
            className={`absolute left-2 top-2 rounded-md px-1.5 py-0.5 text-[10px] font-bold ${
              trusted ? "bg-white/90 text-green" : "bg-white/90 text-rose"
            }`}
          >
            {trusted ? "✓ Trust verified" : sm.label}
          </span>
          {discount > 0 && (
            <span className="absolute bottom-0 left-0 bg-brand px-2 py-0.5 text-[11px] font-bold text-white">
              {discount}% off
            </span>
          )}
        </div>
        <div className="p-2.5">
          <h3 className="line-clamp-1 text-sm text-ink-soft">{p.title}</h3>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-base font-bold text-ink">{money(p.price)}</span>
            {discount > 0 && <span className="text-xs text-ink-faint line-through">{money(p.mrp)}</span>}
          </div>
          <div className="mt-1.5 flex items-center gap-1.5">
            <span className="inline-flex items-center gap-0.5 rounded bg-green px-1.5 py-0.5 text-[11px] font-semibold text-white">
              4.3 ★
            </span>
            <span className="text-[11px] text-ink-faint">Free Delivery</span>
          </div>
        </div>
      </div>
    </Link>
  );
}
