import { ALL_STEPS_COMPLETE } from "./copy";
import { STEPS } from "./steps";
import type { NextAction, PipelineSnapshot, StepId, StepState } from "./types";

/** Resolve every step definition against the current snapshot. */
export function deriveStepStates(
  snapshot: PipelineSnapshot,
  activeStepId: StepId | null
): StepState[] {
  return STEPS.map((step) => {
    const progress = step.progress(snapshot);
    return {
      step,
      progress,
      isActive: step.id === activeStepId,
      count: step.count?.(snapshot) ?? null,
      lockedReason: progress === "locked" ? (step.lockedReason?.(snapshot) ?? null) : null,
      whatHappens: step.whatHappens(snapshot),
      nextAction: step.nextAction?.(snapshot) ?? null
    };
  });
}

export interface GuidedNextMove {
  action: NextAction | null;
  /** Shown when there is no action to take but a step is still gated. */
  blockedReason: string | null;
  done: boolean;
}

/**
 * The single "what do I do next" answer, resolved in pipeline order: the first
 * step that can be acted on, else the first gated step and why, else done.
 */
export function resolveNextMove(states: StepState[]): GuidedNextMove {
  const actionable = states.find((state) => state.progress === "available" && state.nextAction);
  if (actionable?.nextAction) {
    return { action: actionable.nextAction, blockedReason: null, done: false };
  }

  const incomplete = states.filter((state) => state.progress !== "complete");
  if (incomplete.length === 0) {
    return { action: null, blockedReason: ALL_STEPS_COMPLETE, done: true };
  }

  const anyAction = states.find((state) => state.nextAction);
  if (anyAction?.nextAction) {
    return { action: anyAction.nextAction, blockedReason: null, done: false };
  }

  const gated = incomplete.find((state) => state.lockedReason);
  return { action: null, blockedReason: gated?.lockedReason ?? null, done: false };
}
