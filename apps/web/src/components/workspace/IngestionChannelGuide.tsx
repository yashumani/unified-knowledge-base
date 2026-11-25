const CHANNELS = [
  { id: "text", label: "Paste context", detail: "Start with one definition, decision, policy, or operating note.", badge: "Fastest" },
  { id: "files", label: "Files", detail: "Select multiple supported documents and inspect one batch manifest.", badge: "Batch" },
  { id: "folder", label: "Folder", detail: "Keep nested paths from a documentation folder or local vault.", badge: "Hierarchy" },
  { id: "zip", label: "ZIP archive", detail: "Validate paths and expanded size before extraction.", badge: "Portable" },
  { id: "google_drive", label: "Google Drive", detail: "Connect a governed folder through server-side authorization.", badge: "Cloud" },
  { id: "crawl4ai", label: "Crawl4AI", detail: "Capture approved websites as clean, source-linked Markdown.", badge: "Web" },
  { id: "git", label: "Git repository", detail: "Register documentation and code context through a connector profile.", badge: "Code" },
  { id: "object_store", label: "Object container", detail: "Register an approved S3-compatible or internal container.", badge: "Storage" }
] as const;

function sourceHref(source: string): string {
  const parameters = new URLSearchParams(window.location.search);
  parameters.delete("view");
  parameters.delete("page");
  parameters.set("section", "sources");
  parameters.set("source", source);
  return `?${parameters.toString()}#ingestion-studio`;
}

export function IngestionChannelGuide() {
  return (
    <section className="ingestion-channel-guide" aria-labelledby="ingestion-channel-title">
      <div className="ingestion-channel-guide__header">
        <div>
          <span className="owui-eyebrow">Guided source intake</span>
          <h2 id="ingestion-channel-title">Connect. Validate. Create a review batch.</h2>
          <p>
            Choose where the evidence lives. Safe governance and parser defaults are applied automatically;
            advanced ownership, classification, chunking, and duplicate controls remain available in the studio.
          </p>
        </div>
        <ol className="ingestion-channel-guide__steps" aria-label="Recommended ingestion decisions">
          <li><strong>1</strong><span>Connect a source</span></li>
          <li><strong>2</strong><span>Validate evidence quality</span></li>
          <li><strong>3</strong><span>Create candidates for people to review</span></li>
        </ol>
      </div>

      <div className="ingestion-channel-guide__grid">
        {CHANNELS.map((channel) => (
          <a className="ingestion-channel-card" href={sourceHref(channel.id)} key={channel.id}>
            <span className="ingestion-channel-card__badge">{channel.badge}</span>
            <strong>{channel.label}</strong>
            <span>{channel.detail}</span>
            <small>Open channel →</small>
          </a>
        ))}
      </div>

      <div className="ingestion-channel-guide__boundary" role="note">
        <strong>One governance boundary for every channel.</strong>
        <span>
          Original evidence is preserved, the quality firewall runs before AI enrichment, and no connector can
          approve or publish organizational memory.
        </span>
      </div>
    </section>
  );
}
