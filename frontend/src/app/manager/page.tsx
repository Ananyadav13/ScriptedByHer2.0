"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, type ManagerInfo, type ManagerQueueItem, type ManagerSeller } from "@/lib/api";
import { statusMeta } from "@/lib/decisions";
import { Badge, Button, Card, Empty, Page, SectionTitle, Spinner } from "@/components/ui";

// The decisions a manager can take, each mapped to the backend decision that triggers the
// real platform action (status change + buyer/seller notifications).
const ACTIONS: { value: string; label: string; needsComment?: boolean }[] = [
  { value: "approve", label: "Approve — keep listing live" },
  { value: "modify_listing", label: "Ask seller to modify listing (sizing)", needsComment: true },
  { value: "request_changes", label: "Ask for relevant changes", needsComment: true },
  { value: "suspend_and_request_changes", label: "Suspend & require description changes", needsComment: true },
  { value: "suspend", label: "Suspend now", needsComment: true },
  { value: "unlock", label: "Unlock after changes" },
];

// dispute (order) decisions vs listing decisions
const DISPUTE_ACTIONS: { value: string; label: string; needsComment?: boolean }[] = [
  { value: "reject", label: "Reject claim — deny refund (fraud/abuse)", needsComment: true },
  { value: "approve", label: "Approve refund" },
];

