import Link from "next/link";
import type { Product } from "@/lib/api";
import { payLater, ratingTone } from "@/lib/catalog";
import { PRODUCT_IMAGES } from "@/lib/productImages";

function money(n: number) {
  return "₹" + Math.round(n).toLocaleString("en-IN");
}
function compact(n: number) {
  if (n >= 100000) return (n / 100000).toFixed(1).replace(/\.0$/, "") + " L";
  if (n >= 1000) return (n / 1000).toFixed(1).replace(/\.0$/, "") + "k";
  return String(n);
}

// Meesho catalogue tile: photo, title, price/off, Pay Later, green rating pill, wishlist heart.
export function ProductCard({ p, sponsored }: { p: Product; sponsored?: boolean }) {
  const discount = p.mrp > p.price ? Math.round((1 - p.price / p.mrp) * 100) : 0;
  const rating = p.rating > 0 ? p.rating : 4;
  const trusted = p.status === "active";
  return (
    <Link href={`/product/${p.id}`} className="group block">
      <div className="overflow-hidden rounded-lg bg-surface shadow-[0_1px_4px_rgba(28,28,40,0.1)] transition group-hover:shadow-md">
        <div className="relative aspect-[3/4] overflow-hidden bg-[#f2f2f7]">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={(PRODUCT_IMAGES[p.id] ?? [`/products/${p.id}.jpg`])[0]}
            alt={p.title}
            className="h-full w-full bg-white object-contain transition group-hover:scale-[1.03]"
            loading="lazy"
          />
          <span className="absolute right-2 top-2 grid h-7 w-7 place-items-center rounded-full bg-white/95 text-ink-soft shadow-sm">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden>
              <path
                d="M12 20s-7-4.35-9.5-8.5C1 8.5 2.5 5.5 5.5 5.5 7.5 5.5 9 7 12 9c3-2 4.5-3.5 6.5-3.5 3 0 4.5 3 3 6C19 15.65 12 20 12 20Z"
                stroke="currentColor"
                strokeWidth="1.6"
              />
            </svg>
          </span>
          {trusted && (
            <span className="absolute left-2 top-2 inline-flex items-center gap-1 rounded bg-white/95 px-1.5 py-0.5 text-[10px] font-bold text-brand-ink shadow-sm">
              🛡 Trust
            </span>
          )}
        </div>
        <div className="p-2">
          <h3 className="line-clamp-2 min-h-[2.2em] text-[13px] leading-tight text-ink-soft">{p.title}</h3>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-[15px] font-bold text-ink">{money(p.price)}</span>
            {discount > 0 && (
              <>
                <span className="text-[11px] text-ink-faint line-through">{money(p.mrp)}</span>
                <span className="text-[11px] font-semibold text-green">{discount}% off</span>
              </>
            )}
          </div>
          <div className="mt-1 inline-flex items-center rounded bg-[#f2f2f7] px-1.5 py-0.5 text-[11px] text-ink-soft">
            ₹{payLater(p.price)} with Pay Later
          </div>
          <div className="mt-1.5 flex items-center gap-1.5">
            <span
              className="inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[11px] font-semibold text-white"
              style={{ background: ratingTone(Math.round(rating)).badge }}
            >
              {rating.toFixed(1)} ★
            </span>
            {p.rating_count > 0 && (
              <span className="text-[11px] text-ink-faint">({compact(p.rating_count)})</span>
            )}
            {sponsored && <span className="ml-auto text-[10px] text-ink-faint">Ad</span>}
          </div>
        </div>
      </div>
    </Link>
  );
}
