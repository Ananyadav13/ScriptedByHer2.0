"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  api,
  type AdminAction,
  type Agent2Findings,
  type Agent2Product,
  type AuditResult,
} from "@/lib/api";
import { actionMeta, statusMeta } from "@/lib/decisions";
import { Badge, Button, Card, Empty, Page, SectionTitle, Spinner } from "@/components/ui";

const FILTERS = [
  { key: "all", label: "All issues", types: [] as string[] },
  { key: "size", label: "Size & measurement", types: ["size_mismatch", "missing_measurements"] },
  { key: "fabric", label: "Fabric", types: ["fabric_mismatch", "missing_fabric"] },
  { key: "fraud", label: "Fraud & quality", types: ["fraud_quality"] },
  { key: "delivery", label: "Delivery", types: ["delivery_fault"] },
];

const SUMMARY_TILES = [
  { key: "size_mismatch", label: "Size mismatch", tone: "text-amber" },
  { key: "missing_measurements", label: "No measurements", tone: "text-amber" },
  { key: "fabric_mismatch", label: "Fabric issues", tone: "text-teal" },
  { key: "fraud_quality", label: "Fraud/quality", tone: "text-rose" },
  { key: "delivery_fault", label: "Delivery faults", tone: "text-teal" },
];

const ISSUE_TONE: Record<string, "rose" | "amber" | "teal" | "neutral"> = {
  fraud_quality: "rose",
  size_mismatch: "amber",
  fabric_mismatch: "teal",
  delivery_fault: "teal",
  missing_measurements: "neutral",
  missing_fabric: "neutral",
  missing_video: "neutral",
  other: "neutral",
};

