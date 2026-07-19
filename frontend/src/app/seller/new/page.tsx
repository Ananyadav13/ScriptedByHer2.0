"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Card, Page, SectionTitle, Spinner } from "@/components/ui";
import { Trusty, SpeechBubble } from "@/components/Mascot";

type Lang = "en" | "hi" | "ta";
const LANGS: { key: Lang; label: string }[] = [
  { key: "en", label: "English" },
  { key: "hi", label: "हिंदी" },
  { key: "ta", label: "தமிழ்" },
];

const FIELD_LABEL: Record<string, string> = {
  title: "Product title",
  description: "Description",
  color: "Colour",
  size_chart_json: "Size chart / measurements",
  fabric_claim: "Fabric / material",
  listing_video_path: "Listing video",
};

const TIPS: Record<Lang, Record<string, string>> = {
  en: {
    intro: "Hi, I'm Trusty! Fill the details and I'll flag anything missing before your listing goes live.",
    ok: "Perfect — your listing has everything buyers need. This builds trust and cuts returns!",
    title: "Give it a clear, specific title — buyers search for exactly what you sell.",
    description: "Write a real description (20+ characters): what it is, what it's made of, how it fits.",
    color: "State the colour. If you sell more colours, each is a variant of the same listing.",
    size_chart_json: "Add real measurements (chest, length in cm). Accurate sizes mean fewer returns.",
    fabric_claim: "Tell buyers the true material — e.g. “100% cotton”. Honest claims avoid disputes.",
    listing_video_path: "Record a short video of the actual product. It becomes your proof if a dispute happens.",
  },
  hi: {
    intro: "नमस्ते, मैं Trusty हूँ! विवरण भरें, मैं लाइव होने से पहले कमी बता दूँगा।",
    ok: "बढ़िया — आपकी लिस्टिंग में सब कुछ है। इससे भरोसा बढ़ता है और रिटर्न कम होते हैं!",
    title: "स्पष्ट, सटीक टाइटल दें — खरीदार वही खोजते हैं।",
    description: "असली विवरण लिखें (20+ अक्षर): क्या है, किस चीज़ का बना है, फिट कैसा है।",
    color: "रंग बताएं। ज़्यादा रंग हों तो हर एक इसी लिस्टिंग का वेरिएंट है।",
    size_chart_json: "असली माप जोड़ें (छाती, लंबाई cm में)। सही साइज़ = कम रिटर्न।",
    fabric_claim: "सही मटीरियल बताएं — जैसे “100% कॉटन”।",
    listing_video_path: "प्रोडक्ट का छोटा वीडियो बनाएं। विवाद होने पर यही आपका सबूत है।",
  },
  ta: {
    intro: "வணக்கம், நான் Trusty! விவரங்களை நிரப்புங்கள், லைவ் ஆகும் முன் குறையை சொல்கிறேன்.",
    ok: "அருமை — உங்கள் பட்டியலில் எல்லாம் உள்ளது!",
    title: "தெளிவான தலைப்பு கொடுங்கள்.",
    description: "உண்மையான விளக்கம் எழுதுங்கள் (20+ எழுத்துகள்).",
    color: "நிறத்தைச் சொல்லுங்கள்.",
    size_chart_json: "உண்மையான அளவுகளைச் சேர்க்கவும் (மார்பு, நீளம் cm).",
    fabric_claim: "உண்மையான பொருளைச் சொல்லுங்கள்.",
    listing_video_path: "பொருளின் குறு வீடியோவைப் பதிவு செய்யுங்கள்.",
  },
};

// Module scope: a stable identity, so it can be a real effect dependency instead of a
// fresh array on every render.
const SIZE_ROWS = ["S", "M", "L", "XL"];

