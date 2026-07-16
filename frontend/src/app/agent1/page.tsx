"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, type Agent1Evidence, type InvestigationSummary } from "@/lib/api";
import { decisionMeta, toolMeta } from "@/lib/decisions";
import { Badge, Button, Card, Empty, Page, SectionTitle, Spinner } from "@/components/ui";
import { TracePanel } from "@/components/TracePanel";

type Scn = { key: string; label: string; blurb: string; product_id?: string; order_id?: string; trigger: string };

const SCENARIOS: Scn[] = [
  { key: "counterfeit", label: "Counterfeit Rolex", blurb: "₹599 vs ₹8.5L MRP + a 12-review burst from 2-day accounts → expect counterfeit_lock.", product_id: "prod_counterfeit_rolex", trigger: "pre_purchase" },
  { key: "viral", label: "Honest viral seller", blurb: "A volume spike but every reviewer is an aged account → must be cleared, not punished.", product_id: "prod_viral_honest", trigger: "pre_purchase" },
  { key: "fabric", label: "Fabric mismatch (advisory)", blurb: "Low trustworthy rating on a “pure cotton” claim → recommend_review to the manager.", product_id: "prod_fabric_kurti", trigger: "pre_purchase" },
  { key: "dispute", label: "Delivery dispute", blurb: "1 OTP for 3 items via a flagged hub → two independent signals → refund_fast_track.", order_id: "order_otp_dispute", trigger: "post_delivery" },
];

const TOOLS = [
  { name: "check_catalog_risk", desc: "price/MRP · review-burst · image match" },
  { name: "check_seller_profile", desc: "account age · rating · trust flags" },
  { name: "check_delivery_signals", desc: "OTP vs items · hub anomaly · claim history" },
  { name: "check_media_evidence", desc: "vision: listing video vs buyer evidence (advisory)" },
];

const TRIGGER_LABEL: Record<string, string> = {
  pre_purchase: "Buy Now",
  post_delivery: "Dispute",
  tripwire: "Tripwire",
  catalog_gate: "Listing gate",
};

