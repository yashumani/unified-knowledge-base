import type {
  AIProviderStatus,
  ContextPack,
  KnowledgeObject,
  ReviewItem
} from "../types";

export type StepId = "submit" | "enrich" | "review" | "publish" | "compose";
export type StepProgress = "locked" | "available" | "complete";

export interface ReviewDecisionRecord {
  reviewItemId: string;
  candidateTitle: string;
  action: "approved" | "published" | "rejected" | "changes_requested";
  reviewer: string;
  comment: string | null;
  at: string;
  hadAIBrief: boolean;
}

export interface SessionActivity {
  submitted: string[];
  enriched: string[];
  approved: string[];
  published: string[];
  packsBuilt: number;
}

export interface PipelineSnapshot {
  reviewItems: ReviewItem[];
  approvedItems: ReviewItem[];
  objects: KnowledgeObject[];
  contextPack: ContextPack | null;
  aiStatus: AIProviderStatus | null;
  demoMode: boolean;
  ledger: ReviewDecisionRecord[];
  session: SessionActivity;
}

export interface NextAction {
  label: string;
  targetStepId: StepId;
}

export interface StepCount {
  value: number;
  noun: string;
}

export interface StepDefinition {
  id: StepId;
  number: 1 | 2 | 3 | 4 | 5;
  label: string;
  verb: string;
  category: string;
  sectionId: string;
  governanceMeaning: string;
  whatHappens: (snapshot: PipelineSnapshot) => string;
  progress: (snapshot: PipelineSnapshot) => StepProgress;
  lockedReason?: (snapshot: PipelineSnapshot) => string;
  count?: (snapshot: PipelineSnapshot) => StepCount | null;
  nextAction?: (snapshot: PipelineSnapshot) => NextAction | null;
}

export interface StepState {
  step: StepDefinition;
  progress: StepProgress;
  isActive: boolean;
  count: StepCount | null;
  lockedReason: string | null;
  whatHappens: string;
  nextAction: NextAction | null;
}
