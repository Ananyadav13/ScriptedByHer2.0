// Display helpers that make the seeded catalog read like a real Meesho listing.
// Derived deterministically from IDs so the same product always looks the same.
import type { Review } from "@/lib/api";

// Seller storefront card (mirrors Meesho: rating + total ratings + followers + catalogue size).
export const SELLER_INFO: Record<
  string,
  { name: string; rating: number; followers: string; ratings: string; products: number }
> = {
  // scenario sellers
  seller_counterfeit: { name: "LUXDEALS_STORE", rating: 3.1, followers: "0.4 lakh", ratings: "12,480", products: 9 },
  seller_viral: { name: "TRENDYTHREADS", rating: 4.4, followers: "2.3 lakh", ratings: "1,64,902", products: 74 },
  seller_kurti: { name: "ETHNICWEAVE", rating: 3.9, followers: "1.9 lakh", ratings: "88,317", products: 52 },
  seller_shoes: { name: "STEPUP_FOOTWEAR", rating: 4.1, followers: "1.2 lakh", ratings: "60,145", products: 38 },
  seller_lowrated: { name: "BARGAINBIN", rating: 1.8, followers: "0.2 lakh", ratings: "9,204", products: 6 },
  seller_fixable: { name: "HOMECOMFORT", rating: 2.4, followers: "0.6 lakh", ratings: "21,558", products: 17 },
  seller_knockoff: { name: "STREETSTYLE_OPTICS", rating: 4.2, followers: "1.1 lakh", ratings: "48,760", products: 29 },
  // depth sellers
  seller_gadgets: { name: "TECHBAZAAR", rating: 4.6, followers: "3.1 lakh", ratings: "2,04,331", products: 96 },
  seller_beauty: { name: "GLOWUP_COSMETICS", rating: 4.3, followers: "1.6 lakh", ratings: "71,884", products: 44 },
  seller_scam: { name: "MEGADISCOUNT_HUB", rating: 1.4, followers: "0.1 lakh", ratings: "3,117", products: 4 },
  seller_kids: { name: "LITTLESTARS_KIDS", rating: 4.5, followers: "1.4 lakh", ratings: "66,944", products: 61 },
  seller_jewelry: { name: "SHINEON_JEWELS", rating: 2.1, followers: "0.3 lakh", ratings: "14,209", products: 23 },
  seller_mobile: { name: "SMARTWORLD_MOBILES", rating: 3.5, followers: "0.7 lakh", ratings: "33,402", products: 31 },
  seller_bags: { name: "AARAALS_COLLECTION", rating: 4.0, followers: "0.4 lakh", ratings: "1,38,194", products: 150 },
};

export function sellerInfo(seller_id: string) {
  return (
    SELLER_INFO[seller_id] ?? {
      name: seller_id.replace(/^seller_/, "").toUpperCase(),
      rating: 4.0,
      followers: "1.0 lakh",
      ratings: "10,000",
      products: 20,
    }
  );
}

// --- size charts (Meesho "Product Dimensions", inches) ---
export type SizeRow = { size: string; length: number; hip?: number; waist?: number; bust?: number; foot?: number };

const APPAREL_CHART: SizeRow[] = [
  { size: "S", length: 20, hip: 38, waist: 28, bust: 34 },
  { size: "M", length: 20, hip: 40, waist: 30, bust: 36 },
  { size: "L", length: 21, hip: 42, waist: 32, bust: 38 },
  { size: "XL", length: 21, hip: 44, waist: 34, bust: 40 },
  { size: "XXL", length: 22, hip: 46, waist: 36, bust: 42 },
];
const FOOTWEAR_CHART: SizeRow[] = [
  { size: "6", length: 0, foot: 9.6 },
  { size: "7", length: 0, foot: 9.9 },
  { size: "8", length: 0, foot: 10.2 },
  { size: "9", length: 0, foot: 10.6 },
  { size: "10", length: 0, foot: 11.0 },
];

export function sizeChart(category: string): { rows: SizeRow[]; kind: "apparel" | "footwear" } | null {
  if (category === "apparel") return { rows: APPAREL_CHART, kind: "apparel" };
  if (category === "footwear") return { rows: FOOTWEAR_CHART, kind: "footwear" };
  return null;
}

