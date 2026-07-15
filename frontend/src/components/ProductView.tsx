"use client";

import { useState } from "react";
import Link from "next/link";
import type { ProductDetail } from "@/lib/api";
import { statusMeta } from "@/lib/decisions";
import type { DemoOrder } from "@/lib/orders";
import {
  additionalDetails,
  highlights,
  payLater,
  ratingSummary,
  ratingTone,
  reviewDisplay,
  sellerInfo,
  sizeChart,
  sizeOptions,
} from "@/lib/catalog";
import { VerifyPanel } from "@/components/VerifyPanel";
import { DisputeCard } from "@/components/DisputeCard";

const money = (n: number) => "₹" + Math.round(n).toLocaleString("en-IN");
const compact = (n: number) =>
  n >= 100000 ? (n / 100000).toFixed(1) + " L" : n >= 1000 ? (n / 1000).toFixed(1) + "k" : String(n);

function Stars({ n, className = "" }: { n: number; className?: string }) {
  return (
    <span className={className}>
      <span className="text-amber">{"★".repeat(n)}</span>
      <span className="text-line">{"★".repeat(5 - n)}</span>
    </span>
  );
}

function Section({ title, children, action }: { title: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <section className="border-t-8 border-[#f2f2f7] px-4 py-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-bold text-ink">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

export function ProductView({
  detail: p,
  orders,
  focusOrder,
}: {
  detail: ProductDetail;
  orders: DemoOrder[];
  focusOrder?: string;
}) {
  const discount = p.mrp > p.price ? Math.round((1 - p.price / p.mrp) * 100) : 0;
  const seller = sellerInfo(p.seller_id);
  const sizes = sizeOptions(p.category);
  const chart = sizeChart(p.category);
  const rs = ratingSummary(p.reviews);
  const headlineRating = rs.avg || p.rating || 4.0;
  const maxBucket = Math.max(1, ...rs.rows.map((r) => r.count));
  const photoReviews = p.reviews.filter((r) => r.has_video);

  const [size, setSize] = useState<string | null>(null);
  const [showChart, setShowChart] = useState(false);
  const sm = statusMeta(p.status);

  return (
    <div className="mx-auto max-w-2xl bg-surface pb-24">
      {/* status banner */}
      {p.status !== "active" && (
        <div
          className={`px-4 py-2.5 text-sm ${
            sm.tone === "rose" ? "bg-rose-wash text-rose" : sm.tone === "teal" ? "bg-teal-wash text-teal" : "bg-amber-wash text-amber"
          }`}
        >
          <span className="font-semibold">
            {p.status === "flagged" ? "👁️ " : "🔒 "}
            {sm.label}
          </span>
          {p.status === "flagged" && <span className="opacity-80"> — still buyable, a manager is reviewing</span>}
          {p.lock_reason && <div className="mt-0.5 text-xs opacity-90">{p.lock_reason}</div>}
        </div>
      )}

      {/* gallery */}
      <div className="relative bg-[#f7f7fb]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={`/products/${p.id}.jpg`} alt={p.title} className="mx-auto aspect-square w-full max-w-md object-contain" />
        <div className="absolute bottom-3 left-1/2 flex -translate-x-1/2 gap-1.5">
          {[0, 1, 2, 3].map((i) => (
            <span key={i} className={`h-1.5 rounded-full ${i === 0 ? "w-4 bg-brand" : "w-1.5 bg-line"}`} />
          ))}
        </div>
      </div>
      <div className="flex gap-2 overflow-x-auto px-4 py-2.5">
        {[0, 1, 2, 3].map((i) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            key={i}
            src={`/products/${p.id}.jpg`}
            alt=""
            className={`h-16 w-14 shrink-0 rounded-md border object-cover ${i === 0 ? "border-brand" : "border-line"}`}
          />
        ))}
      </div>

      {/* title + price */}
      <div className="px-4 pb-4">
        <h1 className="text-[15px] leading-snug text-ink">{p.title}</h1>
        <div className="mt-2 flex items-center gap-2">
          <span className="text-2xl font-extrabold text-ink">{money(p.price)}</span>
          {discount > 0 && (
            <>
              <span className="text-sm text-ink-faint line-through">{money(p.mrp)}</span>
              <span className="text-sm font-semibold text-green">{discount}% off</span>
            </>
          )}
        </div>
        <div className="mt-2 inline-flex items-center gap-1.5 rounded-md bg-brand-wash px-2 py-1 text-xs font-medium text-brand-ink">
          <span>🪔</span> UPI Offer applied for you!!
        </div>
        <div className="mt-2 text-sm text-ink-soft">
          ₹{payLater(p.price)} with <span className="font-semibold text-brand-ink">Meesho Pay Later</span> ›
        </div>
        <div className="mt-2 inline-flex items-center gap-1.5">
          <span
            className="inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-xs font-semibold text-white"
            style={{ background: ratingTone(Math.round(headlineRating)).badge }}
          >
            {headlineRating.toFixed(1)} ★
          </span>
          <span className="text-xs text-ink-faint">({compact(rs.total || p.rating_count)})</span>
        </div>
      </div>

      {/* size selector */}
      {sizes.length > 0 && (
        <div className="border-t-8 border-[#f2f2f7] px-4 py-4">
          <div className="mb-2 text-sm font-semibold text-ink">Select Size</div>
          <div className="flex flex-wrap gap-2.5">
            {sizes.map((s) => (
              <button
                key={s}
                onClick={() => setSize(s)}
                className={`grid h-11 min-w-11 place-items-center rounded-full border px-3 text-sm transition ${
                  size === s ? "border-brand bg-brand text-white" : "border-line bg-surface text-ink hover:border-brand/50"
                }`}
              >
                {s}
              </button>
            ))}
          </div>

          {chart && (
            <div className="mt-4">
              <button
                onClick={() => setShowChart((v) => !v)}
                className="flex w-full items-center justify-between text-sm font-semibold text-ink"
              >
                Size Chart <span className="text-ink-faint">{showChart ? "▲" : "▼"}</span>
              </button>
              {showChart && (
                <div className="mt-3 overflow-x-auto">
                  <div className="mb-2 text-xs font-medium text-brand-ink">Product Dimensions (inch)</div>
                  <table className="w-full text-center text-sm">
                    <thead>
                      <tr className="bg-[#f7f7fb] text-xs text-ink-soft">
                        <th className="px-2 py-2 font-medium">Size</th>
                        {chart.kind === "apparel" ? (
                          <>
                            <th className="px-2 py-2 font-medium">Length</th>
                            <th className="px-2 py-2 font-medium">Bust</th>
                            <th className="px-2 py-2 font-medium">Waist</th>
                            <th className="px-2 py-2 font-medium">Hip</th>
                          </>
                        ) : (
                          <th className="px-2 py-2 font-medium">Foot Length</th>
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {chart.rows.map((r) => (
                        <tr key={r.size} className="border-t border-line">
                          <td className="px-2 py-2 font-semibold text-ink">{r.size}</td>
                          {chart.kind === "apparel" ? (
                            <>
                              <td className="px-2 py-2 text-ink-soft">{r.length}</td>
                              <td className="px-2 py-2 text-ink-soft">{r.bust}</td>
                              <td className="px-2 py-2 text-ink-soft">{r.waist}</td>
                              <td className="px-2 py-2 text-ink-soft">{r.hip}</td>
                            </>
                          ) : (
                            <td className="px-2 py-2 text-ink-soft">{r.foot}&quot;</td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="mt-2 text-xs text-ink-faint">
                    💡 Build Trust adjusts your size from real return data — see it in your cart.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Build Trust verify — the differentiator, natively placed */}
      <div className="border-t-8 border-[#f2f2f7] px-4 py-4">
        <div className="mb-2 flex items-center gap-2">
          <span className="inline-flex items-center gap-1 rounded-md bg-brand-wash px-2 py-0.5 text-xs font-bold text-brand-ink">
            🛡 Agent 1 · Verification
          </span>
          <span className="text-xs text-ink-faint">fires on Buy Now — authenticity & disputes</span>
        </div>
        <VerifyPanel productId={p.id} title={p.title} />
      </div>

      {/* sold by */}
      <Link
        href="#"
        className="flex items-center justify-between border-t-8 border-[#f2f2f7] px-4 py-3.5"
      >
        <div className="flex items-center gap-2">
          <span className="grid h-8 w-8 place-items-center rounded-full bg-brand-wash text-sm">🏪</span>
          <div>
            <div className="text-[11px] text-ink-faint">Sold by</div>
            <div className="text-sm font-semibold text-ink">{seller.name}</div>
          </div>
          <span className="ml-1 inline-flex items-center gap-0.5 rounded border border-green/40 px-1.5 py-0.5 text-xs font-semibold text-green">
            {seller.rating.toFixed(1)} ★
          </span>
        </div>
        <span className="text-ink-faint">›</span>
      </Link>

      {/* product highlights */}
      <Section title="Product Highlights">
        <div className="grid grid-cols-2 gap-x-6 gap-y-3">
          {highlights(p).map(([k, v]) => (
            <div key={k}>
              <div className="text-xs text-ink-faint">{k}</div>
              <div className="text-sm font-medium text-ink">{v}</div>
            </div>
          ))}
        </div>
      </Section>

      {/* additional details */}
      <Section title="Additional Details">
        <dl className="space-y-2.5">
          {additionalDetails(p).map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4 text-sm">
              <dt className="text-ink-faint">{k}</dt>
              <dd className="text-right font-medium text-ink">{v}</dd>
            </div>
          ))}
        </dl>
      </Section>

      {/* ratings & reviews */}
      <Section title="Customer Ratings & Reviews">
        <div className="flex gap-4">
          <div
            className="grid h-20 w-20 shrink-0 place-content-center rounded-lg text-center text-white"
            style={{ background: ratingTone(Math.round(headlineRating)).badge }}
          >
            <div className="text-2xl font-bold leading-none">{headlineRating.toFixed(1)} ★</div>
            <div className="mt-1 text-[10px] opacity-90">{compact(rs.total)} ratings</div>
          </div>
          <div className="flex-1 space-y-1">
            {rs.rows.map((row) => (
              <div key={row.label} className="flex items-center gap-2 text-xs">
                <span className="w-16 text-ink-soft">{row.label}</span>
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#eee]">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${(row.count / maxBucket) * 100}%`, background: row.color }}
                  />
                </div>
                <span className="w-8 text-right text-ink-faint">{row.count}</span>
              </div>
            ))}
          </div>
        </div>

        {photoReviews.length > 0 && (
          <div className="mt-4">
            <div className="mb-2 text-sm font-semibold text-ink">Real Photos ({photoReviews.length})</div>
            <div className="flex gap-2 overflow-x-auto">
              {photoReviews.slice(0, 5).map((r) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img key={r.id} src={`/products/${p.id}.jpg`} alt="" className="h-16 w-16 shrink-0 rounded-md bg-[#f2f2f7] object-contain" />
              ))}
              {photoReviews.length > 5 && (
                <div className="grid h-16 w-16 shrink-0 place-items-center rounded-md bg-black/70 text-xs font-semibold text-white">
                  +{photoReviews.length - 5}
                </div>
              )}
            </div>
          </div>
        )}

        <div className="mt-4 space-y-4">
          {p.reviews.slice(0, 6).map((r) => {
            const d = reviewDisplay(r, p.id);
            const tone = ratingTone(r.rating);
            return (
              <div key={r.id} className="border-t border-line pt-3 first:border-t-0 first:pt-0">
                <div className="flex items-center gap-2">
                  <span
                    className="inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-xs font-semibold text-white"
                    style={{ background: tone.badge }}
                  >
                    {r.rating} ★
                  </span>
                  <span className="text-sm font-medium" style={{ color: tone.badge }}>
                    {d.verdictLabel}
                  </span>
                  <span className="text-xs text-ink-faint">· {d.date}</span>
                </div>
                <p className="mt-1.5 text-sm text-ink-soft">{r.text}</p>
                {d.photos > 0 && (
                  <div className="mt-2 flex gap-2">
                    {Array.from({ length: d.photos }).map((_, i) => (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img key={i} src={`/products/${p.id}.jpg`} alt="" className="h-14 w-14 rounded-md bg-[#f2f2f7] object-contain" />
                    ))}
                  </div>
                )}
                <div className="mt-2 flex items-center gap-3 text-xs text-ink-faint">
                  <span>~{d.name}</span>
                  <span className={r.reviewer_account_age_days < 30 ? "font-medium text-rose" : ""}>
                    {r.reviewer_account_age_days < 30 ? "⚠ new account" : "👍 Helpful (" + d.helpful + ")"}
                  </span>
                </div>
              </div>
            );
          })}
          {p.reviews.length === 0 && <p className="text-sm text-ink-faint">No reviews yet.</p>}
        </div>
      </Section>

      {/* disputes */}
      {orders.length > 0 && (
        <Section title="Your orders">
          <div className="space-y-4">
            {orders.map((o) => (
              <DisputeCard key={o.id} order={o} highlight={o.id === focusOrder} />
            ))}
          </div>
        </Section>
      )}

      {/* sticky buy bar */}
      <div className="fixed inset-x-0 bottom-0 z-20 mx-auto flex max-w-2xl gap-3 border-t border-line bg-surface px-4 py-2.5">
        <button className="flex-1 rounded-lg border border-brand py-3 text-sm font-bold text-brand-ink">
          🛒 Add to Cart
        </button>
        <button className="flex-1 rounded-lg bg-brand py-3 text-sm font-bold text-white">▶▶ Buy Now</button>
      </div>
    </div>
  );
}
