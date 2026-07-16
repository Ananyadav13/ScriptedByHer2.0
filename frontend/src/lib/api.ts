// Typed client for the Build Trust backend. Shapes mirror backend/app (Phases 2–4).
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
  status: string;
  knockoff_flag: boolean;
  buyer_tip: string | null;
  rating: number;
  rating_count: number;
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
  managerApiAccess: (id: string) =>
    fetch(`${API}/manager/${id}/api-access`, { cache: "no-store" }).then(j<ManagerApiAccess>),
  rotateApiKey: (id: string) =>
    fetch(`${API}/manager/${id}/api-access/rotate`, { method: "POST" }).then(
      j<{ manager_id: string; api_key: string }>,
    ),
  notificationsFor: (audience: string, recipient_id: string) =>
    fetch(`${API}/notifications?audience=${audience}&recipient_id=${recipient_id}`, {
      cache: "no-store",
    }).then(j<Notif[]>),
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
  manager: string | null;
  escalated: boolean;
  issues: Agent2Issue[];
  fit: { runs: string; delta: number; sample: number; note: string } | null;
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

export type ManagerApiAccess = {
  manager_id: string;
  name: string;
  api_key: string | null;
  base_url: string;
  endpoints: { method: string; path: string; desc: string }[];
};
