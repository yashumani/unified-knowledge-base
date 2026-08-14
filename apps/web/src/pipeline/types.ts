import type {
  AIProviderStatus,
  ContextPack,
  KnowledgeObject,
  ReviewItem
} from "../types";

export type StepId = "submit" | "enrich" | "review" | "publish" | "compose";

/**
 * How far the pipeline has got at this step.
 *
 * Deliberately separate from "is the viewer looking at it". A viewer routinely
 * reads a step that is already complete, so folding the two into one enum would
 * force a false choice between showing progress and showing position.
 */
export type StepProgress = "locked" | "available" | "complete";

/**
 * A governed decision a human made. Append-only.
 *
 * The console needs this because the review handlers destroy their own
 * evidence: rejecting an item simply drops it from the queue, leaving nothing
 * to show that a decision ever happened. The ledger is what makes "Review" a
 * completable step, what makes rejection visible, and what the activity feed
 * renders.
 */
export interface ReviewDecisionRecord {
  reviewItemId: string;
  candidateTitle: string;
  action: "approved" | "rejected" | "changes_requested";
  reviewer: string;
  comment: string | null;
  at: string;
  /** False means a human published without ever asking for an AI brief. */
  hadAIBrief: boolean;
}

/** What this viewer did, as opposed to what was seeded for them. */
export interface SessionActivity {
  submitted: string[];
  enriched: string[];
  published: string[];
  packsBuilt: number;
}

export interface PipelineSnapshot {
  reviewItems: ReviewItem[];
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
  /** Short name, used by the stepper and the side nav. */
  label: string;
  /** Imperative heading for the section itself. */
  verb: string;
  /** Category kicker, rendered inside the heading so it joins the a11y name. */
  category: string;
  sectionId: string;
  /** Fixed doctrine. Does not change with state — that contrast is the point. */
  governanceMeaning: string;
  whatHappens: (snapshot: PipelineSnapshot) => string;
  progress: (snapshot: PipelineSnapshot) => StepProgress;
  lockedReason?: (snapshot: PipelineSnapshot) => string;
  count?: (snapshot: PipelineSnapshot) => StepCount | null;
  nextAction?: (snapshot: PipelineSnapshot) => NextAction | null;
}

/** A step definition resolved against the current snapshot. */
export interface StepState {
  step: StepDefinition;
  progress: StepProgress;
  isActive: boolean;
  count: StepCount | null;
  lockedReason: string | null;
  whatHappens: string;
  nextAction: NextAction | null;
}
