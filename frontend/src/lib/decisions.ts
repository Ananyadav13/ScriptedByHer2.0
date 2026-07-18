// Maps backend enum strings -> human labels + tone. Single source for the UI.
export type Tone = "green" | "rose" | "amber" | "brand" | "teal" | "neutral";

type Meta = { label: string; tone: Tone };

export const DECISION_META: Record<string, Meta> = {
  counterfeit_lock: { label: "Counterfeit — listing locked", tone: "rose" },
  request_qc_video: { label: "Quality-check video requested", tone: "amber" },
  relabel_required: { label: "Relabel required", tone: "amber" },
  notify_only: { label: "Seller notified", tone: "amber" },
  hold_pending_fix: { label: "Held pending fix", tone: "amber" },
  ban: { label: "Seller banned", tone: "rose" },
  refund_fast_track: { label: "Refund — fast-tracked", tone: "green" },
  standard_process: { label: "Standard process", tone: "neutral" },
  manual_review: { label: "Routed to manual review", tone: "amber" },
  recommend_review: { label: "Recommended to manager", tone: "teal" },
  cleared: { label: "Cleared — no issue", tone: "green" },
  authentic: { label: "Verified authentic", tone: "green" },
  delist_suspend: { label: "Suspended", tone: "rose" },
  correction_window: { label: "Correction window", tone: "amber" },
  logistics_referral: { label: "Logistics referral", tone: "teal" },
  fix_applied: { label: "Fix applied", tone: "green" },
};

export const STATUS_META: Record<string, Meta> = {
  active: { label: "Active", tone: "green" },
  locked: { label: "Locked", tone: "rose" },
  suspended: { label: "Suspended", tone: "rose" },
  delisted: { label: "Delisted", tone: "rose" },
  on_hold: { label: "On hold", tone: "amber" },
  needs_info: { label: "Needs info", tone: "amber" },
  correction_window: { label: "Being corrected", tone: "amber" },
  flagged: { label: "Under manager review", tone: "teal" },
};

// Every `action` string the backend writes to catalog_actions, so the activity feeds
// never fall back to a raw snake_case enum.
export const ACTION_META: Record<string, Meta> = {
  // --- agent actions ---
  suspend: { label: "Suspend", tone: "rose" },
  correction: { label: "Correction window", tone: "amber" },
  logistics_referral: { label: "Logistics referral", tone: "teal" },
  fix_draft: { label: "Fix draft", tone: "brand" },
  fix_applied: { label: "Fix applied", tone: "green" },
  lock: { label: "Lock", tone: "rose" },
  ban: { label: "Ban", tone: "rose" },
  hold: { label: "Held for info", tone: "amber" },
  notify: { label: "Seller notified", tone: "amber" },
  request_qc_video: { label: "QC video requested", tone: "amber" },
  relabel_request: { label: "Relabel requested", tone: "amber" },
  reverify: { label: "Reverified", tone: "green" },
  recommend_review: { label: "Recommend review", tone: "teal" },
  // --- human manager decisions ---
  manager_approve: { label: "Manager: approved", tone: "green" },
  manager_unlock: { label: "Manager: unlocked", tone: "green" },
  manager_suspend: { label: "Manager: suspended", tone: "rose" },
  manager_suspend_and_request_changes: { label: "Manager: suspended · changes required", tone: "rose" },
  manager_request_changes: { label: "Manager: changes requested", tone: "amber" },
  manager_modify_listing: { label: "Manager: sizing update requested", tone: "amber" },
  manager_confirm_lock: { label: "Manager: confirmed", tone: "rose" },
  manager_delete: { label: "Manager: deleted", tone: "rose" },
  manager_dispute_approve: { label: "Manager: refund approved", tone: "green" },
  manager_dispute_reject: { label: "Manager: claim rejected", tone: "rose" },
};

// decisions that must BLOCK a purchase (the listing is unsafe to buy right now)
const BLOCKING = new Set([
  "counterfeit_lock",
  "ban",
  "hold_pending_fix",
  "request_qc_video",
  "manual_review",
]);
export const isBlocking = (d?: string | null): boolean => !!d && BLOCKING.has(d);

export const decisionMeta = (d?: string | null): Meta =>
  (d && DECISION_META[d]) || { label: d ?? "—", tone: "neutral" };
export const statusMeta = (s?: string | null): Meta =>
  (s && STATUS_META[s]) || { label: s ?? "—", tone: "neutral" };
export const actionMeta = (a?: string | null): Meta =>
  (a && ACTION_META[a]) || { label: a ?? "—", tone: "neutral" };

// friendly names + icons for agent tools (trace panel)
export const TOOL_META: Record<string, { label: string; icon: string }> = {
  check_catalog_risk: { label: "Catalog risk", icon: "🏷️" },
  check_seller_profile: { label: "Seller profile", icon: "🏪" },
  check_delivery_signals: { label: "Delivery signals", icon: "📦" },
  check_media_evidence: { label: "Media evidence (vision)", icon: "🎥" },
};
export const toolMeta = (n: string) =>
  TOOL_META[n] || { label: n.replace(/_/g, " "), icon: "🔎" };
