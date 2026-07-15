import Link from "next/link";
import { api, type ProductDetail } from "@/lib/api";
import { statusMeta } from "@/lib/decisions";
import { DEMO_ORDERS } from "@/lib/orders";
import { Badge, Card, LinkButton, Page } from "@/components/ui";
import { VerifyPanel } from "@/components/VerifyPanel";
import { DisputeCard } from "@/components/DisputeCard";

export const dynamic = "force-dynamic";

function money(n: number) {
  return "₹" + n.toLocaleString("en-IN");
}

function StatusBanner({ p }: { p: ProductDetail }) {
  const sm = statusMeta(p.status);
  if (p.status === "active") return null;
  const tone =
    sm.tone === "green" ? "green" : sm.tone === "rose" ? "rose" : sm.tone === "teal" ? "teal" : "amber";
  const wash =
    tone === "rose"
      ? "bg-rose-wash text-rose"
      : tone === "teal"
        ? "bg-teal-wash text-teal"
        : "bg-amber-wash text-amber";
  return (
    <div className={`mb-5 rounded-xl px-4 py-3 text-sm ${wash}`}>
      <div className="flex items-center gap-2 font-semibold">
        <span>{p.status === "flagged" ? "👁️" : "🔒"}</span>
        {sm.label}
        {p.status === "flagged" && (
          <span className="font-normal opacity-80">— still buyable, a manager is reviewing</span>
        )}
      </div>
      {p.lock_reason && <p className="mt-1 opacity-90">{p.lock_reason}</p>}
    </div>
  );
}

export default async function ProductPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ order?: string }>;
}) {
  const { id } = await params;
  const { order: focusOrder } = await searchParams;

  let p: ProductDetail;
  try {
    p = await api.product(id);
  } catch {
    return (
      <Page>
        <Card className="p-8 text-center">
          <p className="text-ink-soft">Couldn&apos;t load this product. Is the backend running?</p>
          <LinkButton href="/" variant="secondary" className="mt-4">
            ← Back home
          </LinkButton>
        </Card>
      </Page>
    );
  }

  const orders = DEMO_ORDERS[id] ?? [];
  const discount = p.mrp > p.price ? Math.round((1 - p.price / p.mrp) * 100) : 0;
  const newAcctShare =
    p.reviews.length > 0
      ? Math.round(
          (p.reviews.filter((r) => r.reviewer_account_age_days < 30).length / p.reviews.length) * 100,
        )
      : 0;

  return (
    <Page>
      <Link href="/" className="text-sm text-ink-faint hover:text-brand-ink">
        ← All scenarios
      </Link>

      <div className="mt-3 grid gap-6 lg:grid-cols-[1.15fr_1fr]">
        {/* left: product + reviews */}
        <div>
          <StatusBanner p={p} />
          <Card className="overflow-hidden">
            <div className="aspect-square overflow-hidden bg-[#f2f2f7] sm:aspect-[16/11]">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={`/products/${p.id}.jpg`} alt={p.title} className="h-full w-full object-cover" />
            </div>
            <div className="p-5">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium uppercase tracking-wide text-ink-faint">
                  {p.brand}
                </span>
                {p.knockoff_flag && <Badge tone="amber">knockoff claim</Badge>}
              </div>
              <h1 className="mt-1 text-2xl font-bold text-ink">{p.title}</h1>
              <div className="mt-3 flex items-baseline gap-3">
                <span className="text-2xl font-bold text-ink">{money(p.price)}</span>
                {discount > 0 && (
                  <>
                    <span className="text-ink-faint line-through">{money(p.mrp)}</span>
                    <Badge tone={discount > 90 ? "rose" : "green"}>{discount}% off</Badge>
                  </>
                )}
              </div>
              {p.fabric_claim && (
                <p className="mt-2 text-sm text-ink-soft">
                  Material claim: <span className="font-medium text-ink">{p.fabric_claim}</span>
                </p>
              )}
              {p.buyer_tip && (
                <div className="mt-3 rounded-lg bg-brand-wash px-3 py-2 text-sm text-brand-ink">
                  💡 {p.buyer_tip}
                </div>
              )}
            </div>
          </Card>

          {/* reviews */}
          <div className="mt-6">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold text-ink">Reviews ({p.reviews.length})</h2>
              {p.reviews.length > 0 && (
                <span className="text-xs text-ink-faint">
                  {newAcctShare}% from accounts &lt; 30 days old
                </span>
              )}
            </div>
            <div className="space-y-2.5">
              {p.reviews.slice(0, 8).map((r) => (
                <Card key={r.id} className="p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-amber">{"★".repeat(r.rating)}<span className="text-line">{"★".repeat(5 - r.rating)}</span></span>
                    <div className="flex items-center gap-2">
                      {r.has_video && <Badge tone="teal">🎥 video</Badge>}
                      <span
                        className={`text-xs ${r.reviewer_account_age_days < 30 ? "font-medium text-rose" : "text-ink-faint"}`}
                      >
                        {r.reviewer_account_age_days}d old
                      </span>
                    </div>
                  </div>
                  <p className="mt-1.5 text-sm text-ink-soft">{r.text}</p>
                </Card>
              ))}
              {p.reviews.length > 8 && (
                <p className="text-center text-xs text-ink-faint">
                  +{p.reviews.length - 8} more reviews
                </p>
              )}
              {p.reviews.length === 0 && (
                <Card className="p-4 text-sm text-ink-faint">No reviews yet.</Card>
              )}
            </div>
          </div>
        </div>

        {/* right: agent actions */}
        <div className="space-y-6 lg:sticky lg:top-20 lg:self-start">
          <VerifyPanel productId={p.id} title={p.title} />

          {orders.length > 0 && (
            <div>
              <h2 className="mb-3 font-semibold text-ink">Your orders</h2>
              <div className="space-y-4">
                {orders.map((o) => (
                  <DisputeCard key={o.id} order={o} highlight={o.id === focusOrder} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </Page>
  );
}
