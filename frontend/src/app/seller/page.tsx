"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, type Draft, type Notif, type Product } from "@/lib/api";
import { statusMeta } from "@/lib/decisions";
import { Badge, Button, Card, Empty, Page, SectionTitle, Spinner } from "@/components/ui";
import { Trusty, SpeechBubble } from "@/components/Mascot";

const SELLERS = [
  { id: "seller_fixable", name: "HomeComfort" },
  { id: "seller_scam", name: "MegaDiscount Hub" },
  { id: "seller_kids", name: "LittleStars Kids" },
  { id: "seller_gadgets", name: "TechBazaar" },
];

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
    ok: "அருமை — உங்கள் பட்டியலில் எல்லாம் உள்ளது!",
    size_chart_json: "உண்மையான அளவுகளைச் சேர்க்கவும் (மார்பு, நீளம் cm). சரியான அளவு = குறைவான returns.",
    fabric_claim: "உண்மையான பொருளைச் சொல்லுங்கள் — எ.கா. “100% பருத்தி”.",
    listing_video_path: "பொருளின் குறு வீடியோவைப் பதிவு செய்யுங்கள். தகராறின் போது இதுவே சான்று.",
  },
};


export default function SellerPage() {
  const [seller, setSeller] = useState(SELLERS[0]);
  const [lang, setLang] = useState<Lang>("en");

  // my listings + notifications
  const [products, setProducts] = useState<Product[] | null>(null);
  const [notifs, setNotifs] = useState<Notif[]>([]);
  const [drafts, setDrafts] = useState<Draft[] | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (sid: string) => {
    setProducts(null);
    setDrafts(null);
    const [all, n, d] = await Promise.allSettled([
      api.products(),
      api.notificationsFor("seller", sid),
      api.sellerDrafts(sid),
    ]);
    setProducts(all.status === "fulfilled" ? all.value.filter((p) => p.seller_id === sid) : []);
    setNotifs(n.status === "fulfilled" ? n.value : []);
    setDrafts(d.status === "fulfilled" ? d.value.drafts : []);
  }, []);
  useEffect(() => {
    load(seller.id);
  }, [seller, load]);

  // new-listing gate
  const [category, setCategory] = useState("apparel");
  const [meas, setMeas] = useState<Record<string, { chest: string; length: string }>>({});
  const [fabric, setFabric] = useState("");
  const [videoName, setVideoName] = useState<string | null>(null);
  const [gate, setGate] = useState<{ allowed: boolean; missing: string[]; required: string[] } | null>(null);

  const SIZE_ROWS = ["S", "M", "L", "XL"];
  const hasChart = Object.values(meas).some((m) => m?.chest || m?.length);
  const hasVideo = !!videoName;
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
        size_chart_json: rows.length ? { rows } : null,
        fabric_claim: fabric || null,
        listing_video_path: videoName ? `media/videos/${videoName}` : null,
      })
      .then(setGate)
      .catch(() => setGate(null));
  }, [category, meas, fabric, videoName]);

  const firstMissing = gate?.missing?.[0];
  const tip = useMemo(() => {
    if (!gate) return TIPS[lang].intro;
    if (gate.allowed) return TIPS[lang].ok;
    return TIPS[lang][firstMissing ?? "intro"] ?? TIPS[lang].intro;
  }, [gate, firstMissing, lang]);

  const generateDrafts = async () => {
    setBusy(true);
    try {
      await api.audit(false);
      await load(seller.id);
    } finally {
      setBusy(false);
    }
  };
  const approve = async (id: string) => {
    setBusy(true);
    try {
      await api.approveDraft(id);
      await load(seller.id);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page>
      <SectionTitle eyebrow="Seller studio" title="Your shop" sub="List with confidence, see what needs fixing, and approve AI-drafted corrections." />

      {/* seller switcher */}
      <div className="mb-5 flex flex-wrap gap-2">
        {SELLERS.map((s) => (
          <button
            key={s.id}
            onClick={() => setSeller(s)}
            className={`rounded-xl border px-4 py-2 text-sm transition ${
              seller.id === s.id ? "border-brand bg-brand-wash text-brand-ink" : "border-line bg-surface text-ink-soft hover:bg-[#f2f3f8]"
            }`}
          >
            {s.name}
          </button>
        ))}
      </div>

      {/* notifications */}
      {notifs.length > 0 && (
        <div className="mb-6">
          <h2 className="mb-2 text-sm font-semibold text-ink">🔔 Notifications</h2>
          <div className="space-y-2">
            {notifs.map((n) => (
              <Card key={n.id} className="flex items-start justify-between gap-3 p-3">
                <div>
                  <div className="text-sm font-medium text-ink">{n.subject}</div>
                  <p className="text-xs text-ink-soft">{n.body}</p>
                </div>
                <Badge tone={n.priority === "immediate" ? "rose" : n.priority === "high" ? "amber" : "neutral"}>
                  {n.priority}
                </Badge>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* my listings */}
      <div className="mb-6">
        <h2 className="mb-2 text-sm font-semibold text-ink">My listings</h2>
        {products === null ? (
          <Spinner />
        ) : products.length === 0 ? (
          <Empty>No listings.</Empty>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2">
            {products.map((p) => {
              const sm = statusMeta(p.status);
              return (
                <Card key={p.id} className="flex items-center gap-3 p-3">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={`/products/${p.id}.jpg`} alt="" className="h-12 w-12 rounded-md bg-[#f2f2f7] object-contain" />
                  <div className="min-w-0 flex-1">
                    <Link href={`/product/${p.id}`} className="line-clamp-1 text-sm font-medium text-ink hover:text-brand-ink">
                      {p.title}
                    </Link>
                    <div className="text-xs text-ink-faint">₹{p.price}</div>
                  </div>
                  <Badge tone={sm.tone}>{sm.label}</Badge>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* mascot + new listing + drafts */}
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
        <Card className="p-5">
          <h2 className="font-semibold text-ink">New listing</h2>
          <p className="text-sm text-ink-soft">A listing goes live only when the essentials are present.</p>
          <div className="mt-4 space-y-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-ink-faint">Category</label>
              <select value={category} onChange={(e) => setCategory(e.target.value)} className="w-full rounded-xl border border-line bg-surface px-3 py-2 text-sm">
                {["apparel", "footwear", "home", "electronics", "beauty", "accessories",
                  "jewellery", "kitchen", "watches", "kids", "stationery", "sports"].map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            {/* generic size / measurements form */}
            <div>
              <label className="mb-1.5 block text-xs font-medium text-ink-faint">
                Size chart / measurements (inches)
              </label>
              <div className="overflow-hidden rounded-xl border border-line">
                <div className="grid grid-cols-3 bg-[#f7f7fb] text-[11px] font-medium text-ink-faint">
                  <div className="px-3 py-1.5">Size</div>
                  <div className="border-l border-line px-3 py-1.5">Chest</div>
                  <div className="border-l border-line px-3 py-1.5">Length</div>
                </div>
                {SIZE_ROWS.map((s) => (
                  <div key={s} className="grid grid-cols-3 border-t border-line">
                    <div className="px-3 py-2 text-sm font-medium text-ink">{s}</div>
                    <input
                      type="number"
                      inputMode="decimal"
                      placeholder="—"
                      value={meas[s]?.chest ?? ""}
                      onChange={(e) => setCell(s, "chest", e.target.value)}
                      className="border-l border-line px-3 py-2 text-sm outline-none focus:bg-brand-wash/40"
                    />
                    <input
                      type="number"
                      inputMode="decimal"
                      placeholder="—"
                      value={meas[s]?.length ?? ""}
                      onChange={(e) => setCell(s, "length", e.target.value)}
                      className="border-l border-line px-3 py-2 text-sm outline-none focus:bg-brand-wash/40"
                    />
                  </div>
                ))}
              </div>
              <p className="mt-1 text-[11px] text-ink-faint">Fill any row to add a size chart.</p>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-ink-faint">Fabric / material claim</label>
              <input value={fabric} onChange={(e) => setFabric(e.target.value)} placeholder="e.g. 100% cotton" className="w-full rounded-xl border border-line bg-surface px-3 py-2 text-sm" />
            </div>

            {/* listing-video upload placeholder */}
            <div>
              <label className="mb-1.5 block text-xs font-medium text-ink-faint">Listing video (canonical reference)</label>
              {videoName ? (
                <div className="flex items-center justify-between rounded-xl border border-green/40 bg-green-wash px-3 py-2.5 text-sm">
                  <span className="font-medium text-green">🎥 {videoName} uploaded</span>
                  <button onClick={() => setVideoName(null)} className="text-xs text-ink-faint hover:text-ink">
                    remove
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setVideoName("listing_demo.mp4")}
                  className="flex w-full flex-col items-center gap-1 rounded-xl border border-dashed border-line bg-[#fafafe] px-3 py-5 text-center transition hover:border-brand/50 hover:bg-brand-wash/30"
                >
                  <span className="text-2xl">📹</span>
                  <span className="text-sm font-medium text-ink">Record / upload a 5–15s video</span>
                  <span className="text-[11px] text-ink-faint">Shows the real product — your proof in a dispute</span>
                </button>
              )}
            </div>
          </div>
          <div className="mt-5 border-t border-line pt-4">
            {gate ? (
              <>
                <div className="space-y-1.5">
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
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-ink">Suggested fixes</h2>
            <Badge tone="brand">{drafts?.length ?? 0} pending</Badge>
          </div>
          <p className="text-sm text-ink-soft">Agent 2 drafts a correction from clustered complaints. You approve — one tap.</p>
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
