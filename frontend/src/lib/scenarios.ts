// The 6 judge-facing golden paths. Each deep-links into the right flow with a seeded entity.
export type Scenario = {
  key: string;
  emoji: string;
  tag: string;
  title: string;
  blurb: string;
  href: string;
  cta: string;
  tone: "rose" | "green" | "amber" | "teal" | "brand";
};

export const SCENARIOS: Scenario[] = [
  {
    key: "counterfeit",
    emoji: "⌚",
    tag: "Agent 1 · counterfeit defense",
    title: "Counterfeit Rolex",
    blurb: "A ₹599 “Rolex” with a burst of 5★ reviews from 2-day-old accounts. Watch the agent lock it.",
    href: "/product/prod_counterfeit_rolex",
    cta: "Try counterfeit",
    tone: "rose",
  },
  {
    key: "viral",
    emoji: "🔥",
    tag: "Agent 1 · fairness",
    title: "Honest viral seller",
    blurb: "A cheap product going viral — but every reviewer is a real, aged account. It must NOT be punished.",
    href: "/product/prod_viral_honest",
    cta: "Try honest viral",
    tone: "green",
  },
  {
    key: "fabric",
    emoji: "🧵",
    tag: "Agent 1 · vision (advisory)",
    title: "Fabric mismatch",
    blurb: "Buyer says the “pure cotton” kurti feels synthetic. The agent weighs media evidence and recommends a review.",
    href: "/product/prod_fabric_kurti",
    cta: "Try fabric dispute",
    tone: "teal",
  },
  {
    key: "size",
    emoji: "📏",
    tag: "Agent 2 · fit prediction",
    title: "Size drift",
    blurb: "This brand runs small. The cart auto-adjusts the buyer's size from 214 real returns — no LLM needed.",
    href: "/cart",
    cta: "Try size adjust",
    tone: "brand",
  },
  {
    key: "dispute",
    emoji: "📦",
    tag: "Agent 1 · disputes",
    title: "Delivery dispute",
    blurb: "One OTP scanned for 3 items via a flagged hub. Two independent signals → an instant, fair refund.",
    href: "/product/prod_size_shoes?order=order_otp_dispute",
    cta: "Try refund",
    tone: "amber",
  },
  {
    key: "audit",
    emoji: "🗂️",
    tag: "Agent 2 · catalog integrity",
    title: "Catalog audit",
    blurb: "Sweep the catalog: fraud suspended, fixable listings drafted a fix, delivery faults spared the seller.",
    href: "/admin",
    cta: "Try audit",
    tone: "brand",
  },
];
