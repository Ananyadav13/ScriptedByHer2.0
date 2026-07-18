"use client";

import { useState } from "react";
import { API, type MediaEvidence } from "@/lib/api";
import { productImage } from "@/lib/productImages";

// A frame image with a graceful fallback: real dispute stills live in /public/evidence/;
// until they're dropped in, fall back to the product image so nothing renders broken.
function Frame({ src, fallback, alt }: { src: string; fallback: string; alt: string }) {
  const [err, setErr] = useState(false);
  const resolved = src.startsWith("http") ? src : `${src}`;
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={err ? fallback : resolved}
      onError={() => setErr(true)}
      alt={alt}
      className="h-24 w-20 shrink-0 rounded-lg border border-line bg-[#f2f2f7] object-cover"
    />
  );
}

const PRETTY: Record<string, string> = {
  weave_structure: "Weave",
  surface_sheen: "Sheen",
  fibre_texture: "Texture",
  opacity: "Opacity",
  stitch_quality: "Stitch",
  drape: "Drape",
  embellishment_type: "Embellishment",
};

/** The visual heart of a material dispute: the seller's listing frames beside the buyer's
 *  photos, then the attribute-by-attribute verdict — with colour explicitly set aside. */
export function MediaEvidenceCard({ ev, fallbackImg }: { ev: MediaEvidence; fallbackImg: string }) {
  const ref = ev.reference_frame_urls ?? [];
  const buy = ev.evidence_frame_urls ?? [];
  const compared = ev.compared_attributes ?? [];
  const diverged = new Set(ev.diverged_attributes ?? []);
  const ignored = ev.ignored_attributes ?? [];
  const fb = productImage(fallbackImg);

  return (
    <div className="overflow-hidden rounded-xl border border-line">
      {/* cross-variant banner */}
      {ev.variant?.cross_variant && (
        <div className="bg-brand-wash px-3 py-2 text-xs text-brand-ink">
          🎥 Listing video shows the <b>{ev.variant.listing_video_variant}</b> colour · buyer received{" "}
          <b>{ev.variant.ordered_variant}</b> — colour is <b>excluded</b> from the material check.
        </div>
      )}

      {/* the two frame strips */}
      <div className="grid grid-cols-2 gap-2 p-3">
        <div>
          <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
            Seller listing {ev.claimed_material ? `· “${ev.claimed_material}”` : ""}
          </div>
          <div className="flex gap-1.5 overflow-x-auto">
            {(ref.length ? ref : [fb]).map((s, i) => (
              <Frame key={i} src={s} fallback={fb} alt="listing frame" />
            ))}
          </div>
        </div>
        <div>
          <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink-faint">Buyer&apos;s photos</div>
          <div className="flex gap-1.5 overflow-x-auto">
            {(buy.length ? buy : [fb]).map((s, i) => (
              <Frame key={i} src={s} fallback={fb} alt="buyer frame" />
            ))}
          </div>
        </div>
      </div>

      {/* attribute-by-attribute comparison */}
      {compared.length > 0 && (
        <div className="border-t border-line px-3 py-2.5">
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
            Quality attributes compared
          </div>
          <div className="flex flex-wrap gap-1.5">
            {compared.map((a) => {
              const bad = diverged.has(a);
              return (
                <span
                  key={a}
                  className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                    bad ? "bg-rose-wash text-rose" : "bg-green-wash text-green"
                  }`}
                >
                  {bad ? "✗" : "✓"} {PRETTY[a] ?? a}
                </span>
              );
            })}
            {ignored.map((a) => (
              <span key={a} className="inline-flex items-center gap-1 rounded-full bg-[#f2f3f8] px-2 py-0.5 text-xs font-medium text-ink-faint">
                ⃠ {a} (ignored)
              </span>
            ))}
          </div>
        </div>
      )}

      {/* verdict line */}
      <div
        className={`border-t border-line px-3 py-2.5 text-sm ${
          ev.mismatch ? "bg-rose-wash/40 text-rose" : "bg-green-wash/40 text-green"
        }`}
      >
        <b>{ev.mismatch ? "Material mismatch" : "Consistent with the listing"}</b>
        {typeof ev.confidence === "number" ? <span className="opacity-80"> · {Math.round(ev.confidence * 100)}% confidence</span> : null}
        {ev.reason ? <div className="mt-0.5 text-xs text-ink-soft">{ev.reason}</div> : null}
      </div>

      {/* colour heard separately (only for a wrong-colour claim) */}
      {ev.colour_note && (
        <div className="border-t border-line bg-amber-wash/40 px-3 py-2 text-xs text-amber">🎨 {ev.colour_note}</div>
      )}
    </div>
  );
}

// exported so callers can reference the API base if they build absolute URLs later
export { API };
