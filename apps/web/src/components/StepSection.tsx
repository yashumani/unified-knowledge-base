import type { ReactNode } from "react";
import type { StepId, StepState } from "../pipeline/types";

const PROGRESS_CHIP: Record<StepState["progress"], string> = {
  locked: "Not available yet",
  available: "Ready",
  complete: "Done"
};

/**
 * Shared wrapper for a pipeline step.
 *
 * Owns the heading (with the category kicker inside it, so the accessible name
 * carries the stage), the state chip, the per-step next action, and the
 * what-happened / what-it-means pair.
 *
 * The asymmetry in that pair is deliberate: the left side is derived from live
 * state and changes as you work, the right side is fixed doctrine. Seeing a
 * changing fact next to an unchanging rule is what teaches the governance
 * model — docs/UI_CONSOLE_END_TO_END.md structures its whole walkthrough that
 * way.
 */
export function StepSection({
  state,
  intro,
  children,
  onNavigate
}: {
  state: StepState;
  intro: string;
  children: ReactNode;
  onNavigate: (stepId: StepId) => void;
}) {
  const { step, progress, count, lockedReason, whatHappens, nextAction } = state;
  const headingId = `${step.sectionId}-heading`;

  return (
    <section
      className={`step-section is-${progress}`}
      id={step.sectionId}
      aria-labelledby={headingId}
    >
      <div className="step-header">
        <h2 id={headingId} data-step-heading tabIndex={-1}>
          <span className="step-kicker">
            Step {step.number} · {step.category}
          </span>
          {step.verb}
        </h2>
        <div className="step-status">
          <span className={`chip step-chip step-chip-${progress}`}>{PROGRESS_CHIP[progress]}</span>
          {count && <span className="chip">{count.value} {count.noun}</span>}
        </div>
      </div>

      <p className="step-intro">{intro}</p>

      {lockedReason && (
        <p className="step-locked" role="note">{lockedReason}</p>
      )}

      <div className="step-body">{children}</div>

      <div className="step-meaning">
        <div>
          <h3>What just happened</h3>
          <p>{whatHappens}</p>
        </div>
        <div className="step-doctrine">
          <h3>Why it works this way</h3>
          <p>{step.governanceMeaning}</p>
        </div>
      </div>

      {nextAction && nextAction.targetStepId !== step.id && (
        <button
          type="button"
          className="secondary step-next"
          onClick={() => onNavigate(nextAction.targetStepId)}
        >
          {nextAction.label}<span aria-hidden="true"> →</span>
        </button>
      )}
    </section>
  );
}
