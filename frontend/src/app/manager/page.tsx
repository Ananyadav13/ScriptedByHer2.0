"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  api,
  type ManagerInfo,
  type ManagerSeller,
  type ManagerSellerProduct,
  type Notif,
} from "@/lib/api";
import { statusMeta } from "@/lib/decisions";
import { Badge, Button, Card, Empty, Page, SectionTitle, Spinner } from "@/components/ui";
import { ManagerApiPanel } from "@/components/ManagerApiPanel";

const PRIORITY_TONE: Record<string, "rose" | "amber" | "neutral"> = {
  immediate: "rose",
  high: "amber",
  normal: "neutral",
};

function SellerCard({
  s,
  onDecide,
  busy,
}: {
  s: ManagerSeller;
  onDecide: (p: ManagerSellerProduct, decision: string) => void;
  busy: string | null;
}) {
  const ratingTone = s.rating >= 4 ? "green" : s.rating >= 3 ? "amber" : "rose";
  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-full bg-brand-wash text-sm">🏪</span>
          <div>
            <div className="font-semibold text-ink">{s.name}</div>
            <div className="text-xs text-ink-faint">
              {s.account_age_days}d old · {s.product_count} listings
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <Badge tone={ratingTone}>{s.rating.toFixed(1)} ★</Badge>
          {s.case_count > 0 && <Badge tone="rose">{s.case_count} cases</Badge>}
          {s.trust_flags.map((f) => (
            <Badge key={f} tone="amber">
              {f.replace(/_/g, " ")}
            </Badge>
          ))}
          {s.banned && <Badge tone="rose">banned</Badge>}
        </div>
      </div>

      <div className="mt-3 space-y-2">
        {s.products.map((p) => {
          const sm = statusMeta(p.status);
          return (
            <div
              key={p.product_id}
              className={`rounded-lg border p-2.5 ${p.needs_action ? "border-amber/40 bg-amber-wash/30" : "border-line"}`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Link href={`/product/${p.product_id}`} className="text-sm font-medium text-ink hover:text-brand-ink hover:underline">
                  {p.title}
                </Link>
                <div className="flex items-center gap-1.5">
                  {p.rating != null && <span className="text-xs text-ink-faint">{p.rating}★ ({p.review_count})</span>}
                  <Badge tone={sm.tone}>{sm.label}</Badge>
                </div>
              </div>
              {p.complaint && (
                <div className="mt-1 text-xs text-amber">
                  ⚠ {p.complaint.label} — {Math.round(p.complaint.agreement * 100)}% of {p.complaint.count} complaints agree
                </div>
              )}
              {p.needs_action && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <Button size="sm" variant="secondary" disabled={!!busy} onClick={() => onDecide(p, "unlock")}>
                    {busy === p.product_id + "unlock" ? <Spinner /> : "↩︎ Unlock"}
                  </Button>
                  <Button size="sm" disabled={!!busy} onClick={() => onDecide(p, "confirm_lock")}>
                    {busy === p.product_id + "confirm_lock" ? <Spinner /> : "✓ Confirm"}
                  </Button>
                  <Button size="sm" variant="danger" disabled={!!busy} onClick={() => onDecide(p, "delete")}>
                    {busy === p.product_id + "delete" ? <Spinner /> : "🗑 Delist"}
                  </Button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}

export default function ManagerPage() {
  const [managers, setManagers] = useState<ManagerInfo[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [sellers, setSellers] = useState<ManagerSeller[] | null>(null);
  const [notifs, setNotifs] = useState<Notif[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    api
      .managers()
      .then((ms) => {
        setManagers(ms);
        setActive(ms[0]?.id ?? null);
      })
      .catch(() => setManagers([]));
  }, []);

  const load = useCallback(async (id: string) => {
    setSellers(null);
    const [s, n] = await Promise.allSettled([api.managerSellers(id), api.notificationsFor("manager", id)]);
    setSellers(s.status === "fulfilled" ? s.value.sellers : []);
    setNotifs(n.status === "fulfilled" ? n.value : []);
  }, []);

  useEffect(() => {
    if (active) load(active);
  }, [active, load]);

  const decide = async (p: ManagerSellerProduct, decision: string) => {
    if (!active) return;
    setBusy(p.product_id + decision);
    try {
      await api.managerDecide(active, p.product_id, decision);
      await load(active);
    } finally {
      setBusy(null);
    }
  };

  const flagged = (sellers ?? []).reduce((a, s) => a + s.flagged_count, 0);

  return (
    <Page>
      <SectionTitle
        eyebrow="Business-manager console"
        title="Your sellers & their listings"
        sub="Agents recommend and take interim action — you hold the final call. Here's every seller you manage and what needs attention."
      />

      {/* manager switcher */}
      <div className="mb-5 flex flex-wrap gap-2">
        {managers.map((m) => (
          <button
            key={m.id}
            onClick={() => setActive(m.id)}
            className={`rounded-xl border px-4 py-2 text-sm transition ${
              active === m.id ? "border-brand bg-brand-wash text-brand-ink" : "border-line bg-surface text-ink-soft hover:bg-[#f2f3f8]"
            }`}
          >
            <span className="font-medium">{m.name}</span>
            <span className="ml-2 text-xs text-ink-faint">{m.seller_count} sellers</span>
          </button>
        ))}
      </div>

      {/* API access for integrations */}
      {active && <ManagerApiPanel managerId={active} />}

      {/* notifications */}
      {notifs.length > 0 && (
        <div className="mb-6">
          <h2 className="mb-2 text-sm font-semibold text-ink">🔔 Your alerts</h2>
          <div className="space-y-2">
            {notifs.map((n) => (
              <Card key={n.id} className="flex items-start justify-between gap-3 p-3">
                <div>
                  <div className="text-sm font-medium text-ink">{n.subject}</div>
                  <p className="text-xs text-ink-soft">{n.body}</p>
                </div>
                <Badge tone={PRIORITY_TONE[n.priority] ?? "neutral"}>{n.priority}</Badge>
              </Card>
            ))}
          </div>
        </div>
      )}

      <div className="mb-4 flex items-center gap-2 text-sm text-ink-soft">
        <Badge tone={flagged > 0 ? "rose" : "green"}>{flagged} listings need action</Badge>
        <span className="text-ink-faint">across {sellers?.length ?? 0} sellers</span>
      </div>

      {sellers === null ? (
        <Spinner />
      ) : sellers.length === 0 ? (
        <Empty>No sellers for this manager.</Empty>
      ) : (
        <div className="space-y-3">
          {sellers.map((s) => (
            <SellerCard key={s.seller_id} s={s} onDecide={decide} busy={busy} />
          ))}
        </div>
      )}
    </Page>
  );
}