function FindingRow({ p }: { p: Agent2Product }) {
  const sm = statusMeta(p.status);
  const warns = p.issues.filter((i) => i.severity === "warn");
  const infos = p.issues.filter((i) => i.severity === "info");
  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <Link href={`/product/${p.product_id}`} className="font-semibold text-ink hover:text-brand-ink hover:underline">
            {p.title}
          </Link>
          <div className="mt-0.5 text-xs text-ink-faint">
            {p.seller_id} · {p.category}
            {p.rating != null && p.review_count > 0 && ` · ${p.rating}★ (${p.review_count})`}
          </div>
        </div>
        <Badge tone={sm.tone}>{sm.label}</Badge>
      </div>

      {/* issue chips */}
      <div className="mt-3 flex flex-wrap gap-1.5">
        {warns.map((i, k) => (
          <Badge key={k} tone={ISSUE_TONE[i.type] ?? "amber"}>
            ⚠ {i.label}
            {i.agreement != null && ` · ${Math.round(i.agreement * 100)}%`}
          </Badge>
        ))}
        {infos.map((i, k) => (
          <Badge key={k} tone="neutral">
            {i.label}
          </Badge>
        ))}
        {p.issues.length === 0 && <Badge tone="green">✓ clean listing</Badge>}
      </div>

      {p.fit && (
        <div className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-teal-wash px-2.5 py-1 text-xs text-teal">
          📏 {p.fit.note} — fit auto-adjusted at cart
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-line pt-2.5 text-xs">
        <span className="text-ink-faint">
          Business manager: <span className="font-medium text-ink">{p.manager ?? "—"}</span>
        </span>
        {p.escalated ? (
          <Badge tone="rose">escalated to manager</Badge>
        ) : (
          <span className="text-ink-faint">
            recommended: <span className="font-medium text-ink-soft">{p.recommended_action}</span>
          </span>
        )}
      </div>
    </Card>
  );
}

export default function AdminPage() {
  const [findings, setFindings] = useState<Agent2Findings | null>(null);
  const [actions, setActions] = useState<AdminAction[]>([]);
  const [audit, setAudit] = useState<AuditResult | null>(null);
  const [filter, setFilter] = useState("all");
  const [running, setRunning] = useState(false);

  const load = useCallback(async () => {
    const [f, a] = await Promise.allSettled([api.agent2Findings(), api.adminActions(40)]);
    if (f.status === "fulfilled") setFindings(f.value);
    else setFindings({ summary: {}, count: 0, products: [] });
    if (a.status === "fulfilled") setActions(a.value.actions);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const runAudit = async () => {
    setRunning(true);
    try {
      setAudit(await api.audit(false));
      await load();
    } finally {
      setRunning(false);
    }
  };

  const shown = useMemo(() => {
    if (!findings) return [];
    const f = FILTERS.find((x) => x.key === filter)!;
    if (f.types.length === 0) return findings.products.filter((p) => p.issues.length > 0);
    return findings.products.filter((p) => p.issues.some((i) => f.types.includes(i.type)));
  }, [findings, filter]);

  return (
    <Page>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <SectionTitle
          eyebrow="Agent 2 · Listing & Catalog Integrity"
          title="Catalog integrity console"
          sub="An ambient, deterministic sweep flags every listing's issues — size/measurement gaps, fabric mismatches, fraud clusters — and escalates them to the owning business manager."
        />
        <Button onClick={runAudit} disabled={running}>
          {running ? <Spinner /> : "⚙️"} Run catalog audit
        </Button>
      </div>

      {/* summary tiles */}
      {findings && (
        <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-5">
          {SUMMARY_TILES.map((t) => (
            <Card key={t.key} className="p-3 text-center">
              <div className={`text-2xl font-bold ${t.tone}`}>{findings.summary[t.key] ?? 0}</div>
              <div className="text-xs text-ink-faint">{t.label}</div>
            </Card>
          ))}
        </div>
      )}

      {audit && (
        <div className="mb-5 rounded-xl bg-brand-wash px-4 py-3 text-sm text-brand-ink">
          Audit applied — suspended {audit.summary.suspended ?? 0} · correction window{" "}
          {audit.summary.correction_window ?? 0} · logistics {audit.summary.logistics_referral ?? 0} · fix drafts{" "}
          {audit.summary.fix_drafts ?? 0} · kept {audit.summary.kept ?? 0}.
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        {/* findings */}
        <div>
          <div className="mb-3 flex flex-wrap gap-1.5">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                onClick={() => setFilter(f.key)}
                className={`rounded-full px-3 py-1.5 text-xs font-medium transition ${
                  filter === f.key ? "bg-brand text-white" : "border border-line bg-surface text-ink-soft hover:bg-[#f2f3f8]"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {findings === null && <Spinner />}
          {findings !== null && shown.length === 0 && <Empty>No listings with issues in this view.</Empty>}
          <div className="space-y-3">
            {shown.map((p) => (
              <FindingRow key={p.product_id} p={p} />
            ))}
          </div>
        </div>

        {/* recent actions */}
        <div>
          <h2 className="mb-3 font-semibold text-ink">Recent agent actions</h2>
          {actions.length === 0 ? (
            <Empty>No actions yet — run the audit.</Empty>
          ) : (
            <div className="space-y-2.5">
              {actions.slice(0, 12).map((a) => {
                const am = actionMeta(a.action);
                return (
                  <Card key={a.id} className="p-3.5">
                    <div className="flex items-center justify-between gap-2">
                      <Badge tone={am.tone}>{am.label}</Badge>
                      {a.tier && <span className="text-[11px] text-ink-faint">{a.tier}</span>}
                    </div>
                    <div className="mt-1.5 text-sm font-medium text-ink">
                      {a.product_title ?? a.product_id}
                    </div>
                    {a.reason && <p className="mt-0.5 line-clamp-2 text-xs text-ink-soft">{a.reason}</p>}
                  </Card>
                );
              })}
            </div>
          )}
          <Link href="/manager" className="mt-4 inline-block text-sm font-medium text-brand-ink hover:underline">
            See the business-manager queue →
          </Link>
        </div>
      </div>
    </Page>
  );
}
