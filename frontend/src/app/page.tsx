// Phase 1 skeleton: fetch + render seeded catalog. Real UI (scenarios, trace panel) = Phase 5.
type Product = {
  id: string;
  title: string;
  brand: string;
  price: number;
  mrp: number;
  status: string;
};

const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function getProducts(): Promise<Product[]> {
  try {
    const res = await fetch(`${API}/products`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function Home() {
  const products = await getProducts();
  return (
    <main className="min-h-screen bg-neutral-50 p-8">
      <h1 className="text-2xl font-bold text-neutral-900">Build Trust</h1>
      <p className="mb-6 text-neutral-500">
        Two agentic AI systems that act on evidence. (Phase 1 skeleton — catalog from backend)
      </p>
      {products.length === 0 ? (
        <p className="text-red-600">No products — is the backend running on {API}?</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {products.map((p) => (
            <div key={p.id} className="rounded-lg border border-neutral-200 bg-white p-4">
              <div className="flex items-start justify-between gap-2">
                <h2 className="font-semibold text-neutral-900">{p.title}</h2>
                <span className="whitespace-nowrap rounded bg-neutral-100 px-2 py-0.5 text-xs text-neutral-600">
                  {p.status}
                </span>
              </div>
              <p className="text-sm text-neutral-500">{p.brand}</p>
              <p className="mt-2 text-sm">
                <span className="font-semibold">₹{p.price}</span>{" "}
                <span className="text-neutral-400 line-through">₹{p.mrp}</span>
              </p>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
