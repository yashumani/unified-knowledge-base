import { useMemo, useState } from "react";
import type { WorkspacePage } from "./WorkspaceApp";

const GUIDE_STEPS: Array<{
  page: WorkspacePage;
  number: string;
  title: string;
  action: string;
  check: string;
}> = [
  { page: "ingest", number: "01", title: "Collect clean evidence", action: "Choose a source, configure governance metadata and approve the manifest.", check: "The preview contains the expected files, paths, extracted text and warnings." },
  { page: "enrich", number: "02", title: "Run advisory enrichment", action: "Generate a local AI brief and inspect validation findings and proposed relationships.", check: "The brief cites the submitted source and does not claim publication." },
  { page: "review", number: "03", title: "Make the human decision", action: "Approve, reject or request changes with an attributable reviewer comment.", check: "Only approved candidates continue to published memory." },
  { page: "publish", number: "04", title: "Inspect official memory", action: "Confirm owner, domain, sensitivity, source lineage and status.", check: "Published objects remain distinct from source evidence and unapproved candidates." },
  { page: "compose", number: "05", title: "Build a governed context pack", action: "Ask a question and inspect evidence, caveats, confidence and missing context.", check: "The downstream AI receives selected approved context—not the entire document collection." }
];

const FAQ = [
  ["Why is ingestion a separate studio?", "The largest quality risk enters before enrichment. UKB therefore requires a source manifest, parser output preview, duplicate policy and sensitivity decision before review candidates are created."],
  ["Can I upload a folder?", "Yes. The browser preserves relative paths with folder selection, and the connected backend receives the files as one governed batch. A ZIP archive is available when browser folder selection is not practical."],
  ["How does Google Drive work?", "Paste a folder link. The browser sends only the link and ingestion settings. A configured backend uses server-side OAuth or a service account to list and download permitted files; users never paste access tokens into the page."],
  ["What does Crawl4AI add?", "Crawl4AI renders authorized pages, respects robots.txt when enabled, produces clean Markdown, preserves source URLs and can follow bounded same-host links. The preview shows exactly what will enter review."],
  ["Are all file types parsed in the browser demo?", "No. The public browser demo can inspect file manifests and read safe text formats. PDF, Office and archive extraction require the connected backend parser. The UI labels this boundary instead of pretending binary files were parsed."],
  ["Does the LLM publish knowledge?", "No. Local Ollama enrichment is advisory. A human reviewer still controls publication, and the decision is recorded."],
  ["Why are PostgreSQL and Zvec both needed?", "PostgreSQL owns governed truth—versions, approvals, access rules and audit. Zvec is a rebuildable retrieval index that helps locate the right approved memory quickly."],
  ["What happens when the answer is uncertain?", "The context pack exposes confidence, caveats and missing-context warnings. The downstream application should abstain when authoritative evidence is insufficient."],
  ["Where are advanced controls?", "Open the Advanced console from the top bar. It exposes the full long-form workflow, graph controls, reviewer actions and architecture narrative."],
  ["How do I reset the demo?", "Refresh the page or use the reset control in the guided experience. Public GitHub Pages state is intentionally temporary."]
] as const;

const INGESTION_REFERENCE = [
  ["Paste context", "A single manual source, policy, definition or note."],
  ["Files", "Multiple independent documents selected together."],
  ["Folder", "A local hierarchy with relative paths retained."],
  ["ZIP archive", "A portable collection inspected for unsafe paths and unsupported entries."],
  ["Google Drive", "A governed folder link processed by a server-side connector."],
  ["Crawl4AI", "Authorized website capture with clean Markdown and bounded link traversal."],
  ["Git repository", "Repository ingestion through a configured connector profile."],
  ["Object container", "S3-compatible or internal object storage through a server-side profile."]
] as const;

