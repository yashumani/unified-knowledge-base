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
        <input value={question} onChange={(event) => setQuestion(event.target.value)} aria-label="Context-pack question" />
        <select value={mode} onChange={(event) => setMode(event.target.value as ContextPackRequest["mode"])} aria-label="Context-pack mode">
          <option value="default">Default</option>
          <option value="executive_insight">Executive insight</option>
          <option value="metric_definition">Metric definition</option>
          <option value="lineage">Lineage</option>
          <option value="governance_review">Governance review</option>
          <option value="debug">Debug</option>
        </select>
        <button type="submit" disabled={asking}>{asking ? "Building..." : demoMode ? "Simulate pack" : "Build governed pack"}</button>
      </form>

      {contextPack && (
        <div className="context-pack">
          <div className="pack-header">
            <strong>{contextPack.access_decision.toUpperCase()}</strong>
            <span>{Math.round(contextPack.confidence * 100)}% composite confidence</span>
            <span>{contextPack.mode}</span>
            <span>{contextPack.retrieval_engine ?? "demo"}</span>
          </div>
          <p>{contextPack.answer_guidance}</p>

          {contextPack.confidence_factors && (
            <div className="confidence-factor-grid" aria-label="Context confidence factors">
              <Factor label="Retrieval" value={contextPack.confidence_factors.retrieval} />
              <Factor label="Evidence coverage" value={contextPack.confidence_factors.evidence_coverage} />
              <Factor label="Source authority" value={contextPack.confidence_factors.source_authority} />
              <Factor label="Freshness" value={contextPack.confidence_factors.freshness} />
              <Factor label="Conflict penalty" value={contextPack.confidence_factors.conflict_penalty} penalty />
            </div>
          )}

          {contextPack.ai_guidance && (
            <div className="ai-guidance"><strong>Guidance for the downstream AI</strong><span>{contextPack.ai_guidance}</span></div>
          )}
          {contextPack.missing_context.length > 0 && (
            <div className="caveat-box"><strong>Missing context</strong><span>{contextPack.missing_context.join(" · ")}</span></div>
          )}
          {(contextPack.conflicts?.length ?? 0) > 0 && (
            <div className="caveat-box"><strong>Conflicting approved knowledge</strong><span>{contextPack.conflicts?.join(" · ")}</span></div>
          )}

          <div className="pack-grid">
            <div>
              <h4>Citations</h4>
              <ul>
                {contextPack.citations?.length
                  ? contextPack.citations.map((citation) => (
                      <li key={citation.citation_id}>
                        <strong>{citation.title}{citation.locator ? ` · ${citation.locator}` : ""}</strong>
                        <p>“{citation.quote}”</p>
                      </li>
                    ))
                  : contextPack.evidence.map((source) => (
                      <li key={source.source_id}><strong>{source.title}</strong><p>{source.content_excerpt}</p></li>
                    ))}
              </ul>
            </div>
            <div>
              <h4>Approved objects</h4>
              <ul>
                {contextPack.knowledge_objects.map((object) => (
                  <li key={object.id}><strong>{object.title}</strong><p>{object.owner ?? "Owner not assigned"} · v{object.version ?? 1}</p></li>
                ))}
              </ul>
              <h4>Follow-ups</h4>
              <ul>{contextPack.recommended_followups.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
          </div>
          {contextPack.caveats.length > 0 && (
            <div className="caveat-box"><strong>Caveats</strong><span>{contextPack.caveats.join(" · ")}</span></div>
          )}
        </div>
      )}
    </div>
  );
}

function Factor({ label, value, penalty = false }: { label: string; value: number; penalty?: boolean }) {
  return <div><span>{label}</span><strong>{penalty ? "−" : ""}{Math.round(value * 100)}%</strong></div>;
}
