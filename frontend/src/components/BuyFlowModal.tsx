"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, type Verdict } from "@/lib/api";
import { decisionMeta, isBlocking } from "@/lib/decisions";
import { Button } from "@/components/ui";
import { TracePanel } from "@/components/TracePanel";

// "Buy Now / Add to Cart" runs Agent 1 first (PLAN §5A: Agent 1 fires on BUY NOW),
// then gates: a blocking verdict stops the purchase; anything else lets it proceed.
export function BuyFlowModal({
  productId,
  title,
  mode,
  onClose,
}: {
  productId: string;
  title: string;
  mode: "cart" | "buy";
  onClose: () => void;
}) {
  const router = useRouter();
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [resolved, setResolved] = useState(false);
  const [done, setDone] = useState(false);

  const blocked = resolved && isBlocking(verdict?.decision);
  const dm = verdict ? decisionMeta(verdict.decision) : null;

  const proceed = () => {
    setDone(true);
    if (mode === "cart") setTimeout(() => router.push("/cart"), 1200);
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
