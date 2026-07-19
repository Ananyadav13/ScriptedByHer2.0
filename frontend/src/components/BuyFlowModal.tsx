"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type FitResult, type Verdict } from "@/lib/api";
import { decisionMeta, isBlocking } from "@/lib/decisions";
import { Button } from "@/components/ui";
import { addToCart, clearCart } from "@/lib/cart";
import { TracePanel } from "@/components/TracePanel";

// "Buy Now / Add to Cart" runs Agent 1 first (the agent fires on BUY NOW),
// then gates: a blocking verdict stops the purchase; anything else lets it proceed.
export function BuyFlowModal({
  productId,
  title,
  price,
  brand,
  mode,
  onClose,
}: {
  productId: string;
  title: string;
  price?: number | null;
  brand?: string | null;
  mode: "cart" | "buy";
  onClose: () => void;
}) {
  const router = useRouter();
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [resolved, setResolved] = useState(false);
  const [done, setDone] = useState(false);
  const [fit, setFit] = useState<FitResult | null>(null);

  // Agent 2's size prediction, for the Buy Now path only — the cart page already shows it,
  // and Buy Now bypasses the cart entirely. Deterministic and cheap (a pure join), so it
  // runs alongside Agent 1's verification rather than after it.
  useEffect(() => {
    if (mode !== "buy") return;
    let cancelled = false;
    api
      .fit("buyer_normal", productId)
      .then((f) => !cancelled && setFit(f))
      .catch(() => !cancelled && setFit(null));
    return () => {
      cancelled = true;
    };
  }, [mode, productId]);

  const blocked = resolved && isBlocking(verdict?.decision);
  const dm = verdict ? decisionMeta(verdict.decision) : null;

  const proceed = () => {
    // Actually put it in the cart. This screen used to say "Added to your cart" while
    // storing nothing, so the cart page showed the same hardcoded product regardless.
    if (mode === "cart") {
      addToCart({ product_id: productId, title, price: price ?? null, brand });
      setTimeout(() => router.push("/cart"), 1200);
    } else {
      // Buy Now places the order directly, so it lands in My Orders and can be disputed —
      // the same loop checkout follows. Fire-and-forget: the confirmation should not hang
      // on the write, and a failure here must not strand the buyer on a spinner.
      void api.placeOrder(productId).catch(() => {});
      clearCart();
    }
    setDone(true);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4">
      <div className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-surface p-5 sm:rounded-2xl">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-bold text-ink">
            {mode === "cart" ? "Add to Cart" : "Buy Now"} — safety check
          </h2>
          <button onClick={onClose} className="grid h-8 w-8 place-items-center rounded-full text-ink-faint hover:bg-[#f2f2f7]">
            ✕
          </button>
        </div>

        {!done ? (
          <>
            <p className="mb-3 text-sm text-ink-soft">
              Before you pay, <b className="text-brand-ink">Agent 1</b> verifies this listing for
              authenticity. You&apos;ll see it work.
            </p>
            <TracePanel
              label="Verify"
              sublabel={title}
              autoStart
              start={async () => {
                const r = await api.investigate({ product_id: productId, trigger: "pre_purchase" });
                return r.investigation_id;
              }}
              onResolve={(v) => {
                setVerdict(v);
                setResolved(true);
              }}
            />

            {resolved && (
              <div className="mt-4">
                {blocked ? (
                  <div className="rounded-xl bg-rose-wash p-4">
                    <div className="font-semibold text-rose">⚠ Not safe to buy</div>
                    <p className="mt-1 text-sm text-rose">
                      Agent 1 verdict: <b>{dm?.label}</b>. {verdict?.buyer_explanation}
                    </p>
                    <Button variant="secondary" className="mt-3 w-full" onClick={onClose}>
                      Back to shop
                    </Button>
                  </div>
                ) : (
                  <div className="rounded-xl bg-green-wash p-4">
                    <div className="font-semibold text-green">
                      ✓ {verdict ? "Verified — safe to buy" : "Proceeding (verification unavailable)"}
                    </div>
                    {verdict?.buyer_explanation && (
                      <p className="mt-1 text-sm text-green">{verdict.buyer_explanation}</p>
                    )}
                    {/* Buy Now skips the cart, which is the only other place Agent 2's size
                        prediction is shown — so surface it here too. Both agents contribute
                        to the same purchase decision, and a buyer going straight to payment
                        should not silently lose the fit correction. */}
                    {mode === "buy" && fit && fit.source !== "no_history" && (
                      <div className="mt-3 rounded-lg bg-teal-wash px-3 py-2 text-left">
                        <div className="text-xs font-semibold uppercase tracking-wide text-teal">
                          Agent 2 · size recommendation
                        </div>
                        <p className="mt-1 text-sm text-teal">
                          📏 {fit.explanation}
                          {fit.adjusted !== fit.original && (
                            <> Ordering size <b>{fit.adjusted}</b> instead of {fit.original}.</>
                          )}
                        </p>
                      </div>
                    )}
                    <Button className="mt-3 w-full" onClick={proceed}>
                      {mode === "cart" ? "Add to Cart" : "Continue to payment"}
                    </Button>
                  </div>
                )}
              </div>
            )}
          </>
        ) : (
          <div className="py-8 text-center">
            <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-green-wash text-2xl">✓</div>
            <p className="mt-3 font-semibold text-ink">
              {mode === "cart" ? "Added to your cart" : "Order placed — demo"}
            </p>
            <p className="mt-1 text-sm text-ink-faint">
              {mode === "cart" ? "Taking you to your cart…" : "This is a hackathon demo — no real payment."}
            </p>
            <Button variant="secondary" className="mt-4" onClick={onClose}>
              Done
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
