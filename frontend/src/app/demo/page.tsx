"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  api,
  type Agent2Product,
  type BuyerOrder,
  type Draft,
  type ManagerSeller,
  type Notif,
} from "@/lib/api";
import { Badge, Card, Empty, Page, SectionTitle, Spinner } from "@/components/ui";
import { DisputeCard } from "@/components/DisputeCard";
import { FlowRail, type RailStop } from "@/components/FlowRail";
import { productImage } from "@/lib/productImages";

// ---------------------------------------------------------------------------
// Two guided journeys. Each is a short scripted sequence that reuses the REAL
// surfaces + live API, with a persistent flow rail making the hand-offs visible.
// ---------------------------------------------------------------------------
type Journey = "buyer" | "seller";

const RAILS: Record<Journey, RailStop[]> = {
  buyer: [
    { role: "Buyer", label: "File dispute", icon: "🛍️" },
    { role: "Agent 1", label: "Verify", icon: "🛡️" },
    { role: "Manager", label: "Review", icon: "👔" },
    { role: "Buyer", label: "Notified", icon: "🔔" },
  ],
  seller: [
    { role: "Seller", label: "List product", icon: "🏪" },
    { role: "Agent 2", label: "Audit", icon: "🔎" },
    { role: "Manager", label: "Discrepancies", icon: "👔" },
    { role: "Seller", label: "Fix & notified", icon: "🔔" },
  ],
};

type Step = { railActive: number; role: string; hat: string; title: string; narrative: string };

const STEPS: Record<Journey, Step[]> = {
  buyer: [
    {
      railActive: 1,
      role: "Buyer",
      hat: "🛍️",
      title: "You bought a kurti — it feels wrong",
      narrative:
        "You ordered the Rayon Anarkali Kurti in Blue. It arrived sheer and glossy — it feels like crepe, not the opaque rayon promised. Open a dispute and watch Trusty verify it live: delivery checks first, then a visual comparison of the seller's listing frames against your photos.",
    },
    {
      railActive: 2,
      role: "Buyer",
      hat: "📮",
      title: "Your case is with the manager",
      narrative:
        "Media is uncertain (lighting, wear — and the listing video shows the Black variant, not your Blue one), so Trusty never punishes on it. Your case has been handed to manager Priya. You'll be notified the moment she decides — nothing more for you to do.",
    },
    {
      railActive: 3,
      role: "Buyer",
      hat: "🔔",
      title: "The loop closes — you're told what happened",
      narrative:
        "When the manager decides, both you and the seller are notified automatically, in plain language: “your refund was processed”. Transparency is the point — you always know why.",
    },
  ],
  seller: [
    {
      railActive: 0,
      role: "Seller",
      hat: "🏪",
      title: "You list your products",
      narrative:
        "You're EthnicWeave & Aaraals. You listed a Pure Cotton Kurti (you could only film ONE colour) and a handbag combo sold as 'Free Size' with no measurements. Let's see what Agent 2 makes of them.",
    },
    {
      railActive: 1,
      role: "Agent 2",
      hat: "🔎",
      title: "Agent 2 audits every listing",
      narrative:
        "Agent 2 checks mandatory fields, compares each listing against its variant-invariant quality fingerprint, and clusters buyer complaints. The fingerprint comparison is pure deterministic code, so it runs identically every time and needs zero LLM quota.",
    },
    {
      railActive: 2,
      role: "Manager",
      hat: "👔",
      title: "Discrepancies surface to the manager",
      narrative:
        "The manager sees each of their sellers' listings, the dominant complaint, and the current status — riskiest first. Nothing is hidden and nothing is auto-punished without a human in the loop.",
    },
    {
      railActive: 3,
      role: "Seller",
      hat: "🔔",
      title: "You get a drafted fix to approve",
      narrative:
        "Agent 2 doesn't just flag — it drafts the correction (e.g. real bag dimensions) and hands it to you. One tap to approve, and the listing goes back to full visibility.",
    },
  ],
};

