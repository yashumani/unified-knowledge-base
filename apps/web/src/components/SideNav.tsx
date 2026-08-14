import type { StepId, StepState } from "../pipeline/types";
import type { AIProviderStatus } from "../types";

const TRAILING_LINKS = [
  { label: "Brain map", href: "#brain-map" },
  { label: "Activity", href: "#activity" }
];

/**
 * Navigation renders from the same step array as the stepper and the section
 * headings, so the three can no longer drift. They previously disagreed on both
 * order and vocabulary — the nav led with the graph and called step 5
 * "Context Pack" while the timeline called it "Compose".
 */
export function SideNav({
  aiStatus,
  states,
  onNavigate
}: {
  aiStatus: AIProviderStatus;
  states: StepState[];
  onNavigate: (stepId: StepId) => void;
}) {
  return (
    <aside className="side-nav" aria-label="Console navigation">
      <div className="brand-lockup">
        <span className="brand-mark">UKB</span>
        <div>
          <strong>AI Brain</strong>
          <span>Governed context OS</span>
        </div>
      </div>
      <nav aria-label="Sections">
        {states.map((state) => (
          <a
            key={state.step.id}
            href={`#${state.step.sectionId}`}
            aria-current={state.isActive ? "step" : undefined}
            className={state.isActive ? "is-active" : undefined}
            onClick={(event) => {
              event.preventDefault();
              onNavigate(state.step.id);
            }}
          >
            <span className="nav-index" aria-hidden="true">{state.step.number}</span>
            {state.step.label}
          </a>
        ))}
        {TRAILING_LINKS.map((item) => (
          <a href={item.href} key={item.href}>
            <span className="nav-index" aria-hidden="true">·</span>
            {item.label}
          </a>
        ))}
      </nav>
      <div className="nav-callout">
        <span>AI enrichment</span>
        <strong>{aiStatus.provider} · {aiStatus.mode}</strong>
        <p>{aiStatus.enabled ? `Model: ${aiStatus.model}` : "Disabled by server config"}</p>
      </div>
    </aside>
  );
}
