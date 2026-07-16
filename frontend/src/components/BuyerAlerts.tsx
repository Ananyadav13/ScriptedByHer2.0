"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Notif } from "@/lib/api";

const ICON: Record<string, string> = {
  immediate: "🔒",
  high: "🛡️",
  normal: "💡",
};

// Buyer-facing transparency alerts: "the watch you viewed was locked", "size adjusted", etc.
export function BuyerAlerts() {
  const [notifs, setNotifs] = useState<Notif[]>([]);
  const [open, setOpen] = useState(true);

  useEffect(() => {
    api.notificationsFor("buyer", "buyer_normal").then(setNotifs).catch(() => setNotifs([]));
  }, []);

  if (notifs.length === 0 || !open) return null;

  return (
    <div className="mx-auto max-w-6xl px-5 pt-4">
      <div className="rounded-2xl border border-brand/20 bg-brand-wash/60 p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wide text-brand-ink">🔔 For you · from Build Trust</span>
          <button onClick={() => setOpen(false)} className="text-xs text-ink-faint hover:text-ink">
            dismiss
          </button>
        </div>
        <div className="flex gap-2 overflow-x-auto">
          {notifs.map((n) => {
            const inner = (
              <div className="flex min-w-[240px] max-w-xs shrink-0 gap-2 rounded-xl bg-surface p-2.5 shadow-sm">
                <span className="text-base">{ICON[n.priority] ?? "💡"}</span>
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-ink">{n.subject}</div>
                  <p className="line-clamp-2 text-xs text-ink-soft">{n.body}</p>
                </div>
              </div>
            );
            return n.related_id?.startsWith("prod_") ? (
              <Link key={n.id} href={`/product/${n.related_id}`}>
                {inner}
              </Link>
            ) : (
              <div key={n.id}>{inner}</div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