// ---------------------------------------------------------------------------
export default function DemoPage() {
  const [journey, setJourney] = useState<Journey>("buyer");
  const [step, setStep] = useState(0);

  const steps = STEPS[journey];
  const cur = steps[step];
  const atEnd = step === steps.length - 1;

  const pick = (j: Journey) => {
    setJourney(j);
    setStep(0);
  };

  return (
    <Page>
      <SectionTitle
        eyebrow="Guided walkthrough"
        title="Follow the whole flow, role by role"
        sub="Two short stories that show how a buyer, a seller, the two AI agents, and the manager hand off to each other."
      />

      {/* journey picker */}
      <div className="mb-4 flex flex-wrap gap-2">
        {(["buyer", "seller"] as Journey[]).map((j) => (
          <button
            key={j}
            onClick={() => pick(j)}
            className={`rounded-xl border px-4 py-2 text-sm font-medium transition ${
              journey === j
                ? "border-brand bg-brand-wash text-brand-ink"
                : "border-line bg-surface text-ink-soft hover:bg-[#f2f3f8]"
            }`}
          >
            {j === "buyer" ? "🛍️ Buyer: a dispute, resolved fairly" : "🏪 Seller: a listing, audited"}
          </button>
        ))}
      </div>

      {/* persistent flow rail */}
      <div className="sticky top-[52px] z-10 mb-5">
        <FlowRail stops={RAILS[journey]} active={cur.railActive} />
      </div>

      {/* current step */}
      <Card className="p-5">
        <div className="mb-3 flex items-start gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-brand-wash text-xl">
            {cur.hat}
          </span>
          <div>
            <div className="flex items-center gap-2">
              <Badge tone="brand">{cur.role}</Badge>
              <span className="text-xs text-ink-faint">
                Step {step + 1} of {steps.length}
              </span>
            </div>
            <h2 className="mt-1 text-lg font-bold text-ink">{cur.title}</h2>
          </div>
        </div>
        <p className="text-sm text-ink-soft">{cur.narrative}</p>

        <div className="mt-5">
          {journey === "buyer" ? <BuyerStep step={step} /> : <SellerStep step={step} />}
        </div>
      </Card>

      {/* controls */}
      <div className="mt-5 flex items-center justify-between">
        <button
          onClick={() => setStep((s) => Math.max(0, s - 1))}
          disabled={step === 0}
          className="rounded-xl border border-line bg-surface px-4 py-2 text-sm font-medium text-ink-soft transition enabled:hover:bg-[#f2f3f8] disabled:opacity-40"
        >
          ← Back
        </button>
        {atEnd ? (
          <button
            onClick={() => pick(journey === "buyer" ? "seller" : "buyer")}
            className="rounded-xl bg-brand px-5 py-2 text-sm font-semibold text-white transition hover:bg-brand-ink"
          >
            {journey === "buyer" ? "Next: the seller journey →" : "Restart: the buyer journey →"}
          </button>
        ) : (
          <button
            onClick={() => setStep((s) => Math.min(steps.length - 1, s + 1))}
            className="rounded-xl bg-brand px-5 py-2 text-sm font-semibold text-white transition hover:bg-brand-ink"
          >
            Continue →
          </button>
        )}
      </div>
    </Page>
  );
}

// ---------------------------------------------------------------------------
// Buyer journey step surfaces
// ---------------------------------------------------------------------------
function BuyerStep({ step }: { step: number }) {
  const [order, setOrder] = useState<BuyerOrder | null>(null);
  const [buyerNotifs, setBuyerNotifs] = useState<Notif[] | null>(null);

  useEffect(() => {
    if (step === 0 && !order) {
      api
        .buyerOrders("buyer_normal")
        .then((r) => setOrder(r.orders.find((o) => o.id === "order_fabric_dispute") ?? r.orders[0] ?? null))
        .catch(() => setOrder(null));
    }
    if (step === 2 && !buyerNotifs) {
      api.notificationsFor("buyer", "buyer_normal").then(setBuyerNotifs).catch(() => setBuyerNotifs([]));
    }
  }, [step, order, buyerNotifs]);

  if (step === 0) {
    return order ? <DisputeCard order={order} /> : <Spinner />;
  }
  if (step === 1) {
    // buyer's POV: a calm "handed to the manager" card — NOT the manager's console.
    return (
      <div className="rounded-xl border border-line bg-[#fbfbfe] p-5 text-center">
        <div className="text-3xl">📮</div>
        <div className="mt-2 text-sm font-semibold text-ink">Handed to manager Priya for review</div>
        <p className="mx-auto mt-1 max-w-md text-sm text-ink-soft">
          Trusty found the material likely doesn&apos;t match the listing, but media alone isn&apos;t proof — a
          human makes the call. You&apos;ll get a notification the moment it&apos;s decided.
        </p>
        <div className="mt-3 inline-flex items-center gap-2 rounded-full bg-amber-wash px-3 py-1 text-xs font-medium text-amber">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber" /> Awaiting manager decision
        </div>
        <div className="mt-4">
          <Link href="/manager" className="text-xs font-medium text-brand-ink hover:underline">
            (Curious? Switch to the manager&apos;s console to decide it yourself →)
          </Link>
        </div>
      </div>
    );
  }
  return <NotifList title="Your buyer inbox" notifs={buyerNotifs} icon="🔔" />;
}

