import type { ReviewItem, Sensitivity } from "./types";

export type IngestionSourceMode =
  | "text"
  | "files"
  | "folder"
  | "zip"
  | "google_drive"
  | "crawl4ai"
  | "git"
  | "object_store";

export type IngestionItemStatus = "ready" | "warning" | "rejected";

export interface IngestionPreviewItem {
  item_id: string;
  name: string;
  path: string;
  content_type: string;
  size_bytes: number;
  status: IngestionItemStatus;
  extracted_chars: number;
  source_uri?: string | null;
}

export interface IngestionPreview {
  preview_id: string;
  source_mode: IngestionSourceMode;
  ready: boolean;
  items: IngestionPreviewItem[];
  warnings: string[];
  rejected_items: string[];
  extracted_chars: number;
  preview_markdown: string;
  connector: string;
  generated_at: string;
}

export interface BatchIngestionResult {
  batch_id: string;
  status: "previewed" | "review_created" | "partial" | "blocked";
  source_mode: IngestionSourceMode;
  preview: IngestionPreview;
  review_items: ReviewItem[];
  message: string;
}

export interface DriveIngestionRequest {
  folder_url: string;
  title: string;
  submitted_by: string;
  domain: string;
  owner?: string | null;
  sensitivity: Sensitivity;
  tags: string[];
  recursive: boolean;
  max_files: number;
  duplicate_policy: string;
}

export interface CrawlIngestionRequest {
  url: string;
  title: string;
  submitted_by: string;
  domain: string;
  owner?: string | null;
  sensitivity: Sensitivity;
  tags: string[];
  max_pages: number;
  max_depth: number;
  render_javascript: boolean;
  respect_robots: boolean;
  content_filter: "pruning" | "bm25" | "none";
}

export interface ConnectorIngestionRequest {
  connector_type: "git" | "object_store";
  location: string;
  title: string;
  submitted_by: string;
  domain: string;
  owner?: string | null;
  sensitivity: Sensitivity;
  tags: string[];
  profile: string;
}

export interface IngestionCapability {
  id: IngestionSourceMode;
  enabled: boolean;
  configured: boolean;
  formats: string[];
  message: string;
}

export interface IngestionCapabilities {
  capabilities: IngestionCapability[];
  max_batch_files: number;
  max_file_bytes: number;
  max_archive_bytes: number;
}
