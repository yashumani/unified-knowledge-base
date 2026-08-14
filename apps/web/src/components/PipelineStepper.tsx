import type { StepId, StepState } from "../pipeline/types";

const PROGRESS_LABEL: Record<StepState["progress"], string> = {
  locked: "Not available yet",
  available: "Ready",
  complete: "Done"
};

/**
 * The navigational spine. Real anchors, so they survive a JS failure and can be
 * copied; the click handler upgrades them to a focus-moving scroll.
 *
 * A locked step is dimmed and explains itself, but stays clickable. A link that
 * silently does nothing reads as a broken page, and the section underneath has
 * a useful empty state regardless.
 */
export function PipelineStepper({
  states,
  onNavigate
}: {
  states: StepState[];
  onNavigate: (stepId: StepId) => void;
}) {
  return (
    <nav className="pipeline-stepper" aria-label="Pipeline steps">
      <ol>
        {states.map((state) => {
          const { step, progress, isActive, count, lockedReason } = state;
          return (
            <li key={step.id} className={`stepper-item is-${progress}${isActive ? " is-active" : ""}`}>
              <a
                href={`#${step.sectionId}`}
                aria-current={isActive ? "step" : undefined}
                title={lockedReason ?? undefined}
                onClick={(event) => {
                  event.preventDefault();
                  onNavigate(step.id);
                }}
              >
                <span className="stepper-marker" aria-hidden="true">
                  {progress === "complete" ? "✓" : String(step.number).padStart(2, "0")}
                </span>
                <span className="stepper-text">
                  <strong>{step.label}</strong>
                  <small>
                    {count ? `${count.value} ${count.noun}` : PROGRESS_LABEL[progress]}
                  </small>
                </span>
                <span className="visually-hidden">
                  {`Step ${step.number}: ${step.verb}. ${PROGRESS_LABEL[progress]}.`}
                  {lockedReason ? ` ${lockedReason}` : ""}
                </span>
              </a>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
