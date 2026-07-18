"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type BuyerOrders, type BuyerSummary } from "@/lib/api";
import { Badge, Card, Empty, Page, SectionTitle, Spinner } from "@/components/ui";
import { DisputeCard } from "@/components/DisputeCard";

export default function OrdersPage() {
  const [buyers, setBuyers] = useState<BuyerSummary[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [data, setData] = useState<BuyerOrders | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .buyers()
      .then((bs) => {
        setBuyers(bs);
        setActive(bs[0]?.id ?? null);
      })
      .catch(() => setBuyers([]));
  }, []);

  const load = useCallback(async (id: string) => {
    setLoading(true);
    setData(null);
    try {
      setData(await api.buyerOrders(id));
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (active) load(active);
  }, [active, load]);

  return (
    <Page>
      <SectionTitle
        eyebrow="My Orders"
        title="Your orders & disputes"
        sub="Open a dispute and Agent 1 decides — the outcome depends on your history and the delivery evidence, shown up front."
      />

      {/* buyer switcher — demo two very different claim histories */}
      {buyers.length > 0 && (
        <div className="mb-5 flex flex-wrap gap-2">
          {buyers.map((b) => (
            <button
              key={b.id}
              onClick={() => setActive(b.id)}
              className={`rounded-xl border px-4 py-2 text-sm transition ${
                active === b.id
                  ? "border-brand bg-brand-wash text-brand-ink"
                  : "border-line bg-surface text-ink-soft hover:bg-[#f2f3f8]"
              }`}
            >
              {b.name}
              <span className="ml-2 text-xs text-ink-faint">{b.order_count} orders</span>
            </button>
          ))}
        </div>
      )}

      {/* claim-history context — the SAME standing the dispute agent reads */}
      {data && (
        <Card
          className={`mb-6 flex items-start gap-3 p-4 ${
            data.claim_context.is_serial_claimer ? "bg-amber-wash" : "bg-teal-wash"
          }`}
        >
          <span className="text-xl">{data.claim_context.is_serial_claimer ? "⚠️" : "✅"}</span>
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-ink">
              Claim history
              <Badge tone={data.claim_context.is_serial_claimer ? "amber" : "teal"}>
                {data.claim_context.claim_count} prior claims
              </Badge>
            </div>
            <p className="mt-1 text-sm text-ink-soft">{data.claim_context.note}</p>
          </div>
        </Card>
      )}

      {loading && <Spinner />}
      {!loading && data && data.orders.length === 0 && <Empty>No orders yet.</Empty>}

      <div className="space-y-4">
        {data?.orders.map((o) => (
          <DisputeCard key={o.id} order={o} />
        ))}
      </div>
    </Page>
  );
}
