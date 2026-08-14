import type { ReviewStatus } from "../types";

/**
 * Human labels for all nine review states. The UI previously printed the raw
 * snake_case enum, and only ever handled two of the nine.
 */
const STATUS_LABEL: Record<ReviewStatus, string> = {
  draft: "Draft",
  submitted: "Submitted",
  ai_classified: "AI classified",
  human_review_required: "Awaiting review",
  approved: "Approved",
  rejected: "Rejected",
  changes_requested: "Changes requested",
  published: "Published",
  deprecated: "Deprecated"
};

export type StatusTone = "neutral" | "waiting" | "positive" | "negative" | "caution";

const STATUS_TONE: Record<ReviewStatus, StatusTone> = {
  draft: "neutral",
  submitted: "neutral",
  ai_classified: "neutral",
  human_review_required: "waiting",
  approved: "positive",
  rejected: "negative",
  changes_requested: "caution",
  published: "positive",
  deprecated: "neutral"
};

export const formatStatus = (status: string) =>
  STATUS_LABEL[status as ReviewStatus] ?? status.replace(/_/g, " ");

export const statusTone = (status: string): StatusTone =>
  STATUS_TONE[status as ReviewStatus] ?? "neutral";

/**
 * Confidence buckets. Deliberately worded as a review signal: a high-confidence
 * candidate still requires human approval, so this must never read as a
 * go-ahead.
 */
export function confidenceBucket(confidence: number): string {
  if (confidence >= 0.75) return "Strong signal";
  if (confidence >= 0.5) return "Moderate signal";
  return "Weak signal";
}

/** Compact relative time. No dependency; created_at/updated_at were never shown. */
export function formatRelative(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const seconds = Math.round((Date.now() - then) / 1000);
  if (seconds < 45) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days} day${days === 1 ? "" : "s"} ago`;
  return new Date(iso).toLocaleDateString();
}

export const formatProviderMode = (mode: string) => mode.replace(/_/g, " ");
