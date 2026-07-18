"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, type Draft, type Notif, type Product } from "@/lib/api";
import { statusMeta } from "@/lib/decisions";
import { Badge, Button, Card, Empty, Page, SectionTitle, Spinner } from "@/components/ui";
import { TrustyMark, SpeechBubble } from "@/components/Mascot";
import { productImage } from "@/lib/productImages";

const SELLERS = [
  { id: "seller_fixable", name: "HomeComfort" },
  { id: "seller_bags", name: "Aaraals Collection" },
  { id: "seller_scam", name: "MegaDiscount Hub" },
  { id: "seller_kids", name: "LittleStars Kids" },
  { id: "seller_gadgets", name: "TechBazaar" },
];

const FIELD_LABEL: Record<string, string> = {
  title: "Product title",
  description: "Description",
  color: "Colour",
  size_chart_json: "Size chart / measurements",
  fabric_claim: "Fabric / material",
  listing_video_path: "Listing video",
};

export default function SellerPage() {
  const [seller, setSeller] = useState(SELLERS[0]);
  const [products, setProducts] = useState<Product[] | null>(null);
  const [notifs, setNotifs] = useState<Notif[]>([]);
  const [drafts, setDrafts] = useState<Draft[] | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (sid: string) => {
    setProducts(null);
    setDrafts(null);
    const [all, n, d] = await Promise.allSettled([
      api.products(),
      api.notificationsFor("seller", sid),
      api.sellerDrafts(sid),
    ]);
    setProducts(all.status === "fulfilled" ? all.value.filter((p) => p.seller_id === sid) : []);
    setNotifs(n.status === "fulfilled" ? n.value : []);
    setDrafts(d.status === "fulfilled" ? d.value.drafts : []);
  }, []);
  useEffect(() => {
    load(seller.id);
  }, [seller, load]);

  const approve = async (id: string) => {
    setBusy(true);
    try {
      await api.approveDraft(id);
      await load(seller.id);
    } finally {
      setBusy(false);
    }
  };
  const generateDrafts = async () => {
    setBusy(true);
    try {
      await api.audit(false);
      await load(seller.id);
    } finally {
      setBusy(false);
    }
  };

  const flagged = (products ?? []).filter((p) => p.status !== "active");
  const nDrafts = drafts?.length ?? 0;
  const trustyLine = useMemo(() => {
    if (products === null) return "Let me pull up your shop…";
    const parts: string[] = [];
    if (flagged.length) parts.push(`${flagged.length} of your listing${flagged.length > 1 ? "s need" : " needs"} attention.`);
    if (nDrafts) parts.push(`I've drafted ${nDrafts} fix${nDrafts > 1 ? "es" : ""} — approve below, one tap.`);
    if (!parts.length) parts.push("Everything looks healthy. Ready to add a new product?");
    return parts.join(" ");
  }, [products, flagged.length, nDrafts]);

  return (
    <Page>
      <SectionTitle eyebrow="Seller studio" title="Your shop" sub="What's happening with your products, and the fixes Trusty has drafted for you." />

      {/* seller switcher */}
      <div className="mb-5 flex flex-wrap gap-2">
        {SELLERS.map((s) => (
          <button
            key={s.id}
            onClick={() => setSeller(s)}
            className={`rounded-xl border px-4 py-2 text-sm transition ${
              seller.id === s.id ? "border-brand bg-brand-wash text-brand-ink" : "border-line bg-surface text-ink-soft hover:bg-[#f2f3f8]"
            }`}
          >
            {s.name}
          </button>
        ))}
      </div>

      {/* Trusty + the New listing entry point — at the top, the front door to the studio */}
      <Card className="mb-6 p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <TrustyMark size={48} tagline="Your listing assistant" mood={flagged.length || nDrafts ? "think" : "cheer"} />
          <Link
            href="/seller/new"
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-ink"
          >
            <span className="text-lg leading-none">＋</span> New listing
          </Link>
        </div>
        <div className="mt-3">
          <SpeechBubble>{trustyLine}</SpeechBubble>
        </div>
      </Card>

      {/* what's happening — notifications + listing statuses together */}
      <h2 className="mb-2 text-sm font-semibold text-ink">🔔 What&apos;s happening with your products</h2>
      <div className="space-y-2">
        {notifs.map((n) => (
          <Card key={n.id} className="flex items-start justify-between gap-3 p-3.5">
            <div>
              <div className="text-sm font-medium text-ink">{n.subject}</div>
              <p className="text-xs text-ink-soft">{n.body}</p>
            </div>
            <Badge tone={n.priority === "immediate" ? "rose" : n.priority === "high" ? "amber" : "neutral"}>{n.priority}</Badge>
          </Card>
        ))}
        {products === null ? (
          <Spinner />
        ) : products.length === 0 ? (
          <Empty>No listings yet.</Empty>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2">
            {products.map((p) => {
              const sm = statusMeta(p.status);
              return (
                <Card key={p.id} className="flex items-center gap-3 p-3">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={productImage(p.id)} alt="" className="h-12 w-12 rounded-md bg-[#f2f2f7] object-contain" />
                  <div className="min-w-0 flex-1">
                    <Link href={`/product/${p.id}`} className="line-clamp-1 text-sm font-medium text-ink hover:text-brand-ink">{p.title}</Link>
                    <div className="text-xs text-ink-faint">₹{p.price}</div>
                  </div>
                  <Badge tone={sm.tone}>{sm.label}</Badge>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* suggested fixes by Trusty */}
      <div className="mt-6">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-ink">✏️ Suggested fixes by Trusty</h2>
          <Badge tone="brand">{nDrafts} pending</Badge>
        </div>
        <div className="space-y-3">
          {drafts === null && <Spinner />}
          {drafts !== null && drafts.length === 0 && (
            <Empty>
              <p>No pending fixes.</p>
              <Button variant="secondary" size="sm" className="mt-3" disabled={busy} onClick={generateDrafts}>
                {busy ? <Spinner /> : "Run a catalog audit"}
              </Button>
            </Empty>
          )}
          {drafts?.map((d) => (
            <Card key={d.id} className="p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-ink">{d.summary ?? FIELD_LABEL[d.field ?? ""] ?? d.field}</span>
                {d.cluster && <Badge tone="amber">{d.cluster}</Badge>}
              </div>
              {d.rationale && <p className="mt-1 text-xs text-ink-soft">{d.rationale}</p>}
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <div className="rounded-lg bg-rose-wash p-2">
                  <div className="mb-1 font-medium text-rose">Before</div>
                  <pre className="whitespace-pre-wrap break-words text-ink-soft">{fmt(d.before)}</pre>
                </div>
                <div className="rounded-lg bg-green-wash p-2">
                  <div className="mb-1 font-medium text-green">After</div>
                  <pre className="whitespace-pre-wrap break-words text-ink-soft">{fmt(d.after)}</pre>
                </div>
              </div>
              <Button className="mt-3 w-full" size="sm" disabled={busy} onClick={() => approve(d.id)}>
                {busy ? <Spinner /> : "Approve fix"}
              </Button>
            </Card>
          ))}
        </div>
      </div>
    </Page>
  );
}

function fmt(v: unknown): string {
  if (v == null) return "—";
  if (typeof v === "string") return v;
  return JSON.stringify(v, null, 1).replace(/[{}"]/g, "").trim() || "—";
}