// Categories sold as one size that STILL need measurements — a bag has no S/M/L, but the
// buyer needs L x W x H to know what turns up. Mirrors backend `mandatory_fields._DIMENSIONED`.
const FREE_SIZE_CATEGORIES = new Set(["accessories"]);

export function sizeOptions(category: string): string[] {
  if (category === "footwear") return ["6", "7", "8", "9", "10"];
  if (category === "apparel") return ["S", "M", "L", "XL", "XXL"];
  if (FREE_SIZE_CATEGORIES.has(category)) return ["Free Size"];
  return [];
}

/** A size label that carries no measurement is a placeholder, not a spec.
 *  Mirrors backend `mandatory_fields._is_vacuous_size_chart`. */
const VACUOUS_LABELS = new Set(["free size", "one size", "standard", "regular", "default", "n/a"]);

export function hasRealMeasurements(chart: Record<string, string> | null | undefined): boolean {
  if (!chart) return false;
  const entries = Object.entries(chart);
  if (entries.length === 0) return false;
  return entries.some(
    ([label, value]) => /\d/.test(String(value)) || !VACUOUS_LABELS.has(String(label).trim().toLowerCase()),
  );
}

export type SizeSpec =
  | { kind: "apparel" | "footwear"; rows: SizeRow[] }
  | { kind: "dimensions"; rows: [string, string][] }
  | { kind: "missing" }
  | null;

/** What the size section should render for THIS product, from its real data.
 *  `missing` means the seller shipped a placeholder ("Free Size" and nothing else) — we say
 *  so out loud rather than quietly rendering nothing. */
export function sizeSpec(p: {
  category: string;
  size_chart_json: Record<string, string> | null;
}): SizeSpec {
  if (p.category === "apparel") return { kind: "apparel", rows: APPAREL_CHART };
  if (p.category === "footwear") return { kind: "footwear", rows: FOOTWEAR_CHART };
  if (!FREE_SIZE_CATEGORIES.has(p.category)) return null;
  if (!hasRealMeasurements(p.size_chart_json)) return { kind: "missing" };
  return { kind: "dimensions", rows: Object.entries(p.size_chart_json!) };
}

// --- product highlights + additional details ---
function colorFor(title: string): string {
  const t = title.toLowerCase();
  for (const c of ["black", "blue", "white", "red", "green", "grey", "gold", "brown", "pink"])
    if (t.includes(c)) return c[0].toUpperCase() + c.slice(1);
  return "As shown";
}

// Meesho shows a different highlight set per category — a bag lists Material/Net Quantity,
// jewellery lists Stone Type/Plating. A shared Fabric/Fit block told a ceramic mug it was
// "Cotton Blend, Regular Fit", so the fields are chosen per category here.
type Prod = { title: string; category: string; brand: string; fabric_claim: string | null };

export function highlights(p: Prod): [string, string][] {
  const color: [string, string] = ["Color", colorFor(p.title)];
  switch (p.category) {
    case "apparel":
      return [
        ["Occasion", "Casual"],
        color,
        ["Fabric", p.fabric_claim ?? "Cotton Blend"],
        ["Fit/ Shape", "Regular Fit"],
      ];
    case "footwear":
      return [color, ["Material", p.fabric_claim ?? "Synthetic"], ["Fit/ Shape", "Regular"], ["Sole", "EVA"]];
    case "accessories":
      return [["Material", p.fabric_claim ?? "PU Leather"], color, ["Net Quantity (N)", "1"], ["Occasion", "Casual"]];
    case "beauty":
      return [["Type", "Skincare"], color, ["Net Quantity (N)", "1"], ["Preference", "Dermatologist Tested"]];
    case "electronics":
      return [color, ["Material", "ABS Plastic"], ["Warranty", "6 Months"], ["Net Quantity (N)", "1"]];
    case "home":
      return [["Material", p.fabric_claim ?? "Cotton"], color, ["Net Quantity (N)", "1"], ["Care", "Machine Wash"]];
    case "watches":
      return [["Dial Color", colorFor(p.title)], ["Strap Material", "Stainless Steel"], ["Movement", "Quartz"], ["Display", "Analog"]];
    default:
      return [color, ["Material", p.fabric_claim ?? "Mixed"], ["Net Quantity (N)", "1"], ["Occasion", "Casual"]];
  }
}

