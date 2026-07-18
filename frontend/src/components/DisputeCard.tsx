"use client";

import { useState } from "react";
import { api, type BuyerOrder } from "@/lib/api";
import { CLAIM_TYPES } from "@/lib/orders";
import { Badge, Button, Card } from "@/components/ui";
import { TracePanel } from "@/components/TracePanel";

const money = (n: number | null) => (n == null ? "" : "₹" + Math.round(n).toLocaleString("en-IN"));
const STATUS_TONE: Record<string, "neutral" | "teal" | "amber"> = {
  delivered: "neutral",
  refunded: "teal",
  manual_review: "amber",
};

/** One order card in "My Orders". A buyer can open a dispute; the agent's live trace replaces
 *  the card. The `reaction` preview tells the buyer what will happen BEFORE they open it — the
 *  same routing the agent will reach, so buyer-facing copy and the agent never disagree. */
export function DisputeCard({ order, highlight }: { order: BuyerOrder; highlight?: boolean }) {
  const defaultClaim = order.claim_type ?? "item_not_as_described";
  const [claim, setClaim] = useState(defaultClaim);
  const [open, setOpen] = useState(false);

  if (open) {
    return (
      <TracePanel
        label={`Dispute · ${order.product_title}`}
        sublabel={CLAIM_TYPES.find((c) => c.value === claim)?.label}
        autoStart
        start={async () => {
          const r = await api.dispute({ order_id: order.id, claim_type: claim });
          return r.investigation_id;
        }}
      />
    );
  }

  return (
    <Card className={`p-5 ${highlight ? "ring-2 ring-brand/30" : ""}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-ink">{order.product_title}</span>
            {order.variant && <Badge tone="neutral">{order.variant}</Badge>}
            <Badge tone={STATUS_TONE[order.status] ?? "neutral"}>{order.status.replace("_", " ")}</Badge>
          </div>
          <p className="mt-1 text-xs text-ink-faint">
            {money(order.price)}
            {order.delivered_at ? ` · delivered ${new Date(order.delivered_at).toLocaleDateString("en-IN")}` : ""}
            {order.hub_name ? ` · via ${order.hub_name}` : ""}
          </p>
        </div>
        <span className="text-2xl">📦</span>
      </div>

      {/* what a dispute here would trigger — matches the agent's routing */}
      <div
        className={`mt-3 rounded-lg px-3 py-2 text-xs ${
          order.reaction.tone === "amber"
            ? "bg-amber-wash text-amber"
            : order.reaction.tone === "teal"
              ? "bg-teal-wash text-teal"
              : order.reaction.tone === "brand"
                ? "bg-brand-wash text-brand-ink"
                : "bg-[#f2f3f8] text-ink-soft"
        }`}
      >
        🛡 {order.reaction.label}
      </div>

      {order.dispute_available ? (
        <>
          <div className="mt-4">
            <label className="mb-1.5 block text-xs font-medium text-ink-faint">What went wrong?</label>
            <div className="flex flex-wrap gap-2">
              {CLAIM_TYPES.map((c) => (
                <button
                  key={c.value}
                  onClick={() => setClaim(c.value)}
                  className={`rounded-full px-3 py-1.5 text-xs font-medium transition ${
                    claim === c.value
                      ? "bg-brand text-white"
                      : "border border-line bg-surface text-ink-soft hover:bg-[#f2f3f8]"
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>
          </div>
          <Button className="mt-4 w-full" onClick={() => setOpen(true)}>
            Open dispute → let the agent decide
          </Button>
        </>
      ) : (
        <p className="mt-4 text-xs text-ink-faint">This order is closed — no dispute available.</p>
      )}
    </Card>
  );
}
