"use client";

import { useRef, useState } from "react";
import { api, type LiveFingerprint } from "@/lib/api";
import { Badge, Button, Card, Spinner } from "@/components/ui";

// The seven variant-invariant "golden fields", in the order the backend compares them.
// Colour/shade/print are deliberately absent: they are recorded but never scored.
const GOLDEN_FIELDS: { key: string; label: string }[] = [
  { key: "weave_structure", label: "Weave" },
  { key: "surface_sheen", label: "Sheen" },
  { key: "fibre_texture", label: "Texture" },
  { key: "opacity", label: "Opacity" },
  { key: "stitch_quality", label: "Stitch" },
  { key: "drape", label: "Drape" },
  { key: "embellishment_type", label: "Embellishment" },
];
const VARIANT_FIELDS = ["colour", "shade", "print_colourway"];

/**
 * Live listing-video → quality fingerprint, for the demo.
 *
 * The seeded demo proves the deterministic diff; this proves the extraction that feeds it.
 * A presenter drops in a 5-15s clip and the seven golden fields appear, read from real
 * keyframes. Nothing downstream changes — the same fingerprint the seed provided is simply
 * produced live instead.
 */
export function LiveFingerprintPanel({
  productId,
  productTitle,
}: {
  productId: string;
  productTitle: string;
}) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<LiveFingerprint | null>(null);
  const [error, setError] = useState<string>("");
  const [resetDone, setResetDone] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const onPick = async (file: File | undefined) => {
    if (!file || busy) return;   // `busy` guard: a second pick cannot start a second upload
    setBusy(true);
    setError("");
    setResult(null);
    setResetDone(false);
    try {
      setResult(await api.uploadListingVideo(productId, file));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = ""; // allow re-picking the same file
    }
  };

  const onReset = async () => {
    setBusy(true);
    try {
      await api.resetListingVideo(productId);
      setResult(null);
      setError("");
      setResetDone(true);
    } catch {
      setError("Could not restore the seeded fingerprint.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">🎥 Extract a fingerprint, live</h3>
          <p className="mt-0.5 text-xs text-ink-soft">
            Drop in a 5–15s clip of any fabric. OpenCV samples keyframes, one multimodal read
            distils them into the seven <b>variant-invariant</b> golden fields — the same
            fields every dispute is judged against.
          </p>
        </div>
        <Badge tone="neutral">{productTitle}</Badge>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <input
          ref={inputRef}
          id={`video-${productId}`}
          type="file"
          accept="video/mp4,video/quicktime,video/x-msvideo,video/x-matroska"
          className="sr-only"
          disabled={busy}
          onChange={(e) => onPick(e.target.files?.[0])}
        />
        <label
          htmlFor={`video-${productId}`}
          aria-disabled={busy}
          className={`inline-flex cursor-pointer items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition ${
            busy
              ? "cursor-not-allowed bg-[#e9e9f0] text-ink-faint"
              : "bg-brand text-white hover:bg-brand-ink"
          }`}
        >
          {busy ? <Spinner /> : <span aria-hidden="true">⬆</span>}
          {busy ? "Reading keyframes…" : "Upload a listing video"}
        </label>

        {(result || resetDone) && (
          <Button variant="secondary" size="sm" onClick={onReset} disabled={busy}>
            Restore seeded fingerprint
          </Button>
        )}
      </div>

      {/* An honest failure message. Quota exhaustion mid-demo is expected on the free
          tier, and the presenter needs to know the demo is still intact. */}
      {error && (
        <div className="mt-3 rounded-xl bg-amber-wash px-3 py-2.5 text-xs text-amber">
          <b>Live extraction unavailable.</b> {error}
          <div className="mt-1 text-ink-soft">
            The previous fingerprint is still in place — the dispute comparison is unaffected.
          </div>
        </div>
      )}

      {resetDone && !result && (
        <div className="mt-3 rounded-xl bg-teal-wash px-3 py-2 text-xs text-teal">
          ✓ Seeded fingerprint restored — ready to run the demo again.
        </div>
      )}

      {result && (
        <div className="mt-3">
          <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-ink-soft">
            <Badge tone="green">extracted live</Badge>
            <span>
              {result.frames_sampled} keyframes · {(result.size_bytes / 1_048_576).toFixed(1)} MB ·
              confidence {Math.round(result.confidence * 100)}%
            </span>
          </div>

          <p className="mb-2 text-sm text-ink">{result.summary}</p>

          <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
            Golden fields — compared in every dispute
          </div>
          <dl className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
            {GOLDEN_FIELDS.map((f) => (
              <div key={f.key} className="rounded-lg bg-[#f6f6fb] px-2.5 py-1.5">
                <dt className="text-[10px] uppercase tracking-wide text-ink-faint">{f.label}</dt>
                <dd className="truncate text-xs font-medium text-ink" title={result.attributes[f.key]}>
                  {result.attributes[f.key] || "—"}
                </dd>
              </div>
            ))}
          </dl>

          <div className="mt-2.5 mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
            Recorded but never scored — colour cannot cause a false flag
          </div>
          <div className="flex flex-wrap gap-1.5">
            {VARIANT_FIELDS.map((k) => (
              <span
                key={k}
                className="inline-flex items-center gap-1 rounded-full bg-[#f2f3f8] px-2 py-0.5 text-xs text-ink-faint"
              >
                <span aria-hidden="true">⃠</span> {k.replace(/_/g, " ")}: {result.attributes[k] || "—"}
              </span>
            ))}
          </div>

          <p className="mt-3 text-xs text-ink-faint">
            This fingerprint now drives the dispute on this product — open the buyer journey to
            see it compared against the buyer&apos;s photos.
          </p>
        </div>
      )}
    </Card>
  );
}
