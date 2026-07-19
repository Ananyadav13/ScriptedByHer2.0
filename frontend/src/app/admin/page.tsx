"use client";

import { useEffect, useMemo, useState } from "react";
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

// What each recommended outcome means, in the language the console should speak. Grouping by
// this is the point of the panel: a fraud cluster, a fixable spec gap and a courier problem
// are three different problems and must not read as one undifferentiated "bad listing" pile.
const OUTCOME: Record<string, { title: string; tone: "rose" | "amber" | "teal"; blurb: string; cta: string }> = {
  suspend: {
    title: "Remove from catalogue",
    tone: "rose",
    blurb: "Consistently poor customer experience with nothing in the listing left to correct.",
    cta: "Remove from catalogue",
  },
  correction_window: {
    title: "Correction window",
    tone: "amber",
    blurb: "The listing itself is fixable — the seller gets a drafted correction to approve.",
    cta: "Apply correction window",
  },
  logistics_referral: {
    title: "Logistics referral",
    tone: "teal",
    blurb: "A delivery fault, not a seller fault. The listing stays live and the seller's rating is untouched.",
    cta: "Referred to logistics",
  },
};

function DelistRow({
  p,
  onRemove,
  busy,
}: {
  p: Agent2Product;
  onRemove: (id: string) => void;
  busy: boolean;
}) {
  const meta = OUTCOME[p.recommended_action] ?? OUTCOME.suspend;
  // A logistics referral is never a removal — the courier is at fault, not the listing.
  const removable = !p.already_removed && p.recommended_action !== "logistics_referral";

  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <Link href={`/product/${p.product_id}`} className="font-semibold text-ink hover:text-brand-ink hover:underline">
            {p.title}
          </Link>
          <div className="mt-0.5 text-xs text-ink-faint">
            {p.seller_name ?? p.seller_id} · {p.category}
          </div>
        </div>
        <Badge tone={meta.tone}>{meta.title}</Badge>
      </div>

      {/* the evidence, as figures a judge can read at a glance */}
      <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2">
        <div>
          <div className="text-[10px] uppercase tracking-wide text-ink-faint">Rating</div>
          <div className="text-lg font-bold text-rose">★ {p.rating ?? "—"}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wide text-ink-faint">Buyers</div>
          <div className="text-lg font-bold text-ink tabular-nums">
            {p.review_count.toLocaleString("en-IN")}
          </div>
        </div>
        {p.tier_label && (
          <div>
            <div className="text-[10px] uppercase tracking-wide text-ink-faint">Tier tripped</div>
            <div className="font-mono text-sm font-semibold text-ink">{p.tier_label}</div>
          </div>
        )}
      </div>

      <p className="mt-3 border-t border-line pt-2.5 text-sm text-ink-soft">
        <span className="font-medium text-ink">Why: </span>
        {meta.blurb}
      </p>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs text-ink-faint">
          Recommended: <span className="font-medium text-ink-soft">{meta.title}</span>
        </span>
        {p.already_removed ? (
          <Badge tone="neutral">✓ Already removed</Badge>
        ) : removable ? (
          <Button size="sm" variant="danger" disabled={busy} onClick={() => onRemove(p.product_id)}>
            {busy ? <Spinner /> : meta.cta}
          </Button>
        ) : (
          <Badge tone="teal">Referred to logistics — listing stays live</Badge>
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
  const [removing, setRemoving] = useState<string | null>(null);
  const [removeError, setRemoveError] = useState<string>("");

  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [f, a] = await Promise.allSettled([api.agent2Findings(), api.adminActions(40)]);
      if (cancelled) return;
      setFindings(f.status === "fulfilled" ? f.value : { summary: {}, count: 0, products: [] });
      if (a.status === "fulfilled") setActions(a.value.actions);
    })();
    return () => { cancelled = true; };
  }, [reloadToken]);

  const runAudit = async () => {
    setRunning(true);
    try {
      setAudit(await api.audit(false));
      setReloadToken((t) => t + 1);
    } finally {
      setRunning(false);
    }
  };

  const removeListing = async (productId: string) => {
    setRemoving(productId);
    setRemoveError("");
    try {
      await api.delistProduct(productId);
      setReloadToken((t) => t + 1);
    } catch (e) {
      setRemoveError(e instanceof Error ? e.message : "Removal failed.");
    } finally {
      setRemoving(null);
    }
  };

  const shown = useMemo(() => {
    if (!findings) return [];
    const f = FILTERS.find((x) => x.key === filter)!;
    if (f.types.length === 0) return findings.products.filter((p) => p.issues.length > 0);
    return findings.products.filter((p) => p.issues.some((i) => f.types.includes(i.type)));
  }, [findings, filter]);

  // Listings that trip a delisting tier — the products that no longer work for buyers.
  // Sorted worst-rated first, and still-live ones ahead of ones already taken down, so the
  // things that need a decision sit at the top.
  const deadStock = useMemo(() => {
    if (!findings) return [];
    return findings.products
      .filter((p) => p.delist)
      .sort((a, b) =>
        Number(a.already_removed) - Number(b.already_removed) ||
        (a.rating ?? 9) - (b.rating ?? 9));
  }, [findings]);

  const liveDeadStock = deadStock.filter((p) => !p.already_removed);

  // "Needs attention" counts only WARN-severity findings (a complaint cluster, a delist
  // tier) — not the info-severity advisories like "no listing video", which almost every
  // listing carries. Counting those would report the entire catalogue as unhealthy and say
  // nothing about which listings actually have a problem.
  const needsAttention = useMemo(
    () =>
      findings
        ? findings.products.filter(
            (p) => p.delist || p.issues.some((i) => i.severity === "warn"),
          ).length
        : 0,
    [findings],
  );

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

      {/* catalog state at a glance — checked / needs attention / healthy / dead.
          Answers "what shape is the catalogue in?" before any detail is read. */}
      {findings && (
        <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Card className="p-3 text-center">
            <div className="text-2xl font-bold text-ink tabular-nums">{findings.count}</div>
            <div className="text-xs text-ink-faint">Listings checked</div>
          </Card>
          <Card className="p-3 text-center">
            <div className="text-2xl font-bold text-amber tabular-nums">{needsAttention}</div>
            <div className="text-xs text-ink-faint">Need attention</div>
          </Card>
          <Card className="p-3 text-center">
            <div className="text-2xl font-bold text-rose tabular-nums">{deadStock.length}</div>
            <div className="text-xs text-ink-faint">No longer viable</div>
          </Card>
          <Card className="p-3 text-center">
            <div className="text-2xl font-bold text-green tabular-nums">
              {findings.count - needsAttention}
            </div>
            <div className="text-xs text-ink-faint">Selling normally</div>
          </Card>
        </div>
      )}

      {/* issue-type breakdown */}
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

      {/* ------------------------------------------------------------------ */}
      {/* Poor-performing listings — the tiered delisting policy, made visible. */}
      {/* This is the half of Agent 2 that "removes what can't be fixed": products    */}
      {/* whose trustworthy rating trips a tier are listed with the evidence that     */}
      {/* condemned them and an explicit action, rather than being silently swept.    */}
      {/* ------------------------------------------------------------------ */}
      {findings && deadStock.length > 0 && (
        <section className="mb-6">
          <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="font-semibold text-ink">
              Poor-performing listings
              <span className="ml-2 text-sm font-normal text-ink-faint">
                {liveDeadStock.length} awaiting a decision · {deadStock.length - liveDeadStock.length} already removed
              </span>
            </h2>
            <span className="text-xs text-ink-faint">
              Tiers: ★&lt;3.0 over 1,000 buyers · ★&lt;2.0 over 700 · ★≤1.0 over 500
            </span>
          </div>
          <p className="mb-3 text-sm text-ink-soft">
            These listings no longer work for buyers. The rating shown counts only reviews from
            established accounts, so a fake-review burst cannot rescue a product — or condemn one.
          </p>

          {removeError && (
            <div className="mb-3 rounded-xl bg-amber-wash px-3 py-2.5 text-xs text-amber">
              <b>Could not remove that listing.</b> {removeError}
            </div>
          )}

          <div className="grid gap-3 lg:grid-cols-2">
            {deadStock.map((p) => (
              <DelistRow
                key={p.product_id}
                p={p}
                busy={removing === p.product_id}
                onRemove={removeListing}
              />
            ))}
          </div>
        </section>
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
