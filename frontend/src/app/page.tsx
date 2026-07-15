import Link from "next/link";
import { api, type Product } from "@/lib/api";
import { SCENARIOS } from "@/lib/scenarios";
import { ProductCard } from "@/components/ProductCard";

export const dynamic = "force-dynamic";

const CATEGORIES = [
  { label: "Watches", emoji: "⌚" },
  { label: "Kurtis & Dr..", emoji: "👗" },
  { label: "Footwear", emoji: "👟" },
  { label: "Electronics", emoji: "🎧" },
  { label: "Home", emoji: "🛏️" },
  { label: "Beauty", emoji: "💄" },
  { label: "Kitchen", emoji: "🍳" },
  { label: "Jewellery", emoji: "💍" },
  { label: "Men Fashion", emoji: "👕" },
];

async function getProducts(): Promise<Product[]> {
  try {
    return await api.products();
  } catch {
    return [];
  }
}

export default async function Home() {
  const products = await getProducts();
  const sponsored = new Set([1, 4]); // a couple of "Ad" tiles for realism

  return (
    <main className="bg-[#f2f2f7]">
      {/* delivery bar */}
      <div className="bg-surface">
        <div className="mx-auto max-w-6xl px-5 py-2 text-sm text-ink-soft">
          <span className="text-brand">📍</span> Delivering to <b className="text-ink">Jabalpur - 482005</b> ›
        </div>
      </div>

      {/* category circles */}
      <div className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-6xl gap-5 overflow-x-auto px-5 py-3">
          {CATEGORIES.map((c) => (
            <div key={c.label} className="flex shrink-0 flex-col items-center gap-1">
              <span className="grid h-12 w-12 place-items-center rounded-full bg-brand-wash text-xl">{c.emoji}</span>
              <span className="w-14 truncate text-center text-[11px] text-ink-soft">{c.label}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-5 py-5">
        {/* compact USP hero */}
        <section
          className="relative overflow-hidden rounded-2xl px-5 py-6 text-white sm:px-8"
          style={{ background: "linear-gradient(105deg, #e60073 0%, #9f1069 55%, #570d5b 100%)" }}
        >
          <div className="relative max-w-xl">
            <span className="inline-block rounded-full bg-white/20 px-3 py-1 text-xs font-semibold backdrop-blur">
              Powered by two autonomous AI agents
            </span>
            <h1 className="mt-2.5 text-2xl font-extrabold leading-tight sm:text-3xl">
              Shop with confidence. Every listing, verified by AI.
            </h1>
            <p className="mt-1.5 text-sm text-white/85">
              Build Trust catches counterfeits, settles disputes fairly, and predicts your size — on evidence.
            </p>
            <div className="mt-4 flex flex-wrap gap-2.5">
              <Link href="/product/prod_counterfeit_rolex" className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-brand-ink">
                Watch the counterfeit trace →
              </Link>
              <Link href="/admin" className="rounded-lg bg-white/15 px-4 py-2 text-sm font-semibold text-white backdrop-blur">
                Run a catalog audit
              </Link>
            </div>
          </div>
        </section>

        {/* demos strip */}
        <section className="mt-6">
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="text-lg font-bold text-ink">✨ Build Trust demos</h2>
            <span className="text-xs text-ink-faint">6 golden paths · one click</span>
          </div>
          <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
            {SCENARIOS.map((s) => (
              <Link
                key={s.key}
                href={s.href}
                className="group flex items-center gap-2.5 rounded-xl border border-line bg-surface p-2.5 transition hover:border-brand/40"
              >
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-brand-wash text-xl">{s.emoji}</span>
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold text-ink">{s.title}</div>
                  <div className="truncate text-xs text-ink-faint">{s.cta} →</div>
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* product feed */}
        <section className="mt-6">
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="text-lg font-bold text-ink">Products for you</h2>
            <span className="text-xs text-ink-faint">{products.length} items</span>
          </div>
          {products.length === 0 ? (
            <div className="rounded-xl border border-dashed border-line bg-surface p-8 text-center text-sm text-rose">
              No products — is the backend running on :8000?
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-4">
              {products.map((p, i) => (
                <ProductCard key={p.id} p={p} sponsored={sponsored.has(i)} />
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
