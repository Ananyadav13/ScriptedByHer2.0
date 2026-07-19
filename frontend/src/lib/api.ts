// Typed client for the Build Trust backend. Shapes mirror the Pydantic DTOs in backend/app/schemas.py.
export const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type Review = {
  id: string;
  rating: number;
  text: string;
  reviewer_account_age_days: number;
  has_video: boolean;
  created_at: string | null;
};

export type Product = {
  id: string;
  seller_id: string;
  title: string;
  brand: string;
  category: string;
  price: number;
  mrp: number;
  images: string[];
  fabric_claim: string | null;
  size_chart_json: Record<string, string> | null;
  status: string;
  knockoff_flag: boolean;
  buyer_tip: string | null;
  rating: number;
  rating_count: number;
  review_count: number;
};

export type Variant = {
  id: string;
  name: string;
  colour: string | null;
  is_listing_reference: boolean;
};

export type ProductDetail = Product & {
  reviews: Review[];
  variants: Variant[];
  lock_reason: string | null;
  latest_action: string | null;
  qc_requested: boolean;
};

export type OrderReaction = {
  route: string;
  tone: "amber" | "teal" | "brand" | "neutral";
  label: string;
};
export type BuyerOrder = {
  id: string;
  product_id: string;
  product_title: string;
  price: number | null;
  variant: string | null;
  delivered_at: string | null;
  status: string;
  claim_type: string | null;
  hub_name: string | null;
  dispute_available: boolean;
  reaction: OrderReaction;
};
export type ClaimContext = {
  claim_count: number;
  is_serial_claimer: boolean;
  note: string;
};
export type BuyerOrders = {
  buyer_id: string;
  claim_context: ClaimContext;
  order_count: number;
  orders: BuyerOrder[];
};
export type BuyerSummary = {
  id: string;
  name: string;
  claim_count: number;
  is_serial_claimer: boolean;
  order_count: number;
};

// shape of the check_media_evidence tool result (rendered as a visual card in the trace)
export type MediaEvidence = {
  available?: boolean;
  product_id?: string;
  claimed_material?: string;
  variant?: { cross_variant?: boolean; listing_video_variant?: string | null; ordered_variant?: string | null; reason?: string };
  reference_frame_urls?: string[];
  evidence_frame_urls?: string[];
  reference_summary?: string;
  observed_summary?: string;
  reference_attributes?: Record<string, string>;
  observed_attributes?: Record<string, string>;
  compared_attributes?: string[];
  diverged_attributes?: string[];
  ignored_attributes?: string[];
  mismatch?: boolean;
  colour_note?: string | null;
  confidence?: number;
  reason?: string;
};

export type Verdict = {
  decision: string;
  confidence: number;
  evidence: string[];
  action: string;
  buyer_explanation: string;
  recommended_action?: string;
  suggested_remedy?: string;
};

export type Investigation = {
  id: string;
  product_id: string | null;
  order_id: string | null;
  trigger: string;
  status: string;
  tool_calls_log: unknown[];
  verdict: Verdict | null;
};

