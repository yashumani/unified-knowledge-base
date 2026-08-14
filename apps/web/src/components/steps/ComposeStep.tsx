import { useState, type FormEvent } from "react";
import type { ContextPack, ContextPackRequest } from "../../types";

export function ComposeStep({
  onAsk,
  contextPack,
  demoMode
}: {
  onAsk: (request: ContextPackRequest) => Promise<void>;
  contextPack: ContextPack | null;
  demoMode: boolean;
}) {
  const [question, setQuestion] = useState("Why did incident resolution time increase?");
  const [mode, setMode] = useState<ContextPackRequest["mode"]>("executive_insight");
  const [asking, setAsking] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setAsking(true);
    try {
      await onAsk({ question, user_id: "ui.consumer", domains: ["support"], mode });
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="panel wide-panel">
      <form onSubmit={submit} className="context-form">
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          aria-label="Context-pack question"
        />
        <select
          value={mode}
          onChange={(event) => setMode(event.target.value as ContextPackRequest["mode"])}
          aria-label="Context-pack mode"
        >
          <option value="default">Default</option>
          <option value="executive_insight">Executive insight</option>
          <option value="metric_definition">Metric definition</option>
          <option value="lineage">Lineage</option>
          <option value="governance_review">Governance review</option>
        </select>
        <button type="submit" disabled={asking}>
          {asking ? "Building..." : demoMode ? "Simulate pack" : "Build pack"}
        </button>
      </form>
      {contextPack && (
        <div className="context-pack">
          <div className="pack-header">
            <strong>{contextPack.access_decision.toUpperCase()}</strong>
            <span>{Math.round(contextPack.confidence * 100)}% confidence</span>
            <span>{contextPack.mode}</span>
          </div>
          <p>{contextPack.answer_guidance}</p>
          {contextPack.ai_guidance && (
            <div className="ai-guidance">
              <strong>AI enrichment guidance</strong>
              <span>{contextPack.ai_guidance}</span>
            </div>
          )}
          {contextPack.missing_context.length > 0 && (
            <div className="caveat-box">
              <strong>Missing context</strong>
              <span>{contextPack.missing_context.join(" · ")}</span>
            </div>
          )}
          <div className="pack-grid">
            <div>
              <h4>Evidence</h4>
              <ul>
                {contextPack.evidence.map((source) => (
                  <li key={source.source_id}>{source.title}: {source.content_excerpt}</li>
                ))}
              </ul>
            </div>
            <div>
              <h4>Follow-ups</h4>
              <ul>
                {contextPack.recommended_followups.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
          </div>
          {contextPack.caveats.length > 0 && (
            <div className="caveat-box">
              <strong>Caveats</strong>
              <span>{contextPack.caveats.join(" · ")}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
