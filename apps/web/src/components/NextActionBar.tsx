import type { GuidedNextMove } from "../pipeline/derive";
import type { StepId } from "../pipeline/types";

/**
 * One persistent answer to "what now", docked with the stepper so it never
 * scrolls out of reach — unlike the hero call to action it replaces.
 */
export function NextActionBar({
  nextMove,
  onNavigate
}: {
  nextMove: GuidedNextMove;
  onNavigate: (stepId: StepId) => void;
}) {
  if (nextMove.action) {
    return (
      <div className="next-action">
        <span className="next-action-label">Next</span>
        <button type="button" onClick={() => onNavigate(nextMove.action!.targetStepId)}>
          {nextMove.action.label}
          <span aria-hidden="true"> →</span>
        </button>
      </div>
    );
  }

  if (!nextMove.blockedReason) return null;

  return (
    <div className={`next-action${nextMove.done ? " is-done" : " is-blocked"}`}>
      <span className="next-action-label">{nextMove.done ? "Complete" : "Next"}</span>
      <p>{nextMove.blockedReason}</p>
    </div>
  );
}