// SSE event union streamed from GET /events/{id}
export type TraceEvent =
  | { type: "status"; status: string }
  | { type: "tool_call"; name: string; args: Record<string, unknown> }
  | { type: "tool_result"; name: string; result: unknown }
  | ({ type: "verdict" } & Verdict)
  | { type: "error"; error: string }
  | { type: "done" }
  | { type: "closed" };

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  products: () => fetch(`${API}/products`, { cache: "no-store" }).then(j<Product[]>),
  product: (id: string) =>
    fetch(`${API}/products/${id}`, { cache: "no-store" }).then(j<ProductDetail>),
  investigate: (body: { product_id?: string; trigger?: string; order_id?: string }) =>
    fetch(`${API}/investigate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(j<{ investigation_id: string; status: string }>),
  dispute: (body: { order_id: string; claim_type: string; evidence_paths?: string[] }) =>
    fetch(`${API}/dispute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(j<{ investigation_id: string; status: string; order_id: string }>),
  investigation: (id: string) =>
    fetch(`${API}/investigations/${id}`, { cache: "no-store" }).then(j<Investigation>),
  investigations: (limit = 25) =>
    fetch(`${API}/investigations?limit=${limit}`, { cache: "no-store" }).then(j<InvestigationList>),
  agent1Evidence: (opts: { product_id?: string; order_id?: string }) => {
    const q = opts.product_id ? `product_id=${opts.product_id}` : `order_id=${opts.order_id}`;
    return fetch(`${API}/agent1/evidence?${q}`, { cache: "no-store" }).then(j<Agent1Evidence>);
  },
  fit: (buyer_id: string, product_id: string) =>
    fetch(`${API}/fit?buyer_id=${buyer_id}&product_id=${product_id}`, { cache: "no-store" }).then(
      j<FitResult>,
    ),
  audit: (cluster = false) =>
    fetch(`${API}/audit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cluster }),
    }).then(j<AuditResult>),
  adminActions: (limit = 100) =>
    fetch(`${API}/admin/actions?limit=${limit}`, { cache: "no-store" }).then(j<AdminActions>),
  agent2Findings: () =>
    fetch(`${API}/agent2/findings`, { cache: "no-store" }).then(j<Agent2Findings>),
  sellerDrafts: (seller_id: string) =>
    fetch(`${API}/seller/${seller_id}/drafts`, { cache: "no-store" }).then(j<DraftsResult>),
  approveDraft: (action_id: string) =>
    fetch(`${API}/catalog_actions/${action_id}/approve`, { method: "POST" }).then(
      j<{ action_id: string; product_id: string; applied: Record<string, unknown>; new_status: string }>,
    ),
  listingCheck: (body: {
    category: string;
    title?: string | null;
    description?: string | null;
    color?: string | null;
    size_chart_json?: unknown;
    fabric_claim?: string | null;
    listing_video_path?: string | null;
  }) =>
    fetch(`${API}/listing/check`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(j<{ allowed: boolean; missing: string[]; required: string[] }>),
  managers: () => fetch(`${API}/managers`, { cache: "no-store" }).then(j<ManagerInfo[]>),
  managerQueue: (id: string) =>
    fetch(`${API}/manager/${id}/queue`, { cache: "no-store" }).then(j<ManagerQueue>),
  managerSellers: (id: string) =>
    fetch(`${API}/manager/${id}/sellers`, { cache: "no-store" }).then(j<ManagerSellers>),
  notificationsFor: (audience: string, recipient_id: string) =>
    fetch(`${API}/notifications?audience=${audience}&recipient_id=${recipient_id}`, {
      cache: "no-store",
    }).then(j<Notif[]>),
  managerDecide: (manager_id: string, product_id: string, decision: string, comment?: string) =>
    fetch(`${API}/manager/${manager_id}/products/${product_id}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, comment }),
    }).then(j<{ product_id: string; new_status: string; decision: string; buyers_notified: number }>),
  managerDecideDispute: (manager_id: string, order_id: string, decision: string, comment?: string) =>
    fetch(`${API}/manager/${manager_id}/disputes/${order_id}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, comment }),
    }).then(j<{ order_id: string; new_status: string; decision: string }>),
  /** Place one order. Checkout calls this per cart line so what you just bought shows up
   *  in My Orders and can actually be disputed. */
  placeOrder: (product_id: string, items_count = 1, buyer_id = "buyer_normal") =>
    fetch(`${API}/orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ buyer_id, product_id, items_count }),
    }).then(j<BuyerOrder>),
  buyers: () => fetch(`${API}/buyers`, { cache: "no-store" }).then(j<BuyerSummary[]>),
  buyerOrders: (buyer_id: string) =>
    fetch(`${API}/buyers/${buyer_id}/orders`, { cache: "no-store" }).then(j<BuyerOrders>),

  /** Upload a listing video and extract its quality fingerprint live (OpenCV keyframes
   *  -> one multimodal read). Surfaces the server's own message on failure, because
   *  "quota exhausted, previous fingerprint restored" is information a presenter needs. */
  uploadListingVideo: async (product_id: string, file: File): Promise<LiveFingerprint> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API}/products/${product_id}/listing-video`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => null);
      throw new Error(detail?.detail ?? `Upload failed (${res.status})`);
    }
    return res.json() as Promise<LiveFingerprint>;
  },
  resetListingVideo: (product_id: string) =>
    fetch(`${API}/products/${product_id}/listing-video/reset`, { method: "POST" })
      .then(j<{ product_id: string; restored: boolean }>),

  /** Remove one statistically dead listing from the catalogue. The server refuses (409)
   *  unless the product actually trips a delisting tier, so the error text is worth
   *  surfacing rather than swallowing. */
  delistProduct: async (product_id: string) => {
    const res = await fetch(`${API}/products/${product_id}/delist`, { method: "POST" });
    if (!res.ok) {
      const detail = await res.json().catch(() => null);
      throw new Error(detail?.detail ?? `Removal failed (${res.status})`);
    }
    return res.json() as Promise<{
      product_id: string; new_status: string; applied: boolean;
      action?: string; tier?: string; reason?: string;
    }>;
  },
};

export type QualityAttributes = Record<string, string>;
export type LiveFingerprint = {
  product_id: string;
  product_title: string;
  filename: string;
  size_bytes: number;
  frames_sampled: number;
  attributes: QualityAttributes;
  summary: string;
  confidence: number;
  notes: string[];
  replaced_seeded_fingerprint: boolean;
  extracted_live: boolean;
};

export type FitResult = {
  original: string;
  adjusted: string;
  drift_delta: number;
  sample_size: number;
  source: string;
  explanation: string;
};

export type AuditItem = {
  product_id: string;
  applied: string;
  reason?: string;
  tier_label?: string;
  dominant_label?: string;
};
export type AuditResult = {
  summary: Record<string, number>;
  evaluated: number;
  items: AuditItem[];
};

export type AdminAction = {
  id: string;
  product_id: string;
  product_title: string | null;
  seller_id: string | null;
  action: string;
  tier: string | null;
  decision: string | null;
  reason: string | null;
  seller_approved: boolean;
  created_at: string;
};
export type AdminActions = { count: number; actions: AdminAction[] };

export type Draft = {
  id: string;
  product_id: string;
  field: string | null;
  cluster: string | null;
  summary: string | null;
  before: unknown;
  after: unknown;
  rationale: string | null;
  created_at: string;
};
export type DraftsResult = { seller_id: string; count: number; drafts: Draft[] };

export type ManagerInfo = { id: string; name: string; seller_count: number };
export type ManagerQueueItem = {
  kind?: "listing" | "dispute";
  product_id: string;
  title: string;
  seller_id: string | null;
  status: string;
  agent_action?: string | null;
  evidence: Record<string, unknown> | null;
  acted_at: string | null;
  // dispute-only fields
  order_id?: string;
  claim_type?: string | null;
  buyer_id?: string;
  buyer_claim_count?: number;
};
export type ManagerQueue = { manager_id: string; queue_size: number; items: ManagerQueueItem[] };


export type Agent2Issue = {
  type: string;
  label: string;
  severity: "info" | "warn";
  agreement?: number;
  complaints?: number;
  detail?: string;
};
export type Agent2Product = {
  product_id: string;
  title: string;
  seller_id: string;
  category: string;
  status: string;
  rating: number | null;
  review_count: number;
  ratings_total: number;
  seller_name: string | null;
  manager: string | null;
  escalated: boolean;
  issues: Agent2Issue[];
  fit: { runs: string; delta: number; sample: number; note: string } | null;
  // the tiered delisting verdict — "this listing no longer works for buyers"
  delist: boolean;
  tier_label: string | null;
  delist_reason: string | null;
  dominant_complaint: string | null;
  already_removed: boolean;
  recommended_action: string;
};
export type Agent2Findings = {
  summary: Record<string, number>;
  count: number;
  products: Agent2Product[];
};

export type EvidenceSignal = { label: string; flag: boolean; detail: string };
export type Agent1Evidence = {
  product_id: string;
  order_id: string | null;
  risk_flags: number;
  tools: { tool: string; signals: EvidenceSignal[] }[];
};
export type InvestigationSummary = {
  id: string;
  product_id: string | null;
  product_title: string | null;
  seller_id: string | null;
  seller_name: string | null;
  manager: string | null;
  order_id: string | null;
  trigger: string;
  status: string;
  tool_count: number;
  decision: string | null;
  action: string | null;
  confidence: number | null;
  evidence: string[];
  buyer_explanation: string | null;
  created_at: string;
};
export type InvestigationList = { count: number; investigations: InvestigationSummary[] };

export type Notif = {
  id: string;
  audience: string;
  recipient_id: string | null;
  subject: string;
  body: string;
  priority: string;
  related_id: string | null;
  created_at: string;
};

export type ManagerSellerProduct = {
  product_id: string;
  title: string;
  status: string;
  rating: number | null;
  review_count: number;
  complaint: { label: string; agreement: number; count: number } | null;
  needs_action: boolean;
};
export type ManagerSeller = {
  seller_id: string;
  name: string;
  rating: number;
  trust_flags: string[];
  case_count: number;
  account_age_days: number | null;
  banned: boolean;
  product_count: number;
  flagged_count: number;
  products: ManagerSellerProduct[];
};
export type ManagerSellers = {
  manager_id: string;
  name: string;
  seller_count: number;
  sellers: ManagerSeller[];
};
