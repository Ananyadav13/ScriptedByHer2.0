"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type ManagerInfo, type ManagerQueue, type ManagerQueueItem } from "@/lib/api";
import { actionMeta, statusMeta } from "@/lib/decisions";
import { Badge, Button, Card, Empty, Page, SectionTitle, Spinner } from "@/components/ui";

export default function ManagerPage() {
  const [managers, setManagers] = useState<ManagerInfo[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [queue, setQueue] = useState<ManagerQueue | null>(null);
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
    setQueue(null);
    try {
      setQueue(await api.managerQueue(id));
    } catch {
      setQueue({ manager_id: id, queue_size: 0, items: [] });
    }
  }, []);

  useEffect(() => {
    if (active) load(active);
  }, [active, load]);

  const decide = async (item: ManagerQueueItem, decision: string) => {
    if (!active) return;
    setBusy(item.product_id + decision);
    try {
      await api.managerDecide(active, item.product_id, decision);
      await load(active);
    } finally {
      setBusy(null);
    }
  };

  return (
    <Page>
      <SectionTitle
        eyebrow="Governance"
        title="Manager console"
        sub="Agents recommend and take interim action — the human manager holds the final call."
      />

      <div className="mb-5 flex flex-wrap gap-2">
        {managers.map((m) => (
          <button
            key={m.id}
            onClick={() => setActive(m.id)}
            className={`rounded-xl border px-4 py-2 text-sm transition ${
              active === m.id
                ? "border-brand bg-brand-wash text-brand-ink"
                : "border-line bg-surface text-ink-soft hover:bg-[#f2f3f8]"
            }`}
          >
            <span className="font-medium">{m.name}</span>
            <span className="ml-2 text-xs text-ink-faint">{m.seller_count} sellers</span>
          </button>
        ))}
      </div>

      {queue === null && <Spinner />}
      {queue !== null && queue.items.length === 0 && (
        <Empty>
          Queue is clear. Lock a counterfeit or run an audit to see items arrive here for review.
        </Empty>
      )}

      <div className="space-y-4">
        {queue?.items.map((item) => {
          const sm = statusMeta(item.status);
          const ev = item.evidence ?? {};
          const evidence = (ev.evidence as string[]) ?? [];
          const remedy = (ev.suggested_remedy as string) || (ev.recommended_action as string) || "";
          const advisory = item.status === "flagged" || item.status === "needs_info";
          return (
            <Card key={item.product_id} className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-ink">{item.title}</h3>
                    <Badge tone={sm.tone}>{sm.label}</Badge>
                    {advisory ? (
                      <Badge tone="teal">advisory</Badge>
                    ) : (
                      <Badge tone="rose">interim action</Badge>
                    )}
                  </div>
                  <p className="mt-0.5 text-xs text-ink-faint">
                    {item.seller_id} · agent action: {actionMeta(item.agent_action).label}
                    {item.acted_at ? ` · ${new Date(item.acted_at).toLocaleString()}` : ""}
                  </p>
                </div>
              </div>

              {evidence.length > 0 && (
                <ul className="mt-3 space-y-1.5">
                  {evidence.map((e, i) => (
                    <li key={i} className="flex gap-2 text-sm text-ink-soft">
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />
                      {e}
                    </li>
                  ))}
                </ul>
              )}
              {remedy && (
                <div className="mt-3 rounded-lg bg-teal-wash px-3 py-2 text-sm text-teal">
                  Suggested remedy: {remedy}
                </div>
              )}

              <div className="mt-4 flex flex-wrap gap-2">
                <Button size="sm" variant="secondary" disabled={!!busy} onClick={() => decide(item, "unlock")}>
                  {busy === item.product_id + "unlock" ? <Spinner /> : "↩︎ Unlock"}
                </Button>
                <Button size="sm" disabled={!!busy} onClick={() => decide(item, "confirm_lock")}>
                  {busy === item.product_id + "confirm_lock" ? <Spinner /> : "✓ Confirm"}
                </Button>
                <Button size="sm" variant="danger" disabled={!!busy} onClick={() => decide(item, "delete")}>
                  {busy === item.product_id + "delete" ? <Spinner /> : "🗑 Delete"}
                </Button>
              </div>
            </Card>
          );
        })}
      </div>
    </Page>
  );
}
