// Display helpers that make the seeded catalog read like a real Meesho listing.
// Derived deterministically from IDs so the same product always looks the same.
import type { Review } from "@/lib/api";

export const SELLER_INFO: Record<string, { name: string; rating: number; followers: string }> = {
  seller_counterfeit: { name: "LUXDEALS_STORE", rating: 3.1, followers: "0.4 lakh" },
  seller_viral: { name: "TRENDYTHREADS", rating: 4.4, followers: "2.3 lakh" },
  seller_kurti: { name: "ETHNICWEAVE", rating: 3.9, followers: "1.9 lakh" },
  seller_shoes: { name: "STEPUP_FOOTWEAR", rating: 4.1, followers: "1.2 lakh" },
  seller_lowrated: { name: "BARGAINBIN", rating: 1.8, followers: "0.2 lakh" },
  seller_fixable: { name: "HOMECOMFORT", rating: 2.4, followers: "0.6 lakh" },
  seller_knockoff: { name: "STREETSTYLE_OPTICS", rating: 4.2, followers: "1.1 lakh" },
};

export function sellerInfo(seller_id: string) {
  return (
    SELLER_INFO[seller_id] ?? {
      name: seller_id.replace(/^seller_/, "").toUpperCase(),
      rating: 4.0,
      followers: "1.0 lakh",
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

export function sizeOptions(category: string): string[] {
  if (category === "footwear") return ["6", "7", "8", "9", "10"];
  if (category === "apparel") return ["S", "M", "L", "XL"];
  return [];
}

// --- product highlights + additional details ---
function colorFor(title: string): string {
  const t = title.toLowerCase();
  for (const c of ["black", "blue", "white", "red", "green", "grey", "gold", "brown", "pink"])
    if (t.includes(c)) return c[0].toUpperCase() + c.slice(1);
  return "As shown";
}

export function highlights(p: { title: string; category: string; fabric_claim: string | null }) {
  const base: [string, string][] = [
    ["Color", colorFor(p.title)],
    ["Fabric", p.fabric_claim ?? (p.category === "footwear" ? "Synthetic" : "Cotton Blend")],
    ["Fit/ Shape", p.category === "footwear" ? "Regular" : "Regular Fit"],
    ["Length", "Regular"],
  ];
  return base;
}

export function additionalDetails(p: { category: string; brand: string }): [string, string][] {
  return [
    ["Occasion", "Casual"],
    ["Pattern", "Solid"],
    ["Net Quantity (N)", "1"],
    ["Brand", p.brand || "Generic"],
    ["Country of Origin", "India"],
  ];
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