export default function NewListingPage() {
  const [lang, setLang] = useState<Lang>("en");
  const [category, setCategory] = useState("apparel");
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [color, setColor] = useState("");
  const [pattern, setPattern] = useState("");
  const [meas, setMeas] = useState<Record<string, { chest: string; length: string }>>({});
  const [fabric, setFabric] = useState("");
  const [videoName, setVideoName] = useState<string | null>(null);
  const [gate, setGate] = useState<{ allowed: boolean; missing: string[]; required: string[] } | null>(null);

  const setCell = (size: string, key: "chest" | "length", val: string) =>
    setMeas((m) => ({ ...m, [size]: { ...(m[size] ?? { chest: "", length: "" }), [key]: val } }));

  useEffect(() => {
    const rows = SIZE_ROWS.filter((s) => meas[s]?.chest || meas[s]?.length).map((s) => ({
      size: s,
      chest: meas[s]?.chest,
      length: meas[s]?.length,
    }));
    api
      .listingCheck({
        category,
        title: title || null,
        description: desc || null,
        color: color || null,
        size_chart_json: rows.length ? { rows } : null,
        fabric_claim: fabric || null,
        listing_video_path: videoName ? `media/videos/${videoName}` : null,
      })
      .then(setGate)
      .catch(() => setGate(null));
  }, [category, title, desc, color, meas, fabric, videoName]);

  const firstMissing = gate?.missing?.[0];
  const tip = useMemo(() => {
    if (!gate) return TIPS[lang].intro;
    if (gate.allowed) return TIPS[lang].ok;
    return TIPS[lang][firstMissing ?? "intro"] ?? TIPS[lang].intro;
  }, [gate, firstMissing, lang]);
  const mood = gate?.allowed ? "cheer" : firstMissing ? "think" : "happy";

  return (
    <Page>
      <Link href="/seller" className="mb-2 inline-block text-sm font-medium text-brand-ink hover:underline">
        ← Back to your shop
      </Link>
      <SectionTitle eyebrow="New listing" title="Add a product" sub="A listing goes live only when the essentials are present — Trusty checks as you type." />

      {/* Trusty guidance */}
      <Card className="mb-6 p-5">
        <div className="flex items-start gap-4">
          <Trusty mood={mood} />
          <div className="min-w-0 flex-1">
            <div className="mb-2 flex flex-wrap gap-1.5">
              {LANGS.map((l) => (
                <button
                  key={l.key}
                  onClick={() => setLang(l.key)}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                    lang === l.key ? "bg-brand text-white" : "border border-line text-ink-soft hover:bg-[#f2f3f8]"
                  }`}
                >
                  {l.label}
                </button>
              ))}
            </div>
            <SpeechBubble>{tip}</SpeechBubble>
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1.3fr_.9fr]">
        <Card className="p-5">
          <div className="space-y-4">
            <div>
              <label htmlFor="nl-title" className="mb-1 block text-xs font-medium text-ink-faint">Product title</label>
              <input id="nl-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Rayon Embroidered Anarkali Kurti" className="w-full rounded-xl border border-line bg-surface px-3 py-2 text-sm" />
            </div>
            <div>
              <label htmlFor="nl-desc" className="mb-1 block text-xs font-medium text-ink-faint">Description <span className="text-ink-faint/70">(what it is, material, fit)</span></label>
              <textarea id="nl-desc" value={desc} onChange={(e) => setDesc(e.target.value)} rows={3} placeholder="Describe the product honestly — buyers who know what they're getting return less." className="w-full resize-y rounded-xl border border-line bg-surface px-3 py-2 text-sm" />
              <p className="mt-1 text-[11px] text-ink-faint">{desc.trim().length}/20 characters minimum</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="nl-colour" className="mb-1 block text-xs font-medium text-ink-faint">Colour</label>
                <input id="nl-colour" value={color} onChange={(e) => setColor(e.target.value)} placeholder="e.g. Navy Blue" className="w-full rounded-xl border border-line bg-surface px-3 py-2 text-sm" />
              </div>
              <div>
                <label htmlFor="nl-pattern" className="mb-1 block text-xs font-medium text-ink-faint">Pattern <span className="text-ink-faint/70">(optional)</span></label>
                <input id="nl-pattern" value={pattern} onChange={(e) => setPattern(e.target.value)} placeholder="e.g. Solid, Printed" className="w-full rounded-xl border border-line bg-surface px-3 py-2 text-sm" />
              </div>
            </div>
            <div>
              <label htmlFor="nl-category" className="mb-1 block text-xs font-medium text-ink-faint">Category</label>
              <select id="nl-category" value={category} onChange={(e) => setCategory(e.target.value)} className="w-full rounded-xl border border-line bg-surface px-3 py-2 text-sm">
                {["apparel", "footwear", "home", "electronics", "beauty", "accessories", "jewellery", "kitchen", "watches", "kids", "stationery", "sports"].map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-ink-faint">Size chart / measurements (inches)</label>
              <div className="overflow-hidden rounded-xl border border-line">
                <div className="grid grid-cols-3 bg-[#f7f7fb] text-[11px] font-medium text-ink-faint">
                  <div className="px-3 py-1.5">Size</div>
                  <div className="border-l border-line px-3 py-1.5">Chest</div>
                  <div className="border-l border-line px-3 py-1.5">Length</div>
                </div>
                {SIZE_ROWS.map((s) => (
                  <div key={s} className="grid grid-cols-3 border-t border-line">
                    <div className="px-3 py-2 text-sm font-medium text-ink">{s}</div>
                    <input type="number" inputMode="decimal" placeholder="—" value={meas[s]?.chest ?? ""} onChange={(e) => setCell(s, "chest", e.target.value)} className="border-l border-line px-3 py-2 text-sm outline-none focus:bg-brand-wash/40" />
                    <input type="number" inputMode="decimal" placeholder="—" value={meas[s]?.length ?? ""} onChange={(e) => setCell(s, "length", e.target.value)} className="border-l border-line px-3 py-2 text-sm outline-none focus:bg-brand-wash/40" />
                  </div>
                ))}
              </div>
            </div>
            <div>
              <label htmlFor="nl-fabric" className="mb-1 block text-xs font-medium text-ink-faint">Fabric / material claim</label>
              <input id="nl-fabric" value={fabric} onChange={(e) => setFabric(e.target.value)} placeholder="e.g. 100% cotton" className="w-full rounded-xl border border-line bg-surface px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-ink-faint">Listing video (canonical reference)</label>
              {/* A real file picker. It previously set a hardcoded "listing_demo.mp4" and
                  reported it as uploaded, which was untrue — this form drafts a listing that
                  does not exist yet, so there is no product to attach a file to. It now
                  records the file the seller actually chose, which is what the
                  mandatory-field gate is checking for, and says plainly that extraction
                  happens when the listing is created. */}
              <input
                id="nl-video"
                type="file"
                accept="video/mp4,video/quicktime,video/x-msvideo,video/x-matroska"
                className="sr-only"
                onChange={(e) => setVideoName(e.target.files?.[0]?.name ?? null)}
              />
              {videoName ? (
                <div className="flex items-center justify-between rounded-xl border border-green/40 bg-green-wash px-3 py-2.5 text-sm">
                  <span className="truncate font-medium text-green">🎥 {videoName} attached</span>
                  <button onClick={() => setVideoName(null)} className="shrink-0 text-xs text-ink-faint hover:text-ink">remove</button>
                </div>
              ) : (
                <label htmlFor="nl-video" className="flex w-full cursor-pointer flex-col items-center gap-1 rounded-xl border border-dashed border-line bg-[#fafafe] px-3 py-5 text-center transition hover:border-brand/50 hover:bg-brand-wash/30">
                  <span className="text-2xl" aria-hidden="true">📹</span>
                  <span className="text-sm font-medium text-ink">Record / upload a 5–15s video</span>
                  <span className="text-[11px] text-ink-faint">Trusty distils it into a quality fingerprint — your proof in a dispute</span>
                </label>
              )}
              <p className="mt-1.5 text-[11px] text-ink-faint">
                The fingerprint is extracted when the listing is created. To watch that
                extraction run live on an existing listing, open the{" "}
                <Link href="/demo" className="font-medium text-brand-ink hover:underline">
                  seller walkthrough
                </Link>
                .
              </p>
            </div>
          </div>
        </Card>

        {/* live gate checklist */}
        <Card className="h-fit p-5">
          <h2 className="font-semibold text-ink">Trusty&apos;s checklist</h2>
          <p className="mt-1 text-sm text-ink-soft">Everything below must be present before the listing can publish.</p>
          {gate ? (
            <>
              <div className="mt-4 space-y-1.5">
                {gate.required.map((f) => {
                  const missing = gate.missing.includes(f);
                  return (
                    <div key={f} className="flex items-center gap-2 text-sm">
                      <span className={missing ? "text-rose" : "text-green"}>{missing ? "○" : "✓"}</span>
                      <span className={missing ? "text-ink-soft" : "text-ink"}>{FIELD_LABEL[f] ?? f}</span>
                    </div>
                  );
                })}
              </div>
              <button
                disabled={!gate.allowed}
                className={`mt-4 w-full rounded-xl px-4 py-2.5 text-sm font-medium transition ${
                  gate.allowed ? "bg-brand text-white hover:bg-brand-ink" : "cursor-not-allowed bg-[#eef0f4] text-ink-faint"
                }`}
              >
                {gate.allowed ? "Publish listing" : `Add ${gate.missing.length} more to publish`}
              </button>
            </>
          ) : (
            <Spinner />
          )}
        </Card>
      </div>
    </Page>
  );
}
