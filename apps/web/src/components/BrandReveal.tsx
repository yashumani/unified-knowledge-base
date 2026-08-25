import { useCallback, useEffect, useState, type CSSProperties } from "react";

const INTRO_SESSION_KEY = "ai-brain-brand-reveal-v1";
const EXIT_DURATION_MS = 360;

function shouldPlayIntro(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.sessionStorage.getItem(INTRO_SESSION_KEY) !== "seen";
  } catch {
    return true;
  }
}

export function BrandReveal() {
  const [visible, setVisible] = useState(shouldPlayIntro);
  const [leaving, setLeaving] = useState(false);

  const dismiss = useCallback(() => {
    if (leaving) return;
    try {
      window.sessionStorage.setItem(INTRO_SESSION_KEY, "seen");
    } catch {
      // A blocked storage API should never prevent access to the workspace.
    }
    setLeaving(true);
    window.setTimeout(() => setVisible(false), EXIT_DURATION_MS);
  }, [leaving]);

  useEffect(() => {
    if (!visible) return;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const timer = window.setTimeout(dismiss, reducedMotion ? 500 : 2400);
    return () => window.clearTimeout(timer);
  }, [dismiss, visible]);

  useEffect(() => {
    if (!visible) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" || event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        dismiss();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [dismiss, visible]);

  if (!visible) return null;

  const markUrl = `${import.meta.env.BASE_URL}ai-brain-mark.svg`;

  return (
    <section
      className={`brand-reveal${leaving ? " is-leaving" : ""}`}
      aria-label="AI Brain introduction"
      aria-live="polite"
    >
      <div className="brand-reveal__field" aria-hidden="true">
        {Array.from({ length: 14 }, (_, index) => (
          <span key={index} style={{ "--node-index": index } as CSSProperties} />
        ))}
      </div>
      <div className="brand-reveal__halo" aria-hidden="true" />
      <div className="brand-reveal__stage">
        <p className="brand-reveal__overline">Unified Knowledge Base presents</p>
        <div className="brand-reveal__logo" aria-label="AI Brain">
          <img src={markUrl} alt="" aria-hidden="true" fetchPriority="high" />
          <span className="brand-reveal__wordmark"><b>AI</b><strong>Brain</strong></span>
        </div>
        <div className="brand-reveal__rule" aria-hidden="true"><span /></div>
        <p className="brand-reveal__tagline">Governed intelligence starts here.</p>
        <p className="brand-reveal__subline">Evidence in. Human judgment. Trusted memory out.</p>
      </div>
      <button type="button" className="brand-reveal__skip" onClick={dismiss}>
        Skip intro <span aria-hidden="true">↗</span>
      </button>
    </section>
  );
}
