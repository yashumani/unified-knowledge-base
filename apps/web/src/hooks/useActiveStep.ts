import { useCallback, useEffect, useState } from "react";
import { STEPS, stepBySectionId } from "../pipeline/steps";
import type { StepId } from "../pipeline/types";

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * Tracks which step the viewer is looking at, and moves them between steps.
 *
 * Scroll position alone cannot express progress, and progress alone cannot say
 * where someone is, so this owns only the "where" half. The observer band is a
 * thin strip near the top third of the viewport, which stays unambiguous
 * whether a section is half a screen tall or three screens tall.
 */
export function useActiveStep() {
  const [activeStepId, setActiveStepId] = useState<StepId | null>(STEPS[0].id);

  const goToStep = useCallback((stepId: StepId) => {
    const step = STEPS.find((candidate) => candidate.id === stepId);
    if (!step) return;
    const section = document.getElementById(step.sectionId);
    if (!section) return;

    section.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "start" });
    // Focus the heading so keyboard and screen-reader users travel with the
    // scroll rather than being left behind at the stepper.
    const heading = section.querySelector<HTMLElement>("[data-step-heading]");
    heading?.focus({ preventScroll: true });
    setActiveStepId(stepId);
    window.history.replaceState(null, "", `#${step.sectionId}`);
  }, []);

  useEffect(() => {
    const sections = STEPS.map((step) => document.getElementById(step.sectionId)).filter(
      (element): element is HTMLElement => element !== null
    );
    if (!sections.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (!visible.length) return;
        const step = stepBySectionId(visible[0].target.id);
        if (step) setActiveStepId(step.id);
      },
      { rootMargin: "-40% 0px -55% 0px", threshold: 0 }
    );

    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, []);

  // Honour a deep link on first paint.
  useEffect(() => {
    const hash = window.location.hash.replace("#", "");
    if (!hash) return;
    const step = stepBySectionId(hash);
    if (!step) return;
    const timer = window.setTimeout(() => goToStep(step.id), 120);
    return () => window.clearTimeout(timer);
  }, [goToStep]);

  return { activeStepId, goToStep };
}
