"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type FitResult } from "@/lib/api";
import { Badge, Button, Card, Empty, Page, SectionTitle, Spinner } from "@/components/ui";
import { productImage } from "@/lib/productImages";
import { cartTotal, clearCart, removeFromCart, useCart, type CartItem } from "@/lib/cart";

const BUYER = "buyer_normal";
const money = (n: number) => "₹" + Math.round(n).toLocaleString("en-IN");

/** One cart line. Agent 2's size prediction runs per item — it only returns a result for
 *  categories the size-drift table covers, so an item without drift data simply shows no
 *  size chip rather than an error. */
function CartLine({ item, smart }: { item: CartItem; smart: boolean }) {
  // Tagged with the product it describes, so "loading" is derived rather than a separate
  // flag that could disagree with the data — and a slow response for a removed item can
  // never paint under a different line.
  const [result, setResult] = useState<{ productId: string; fit: FitResult | null } | null>(null);
  const loading = result?.productId !== item.product_id;
  const fit = loading ? null : result!.fit;

  useEffect(() => {
    const pid = item.product_id;
    let cancelled = false;
    (async () => {
      try {
        const f = await api.fit(BUYER, pid);
        if (!cancelled) setResult({ productId: pid, fit: f });
      } catch {
        // no drift data for this category — the item just shows no size chip
        if (!cancelled) setResult({ productId: pid, fit: null });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [item.product_id]);

  // `/fit` always answers, falling back to `no_history` for categories it knows nothing
  // about (a coffee mug has no size). Showing a size chip in that case would invent a
  // recommendation the engine never made, so those items render without one.
  const hasFitData = !!fit && fit.source !== "no_history";
  const adjusted = hasFitData && fit!.adjusted !== fit!.original;
  const shown = hasFitData ? (smart ? fit!.adjusted : fit!.original) : null;

  return (
    <div className="flex gap-4 border-b border-line py-4 last:border-b-0">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={productImage(item.product_id)}
        alt=""
        className="h-24 w-24 shrink-0 rounded-xl bg-[#f2f2f7] object-cover"
      />
      <div className="min-w-0 flex-1">
        {item.brand && (
          <div className="text-xs uppercase tracking-wide text-ink-faint">{item.brand}</div>
        )}
        <Link href={`/product/${item.product_id}`} className="font-semibold text-ink hover:text-brand-ink hover:underline">
          {item.title}
        </Link>
        <div className="mt-0.5 text-sm text-ink-soft">
          {item.price != null ? money(item.price) : "—"}
          {item.qty > 1 && <span className="text-ink-faint"> × {item.qty}</span>}
        </div>

        {loading ? (
          <div className="mt-2"><Spinner /></div>
        ) : shown ? (
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className="text-sm text-ink-soft">Size:</span>
            <span
              className={`grid h-9 min-w-9 place-items-center rounded-lg px-3 text-sm font-semibold transition ${
                smart && adjusted ? "bg-brand text-white" : "border border-line bg-surface text-ink"
              }`}
            >
              {shown}
            </span>
            {smart && adjusted && <Badge tone="brand">auto-adjusted from {fit!.original}</Badge>}
          </div>
        ) : null}

        {hasFitData && smart && (
          <div className="mt-2 rounded-lg bg-teal-wash px-3 py-2 text-sm text-teal">
            📏 {fit.explanation}
          </div>
        )}
        {hasFitData && !smart && adjusted && (
          <div className="mt-2 rounded-lg bg-amber-wash px-3 py-2 text-sm text-amber">
            Without Build Trust you&apos;d order your usual {fit.original} — and this brand runs{" "}
            {fit.drift_delta < 0 ? "small" : "large"}. That&apos;s a likely return.
          </div>
        )}
      </div>
      <button
        onClick={() => removeFromCart(item.product_id)}
        aria-label={`Remove ${item.title} from cart`}
        className="h-8 shrink-0 rounded-lg px-2 text-sm text-ink-faint transition hover:bg-[#f2f2f7] hover:text-rose"
      >
        Remove
      </button>
    </div>
  );
}

export default function CartPage() {
  const items = useCart();
  const [smart, setSmart] = useState(true);
  const [placed, setPlaced] = useState(false);

  const total = cartTotal(items);

  const checkout = () => {
    // No payment integration in a prototype — but the order must visibly complete and the
    // cart must actually empty, otherwise the button reads as broken (it previously had no
    // handler at all and did nothing when clicked).
    clearCart();
    setPlaced(true);
  };

  if (placed) {
    return (
      <Page>
        <SectionTitle eyebrow="Checkout" title="Order placed" sub="This is a prototype — no real payment was taken." />
        <Card className="p-8 text-center">
          <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-green-wash text-2xl">✓</div>
          <p className="mt-3 font-semibold text-ink">Your order is confirmed</p>
          <p className="mt-1 text-sm text-ink-soft">
            Sizes were set from your kept-size history, so this order should not come back as a
            fit return.
          </p>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            <Link href="/orders" className="rounded-xl bg-brand px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-ink">
              View your orders →
            </Link>
            <Link href="/" className="rounded-xl border border-line px-4 py-2.5 text-sm font-medium text-ink-soft transition hover:bg-[#f2f3f8]">
              Keep shopping
            </Link>
          </div>
        </Card>
      </Page>
    );
  }

  return (
    <Page>
      <SectionTitle
        eyebrow="Trusty · Agent 2 recommendation"
        title="Your cart"
        sub="Before you buy, Trusty predicts your true size from real return data — a pre-purchase recommendation, no LLM on this path."
      />

      {items.length === 0 ? (
        <Empty>
          <p>Your cart is empty.</p>
          <Link href="/" className="mt-3 inline-block text-sm font-medium text-brand-ink hover:underline">
            Browse the catalogue →
          </Link>
        </Empty>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
          <Card className="p-5">
            {items.map((it) => (
              <CartLine key={it.product_id} item={it} smart={smart} />
            ))}

            <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
              <label className="flex cursor-pointer items-center gap-2 text-sm text-ink-soft">
                <input
                  type="checkbox"
                  checked={smart}
                  onChange={(e) => setSmart(e.target.checked)}
                  className="h-4 w-4 accent-[var(--brand)]"
                />
                Build Trust size adjustment
              </label>
              <div className="flex items-center gap-3">
                <span className="text-sm text-ink-soft">
                  Total <b className="text-ink">{money(total)}</b>
                </span>
                <Button onClick={checkout}>Checkout</Button>
              </div>
            </div>
          </Card>

          <Card className="p-5">
            <h3 className="font-semibold text-ink">How your sizes were chosen</h3>
            <p className="mt-2 text-sm text-ink-soft">
              For every item in your cart, Trusty joins your kept-size history against that
              brand&apos;s return-drift table. Items in categories with no drift data are left
              exactly as listed.
            </p>
            <p className="mt-4 text-xs text-ink-faint">
              A pure join — no model call. Fast, free, and explainable.
            </p>
            <Link
              href="/orders"
              className="mt-3 inline-block text-sm font-medium text-brand-ink hover:underline"
            >
              See your orders &amp; open a delivery dispute →
            </Link>
          </Card>
        </div>
      )}
    </Page>
  );
}
