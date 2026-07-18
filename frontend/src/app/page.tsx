import { api, type Product } from "@/lib/api";
import { ProductCard } from "@/components/ProductCard";
import { BuyerAlerts } from "@/components/BuyerAlerts";

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
  const sponsored = new Set([1, 4]);

  return (
    <main className="bg-[#f2f2f7]">
      <div className="bg-surface">
        <div className="mx-auto max-w-6xl px-5 py-2 text-sm text-ink-soft">
          <span className="text-brand">📍</span> Delivering to <b className="text-ink">Jabalpur - 482005</b> ›
        </div>
      </div>

      <BuyerAlerts />

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
        <section>
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
