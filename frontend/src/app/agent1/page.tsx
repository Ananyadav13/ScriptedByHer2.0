"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, type Agent1Evidence, type InvestigationSummary } from "@/lib/api";
import { decisionMeta, toolMeta } from "@/lib/decisions";
import { Badge, Card, Empty, Page, SectionTitle, Spinner } from "@/components/ui";
import { TracePanel } from "@/components/TracePanel";

type Scn = {
  key: string;
  label: string;
  blurb: string;
  product_id?: string;
  order_id?: string;
  trigger: string;
};

const SCENARIOS: Scn[] = [
  {
    key: "counterfeit",
    label: "Counterfeit Rolex",
    blurb: "₹599 vs ₹8.5L MRP + a 12-review burst from 2-day accounts → expect counterfeit_lock.",
    product_id: "prod_counterfeit_rolex",
    trigger: "pre_purchase",
  },
  {
    key: "viral",
    label: "Honest viral seller",
    blurb: "A volume spike but every reviewer is an aged account → must be cleared, not punished.",
    product_id: "prod_viral_honest",
    trigger: "pre_purchase",
  },
  {
    key: "fabric",
    label: "Fabric mismatch (advisory)",
    blurb: "Low trustworthy rating on a “pure cotton” claim → media scan → recommend_review to the manager.",
    product_id: "prod_fabric_kurti",
    trigger: "pre_purchase",
  },
  {
    key: "dispute",
    label: "Delivery dispute",
    blurb: "1 OTP for 3 items via a flagged hub → two independent signals → refund_fast_track.",
    order_id: "order_otp_dispute",
    trigger: "post_delivery",
  },
];

const TOOLS = [
  { name: "check_catalog_risk", desc: "price/MRP · review-burst · image match" },
  { name: "check_seller_profile", desc: "account age · rating · trust flags" },
  { name: "check_delivery_signals", desc: "OTP vs items · hub anomaly · claim history" },
  { name: "check_media_evidence", desc: "vision: listing video vs buyer evidence (advisory)" },
];

