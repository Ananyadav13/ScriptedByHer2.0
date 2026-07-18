"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type FitResult } from "@/lib/api";
import { Badge, Card, Empty, Page, SectionTitle, Spinner } from "@/components/ui";
import { productImage } from "@/lib/productImages";

const BUYER = "buyer_normal";
const PRODUCT = "prod_size_shoes";

export default function CartPage() {
  const [fit, setFit] = useState<FitResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(false);
  const [smart, setSmart] = useState(true);

  useEffect(() => {
    api
      .fit(BUYER, PRODUCT)
      .then(setFit)
      .catch(() => setErr(true))
      .finally(() => setLoading(false));
  }, []);

  const shown = fit ? (smart ? fit.adjusted : fit.original) : "—";

  return (
    <Page>
      <SectionTitle
        eyebrow="Trusty · Agent 2 recommendation"
        title="Your cart"
        sub="Before you buy, Trusty predicts your true size from real return data — a pre-purchase recommendation, no LLM on this path."
      />

      <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
        <Card className="p-5">
          <div className="flex gap-4">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={productImage(PRODUCT)}
              alt="Running Shoes"
              className="h-24 w-24 shrink-0 rounded-xl object-cover"
            />
            <div className="min-w-0 flex-1">
              <div className="text-xs uppercase tracking-wide text-ink-faint">StepUp</div>
              <h2 className="font-semibold text-ink">Running Shoes</h2>
              <p className="mt-1 text-sm text-ink-soft">Sold by seller_shoes · footwear</p>

              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className="text-sm text-ink-soft">Size:</span>
                <span
                  className={`grid h-9 min-w-9 place-items-center rounded-lg px-3 text-sm font-semibold transition ${
                    smart && fit && fit.adjusted !== fit.original
                      ? "bg-brand text-white"
                      : "border border-line bg-surface text-ink"
                  }`}
                >
                  {loading ? <Spinner /> : shown}
                </span>
                {smart && fit && fit.adjusted !== fit.original && (
                  <Badge tone="brand">auto-adjusted from {fit.original}</Badge>
                )}
              </div>

              {loading && <p className="mt-3 text-sm text-ink-faint">Predicting your fit…</p>}
              {err && (
                <p className="mt-3 text-sm text-rose">Couldn&apos;t reach the fit service.</p>
              )}
              {fit && smart && (
                <div className="mt-3 rounded-lg bg-teal-wash px-3 py-2 text-sm text-teal">
                  📏 {fit.explanation}
                </div>
              )}
              {fit && !smart && (
                <div className="mt-3 rounded-lg bg-amber-wash px-3 py-2 text-sm text-amber">
                  Without Build Trust, you&apos;d order your usual {fit.original} — and this brand runs{" "}
                  {fit.drift_delta < 0 ? "small" : "large"}. That&apos;s a likely return.
                </div>
              )}
            </div>
          </div>

          <div className="mt-5 flex items-center justify-between border-t border-line pt-4">
            <label className="flex cursor-pointer items-center gap-2 text-sm text-ink-soft">
              <input
                type="checkbox"
                checked={smart}
                onChange={(e) => setSmart(e.target.checked)}
                className="h-4 w-4 accent-[var(--brand)]"
              />
              Build Trust size adjustment
            </label>
            <button className="rounded-xl bg-brand px-4 py-2.5 text-sm font-medium text-white transition hover:bg-brand-ink">
              Checkout · size {loading ? "…" : shown}
            </button>
          </div>
        </Card>

        <Card className="p-5">
          <h3 className="font-semibold text-ink">How this size was chosen</h3>
          {fit ? (
            <dl className="mt-3 space-y-2.5 text-sm">
              {[
                ["Your usual size", fit.original],
                ["Adjusted size", fit.adjusted],
                ["Brand drift", `${fit.drift_delta > 0 ? "+" : ""}${fit.drift_delta} vs label`],
                ["Return sample", `${fit.sample_size} orders`],
                ["Source", fit.source],
              ].map(([k, v]) => (
                <div key={k} className="flex items-center justify-between gap-3">
                  <dt className="text-ink-faint">{k}</dt>
                  <dd className="font-medium text-ink">{v}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <Empty>{loading ? "Loading…" : "No fit data."}</Empty>
          )}
          <p className="mt-4 text-xs text-ink-faint">
            Pure join of your kept-size history × the brand&apos;s return-drift table. No model call —
            fast, free, and explainable.
          </p>
          <Link
            href="/orders"
            className="mt-3 inline-block text-sm font-medium text-brand-ink hover:underline"
          >
            See your orders & open a delivery dispute →
          </Link>
        </Card>
      </div>
    </Page>
  );
}
