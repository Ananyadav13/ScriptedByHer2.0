// Typed client for the Build Trust backend. Shapes mirror backend/app (Phases 2–4).
export const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type Review = {
  id: string;
  rating: number;
  text: string;
  reviewer_account_age_days: number;
  has_video: boolean;
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
  status: string;
  knockoff_flag: boolean;
  buyer_tip: string | null;
};

export type ProductDetail = Product & {
  reviews: Review[];
  lock_reason: string | null;
  latest_action: string | null;
  qc_requested: boolean;
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
  sellerDrafts: (seller_id: string) =>
    fetch(`${API}/seller/${seller_id}/drafts`, { cache: "no-store" }).then(j<DraftsResult>),
  approveDraft: (action_id: string) =>
    fetch(`${API}/catalog_actions/${action_id}/approve`, { method: "POST" }).then(
      j<{ action_id: string; product_id: string; applied: Record<string, unknown>; new_status: string }>,
    ),
  listingCheck: (body: {
    category: string;
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
  managerDecide: (manager_id: string, product_id: string, decision: string) =>
    fetch(`${API}/manager/${manager_id}/products/${product_id}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision }),
    }).then(j<{ product_id: string; new_status: string; decision: string }>),
  notifications: () => fetch(`${API}/notifications`, { cache: "no-store" }).then(j<Notification[]>),
  hubs: () => fetch(`${API}/hubs`, { cache: "no-store" }).then(j<Hub[]>),
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
  product_id: string;
  title: string;
  seller_id: string;
  status: string;
  agent_action: string | null;
  evidence: Record<string, unknown> | null;
  acted_at: string | null;
};
export type ManagerQueue = { manager_id: string; queue_size: number; items: ManagerQueueItem[] };

export type Notification = {
  id: string;
  audience: string;
  subject: string;
  body: string;
  priority: string;
  related_id: string | null;
  created_at: string;
};
export type Hub = { id: string; name: string; region: string; score: number; case_count: number };
