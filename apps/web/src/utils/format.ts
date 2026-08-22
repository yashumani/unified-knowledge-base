import type { ReviewStatus } from "../types";

const STATUS_LABEL: Record<ReviewStatus, string> = {
  draft: "Draft",
  submitted: "Submitted",
  parsing: "Parsing source",
  enrichment_pending: "Enrichment pending",
  ai_classified: "AI classified",
  human_review_required: "Awaiting review",
  changes_requested: "Changes requested",
  approved: "Approved for publication",
  publication_pending: "Publication pending",
  published: "Published",
  rejected: "Rejected",
  superseded: "Superseded",
  deprecated: "Deprecated"
};

export type StatusTone = "neutral" | "waiting" | "positive" | "negative" | "caution";

const STATUS_TONE: Record<ReviewStatus, StatusTone> = {
  draft: "neutral",
  submitted: "neutral",
  parsing: "waiting",
  enrichment_pending: "waiting",
  ai_classified: "neutral",
  human_review_required: "waiting",
  changes_requested: "caution",
  approved: "positive",
  publication_pending: "waiting",
  published: "positive",
  rejected: "negative",
  superseded: "neutral",
  deprecated: "neutral"
};

export const formatStatus = (status: string) =>
  STATUS_LABEL[status as ReviewStatus] ?? status.replace(/_/g, " ");

export const statusTone = (status: string): StatusTone =>
  STATUS_TONE[status as ReviewStatus] ?? "neutral";

export function confidenceBucket(confidence: number): string {
  if (confidence >= 0.75) return "Strong signal";
  if (confidence >= 0.5) return "Moderate signal";
  return "Weak signal";
}

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
