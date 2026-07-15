"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { api, type Draft } from "@/lib/api";
import { Badge, Button, Card, Empty, Page, SectionTitle, Spinner } from "@/components/ui";
import { Trusty, SpeechBubble } from "@/components/Mascot";

const SELLER = "seller_fixable";

type Lang = "en" | "hi" | "ta";
const LANGS: { key: Lang; label: string }[] = [
  { key: "en", label: "English" },
  { key: "hi", label: "हिंदी" },
  { key: "ta", label: "தமிழ்" },
];

const FIELD_LABEL: Record<string, string> = {
  size_chart_json: "Size chart / measurements",
  fabric_claim: "Fabric / material",
  listing_video_path: "Listing video",
};

const TIPS: Record<Lang, Record<string, string>> = {
  en: {
    intro: "Hi! I'm Trusty. I'll help you list a product buyers can trust. Three things keep your listing safe.",
    ok: "Perfect — your listing has everything buyers need. This builds trust and cuts returns!",
    size_chart_json: "Add real measurements (chest, length in cm). Accurate sizes mean fewer returns.",
    fabric_claim: "Tell buyers the true material — e.g. “100% cotton”. Honest claims avoid disputes.",
    listing_video_path: "Record a short video of the actual product. It becomes your proof if a dispute happens.",
  },
  hi: {
    intro: "नमस्ते! मैं Trusty हूँ। ऐसा प्रोडक्ट लिस्ट करें जिस पर खरीदार भरोसा करें। तीन चीज़ें ज़रूरी हैं।",
    ok: "बढ़िया — आपकी लिस्टिंग में सब कुछ है। इससे भरोसा बढ़ता है और रिटर्न कम होते हैं!",
    size_chart_json: "असली माप जोड़ें (छाती, लंबाई cm में)। सही साइज़ = कम रिटर्न।",
    fabric_claim: "सही मटीरियल बताएं — जैसे “100% कॉटन”। सच्चा दावा विवाद से बचाता है।",
    listing_video_path: "प्रोडक्ट का छोटा वीडियो बनाएं। विवाद होने पर यही आपका सबूत है।",
  },
  ta: {
    intro: "வணக்கம்! நான் Trusty. வாங்குபவர்கள் நம்பும் பொருளை பட்டியலிட உதவுவேன். மூன்று விஷயங்கள் முக்கியம்.",
    ok: "அருமை — உங்கள் பட்டியலில் எல்லாம் உள்ளது. இது நம்பிக்கையை அதிகரிக்கும், திரும்பப்பெறுதலைக் குறைக்கும்!",
    size_chart_json: "உண்மையான அளவுகளைச் சேர்க்கவும் (மார்பு, நீளம் cm). சரியான அளவு = குறைவான returns.",
    fabric_claim: "உண்மையான பொருளைச் சொல்லுங்கள் — எ.கா. “100% பருத்தி”. நேர்மை தகராறைத் தவிர்க்கும்.",
    listing_video_path: "பொருளின் குறு வீடியோவைப் பதிவு செய்யுங்கள். தகராறின் போது இதுவே சான்று.",
  },
};

const SAMPLE_CHART = [
  { size: "single", chest: 90, length: 220 },
  { size: "double", chest: 150, length: 230 },
];