export default function Agent1Page() {
  const [active, setActive] = useState<Scn>(SCENARIOS[0]);
  const [evidence, setEvidence] = useState<Agent1Evidence | null>(null);
  const [log, setLog] = useState<InvestigationSummary[]>([]);

  const loadEvidence = useCallback(async (s: Scn) => {
    setEvidence(null);
    try {
      setEvidence(await api.agent1Evidence({ product_id: s.product_id, order_id: s.order_id }));
    } catch {
      setEvidence(null);
    }
  }, []);
  const loadLog = useCallback(async () => {
    try {
      setLog((await api.investigations(15)).investigations);
    } catch {
      setLog([]);
    }
  }, []);

  useEffect(() => {
    loadEvidence(active);
  }, [active, loadEvidence]);
  useEffect(() => {
    loadLog();
  }, [loadLog]);

  const start = useMemo(
    () => async () => {
      if (active.order_id) {
        const r = await api.dispute({ order_id: active.order_id, claim_type: "item_not_as_described" });
        setTimeout(loadLog, 1500);
        return r.investigation_id;
      }
      const r = await api.investigate({ product_id: active.product_id!, trigger: active.trigger });
      setTimeout(loadLog, 1500);
      return r.investigation_id;
    },
    [active, loadLog],
  );

  return (
    <Page>
      <SectionTitle
        eyebrow="Agent 1 · Verification & Authenticity"
        title="Verification console"
        sub="On-demand agent — fires on Buy Now, a deterministic tripwire, or a dispute. It gathers evidence with four tools, reasons over it, and takes a graduated, reversible action."
      />

      {/* how it works */}
      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <Card className="p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-brand">Triggers</div>
          <ul className="mt-2 space-y-1 text-sm text-ink-soft">
            <li>🛒 Buyer hits <b className="text-ink">Buy Now / Verify</b></li>
            <li>⚡ A deterministic <b className="text-ink">tripwire</b> (review burst, rating drop, price change)</li>
            <li>📦 A post-delivery <b className="text-ink">dispute</b></li>
          </ul>
        </Card>
        <Card className="p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-brand">Tools (function-calling)</div>
          <ul className="mt-2 space-y-1.5 text-sm text-ink-soft">
            {TOOLS.map((t) => (
              <li key={t.name} className="flex gap-2">
                <span>{toolMeta(t.name).icon}</span>
                <span>
                  <b className="text-ink">{toolMeta(t.name).label}</b> — {t.desc}
                </span>
              </li>
            ))}
          </ul>
        </Card>
        <Card className="p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-brand">Graduated actions</div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {["cleared", "notify_only", "relabel_required", "request_qc_video", "recommend_review", "refund_fast_track", "manual_review", "counterfeit_lock", "ban"].map((d) => (
              <Badge key={d} tone={decisionMeta(d).tone}>
                {decisionMeta(d).label}
              </Badge>
            ))}
          </div>
          <p className="mt-2 text-xs text-ink-faint">
            Agents recommend; a business manager holds the final call.
          </p>
        </Card>
      </div>

      {/* scenario picker */}
      <div className="mb-4 flex flex-wrap gap-2">
        {SCENARIOS.map((s) => (
          <button
            key={s.key}
            onClick={() => setActive(s)}
            className={`rounded-xl border px-3.5 py-2 text-sm transition ${
              active.key === s.key
                ? "border-brand bg-brand-wash text-brand-ink"
                : "border-line bg-surface text-ink-soft hover:bg-[#f2f3f8]"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>
      <p className="mb-4 text-sm text-ink-soft">{active.blurb}</p>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* deterministic evidence layer */}
        <div>
          <h2 className="mb-2 flex items-center gap-2 font-semibold text-ink">
            Always-watching evidence
            <Badge tone="neutral">deterministic · no LLM</Badge>
          </h2>
          <p className="mb-3 text-xs text-ink-faint">
            These signals are computed in code on every review/price change — the LLM only reasons
            over them when a trigger fires.
          </p>
          {evidence === null ? (
            <Spinner />
          ) : (
            <div className="space-y-3">
              <div className="text-sm text-ink-soft">
                {evidence.risk_flags > 0 ? (
                  <Badge tone="rose">{evidence.risk_flags} risk signal(s) flagged</Badge>
                ) : (
                  <Badge tone="green">no risk signals</Badge>
                )}
              </div>
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

        {/* live LLM trace */}
        <div>
          <h2 className="mb-2 flex items-center gap-2 font-semibold text-ink">
            Live investigation
            <Badge tone="brand">LLM on trigger</Badge>
          </h2>
          <p className="mb-3 text-xs text-ink-faint">
            Run the full agent: it calls tools, streams each step, and returns a structured verdict.
          </p>
          <TracePanel
            key={active.key}
            label="Run Agent 1"
            sublabel={active.label}
            start={start}
          />
        </div>
      </div>

      {/* activity log */}
      <div className="mt-8">
        <h2 className="mb-3 font-semibold text-ink">Recent investigations</h2>
        {log.length === 0 ? (
          <Empty>No investigations yet — run one above and it appears here.</Empty>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="border-b border-line text-left text-xs text-ink-faint">
                  <th className="py-2 pr-3 font-medium">Trigger</th>
                  <th className="py-2 pr-3 font-medium">Target</th>
                  <th className="py-2 pr-3 font-medium">Tools</th>
                  <th className="py-2 pr-3 font-medium">Verdict</th>
                  <th className="py-2 pr-3 font-medium">Conf.</th>
                  <th className="py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {log.map((inv) => (
                  <tr key={inv.id} className="border-b border-line">
                    <td className="py-2 pr-3">
                      <Badge tone="neutral">{inv.trigger}</Badge>
                    </td>
                    <td className="py-2 pr-3 text-ink-soft">{inv.product_title ?? inv.order_id ?? "—"}</td>
                    <td className="py-2 pr-3 text-ink-faint">{inv.tool_count}</td>
                    <td className="py-2 pr-3">
                      {inv.decision ? (
                        <Badge tone={decisionMeta(inv.decision).tone}>{decisionMeta(inv.decision).label}</Badge>
                      ) : (
                        <span className="text-ink-faint">—</span>
                      )}
                    </td>
                    <td className="py-2 pr-3 text-ink-soft">
                      {inv.confidence != null ? `${Math.round(inv.confidence * 100)}%` : "—"}
                    </td>
                    <td className="py-2 text-ink-faint">{inv.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Link href="/manager" className="mt-6 inline-block text-sm font-medium text-brand-ink hover:underline">
        Locks & recommendations flow to the business-manager queue →
      </Link>
    </Page>
  );
}
