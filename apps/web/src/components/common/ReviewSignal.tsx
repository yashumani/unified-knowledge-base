import { confidenceBucket } from "../../utils/format";

/**
 * Confidence, rendered as a review signal rather than a score.
 *
 * docs/UI_CONSOLE_END_TO_END.md is explicit: "Confidence is a review signal,
 * not approval. A high-confidence candidate still requires human approval."
 * So this is never green and never reads as a go-ahead — the caption says what
 * the number is for, and the bar is the same neutral cyan at every value.
 */
export function ReviewSignal({
  confidence,
  label = "Review signal"
}: {
  confidence: number;
  label?: string;
}) {
  const percent = Math.round(confidence * 100);
  return (
    <div className="review-signal">
      <div className="review-signal-head">
        <span>{label}</span>
        <strong>{percent}% · {confidenceBucket(confidence)}</strong>
      </div>
      <div
        className="review-signal-track"
        role="meter"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label}: ${percent} percent. Not an approval.`}
      >
        <span style={{ width: `${percent}%` }} />
      </div>
      <small>Not an approval — a human still decides.</small>
    </div>
  );
}
