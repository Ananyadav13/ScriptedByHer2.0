"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, type AdminAction, type ManagerInfo } from "@/lib/api";
import { Badge, Card, Empty, Page, SectionTitle, Spinner } from "@/components/ui";

function actionLabel(action: string): { text: string; tone: "rose" | "amber" | "green" | "neutral" } {
  const map: Record<string, { text: string; tone: "rose" | "amber" | "green" | "neutral" }> = {
    manager_approve: { text: "Manager approved", tone: "green" },
    manager_unlock: { text: "Manager unlocked", tone: "green" },
    manager_suspend: { text: "Manager suspended", tone: "rose" },
    manager_suspend_and_request_changes: { text: "Suspended · changes required", tone: "rose" },
    manager_request_changes: { text: "Changes requested", tone: "amber" },
    manager_modify_listing: { text: "Sizing update requested", tone: "amber" },
    manager_confirm_lock: { text: "Manager confirmed", tone: "rose" },
    manager_delete: { text: "Manager delisted", tone: "rose" },
    manager_dispute_reject: { text: "Refund claim rejected", tone: "rose" },
    manager_dispute_approve: { text: "Refund approved", tone: "green" },
    lock: { text: "Trusty locked", tone: "rose" },
    suspend: { text: "Trusty suspended", tone: "rose" },
    correction: { text: "Correction window", tone: "amber" },
    hold: { text: "Held for info", tone: "amber" },
    recommend_review: { text: "Recommended to manager", tone: "amber" },
    fix_draft: { text: "Fix drafted", tone: "neutral" },
    fix_applied: { text: "Seller applied fix", tone: "green" },
    relabel_request: { text: "Relabel requested", tone: "amber" },
    request_qc_video: { text: "QC video requested", tone: "amber" },
    logistics_referral: { text: "Referred to logistics", tone: "neutral" },
    reverify: { text: "Seller reverified", tone: "green" },
  };
  return map[action] ?? { text: action.replace(/_/g, " "), tone: "neutral" };
}

export default function ManagerLogs() {
  const [managers, setManagers] = useState<ManagerInfo[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [rows, setRows] = useState<AdminAction[] | null>(null);

  useEffect(() => {
    api.managers().then((ms) => { setManagers(ms); setActive(ms[0]?.id ?? null); }).catch(() => setManagers([]));
  }, []);

  const load = useCallback(async (id: string) => {
    setRows(null);
    const [a, s] = await Promise.allSettled([api.adminActions(300), api.managerSellers(id)]);
    const mine = new Set(s.status === "fulfilled" ? s.value.sellers.map((x) => x.seller_id) : []);
    setRows(a.status === "fulfilled" ? a.value.actions.filter((x) => x.seller_id && mine.has(x.seller_id)) : []);
  }, []);

  useEffect(() => { if (active) load(active); }, [active, load]);

  return (
    <Page>
      <SectionTitle
        eyebrow="Manager · audit trail"
        title="Moderation logs"
        sub="Every action taken on your sellers' listings — by Trusty and by you — in one auditable trail."
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {managers.map((m) => (
          <button
            key={m.id}
            onClick={() => setActive(m.id)}
            className={`rounded-xl border px-4 py-2 text-sm transition ${
              active === m.id ? "border-brand bg-brand-wash text-brand-ink" : "border-line bg-surface text-ink-soft hover:bg-[#f2f3f8]"
            }`}
          >
            <span className="font-medium">{m.name}</span>
          </button>
        ))}
        <Link href="/manager" className="ml-auto text-sm font-medium text-brand-ink hover:underline">
          ← Back to action needed
        </Link>
      </div>

      {rows === null ? (
        <Spinner />
      ) : rows.length === 0 ? (
        <Empty>No recorded actions yet.</Empty>
      ) : (
        <Card className="divide-y divide-line p-0">
          {rows.map((a) => {
            const al = actionLabel(a.action);
            const comment = (a as unknown as { comment?: string }).comment;
            return (
              <div key={a.id} className="flex items-start gap-3 px-4 py-3">
                <Badge tone={al.tone}>{al.text}</Badge>
                <div className="min-w-0 flex-1">
                  <Link href={`/product/${a.product_id}`} className="text-sm font-medium text-ink hover:text-brand-ink hover:underline">
                    {a.product_title ?? a.product_id}
                  </Link>
                  {a.reason && <div className="truncate text-xs text-ink-faint">{a.reason}</div>}
                  {comment && <div className="mt-0.5 text-xs italic text-ink-soft">“{comment}”</div>}
                </div>
                <span className="shrink-0 text-xs text-ink-faint">{new Date(a.created_at).toLocaleDateString("en-IN")}</span>
              </div>
            );
          })}
        </Card>
      )}
    </Page>
  );
}