function CaseCard({
  item,
  seller,
  complaint,
  onDecideListing,
  onDecideDispute,
  busy,
}: {
  item: ManagerQueueItem;
  seller?: ManagerSeller;
  complaint?: { label: string; agreement: number; count: number } | null;
  onDecideListing: (productId: string, decision: string, comment: string) => void;
  onDecideDispute: (orderId: string, decision: string, comment: string) => void;
  busy: boolean;
}) {
  const isDispute = item.kind === "dispute";
  const actions = isDispute ? DISPUTE_ACTIONS : ACTIONS;
  const [decision, setDecision] = useState(actions[0].value);
  const [comment, setComment] = useState("");
  const sm = statusMeta(item.status);
  const reason = (item.evidence as { evidence?: string[] } | null)?.evidence;
  const chosen = actions.find((a) => a.value === decision);

  return (
    <Card className={`p-4 ${isDispute ? "border-l-4 border-l-amber" : ""}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Badge tone={isDispute ? "amber" : "neutral"}>{isDispute ? "Refund dispute" : "Listing"}</Badge>
            <Link href={`/product/${item.product_id}`} className="text-sm font-semibold text-ink hover:text-brand-ink hover:underline">
              {item.title}
            </Link>
          </div>
          <div className="mt-0.5 text-xs text-ink-faint">
            {isDispute
              ? `Buyer ${item.buyer_id} · ${item.buyer_claim_count ?? 0} prior claims`
              : seller?.name ?? item.seller_id}
            {item.acted_at ? ` · ${new Date(item.acted_at).toLocaleString("en-IN")}` : ""}
          </div>
        </div>
        <Badge tone={isDispute ? "amber" : sm.tone}>{isDispute ? "manual review" : sm.label}</Badge>
      </div>

      {complaint && !isDispute && (
        <div className="mt-2 text-xs text-amber">
          ⚠ {complaint.label} — {Math.round(complaint.agreement * 100)}% of {complaint.count} complaints agree
        </div>
      )}
      {Array.isArray(reason) && reason.length > 0 && (
        <ul className="mt-2 space-y-0.5">
          {reason.slice(0, 3).map((r, i) => (
            <li key={i} className="flex gap-1.5 text-xs text-ink-soft">
              <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-brand" />
              {r}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-3 rounded-xl border border-line bg-[#fafafe] p-3">
        <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-ink-faint">Decision</label>
        <select
          value={decision}
          onChange={(e) => setDecision(e.target.value)}
          className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm"
        >
          {actions.map((a) => (
            <option key={a.value} value={a.value}>{a.label}</option>
          ))}
        </select>
        {chosen?.needsComment && (
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={2}
            placeholder={isDispute ? "Reason shown to the buyer…" : "Note for the seller (what to change and why)…"}
            className="mt-2 w-full resize-y rounded-lg border border-line bg-surface px-3 py-2 text-sm"
          />
        )}
        <Button
          className="mt-2 w-full"
          size="sm"
          disabled={busy}
          onClick={() =>
            isDispute
              ? onDecideDispute(item.order_id!, decision, comment)
              : onDecideListing(item.product_id, decision, comment)
          }
        >
          {busy ? <Spinner /> : "Apply decision"}
        </Button>
      </div>
    </Card>
  );
}

export default function ManagerActionNeeded() {
  const [managers, setManagers] = useState<ManagerInfo[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [queue, setQueue] = useState<ManagerQueueItem[] | null>(null);
  const [sellers, setSellers] = useState<ManagerSeller[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    api.managers().then((ms) => { setManagers(ms); setActive(ms[0]?.id ?? null); }).catch(() => setManagers([]));
  }, []);

  const load = useCallback(async (id: string) => {
    setQueue(null);
    const [q, s] = await Promise.allSettled([api.managerQueue(id), api.managerSellers(id)]);
    // newest-reported first — a just-filed case jumps to the top
    const items = q.status === "fulfilled" ? [...q.value.items] : [];
    items.sort((a, b) => (b.acted_at ?? "").localeCompare(a.acted_at ?? ""));
    setQueue(items);
    setSellers(s.status === "fulfilled" ? s.value.sellers : []);
  }, []);

  useEffect(() => { if (active) load(active); }, [active, load]);

  const decideListing = async (productId: string, decision: string, comment: string) => {
    if (!active) return;
    setBusy(productId);
    try {
      const r = await api.managerDecide(active, productId, decision, comment);
      setToast(r.buyers_notified > 0 ? "Decision applied — buyer and seller notified." : "Decision applied — seller notified.");
      await load(active);
      setTimeout(() => setToast(null), 3500);
    } finally {
      setBusy(null);
    }
  };

  const decideDispute = async (orderId: string, decision: string, comment: string) => {
    if (!active) return;
    setBusy(orderId);
    try {
      await api.managerDecideDispute(active, orderId, decision, comment);
      setToast(decision === "reject" ? "Claim rejected — buyer notified." : "Refund approved — buyer notified.");
      await load(active);
      setTimeout(() => setToast(null), 3500);
    } finally {
      setBusy(null);
    }
  };

  const sellerOf = (sid: string | null | undefined) => (sid ? sellers.find((s) => s.seller_id === sid) : undefined);
  const complaintOf = (item: ManagerQueueItem) =>
    sellerOf(item.seller_id)?.products.find((p) => p.product_id === item.product_id)?.complaint ?? null;

  return (
    <Page>
      <SectionTitle
        eyebrow="Manager · moderation"
        title="Action needed"
        sub="Live cases awaiting your decision, newest first. Your call triggers the real workflow — status changes and buyer/seller notifications."
      />

      <div className="mb-1 flex flex-wrap items-center gap-2">
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
        <Link href="/manager/logs" className="ml-auto text-sm font-medium text-brand-ink hover:underline">
          View decision logs →
        </Link>
      </div>

      {toast && (
        <div className="my-3 rounded-xl bg-green-wash px-4 py-2.5 text-sm font-medium text-green">✓ {toast}</div>
      )}

      <div className="mt-4">
        {queue === null ? (
          <Spinner />
        ) : queue.length === 0 ? (
          <Empty>Nothing in the queue — every listing is in good standing.</Empty>
        ) : (
          <div className="space-y-3">
            {queue.map((item) => (
              <CaseCard
                key={item.order_id ?? item.product_id}
                item={item}
                seller={sellerOf(item.seller_id)}
                complaint={complaintOf(item)}
                onDecideListing={decideListing}
                onDecideDispute={decideDispute}
                busy={busy === (item.order_id ?? item.product_id)}
              />
            ))}
          </div>
        )}
      </div>
    </Page>
  );
}
