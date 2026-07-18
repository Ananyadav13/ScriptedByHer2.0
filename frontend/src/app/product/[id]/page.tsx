import Link from "next/link";
import { api, type ProductDetail } from "@/lib/api";
import { ProductView } from "@/components/ProductView";

export const dynamic = "force-dynamic";

export default async function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  let p: ProductDetail;
  try {
    p = await api.product(id);
  } catch {
    return (
      <main className="mx-auto max-w-2xl px-5 py-16 text-center">
        <p className="text-ink-soft">Couldn&apos;t load this product. Is the backend running?</p>
        <Link href="/" className="mt-4 inline-block text-sm font-medium text-brand-ink hover:underline">
          ← Back to shop
        </Link>
      </main>
    );
  }

  return <ProductView detail={p} />;
}
