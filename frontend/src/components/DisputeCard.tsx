"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { CLAIM_TYPES, type DemoOrder } from "@/lib/orders";
import { Badge, Button, Card } from "@/components/ui";
import { TracePanel } from "@/components/TracePanel";

export function DisputeCard({ order, highlight }: { order: DemoOrder; highlight?: boolean }) {
  const [claim, setClaim] = useState(order.defaultClaim);
  const [open, setOpen] = useState(false);

  if (open) {
    return (
      <TracePanel
        label="Submit dispute"
        sublabel={`${order.label} · ${CLAIM_TYPES.find((c) => c.value === claim)?.label}`}
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
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-ink">{order.label}</span>
            <Badge tone="neutral">delivered</Badge>
          </div>
          <p className="mt-1 text-sm text-ink-soft">{order.note}</p>
        </div>
        <span className="text-2xl">📦</span>
      </div>
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
    </Card>
  );
}