export function additionalDetails(p: Prod): [string, string][] {
  const common: [string, string][] = [
    ["Brand", p.brand || "Generic"],
    ["Country of Origin", "India"],
  ];
  switch (p.category) {
    case "apparel":
      return [["Pattern", "Solid"], ["Sleeve Length", "Short Sleeve"], ["Net Quantity (N)", "1"], ...common];
    case "accessories":
      return [["Pattern", "Solid"], ["Closure", "Zip"], ["Net Quantity (N)", "1"], ...common];
    case "beauty":
      return [["Skin Type", "All"], ["Shelf Life", "24 Months"], ["Net Quantity (N)", "1"], ...common];
    case "electronics":
      return [["Model", "Universal"], ["Warranty Type", "Manufacturer"], ["Net Quantity (N)", "1"], ...common];
    default:
      return [["Occasion", "Casual"], ["Pattern", "Solid"], ["Net Quantity (N)", "1"], ...common];
  }
}

// --- reviews: names, dates, helpful counts, photos, rating breakdown ---
const NAMES = [
  "Saransh Kumar", "Priya Sharma", "Anjali Verma", "Rahul Singh", "Meesho User",
  "Pooja Yadav", "Amit Patel", "Sneha Reddy", "Vikram Das", "Neha Gupta",
  "Karan Mehta", "Divya Nair", "Ravi Kumar", "Simran Kaur", "Aditya Rao",
];

function hash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

export type ReviewDisplay = {
  name: string;
  date: string;
  helpful: number;
  verdictLabel: string;
  photos: number;
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function reviewDisplay(r: Review, productId: string): ReviewDisplay {
  const h = hash(r.id + productId);
  const name = NAMES[h % NAMES.length];
  // Use the REAL review date so a coordinated burst reads as same-day/recent, not spread out.
  let date: string;
  if (r.created_at) {
    const d = new Date(r.created_at);
    date = `${String(d.getDate()).padStart(2, "0")} ${MONTHS[d.getMonth()]}, ${d.getFullYear()}`;
  } else {
    date = `${String((h % 27) + 1).padStart(2, "0")} ${MONTHS[h % 12]}, ${2025 + ((h >> 3) % 2)}`;
  }
  const helpful = (h % 60) + (r.rating >= 4 ? 8 : 1);
  const verdictLabel =
    r.rating >= 5 ? "Very Good" : r.rating === 4 ? "Good" : r.rating === 3 ? "Ok-Ok" : r.rating === 2 ? "Bad" : "Very Bad";
  const photos = r.has_video ? 2 : h % 3 === 0 ? 1 : 0;
  return { name, date, helpful, verdictLabel, photos };
}

// star-rating -> tone (matches Meesho: green for good, amber mid, red for bad)
export function ratingTone(rating: number): { bar: string; badge: string } {
  if (rating >= 5) return { bar: "#16794c", badge: "#16794c" };
  if (rating === 4) return { bar: "#4caf50", badge: "#4caf50" };
  if (rating === 3) return { bar: "#f0ad4e", badge: "#e08a1e" };
  if (rating === 2) return { bar: "#f0752b", badge: "#e0611a" };
  return { bar: "#e53935", badge: "#d32f2f" };
}

export function ratingSummary(reviews: Review[]) {
  const buckets = [0, 0, 0, 0, 0]; // index0=1star ... index4=5star
  reviews.forEach((r) => {
    const i = Math.min(5, Math.max(1, r.rating)) - 1;
    buckets[i]++;
  });
  const total = reviews.length;
  const avg = total ? reviews.reduce((s, r) => s + r.rating, 0) / total : 0;
  const withPhotos = reviews.filter((r) => r.has_video).length;
  return {
    avg: Math.round(avg * 10) / 10,
    total,
    withPhotos,
    rows: [
      { label: "Very Good", count: buckets[4], color: "#16794c" },
      { label: "Good", count: buckets[3], color: "#4caf50" },
      { label: "Ok-Ok", count: buckets[2], color: "#f0ad4e" },
      { label: "Bad", count: buckets[1], color: "#f0752b" },
      { label: "Very Bad", count: buckets[0], color: "#e53935" },
    ],
  };
}

export function payLater(price: number): number {
  return Math.max(1, Math.round(price * 0.88));
}