export function HelpCenter({ onNavigate }: { onNavigate: (page: WorkspacePage) => void }) {
  const [query, setQuery] = useState("");
  const [tab, setTab] = useState<"guide" | "ingestion" | "faq" | "troubleshoot">("guide");

  const filteredFaq = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return FAQ;
    return FAQ.filter(([question, answer]) => `${question} ${answer}`.toLowerCase().includes(normalized));
  }, [query]);

  return (
    <div className="help-center">
      <aside className="help-sidebar">
        <label>
          Search help
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Drive, Crawl4AI, review…" />
        </label>
        <nav aria-label="Help topics">
          <button type="button" className={tab === "guide" ? "is-active" : ""} onClick={() => setTab("guide")}>End-to-end guide</button>
          <button type="button" className={tab === "ingestion" ? "is-active" : ""} onClick={() => setTab("ingestion")}>Ingestion reference</button>
          <button type="button" className={tab === "faq" ? "is-active" : ""} onClick={() => setTab("faq")}>Frequently asked questions</button>
          <button type="button" className={tab === "troubleshoot" ? "is-active" : ""} onClick={() => setTab("troubleshoot")}>Troubleshooting</button>
        </nav>
        <div className="help-sidebar-callout">
          <strong>Need every control?</strong>
          <span>Use the Advanced console from the workspace top bar.</span>
        </div>
      </aside>

      <section className="help-content">
        {tab === "guide" && (
          <div className="help-guide">
            <header><span>Complete workflow</span><h2>Five visible stages. One governed outcome.</h2><p>Use this checklist during a demo or a real ingestion review.</p></header>
            <ol>
              {GUIDE_STEPS.map((step) => (
                <li key={step.number}>
                  <span>{step.number}</span>
                  <div><h3>{step.title}</h3><p>{step.action}</p><small>Success check: {step.check}</small></div>
                  <button type="button" onClick={() => onNavigate(step.page)}>Open page →</button>
                </li>
              ))}
            </ol>
          </div>
        )}

        {tab === "ingestion" && (
          <div className="help-reference">
            <header><span>Source catalog</span><h2>Choose the source that preserves the most evidence.</h2></header>
            <div className="help-reference-grid">
              {INGESTION_REFERENCE.map(([name, detail], index) => (
                <article key={name}><span>{String(index + 1).padStart(2, "0")}</span><h3>{name}</h3><p>{detail}</p></article>
              ))}
            </div>
            <div className="help-format-band">
              <strong>Supported parser targets</strong>
              <p>PDF · DOCX · PPTX · XLSX · CSV · TXT · Markdown · HTML · XML · JSON · YAML · SQL · RST · LOG · ZIP</p>
              <small>Binary extraction and archive inspection require the connected backend parser.</small>
            </div>
          </div>
        )}

        {tab === "faq" && (
          <div className="help-faq">
            <header><span>Frequently asked questions</span><h2>{filteredFaq.length} answers</h2></header>
            {filteredFaq.map(([question, answer]) => <details key={question}><summary>{question}</summary><p>{answer}</p></details>)}
            {filteredFaq.length === 0 && <div className="help-empty">No answer matched “{query}”.</div>}
          </div>
        )}

        {tab === "troubleshoot" && (
          <div className="help-troubleshoot">
            <header><span>Fast diagnosis</span><h2>Start with the boundary that failed.</h2></header>
            <article><strong>The public page says Browser demo</strong><p>GitHub Pages is static. Start the FastAPI backend, configure the Pages API base URL, and provide a trusted session or development API token.</p></article>
            <article><strong>Crawl4AI is unavailable</strong><p>Install the connector extra and browser runtime on the backend, enable the connector, and add authorized hosts. Keep crawler egress private and bounded.</p></article>
            <article><strong>Google Drive cannot list the folder</strong><p>Confirm the folder is shared with the configured service account or that the server OAuth token has Drive read access. Do not paste credentials into the browser.</p></article>
            <article><strong>A file is rejected</strong><p>Check format, size, empty content, archive paths, parser availability and quality-gate findings. The source preview explains the rejection before submission.</p></article>
            <article><strong>The candidate looks wrong</strong><p>Request changes rather than approving. Preserve the source evidence and reviewer reason so the compiler can be corrected without losing lineage.</p></article>
          </div>
        )}
      </section>
    </div>
  );
}
