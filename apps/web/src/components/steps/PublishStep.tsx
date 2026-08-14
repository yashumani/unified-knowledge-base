import type { KnowledgeObject } from "../../types";

export function PublishStep({ objects }: { objects: KnowledgeObject[] }) {
  return (
    <div className="panel wide-panel">
      <div className="object-grid">
        {objects.length === 0 && (
          <div className="empty-state">Approved knowledge will appear here after review.</div>
        )}
        {objects.map((object) => (
          <article className="object-card" key={object.id}>
            <span className="badge">{object.type}</span>
            <h3>{object.title}</h3>
            <p>{object.summary}</p>
            <small>{object.domain} · {object.owner ?? "No owner"} · {object.status}</small>
          </article>
        ))}
      </div>
    </div>
  );
}