// ---------------------------------------------------------------------------
// Seller journey step surfaces
// ---------------------------------------------------------------------------
const SELLER_PRODUCTS = new Set(["prod_fabric_kurti", "prod_bag_combo"]);

function SellerStep({ step }: { step: number }) {
  const [findings, setFindings] = useState<Agent2Product[] | null>(null);
  const [sellers, setSellers] = useState<ManagerSeller[] | null>(null);
  const [drafts, setDrafts] = useState<Draft[] | null>(null);
  const [sellerNotifs, setSellerNotifs] = useState<Notif[] | null>(null);

  const loadFindings = useCallback(async () => {
    try {
      const r = await api.agent2Findings();
      setFindings(r.products.filter((p) => SELLER_PRODUCTS.has(p.product_id)));
    } catch {
      setFindings([]);
    }
  }, []);

  useEffect(() => {
    if ((step === 0 || step === 1) && !findings) loadFindings();
    if (step === 2 && !sellers) {
      api.managerSellers("mgr_north").then((r) => setSellers(r.sellers)).catch(() => setSellers([]));
    }
    if (step === 3) {
      if (!drafts) {
        Promise.all([api.sellerDrafts("seller_bags"), api.sellerDrafts("seller_fixable")])
          .then(([a, b]) => setDrafts([...a.drafts, ...b.drafts]))
          .catch(() => setDrafts([]));
      }
      if (!sellerNotifs) {
        api.notificationsFor("seller", "seller_fixable").then(setSellerNotifs).catch(() => setSellerNotifs([]));
      }
    }
  }, [step, findings, sellers, drafts, sellerNotifs, loadFindings]);

  if (step === 0) {
    return (
      <div className="grid gap-3 sm:grid-cols-2">
        <ListingSummary
          title="Rayon Embroidered Anarkali Kurti"
          seller="EthnicWeave"
          note="Sold in Black / Blue / Red — the listing video shows only Black (its quality fingerprint covers every colour)."
          img="prod_fabric_kurti"
        />
        <ListingSummary
          title="Women's Handbag Combo (Pack of 4)"
          seller="Aaraals Collection"
          note="Listed as 'Free Size' with no measurements — the classic size-complaint trap."
          img="prod_bag_combo"
        />
        <p className="text-xs text-ink-faint sm:col-span-2">
          Want to list one yourself? Open the{" "}
          <Link href="/seller" className="font-medium text-brand-ink hover:underline">
            Seller studio
          </Link>{" "}
          — the mandatory-field gate blocks an incomplete listing before it can go live.
        </p>
      </div>
    );
  }
  if (step === 1) {
    return findings ? <FindingsList products={findings} /> : <Spinner />;
  }
  if (step === 2) {
    return sellers ? <ManagerPeek sellers={sellers} /> : <Spinner />;
  }
  return (
    <div className="space-y-4">
      <DraftList drafts={drafts} />
      <NotifList title="Seller inbox (HomeComfort)" notifs={sellerNotifs} icon="🔔" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Small presentational helpers
// ---------------------------------------------------------------------------
function NotifList({ title, notifs, icon }: { title: string; notifs: Notif[] | null; icon: string }) {
  if (notifs === null) return <Spinner />;
  if (notifs.length === 0) return <Empty>No messages.</Empty>;
  return (
    <div>
      <div className="mb-2 text-sm font-semibold text-ink">
        {icon} {title}
      </div>
      <div className="space-y-2">
        {notifs.map((n) => (
          <Card key={n.id} className="flex items-start justify-between gap-3 p-3">
            <div>
              <div className="text-sm font-medium text-ink">{n.subject}</div>
              <p className="text-xs text-ink-soft">{n.body}</p>
            </div>
            <Badge tone={n.priority === "immediate" ? "rose" : n.priority === "high" ? "amber" : "neutral"}>
              {n.priority}
            </Badge>
          </Card>
        ))}
      </div>
    </div>
  );
}

function ListingSummary({ title, seller, note, img }: { title: string; seller: string; note: string; img: string }) {
  return (
    <Card className="flex gap-3 p-3">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={productImage(img)} alt="" className="h-16 w-16 shrink-0 rounded-md bg-[#f2f2f7] object-contain" />
      <div className="min-w-0">
        <div className="text-sm font-semibold text-ink">{title}</div>
        <div className="text-xs text-ink-faint">{seller}</div>
        <p className="mt-1 text-xs text-ink-soft">{note}</p>
      </div>
    </Card>
  );
}

function FindingsList({ products }: { products: Agent2Product[] }) {
  return (
    <div className="space-y-3">
      {products.map((p) => (
        <Card key={p.product_id} className="p-4">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-semibold text-ink">{p.title}</span>
            <Badge tone={p.escalated ? "amber" : "neutral"}>{p.status}</Badge>
          </div>
          <ul className="mt-2 space-y-1.5">
            {p.issues.length === 0 && <li className="text-xs text-ink-faint">No issues — clean listing.</li>}
            {p.issues.map((i, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm">
                <span className={i.severity === "warn" ? "text-amber" : "text-ink-faint"}>
                  {i.severity === "warn" ? "⚠" : "○"}
                </span>
                <span className="text-ink-soft">
                  {i.label}
                  {i.detail ? <span className="text-ink-faint"> — {i.detail}</span> : null}
                </span>
              </li>
            ))}
          </ul>
          {p.recommended_action && (
            <div className="mt-2 rounded-lg bg-brand-wash px-3 py-1.5 text-xs text-brand-ink">
              Recommended: {p.recommended_action}
            </div>
          )}
        </Card>
      ))}
    </div>
  );
}

function ManagerPeek({ sellers }: { sellers: ManagerSeller[] }) {
  // include sellers with a flagged listing OR a live complaint cluster (a kept-active
  // listing like the kurti still shows its fabric complaint to the manager)
  const shown = sellers
    .filter((s) => s.flagged_count > 0 || s.products.some((p) => p.complaint))
    .slice(0, 5);
  return (
    <div className="space-y-3">
      {shown.map((s) => (
        <Card key={s.seller_id} className="p-4">
          <div className="flex items-center justify-between gap-2">
            <div>
              <div className="text-sm font-semibold text-ink">{s.name}</div>
              <div className="text-xs text-ink-faint">
                {s.rating.toFixed(1)}★ · {s.account_age_days ?? "?"}d old · {s.product_count} listings
              </div>
            </div>
            {s.flagged_count > 0 && <Badge tone="amber">{s.flagged_count} need action</Badge>}
          </div>
          <div className="mt-2 space-y-1.5">
            {s.products
              .filter((p) => p.needs_action || p.complaint)
              .slice(0, 3)
              .map((p) => (
                <div key={p.product_id} className="flex items-center justify-between gap-2 text-sm">
                  <span className="min-w-0 truncate text-ink-soft">{p.title}</span>
                  <div className="flex shrink-0 items-center gap-1.5">
                    {p.complaint && (
                      <span className="text-xs text-amber">
                        {p.complaint.label} {Math.round(p.complaint.agreement * 100)}%
                      </span>
                    )}
                    <Badge tone={p.status === "active" ? "neutral" : "amber"}>{p.status}</Badge>
                  </div>
                </div>
              ))}
          </div>
        </Card>
      ))}
      <Link href="/manager" className="inline-block text-sm font-medium text-brand-ink hover:underline">
        Open the full Manager console →
      </Link>
    </div>
  );
}

function DraftList({ drafts }: { drafts: Draft[] | null }) {
  if (drafts === null) return <Spinner />;
  if (drafts.length === 0) return <Empty>No pending fix drafts.</Empty>;
  return (
    <div className="space-y-3">
      <div className="text-sm font-semibold text-ink">✏️ Agent 2 drafted these corrections for you</div>
      {drafts.map((d) => (
        <Card key={d.id} className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-ink">{d.summary ?? d.field}</span>
            {d.cluster && <Badge tone="amber">{d.cluster}</Badge>}
          </div>
          {d.rationale && <p className="mt-1 text-xs text-ink-soft">{d.rationale}</p>}
          <div className="mt-2 rounded-lg bg-green-wash p-2 text-xs">
            <span className="font-medium text-green">Proposed: </span>
            <span className="text-ink-soft">{JSON.stringify(d.after).replace(/[{}"]/g, " ").trim()}</span>
          </div>
        </Card>
      ))}
      <Link href="/seller" className="inline-block text-sm font-medium text-brand-ink hover:underline">
        Approve fixes in the Seller studio →
      </Link>
    </div>
  );
}