export default function SellerPage() {
  const [lang, setLang] = useState<Lang>("en");

  // ---- new-listing gate ----
  const [category, setCategory] = useState("apparel");
  const [hasChart, setHasChart] = useState(false);
  const [fabric, setFabric] = useState("");
  const [hasVideo, setHasVideo] = useState(false);
  const [gate, setGate] = useState<{ allowed: boolean; missing: string[]; required: string[] } | null>(
    null,
  );

  useEffect(() => {
    const body = {
      category,
      size_chart_json: hasChart ? { rows: SAMPLE_CHART } : null,
      fabric_claim: fabric || null,
      listing_video_path: hasVideo ? "media/videos/listing_demo.mp4" : null,
    };
    api.listingCheck(body).then(setGate).catch(() => setGate(null));
  }, [category, hasChart, fabric, hasVideo]);

  const firstMissing = gate?.missing?.[0];
  const tip = useMemo(() => {
    if (!gate) return TIPS[lang].intro;
    if (gate.allowed) return TIPS[lang].ok;
    return TIPS[lang][firstMissing ?? "intro"] ?? TIPS[lang].intro;
  }, [gate, firstMissing, lang]);

  // ---- fix drafts ----
  const [drafts, setDrafts] = useState<Draft[] | null>(null);
  const [busy, setBusy] = useState(false);

  const loadDrafts = useCallback(async () => {
    try {
      const r = await api.sellerDrafts(SELLER);
      setDrafts(r.drafts);
    } catch {
      setDrafts([]);
    }
  }, []);
  useEffect(() => {
    loadDrafts();
  }, [loadDrafts]);

  const generateDrafts = async () => {
    setBusy(true);
    try {
      await api.audit(false); // deterministic sweep creates the fix draft
      await loadDrafts();
    } finally {
      setBusy(false);
    }
  };

  const approve = async (id: string) => {
    setBusy(true);
    try {
      await api.approveDraft(id);
      await loadDrafts();
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page>
      <SectionTitle
        eyebrow="Seller studio"
        title="List with confidence"
        sub="Trusty guides you through every field buyers need — in your language."
      />

      {/* Mascot + language */}
      <Card className="mb-6 p-5">
        <div className="flex items-start gap-4">
          <Trusty mood={gate?.allowed ? "cheer" : firstMissing ? "think" : "happy"} />
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

      <div className="grid gap-6 lg:grid-cols-2">
        {/* New listing gate */}
        <Card className="p-5">
          <h2 className="font-semibold text-ink">New listing</h2>
          <p className="text-sm text-ink-soft">A listing goes live only when the essentials are present.</p>

          <div className="mt-4 space-y-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-ink-faint">Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full rounded-xl border border-line bg-surface px-3 py-2 text-sm"
              >
                {["apparel", "footwear", "home", "electronics"].map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <label className="flex items-center justify-between rounded-xl border border-line px-3 py-2.5 text-sm">
              <span className="text-ink">Size chart / measurements</span>
              <input type="checkbox" checked={hasChart} onChange={(e) => setHasChart(e.target.checked)} className="h-4 w-4 accent-[var(--brand)]" />
            </label>

            <div>
              <label className="mb-1 block text-xs font-medium text-ink-faint">Fabric / material claim</label>
              <input
                value={fabric}
                onChange={(e) => setFabric(e.target.value)}
                placeholder="e.g. 100% cotton"
                className="w-full rounded-xl border border-line bg-surface px-3 py-2 text-sm"
              />
            </div>

            <label className="flex items-center justify-between rounded-xl border border-line px-3 py-2.5 text-sm">
              <span className="text-ink">🎥 Listing video recorded</span>
              <input type="checkbox" checked={hasVideo} onChange={(e) => setHasVideo(e.target.checked)} className="h-4 w-4 accent-[var(--brand)]" />
            </label>
          </div>

          {/* gate result */}
          <div className="mt-5 border-t border-line pt-4">
            {gate ? (
              <>
                <div className="space-y-1.5">
                  {gate.required.map((f) => {
                    const missing = gate.missing.includes(f);
                    return (
                      <div key={f} className="flex items-center gap-2 text-sm">
                        <span className={missing ? "text-rose" : "text-green"}>{missing ? "○" : "✓"}</span>
                        <span className={missing ? "text-ink-soft" : "text-ink line-through-none"}>
                          {FIELD_LABEL[f] ?? f}
                        </span>
                      </div>
                    );
                  })}
                </div>
                <button
                  disabled={!gate.allowed}
                  className={`mt-4 w-full rounded-xl px-4 py-2.5 text-sm font-medium transition ${
                    gate.allowed
                      ? "bg-brand text-white hover:bg-brand-ink"
                      : "cursor-not-allowed bg-[#eef0f4] text-ink-faint"
                  }`}
                >
                  {gate.allowed ? "Publish listing" : `Add ${gate.missing.length} more to publish`}
                </button>
              </>
            ) : (
              <Spinner />
            )}
          </div>
        </Card>

        {/* Fix drafts */}
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-ink">Suggested fixes</h2>
            <Badge tone="brand">{drafts?.length ?? 0} pending</Badge>
          </div>
          <p className="text-sm text-ink-soft">
            Agent 2 drafts a correction from clustered complaints. You approve — one tap.
          </p>

          <div className="mt-4 space-y-3">
            {drafts === null && <Spinner />}
            {drafts !== null && drafts.length === 0 && (
              <Empty>
                <p>No pending drafts.</p>
                <Button variant="secondary" size="sm" className="mt-3" disabled={busy} onClick={generateDrafts}>
                  {busy ? <Spinner /> : "Run a catalog audit to generate one"}
                </Button>
              </Empty>
            )}
            {drafts?.map((d) => (
              <div key={d.id} className="rounded-xl border border-line p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-ink">{FIELD_LABEL[d.field ?? ""] ?? d.field}</span>
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
              </div>
            ))}
          </div>
        </Card>
      </div>
    </Page>
  );
}

function fmt(v: unknown): string {
  if (v == null) return "—";
  if (typeof v === "string") return v;
  return JSON.stringify(v, null, 1).replace(/[{}"]/g, "").trim() || "—";
}
