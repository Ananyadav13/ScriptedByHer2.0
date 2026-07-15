"use client";

// Client wrapper: builds the investigate closure in the browser so a Server Component
// can render the live trace panel by passing only plain string props.
import { api } from "@/lib/api";
import { TracePanel } from "@/components/TracePanel";

export function VerifyPanel({ productId, title }: { productId: string; title: string }) {
  return (
    <TracePanel
      sublabel={`Investigating “${title}”`}
      start={async () => {
        const r = await api.investigate({ product_id: productId, trigger: "pre_purchase" });
        return r.investigation_id;
      }}
    />
  );
}