function CaseCard({ c }: { c: InvestigationSummary }) {
  const dm = decisionMeta(c.decision);
  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          {c.product_id ? (
            <Link href={`/product/${c.product_id}`} className="font-semibold text-ink hover:text-brand-ink hover:underline">
              {c.product_title ?? c.product_id}
            </Link>
          ) : (
            <span className="font-semibold text-ink">{c.order_id}</span>
          )}
          <div className="mt-0.5 text-xs text-ink-faint">
            {c.seller_name && <>seller <b className="text-ink-soft">{c.seller_name}</b> · </>}
            {c.manager && <>manager <b className="text-ink-soft">{c.manager}</b></>}
          </div>
        </div>
        <div className="text-right">
          <Badge tone={dm.tone}>{dm.label}</Badge>
          <div className="mt-1 text-[11px] text-ink-faint">
            {TRIGGER_LABEL[c.trigger] ?? c.trigger} · {c.confidence != null ? `${Math.round(c.confidence * 100)}%` : "—"}
          </div>
        </div>
      </div>
      {(c.evidence?.length ?? 0) > 0 && (
        <ul className="mt-2.5 space-y-1">
          {(c.evidence ?? []).slice(0, 3).map((e, i) => (
            <li key={i} className="flex gap-2 text-xs text-ink-soft">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-brand" />
              {e}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export default function Agent1Page() {
  const [cases, setCases] = useState<InvestigationSummary[] | null>(null);
  const [showTech, setShowTech] = useState(false);
  const [active, setActive] = useState<Scn>(SCENARIOS[0]);
  const [evidence, setEvidence] = useState<Agent1Evidence | null>(null);

  const loadCases = useCallback(async () => {
    try {
      setCases((await api.investigations(20)).investigations);
    } catch {
      setCases([]);
    }
  }, []);
  useEffect(() => {
    loadCases();
  }, [loadCases]);

  useEffect(() => {
    if (!showTech) return;
    setEvidence(null);
    api.agent1Evidence({ product_id: active.product_id, order_id: active.order_id }).then(setEvidence).catch(() => setEvidence(null));
  }, [active, showTech]);

  const start = useMemo(
    () => async () => {
      const r = active.order_id
        ? await api.dispute({ order_id: active.order_id, claim_type: "item_not_as_described" })
        : await api.investigate({ product_id: active.product_id!, trigger: active.trigger });
      setTimeout(loadCases, 1500);
      return r.investigation_id;
    },
    [active, loadCases],
  );

  const stats = useMemo(() => {
    const c = cases ?? [];
    return {
      total: c.length,
      locked: c.filter((x) => x.decision === "counterfeit_lock" || x.decision === "ban").length,
      refunds: c.filter((x) => x.decision === "refund_fast_track").length,
      cleared: c.filter((x) => x.decision === "cleared" || x.decision === "authentic").length,
    };
  }, [cases]);

  return (
    <Page>
      <SectionTitle
        eyebrow="Agent 1 · Verification & Authenticity"
        title="Verification console"
        sub="On-demand agent — fires on Buy Now, a tripwire, or a dispute. Below are the cases it has resolved: the product, the seller, and the business manager involved."
      />

      {/* headline stats */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { n: stats.total, l: "Cases resolved", t: "text-brand-ink" },
          { n: stats.locked, l: "Counterfeits locked", t: "text-rose" },
          { n: stats.refunds, l: "Refunds fast-tracked", t: "text-green" },
          { n: stats.cleared, l: "Cleared (no action)", t: "text-teal" },
        ].map((s) => (
          <Card key={s.l} className="p-3 text-center">
            <div className={`text-2xl font-bold ${s.t}`}>{s.n}</div>
            <div className="text-xs text-ink-faint">{s.l}</div>
          </Card>
        ))}
      </div>

      {/* PRIMARY: cases resolved */}
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-semibold text-ink">Recent cases</h2>
        <Button variant="secondary" size="sm" onClick={() => setShowTech((v) => !v)}>
          🔧 {showTech ? "Hide" : "Show"} live investigation & backend evidence
        </Button>
      </div>

      {cases === null ? (
        <Spinner />
      ) : cases.length === 0 ? (
        <Empty>No cases yet — run a live investigation below.</Empty>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {cases.map((c) => (
            <CaseCard key={c.id} c={c} />
          ))}
        </div>
      )}

      {/* SECONDARY (toggle): the technical / backend view for judges */}
      {showTech && (
        <div className="mt-8 rounded-2xl border border-line bg-[#fbfbfe] p-5">
          <div className="mb-4 text-sm font-semibold text-brand-ink">🔧 How Agent 1 works — live</div>
          <div className="mb-5 grid gap-4 md:grid-cols-3">
            <Card className="p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-brand">Triggers</div>
              <ul className="mt-2 space-y-1 text-sm text-ink-soft">
                <li>🛒 Buyer hits <b className="text-ink">Buy Now / Verify</b></li>
                <li>⚡ A deterministic <b className="text-ink">tripwire</b></li>
                <li>📦 A post-delivery <b className="text-ink">dispute</b></li>
              </ul>
            </Card>
            <Card className="p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-brand">Tools</div>
              <ul className="mt-2 space-y-1.5 text-sm text-ink-soft">
                {TOOLS.map((t) => (
                  <li key={t.name} className="flex gap-2">
                    <span>{toolMeta(t.name).icon}</span>
                    <span><b className="text-ink">{toolMeta(t.name).label}</b> — {t.desc}</span>
                  </li>
                ))}
              </ul>
            </Card>
            <Card className="p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-brand">Graduated actions</div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {["cleared", "notify_only", "relabel_required", "request_qc_video", "recommend_review", "refund_fast_track", "manual_review", "counterfeit_lock", "ban"].map((d) => (
                  <Badge key={d} tone={decisionMeta(d).tone}>{decisionMeta(d).label}</Badge>
                ))}
              </div>
            </Card>
          </div>

          <div className="mb-3 flex flex-wrap gap-2">
            {SCENARIOS.map((s) => (
              <button
                key={s.key}
                onClick={() => setActive(s)}
                className={`rounded-xl border px-3.5 py-2 text-sm transition ${active.key === s.key ? "border-brand bg-brand-wash text-brand-ink" : "border-line bg-surface text-ink-soft hover:bg-[#f2f3f8]"}`}
              >
                {s.label}
              </button>
            ))}
          </div>
          <p className="mb-4 text-sm text-ink-soft">{active.blurb}</p>

          <div className="grid gap-6 lg:grid-cols-2">
            <div>
              <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-ink">
                Always-watching evidence <Badge tone="neutral">deterministic · no LLM</Badge>
              </h3>
              {evidence === null ? (
                <Spinner />
              ) : (
                <div className="space-y-3">
                  {evidence.tools.map((t) => (
                    <Card key={t.tool} className="p-4">
                      <div className="mb-2 flex items-center gap-2 text-sm font-medium text-ink">
                        <span>{toolMeta(t.tool).icon}</span>
                        {toolMeta(t.tool).label}
                      </div>
                      <ul className="space-y-1.5">
                        {t.signals.map((s, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm">
                            {s.flag ? <Badge tone="rose">signal</Badge> : <Badge tone="green">clear</Badge>}
                            <span className="text-ink-soft">{s.detail}</span>
                          </li>
                        ))}
                      </ul>
                    </Card>
                  ))}
                </div>
              )}
            </div>
            <div>
              <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-ink">
                Live investigation <Badge tone="brand">LLM on trigger</Badge>
              </h3>
              <TracePanel key={active.key} label="Run Agent 1" sublabel={active.label} start={start} />
            </div>
          </div>
        </div>
      )}

      <Link href="/manager" className="mt-6 inline-block text-sm font-medium text-brand-ink hover:underline">
        Locks & recommendations flow to the business-manager queue →
      </Link>
    </Page>
  );
}
