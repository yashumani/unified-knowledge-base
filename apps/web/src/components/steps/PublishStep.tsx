import type { KnowledgeObject } from "../../types";

export function PublishStep({ objects }: { objects: KnowledgeObject[] }) {
  return (
    <section className="panel wide-panel" id="published-objects">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Published AI Brain</p>
          <h2>Approved knowledge</h2>
        </div>
        <span className="chip success-chip">{objects.length} published</span>
      </div>
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
    </section>
  );
}
