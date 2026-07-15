"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  api,
  type AdminAction,
  type AuditResult,
  type Hub,
  type Notification,
} from "@/lib/api";
import { actionMeta } from "@/lib/decisions";
import { Badge, Button, Card, Empty, Page, SectionTitle, Spinner } from "@/components/ui";

const SUMMARY_META: { key: string; label: string; tone: string }[] = [
  { key: "suspended", label: "Suspended", tone: "text-rose" },
  { key: "correction_window", label: "Correction", tone: "text-amber" },
  { key: "logistics_referral", label: "Logistics", tone: "text-teal" },
  { key: "fix_drafts", label: "Fix drafts", tone: "text-brand-ink" },
  { key: "kept", label: "Kept", tone: "text-green" },
];

const PRIORITY_TONE: Record<string, "rose" | "amber" | "neutral"> = {
  immediate: "rose",
  high: "amber",
  normal: "neutral",
};

export default function AdminPage() {
  const [actions, setActions] = useState<AdminAction[] | null>(null);
  const [notifs, setNotifs] = useState<Notification[]>([]);
  const [hubs, setHubs] = useState<Hub[]>([]);
  const [audit, setAudit] = useState<AuditResult | null>(null);
  const [running, setRunning] = useState(false);

  const loadAll = useCallback(async () => {
    const [a, n, h] = await Promise.allSettled([
      api.adminActions(50),
      api.notifications(),
      api.hubs(),
    ]);
    if (a.status === "fulfilled") setActions(a.value.actions);
    else setActions([]);
    if (n.status === "fulfilled") setNotifs(n.value);
    if (h.status === "fulfilled") setHubs(h.value);
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const runAudit = async () => {
    setRunning(true);
    try {
      const r = await api.audit(false); // deterministic sweep — fast, no LLM quota
      setAudit(r);
      await loadAll();
    } catch {
      // ignore — surfaced via empty state
    } finally {
      setRunning(false);
    }
  };

  return (
    <Page>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <SectionTitle
          eyebrow="Agent 2 · catalog integrity"
          title="Admin console"
          sub="Sweep the catalog, route each listing fairly, and watch the action queue fill."
        />
        <Button onClick={runAudit} disabled={running}>
          {running ? <Spinner /> : "🗂️"} Run catalog audit
        </Button>
      </div>

      {audit && (
        <Card className="mb-6 p-5">
          <div className="mb-3 text-sm font-medium text-ink">
            Audit swept {audit.evaluated} active listings
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            {SUMMARY_META.map((s) => (
              <div key={s.key} className="rounded-xl border border-line p-3 text-center">
                <div className={`text-2xl font-bold ${s.tone}`}>{audit.summary[s.key] ?? 0}</div>
                <div className="text-xs text-ink-faint">{s.label}</div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-ink-faint">
            Fraud suspended · fixable listings drafted a correction · delivery faults referred to
            logistics with <b>no seller penalty</b>.
          </p>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        {/* Action queue */}
        <div>
          <h2 className="mb-3 font-semibold text-ink">Action queue</h2>
          {actions === null && <Spinner />}
          {actions !== null && actions.length === 0 && (
            <Empty>No catalog actions yet. Run an audit or trigger an investigation.</Empty>
          )}
          <div className="space-y-2.5">
            {actions?.map((a) => {
              const am = actionMeta(a.action);
              return (
                <Card key={a.id} className="p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Badge tone={am.tone}>{am.label}</Badge>
                      {a.tier && <Badge tone="neutral">{a.tier}</Badge>}
                      {a.seller_approved && <Badge tone="green">approved</Badge>}
                    </div>
                    <span className="text-xs text-ink-faint">
                      {new Date(a.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="mt-2 text-sm font-medium text-ink">
                    {a.product_title ? (
                      <Link href={`/product/${a.product_id}`} className="hover:text-brand-ink hover:underline">
                        {a.product_title}
                      </Link>
                    ) : (
                      a.product_id
                    )}
                    {a.seller_id && <span className="ml-2 text-xs text-ink-faint">{a.seller_id}</span>}
                  </div>
                  {a.reason && <p className="mt-1 text-sm text-ink-soft">{a.reason}</p>}
                </Card>
              );
            })}
          </div>
        </div>

        {/* Ops sidebar */}
        <div className="space-y-6">
          <div>
            <h2 className="mb-3 font-semibold text-ink">Notifications</h2>
            {notifs.length === 0 ? (
              <Empty>No notifications.</Empty>
            ) : (
              <div className="space-y-2.5">
                {notifs.slice(0, 8).map((n) => (
                  <Card key={n.id} className="p-3.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium text-ink">{n.subject}</span>
                      <Badge tone={PRIORITY_TONE[n.priority] ?? "neutral"}>{n.priority}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-ink-soft">{n.body}</p>
                    <span className="mt-1 block text-[10px] uppercase tracking-wide text-ink-faint">
                      → {n.audience}
                    </span>
                  </Card>
                ))}
              </div>
            )}
          </div>

          <div>
            <h2 className="mb-3 font-semibold text-ink">Delivery hubs</h2>
            <Card className="divide-y divide-line">
              {hubs.length === 0 && <div className="p-4 text-sm text-ink-faint">No hub data.</div>}
              {hubs.map((h) => (
                <div key={h.id} className="flex items-center justify-between p-3.5">
                  <div>
                    <div className="text-sm font-medium text-ink">{h.name}</div>
                    <div className="text-xs text-ink-faint">{h.region}</div>
                  </div>
                  <Badge tone={h.case_count >= 5 ? "rose" : h.case_count > 0 ? "amber" : "green"}>
                    {h.case_count} cases
                  </Badge>
                </div>
              ))}
            </Card>
          </div>
        </div>
      </div>
    </Page>
  );
}
