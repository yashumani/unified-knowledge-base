import { useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { brainClient } from "../../api/brainClient";
import type { IngestionPayload, Sensitivity } from "../../types";
import type {
  BatchIngestionResult,
  ConnectorIngestionRequest,
  CrawlIngestionRequest,
  DriveIngestionRequest,
  IngestionCapabilities,
  IngestionPreview,
  IngestionPreviewItem,
  IngestionSourceMode
} from "../../ingestionTypes";

const SOURCE_METHODS: Array<{
  id: IngestionSourceMode;
  label: string;
  detail: string;
  badge: string;
  ready: boolean;
}> = [
  { id: "text", label: "Paste context", detail: "Write or paste a single source directly.", badge: "Fast", ready: true },
  { id: "files", label: "Files", detail: "Select many documents in one batch.", badge: "Batch", ready: true },
  { id: "folder", label: "Folder", detail: "Preserve nested paths from a local folder.", badge: "Hierarchy", ready: true },
  { id: "zip", label: "ZIP archive", detail: "Inspect an archive before extracting it.", badge: "Portable", ready: true },
  { id: "google_drive", label: "Google Drive", detail: "Use a governed folder link and server-side connector.", badge: "Cloud", ready: true },
  { id: "crawl4ai", label: "Crawl4AI", detail: "Capture clean Markdown from an authorized website.", badge: "Web", ready: true },
  { id: "git", label: "Git repository", detail: "Point to a public or configured private repository.", badge: "Code", ready: false },
  { id: "object_store", label: "Object container", detail: "Use an S3-compatible bucket or internal container profile.", badge: "Storage", ready: false }
];

const SUPPORTED_FORMATS = [
  "PDF", "DOCX", "PPTX", "XLSX", "CSV", "TXT", "Markdown", "HTML", "XML",
  "JSON", "YAML", "SQL", "RST", "LOG", "ZIP"
];

const TEXT_EXTENSIONS = new Set([
  "txt", "md", "markdown", "csv", "json", "yaml", "yml", "sql", "html", "htm", "xml", "rst", "log"
]);

const SAMPLE_CONTEXT =
  "Support Handoff Time is the elapsed time between a support case being reassigned from first-line support to specialist support. It is owned by Support Operations and appears in the Service Quality Review. Cases waiting for a customer response are excluded. Recently reassigned cases may take 12 hours to reconcile before the metric is final.";

type StudioStep = "source" | "governance" | "validate" | "create";

const STUDIO_STEPS: Array<{ id: StudioStep; number: string; label: string; hint: string }> = [
  { id: "source", number: "01", label: "Source", hint: "Choose the entry point" },
  { id: "governance", number: "02", label: "Governance", hint: "Set ownership and policy" },
  { id: "validate", number: "03", label: "Validate", hint: "Inspect evidence quality" },
  { id: "create", number: "04", label: "Create", hint: "Send candidates to review" }
];

interface LocalFileItem {
  file: File;
  path: string;
}

function fileExtension(name: string): string {
  return name.includes(".") ? name.split(".").pop()!.toLowerCase() : "";
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function nowIso(): string {
  return new Date().toISOString();
}

export function IngestionStudio({
  demoMode,
  onSubmitContext,
  onCompleted
}: {
  demoMode: boolean;
  onSubmitContext: (payload: IngestionPayload) => Promise<void>;
  onCompleted: () => void;
}) {
  const [studioStep, setStudioStep] = useState<StudioStep>("source");
  const [method, setMethod] = useState<IngestionSourceMode>("files");
  const [title, setTitle] = useState("Support Operations Knowledge Batch");
  const [domain, setDomain] = useState("support");
  const [owner, setOwner] = useState("Support Operations");
  const [sensitivity, setSensitivity] = useState<Sensitivity>("internal");
  const [tags, setTags] = useState("support,service-quality,synthetic");
  const [effectiveDate, setEffectiveDate] = useState("");
  const [parserMode, setParserMode] = useState("layout-aware");
  const [chunking, setChunking] = useState("heading-and-table");
  const [duplicatePolicy, setDuplicatePolicy] = useState("new-version");
  const [qualityMode, setQualityMode] = useState("flag-sensitive");
  const [context, setContext] = useState(SAMPLE_CONTEXT);
  const [driveUrl, setDriveUrl] = useState("https://drive.google.com/drive/folders/example-folder-id");
  const [crawlUrl, setCrawlUrl] = useState("https://docs.example.org/service-quality");
  const [connectorUri, setConnectorUri] = useState("s3://knowledge-demo/support/");
  const [maxPages, setMaxPages] = useState(8);
  const [crawlDepth, setCrawlDepth] = useState(1);
  const [renderJavaScript, setRenderJavaScript] = useState(true);
  const [respectRobots, setRespectRobots] = useState(true);
  const [files, setFiles] = useState<LocalFileItem[]>([]);
  const [preview, setPreview] = useState<IngestionPreview | null>(null);
  const [result, setResult] = useState<BatchIngestionResult | null>(null);
  const [busy, setBusy] = useState<"preview" | "submit" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [capabilities, setCapabilities] = useState<IngestionCapabilities | null>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (demoMode) return;
    brainClient.getIngestionCapabilities().then(setCapabilities).catch(() => setCapabilities(null));
  }, [demoMode]);

  const selectedMethod = SOURCE_METHODS.find((item) => item.id === method)!;
  const tagList = useMemo(
    () => tags.split(",").map((tag) => tag.trim()).filter(Boolean),
    [tags]
  );

  function resetOutput(nextMethod: IngestionSourceMode) {
    setStudioStep("source");
    setMethod(nextMethod);
    setPreview(null);
    setResult(null);
    setError(null);
    if (nextMethod !== "files" && nextMethod !== "folder" && nextMethod !== "zip") setFiles([]);
  }

  function selectFiles(event: ChangeEvent<HTMLInputElement>, preservePaths = false) {
    const next = Array.from(event.target.files ?? []).map((file) => ({
      file,
      path: preservePaths && file.webkitRelativePath ? file.webkitRelativePath : file.name
    }));
    setFiles(next);
    setPreview(null);
    setResult(null);
    setError(null);
  }

  async function createDemoPreview(): Promise<IngestionPreview> {
    if (method === "text") {
      return {
        preview_id: `preview_${Date.now()}`,
        source_mode: method,
        ready: context.trim().length > 0,
        items: [{
          item_id: "manual-source",
          name: title,
          path: "manual/context",
          content_type: "text/plain",
          size_bytes: new Blob([context]).size,
          status: "ready",
          extracted_chars: context.length,
          source_uri: null
        }],
        warnings: context.length < 120 ? ["The source is short; confirm that the definition is complete."] : [],
        rejected_items: [],
        extracted_chars: context.length,
        preview_markdown: context,
        connector: "browser-demo",
        generated_at: nowIso()
      };
    }

    if (method === "files" || method === "folder" || method === "zip") {
      const items: IngestionPreviewItem[] = files.map(({ file, path }, index) => ({
        item_id: `local-${index}`,
        name: file.name,
        path,
        content_type: file.type || "application/octet-stream",
        size_bytes: file.size,
        status: file.size === 0 ? "rejected" : "ready",
        extracted_chars: TEXT_EXTENSIONS.has(fileExtension(file.name)) ? Math.min(file.size, 4000) : 0,
        source_uri: null
      }));
      const textFile = files.find(({ file }) => TEXT_EXTENSIONS.has(fileExtension(file.name)) && file.size < 2_000_000);
      const excerpt = textFile
        ? (await textFile.file.text()).slice(0, 5000)
        : "Binary document extraction requires the connected backend parser. The browser demo validates the manifest only.";
      const rejected = items.filter((item) => item.status === "rejected").map((item) => item.path);
      return {
        preview_id: `preview_${Date.now()}`,
        source_mode: method,
        ready: items.length > 0 && rejected.length < items.length,
        items,
        warnings: [
          ...(items.length > 50 ? ["Large batch: review sampling and ownership before submission."] : []),
          ...(!textFile ? ["No browser-readable text file was selected; connected extraction is required for binary content."] : [])
        ],
        rejected_items: rejected,
        extracted_chars: items.reduce((sum, item) => sum + item.extracted_chars, 0),
        preview_markdown: excerpt,
        connector: "browser-file-manifest",
        generated_at: nowIso()
      };
    }

    if (method === "google_drive") {
      return {
        preview_id: `preview_${Date.now()}`,
        source_mode: method,
        ready: driveUrl.includes("drive.google.com"),
        items: [
          { item_id: "drive-1", name: "Service Quality Glossary.docx", path: "Operations/Glossary", content_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", size_bytes: 48210, status: "ready", extracted_chars: 6230, source_uri: driveUrl },
          { item_id: "drive-2", name: "Metric Definitions.xlsx", path: "Operations/Metrics", content_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", size_bytes: 91104, status: "ready", extracted_chars: 8840, source_uri: driveUrl },
          { item_id: "drive-3", name: "Archive Shortcut", path: "Operations", content_type: "application/vnd.google-apps.shortcut", size_bytes: 0, status: "warning", extracted_chars: 0, source_uri: driveUrl }
        ],
        warnings: ["Demo manifest only. A connected runtime uses server-side OAuth or a service account; credentials are never pasted into the browser."],
        rejected_items: [],
        extracted_chars: 15070,
        preview_markdown: "# Google Drive folder preview\n\n- 2 extractable documents\n- 1 shortcut requiring review\n- Folder hierarchy and source links will be preserved.",
        connector: "google-drive-demo",
        generated_at: nowIso()
      };
    }

    if (method === "crawl4ai") {
      return {
        preview_id: `preview_${Date.now()}`,
        source_mode: method,
        ready: /^https?:\/\//.test(crawlUrl),
        items: [
          { item_id: "crawl-1", name: "Service quality overview", path: "/service-quality", content_type: "text/markdown", size_bytes: 18342, status: "ready", extracted_chars: 7120, source_uri: crawlUrl },
          { item_id: "crawl-2", name: "Metric definitions", path: "/service-quality/metrics", content_type: "text/markdown", size_bytes: 21104, status: "ready", extracted_chars: 9320, source_uri: `${crawlUrl.replace(/\/$/, "")}/metrics` }
        ],
        warnings: [respectRobots ? "robots.txt compliance enabled" : "robots.txt compliance is disabled; enable it unless an approved exception exists."],
        rejected_items: [],
        extracted_chars: 16440,
        preview_markdown: "# Crawl4AI output preview\n\nClean Markdown keeps headings, lists, code blocks and source links while pruning navigation and repeated chrome.\n\n## Quality gate\nOnly authorized hosts and the configured page limit are collected.",
        connector: renderJavaScript ? "crawl4ai-browser-rendered-demo" : "crawl4ai-static-demo",
        generated_at: nowIso()
      };
    }

    return {
      preview_id: `preview_${Date.now()}`,
      source_mode: method,
      ready: connectorUri.trim().length > 0,
      items: [
        { item_id: "container-1", name: "knowledge/manifest.json", path: connectorUri, content_type: "application/json", size_bytes: 2048, status: "warning", extracted_chars: 0, source_uri: connectorUri }
      ],
      warnings: ["This connector requires a server-side connection profile. Secrets and access keys are never collected in this page."],
      rejected_items: [],
      extracted_chars: 0,
      preview_markdown: "# Connector manifest\n\nThe location is valid. Configure an approved connector profile in the runtime before ingestion.",
      connector: `${method}-profile-demo`,
      generated_at: nowIso()
    };
  }

  function buildFormData(): FormData {
    const form = new FormData();
    files.forEach(({ file }) => form.append("files", file, file.name));
    form.set("relative_paths", JSON.stringify(files.map(({ path }) => path)));
    form.set("title", title);
    form.set("submitted_by", "ui.ingestion");
    form.set("domain", domain);
    form.set("owner", owner);
    form.set("sensitivity", sensitivity);
    form.set("tags", tagList.join(","));
    form.set("effective_date", effectiveDate);
    form.set("parser_mode", parserMode);
    form.set("chunking", chunking);
    form.set("duplicate_policy", duplicatePolicy);
    form.set("quality_mode", qualityMode);
    form.set("source_mode", method);
    return form;
  }

  function driveRequest(): DriveIngestionRequest {
    return {
      folder_url: driveUrl,
      title,
      submitted_by: "ui.ingestion",
      domain,
      owner: owner || null,
      sensitivity,
      tags: tagList,
      recursive: true,
      max_files: 100,
      duplicate_policy: duplicatePolicy
    };
  }

  function crawlRequest(): CrawlIngestionRequest {
    return {
      url: crawlUrl,
      title,
      submitted_by: "ui.ingestion",
      domain,
      owner: owner || null,
      sensitivity,
      tags: tagList,
      max_pages: maxPages,
      max_depth: crawlDepth,
      render_javascript: renderJavaScript,
      respect_robots: respectRobots,
      content_filter: "pruning"
    };
  }

  function connectorRequest(): ConnectorIngestionRequest {
    return {
      connector_type: method === "git" ? "git" : "object_store",
      location: connectorUri,
      title,
      submitted_by: "ui.ingestion",
      domain,
      owner: owner || null,
      sensitivity,
      tags: tagList,
      profile: "default"
    };
  }

  async function previewSource(event?: FormEvent) {
    event?.preventDefault();
    setBusy("preview");
    setError(null);
    setResult(null);
    try {
      let next: IngestionPreview;
      if (demoMode) next = await createDemoPreview();
      else if (method === "files" || method === "folder" || method === "zip") next = await brainClient.previewFiles(buildFormData());
      else if (method === "google_drive") next = await brainClient.previewDriveFolder(driveRequest());
      else if (method === "crawl4ai") next = await brainClient.previewCrawl(crawlRequest());
      else if (method === "git" || method === "object_store") next = await brainClient.previewConnector(connectorRequest());
      else next = await createDemoPreview();
      setPreview(next);
      setStudioStep("validate");
      return true;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The source preview could not be created.");
      setStudioStep("validate");
      return false;
    } finally {
      setBusy(null);
    }
  }

  async function submitBatch() {
    if (!preview?.ready) return;
    setBusy("submit");
    setError(null);
    try {
      let nextResult: BatchIngestionResult | null = null;
      if (method === "text" || demoMode) {
        const combinedContent = method === "text"
          ? context
          : `${preview.preview_markdown}\n\nSource manifest:\n${preview.items.map((item) => `- ${item.path} (${item.status})`).join("\n")}`;
        await onSubmitContext({
          title,
          source_type: method === "crawl4ai" ? "api" : method === "google_drive" ? "document" : method === "git" ? "git" : "document",
          submitted_by: "ui.ingestion",
          content: combinedContent,
          source_uri: method === "google_drive" ? driveUrl : method === "crawl4ai" ? crawlUrl : method === "git" || method === "object_store" ? connectorUri : null,
          domain,
          sensitivity,
          tags: [...tagList, `source:${method}`, owner ? `owner:${owner}` : "owner:unassigned"]
        });
        nextResult = {
          batch_id: `batch_${Date.now()}`,
          status: "review_created",
          source_mode: method,
          preview,
          review_items: [],
          message: demoMode
            ? "Demo candidate created. The batch is temporary and will reset on refresh."
            : "Candidate created from the normalized source."
        };
      } else if (method === "files" || method === "folder" || method === "zip") {
        nextResult = await brainClient.submitFiles(buildFormData());
      } else if (method === "google_drive") {
        nextResult = await brainClient.submitDriveFolder(driveRequest());
      } else if (method === "crawl4ai") {
        nextResult = await brainClient.submitCrawl(crawlRequest());
      } else {
        nextResult = await brainClient.submitConnector(connectorRequest());
      }
      setResult(nextResult);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The ingestion batch could not be submitted.");
    } finally {
      setBusy(null);
    }
  }

  const sourceNeedsFiles = method === "files" || method === "folder" || method === "zip";
  const sourceReady =
    (method === "text" && Boolean(context.trim())) ||
    (sourceNeedsFiles && files.length > 0) ||
    (method === "google_drive" && Boolean(driveUrl.trim())) ||
    (method === "crawl4ai" && Boolean(crawlUrl.trim())) ||
    ((method === "git" || method === "object_store") && Boolean(connectorUri.trim()));
  const governanceReady = Boolean(title.trim() && domain.trim());
  const previewDisabled = busy !== null || !sourceReady || !governanceReady;
  const stepIndex = STUDIO_STEPS.findIndex((item) => item.id === studioStep);
  const maxUnlockedStep = result ? 3 : preview?.ready ? 3 : preview || busy === "preview" ? 2 : sourceReady ? 1 : 0;
  const sourceSummary = sourceNeedsFiles
    ? `${files.length} ${files.length === 1 ? "item" : "items"} selected`
    : method === "text"
      ? `${context.trim().length.toLocaleString()} characters`
      : method === "google_drive"
        ? driveUrl
        : method === "crawl4ai"
          ? crawlUrl
          : connectorUri;

  function moveBack() {
    const destination = STUDIO_STEPS[Math.max(0, stepIndex - 1)]?.id;
    if (destination) setStudioStep(destination);
  }

  async function moveToValidation() {
    setStudioStep("validate");
    await previewSource();
  }

  return (
    <div className="ingestion-studio" data-studio-step={studioStep}>
      <nav className="studio-stepper" aria-label="Ingestion studio progress">
        {STUDIO_STEPS.map((item, index) => {
          const current = item.id === studioStep;
          const complete = index < stepIndex || (item.id === "validate" && Boolean(preview)) || (item.id === "create" && Boolean(result));
          const unlocked = index <= maxUnlockedStep;
          return (
            <button
              type="button"
              key={item.id}
              className={`${current ? "is-current" : ""}${complete ? " is-complete" : ""}`}
              disabled={!unlocked}
              onClick={() => unlocked && setStudioStep(item.id)}
              aria-current={current ? "step" : undefined}
            >
              <span>{complete && !current ? "✓" : item.number}</span>
              <div><strong>{item.label}</strong><small>{item.hint}</small></div>
            </button>
          );
        })}
      </nav>

      <section className="studio-workspace" aria-live="polite">
        <header className="studio-stage-heading">
          <div>
            <span>Decision {stepIndex + 1} of {STUDIO_STEPS.length}</span>
            <h2>{STUDIO_STEPS[stepIndex].label}</h2>
            <p>{STUDIO_STEPS[stepIndex].hint}. Only the controls needed for this decision are shown.</p>
          </div>
          <strong>{selectedMethod.label}</strong>
        </header>

        <div className="studio-stage-canvas">
          {studioStep === "source" && (
            <div className="studio-source-stage">
              <div className="ingestion-method-grid">
                {SOURCE_METHODS.map((item) => (
                  <button
                    type="button"
                    key={item.id}
                    className={method === item.id ? "is-selected" : ""}
                    onClick={() => resetOutput(item.id)}
                    aria-pressed={method === item.id}
                  >
                    <span>{item.badge}</span>
                    <strong>{item.label}</strong>
                    <small>{item.detail}</small>
                    {(() => {
                      const capability = capabilities?.capabilities.find((candidate) => candidate.id === item.id);
                      if (demoMode) return <b>{item.ready ? "Demo ready" : "Profile required"}</b>;
                      if (!capability) return <b>Checking runtime</b>;
                      return (
                        <b title={capability.message}>
                          {capability.configured ? "Connected" : capability.enabled ? "Setup required" : "Profile required"}
                        </b>
                      );
                    })()}
                  </button>
                ))}
              </div>

              <div className="studio-source-control">
                <header><strong>Connect {selectedMethod.label}</strong><span>{selectedMethod.detail}</span></header>
                {method === "text" && (
                  <label>Source context<textarea rows={8} value={context} onChange={(event) => { setContext(event.target.value); setPreview(null); setResult(null); }} required /></label>
                )}
                {method === "files" && (
                  <label className="ingestion-dropzone">Select many files<input type="file" multiple onChange={(event) => selectFiles(event)} /></label>
                )}
                {method === "folder" && (
                  <>
                    <label className="ingestion-dropzone">Select a folder
                      <input
                        ref={folderInputRef}
                        type="file"
                        multiple
                        onChange={(event) => selectFiles(event, true)}
                        {...({ webkitdirectory: "", directory: "" } as Record<string, string>)}
                      />
                    </label>
                    <small>Nested relative paths are retained in the batch manifest.</small>
                  </>
                )}
                {method === "zip" && (
                  <label className="ingestion-dropzone">Select a ZIP archive<input type="file" accept=".zip,application/zip" onChange={(event) => selectFiles(event)} /></label>
                )}
                {method === "google_drive" && (
                  <label>Google Drive folder link<input type="url" value={driveUrl} onChange={(event) => { setDriveUrl(event.target.value); setPreview(null); setResult(null); }} required /></label>
                )}
                {method === "crawl4ai" && (
                  <div className="ingestion-crawl-options">
                    <label>Authorized website URL<input type="url" value={crawlUrl} onChange={(event) => { setCrawlUrl(event.target.value); setPreview(null); setResult(null); }} required /></label>
                    <div>
                      <label>Page limit<input type="number" min={1} max={25} value={maxPages} onChange={(event) => setMaxPages(Number(event.target.value))} /></label>
                      <label>Link depth<input type="number" min={0} max={3} value={crawlDepth} onChange={(event) => setCrawlDepth(Number(event.target.value))} /></label>
                    </div>
                    <label className="ingestion-check"><input type="checkbox" checked={renderJavaScript} onChange={(event) => setRenderJavaScript(event.target.checked)} /> Render JavaScript and dynamic content</label>
                    <label className="ingestion-check"><input type="checkbox" checked={respectRobots} onChange={(event) => setRespectRobots(event.target.checked)} /> Respect robots.txt</label>
                  </div>
                )}
                {(method === "git" || method === "object_store") && (
                  <label>{method === "git" ? "Repository URL" : "Container URI"}<input value={connectorUri} onChange={(event) => { setConnectorUri(event.target.value); setPreview(null); setResult(null); }} required /></label>
                )}

                {sourceNeedsFiles && files.length > 0 && (
                  <ul className="selected-file-list">
                    {files.slice(0, 8).map(({ file, path }) => <li key={`${path}-${file.size}`}><span>{path}</span><strong>{formatBytes(file.size)}</strong></li>)}
                    {files.length > 8 && <li><span>+ {files.length - 8} more files</span></li>}
                  </ul>
                )}
              </div>

              <div className="ingestion-format-list">
                <strong>Parser catalog</strong>
                <div>{SUPPORTED_FORMATS.map((format) => <span key={format}>{format}</span>)}</div>
              </div>
            </div>
          )}

          {studioStep === "governance" && (
            <form className="studio-governance-stage" onSubmit={(event) => { event.preventDefault(); void moveToValidation(); }}>
              <div className="studio-governance-intro">
                <strong>Define who owns this knowledge and how it may be used.</strong>
                <p>These values travel with every source version, evidence chunk and candidate object.</p>
              </div>
              <div className="ingestion-form-grid">
                <label>Batch title<input value={title} onChange={(event) => setTitle(event.target.value)} required /></label>
                <label>Domain<input value={domain} onChange={(event) => setDomain(event.target.value)} required /></label>
                <label>Owner<input value={owner} onChange={(event) => setOwner(event.target.value)} placeholder="Responsible team or person" /></label>
                <label>Sensitivity<select value={sensitivity} onChange={(event) => setSensitivity(event.target.value as Sensitivity)}><option value="public">Public</option><option value="internal">Internal</option><option value="confidential">Confidential</option><option value="restricted">Restricted</option></select></label>
                <label>Tags<input value={tags} onChange={(event) => setTags(event.target.value)} /></label>
                <label>Effective date<input type="date" value={effectiveDate} onChange={(event) => setEffectiveDate(event.target.value)} /></label>
                <label>Parser<select value={parserMode} onChange={(event) => setParserMode(event.target.value)}><option value="layout-aware">Layout-aware</option><option value="fast-text">Fast text</option><option value="table-first">Table-first</option><option value="ocr-fallback">OCR fallback</option></select></label>
                <label>Chunking<select value={chunking} onChange={(event) => setChunking(event.target.value)}><option value="heading-and-table">Heading + table</option><option value="semantic-sections">Semantic sections</option><option value="page-boundaries">Page boundaries</option><option value="no-chunking">No chunking</option></select></label>
                <label>Duplicates<select value={duplicatePolicy} onChange={(event) => setDuplicatePolicy(event.target.value)}><option value="new-version">Create new version</option><option value="skip-exact">Skip exact duplicates</option><option value="flag-similar">Flag similar documents</option></select></label>
                <label>Quality gate<select value={qualityMode} onChange={(event) => setQualityMode(event.target.value)}><option value="flag-sensitive">Flag secrets and sensitive data</option><option value="strict">Block on any high-risk finding</option><option value="manifest-only">Manifest validation only</option></select></label>
              </div>
              <button type="submit" className="visually-hidden" tabIndex={-1}>Continue</button>
            </form>
          )}

          {studioStep === "validate" && (
            <div className="studio-validation-stage">
              {error && <div className="ingestion-error" role="alert">{error}</div>}
              {busy === "preview" && !preview && <div className="ingestion-empty"><strong>Building the source manifest…</strong><span>Parsing, normalizing and running deterministic quality gates.</span></div>}
              {!preview && busy !== "preview" && (
                <div className="ingestion-empty">
                  <strong>Validation has not run yet.</strong>
                  <span>Run the preview to inspect accepted, warned and rejected evidence before candidate creation.</span>
                  <button type="button" className="ingestion-preview-button" disabled={previewDisabled} onClick={() => void previewSource()}>
                    Preview and validate source
                  </button>
                </div>
              )}
              {preview && (
                <>
                  <div className="ingestion-quality-summary">
                    <div><span>Ready items</span><strong>{preview.items.filter((item) => item.status === "ready").length}</strong></div>
                    <div><span>Warnings</span><strong>{preview.warnings.length}</strong></div>
                    <div><span>Rejected</span><strong>{preview.rejected_items.length}</strong></div>
                    <div><span>Extracted</span><strong>{preview.extracted_chars.toLocaleString()} chars</strong></div>
                  </div>
                  <div className="studio-validation-grid">
                    <div className="ingestion-manifest">
                      <header><strong>Source manifest</strong><span>{preview.connector}</span></header>
                      <div className="ingestion-manifest-list">
                        {preview.items.slice(0, 20).map((item) => (
                          <div key={item.item_id}>
                            <span className={`manifest-status is-${item.status}`} />
                            <div><strong>{item.name}</strong><small>{item.path}</small></div>
                            <span>{formatBytes(item.size_bytes)}</span>
                            <b>{item.status}</b>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="ingestion-output-preview">
                      <header><strong>Normalized evidence preview</strong><span>Markdown / extracted text</span></header>
                      <pre>{preview.preview_markdown.slice(0, 6000)}</pre>
                    </div>
                  </div>
                  {preview.warnings.length > 0 && (
                    <div className="ingestion-warning-list"><strong>Quality findings</strong><ul>{preview.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>
                  )}
                  <button type="button" className="studio-rerun-button" disabled={busy !== null} onClick={() => void previewSource()}>
                    {busy === "preview" ? "Rebuilding preview…" : "Run validation again"}
                  </button>
                </>
              )}
            </div>
          )}

          {studioStep === "create" && (
            <div className="studio-create-stage">
              <div className="studio-release-card">
                <span>Governance boundary</span>
                <h3>Create candidates—not official memory.</h3>
                <p>The batch creates source versions, evidence chunks and review candidates. Local AI remains advisory; a human must approve and a publisher must release the final version.</p>
                <dl>
                  <div><dt>Source</dt><dd>{selectedMethod.label}</dd></div>
                  <div><dt>Domain</dt><dd>{domain}</dd></div>
                  <div><dt>Owner</dt><dd>{owner || "Unassigned"}</dd></div>
                  <div><dt>Sensitivity</dt><dd>{sensitivity}</dd></div>
                  <div><dt>Evidence items</dt><dd>{preview?.items.length ?? 0}</dd></div>
                  <div><dt>Quality findings</dt><dd>{preview?.warnings.length ?? 0}</dd></div>
                </dl>
              </div>

              {error && <div className="ingestion-error" role="alert">{error}</div>}
              {!result ? (
                <div className="studio-create-ready">
                  <strong>Ready to create the governed review batch.</strong>
                  <span>Use the primary action below. No knowledge is published by this step.</span>
                </div>
              ) : (
                <div className="ingestion-success">
                  <div><strong>Batch sent to human review</strong><span>{result.message}</span></div>
                </div>
              )}
            </div>
          )}
        </div>

        <footer className="studio-stage-actions">
          <button type="button" onClick={moveBack} disabled={stepIndex === 0}>← Back</button>
          <span>{STUDIO_STEPS[stepIndex].number} / 04</span>
          {studioStep === "source" && <button type="button" className="studio-primary" disabled={!sourceReady} onClick={() => setStudioStep("governance")}>Continue to governance →</button>}
          {studioStep === "governance" && <button type="button" className="studio-primary" disabled={previewDisabled} onClick={() => void moveToValidation()}>{busy === "preview" ? "Building preview…" : "Preview and validate source"}</button>}
          {studioStep === "validate" && <button type="button" className="studio-primary" disabled={!preview?.ready} onClick={() => setStudioStep("create")}>Continue to create →</button>}
          {studioStep === "create" && !result && <button type="button" className="studio-primary" disabled={!preview?.ready || busy !== null} onClick={submitBatch}>{busy === "submit" ? "Creating review candidates…" : "Create governed review batch"}</button>}
          {studioStep === "create" && result && <button type="button" className="studio-primary" onClick={onCompleted}>Continue to enrichment →</button>}
        </footer>
      </section>

      <aside className="studio-live-brief" aria-label="Current ingestion brief">
        <header>
          <span>Live brief</span>
          <strong>{title || "Untitled batch"}</strong>
          <small>Updates as decisions are made</small>
        </header>
        <div className="studio-brief-visual" aria-hidden="true">
          <span className={`studio-source-glyph source-${method}`}>{selectedMethod.badge.slice(0, 1)}</span>
          <i /><i /><i />
        </div>
        <dl>
          <div><dt>Entry point</dt><dd>{selectedMethod.label}</dd></div>
          <div><dt>Source</dt><dd title={sourceSummary}>{sourceSummary || "Not connected"}</dd></div>
          <div><dt>Domain</dt><dd>{domain || "Not set"}</dd></div>
          <div><dt>Owner</dt><dd>{owner || "Unassigned"}</dd></div>
          <div><dt>Sensitivity</dt><dd>{sensitivity}</dd></div>
          <div><dt>Parser</dt><dd>{parserMode}</dd></div>
          <div><dt>Duplicates</dt><dd>{duplicatePolicy}</dd></div>
        </dl>
        <div className="studio-brief-status">
          <span className={preview?.ready ? "is-ready" : preview ? "is-warning" : ""} />
          <div>
            <strong>{result ? "Review batch created" : preview?.ready ? "Validation passed" : preview ? "Review findings" : "Awaiting validation"}</strong>
            <small>{preview ? `${preview.items.length} evidence items · ${preview.warnings.length} findings` : "Complete Source and Governance first"}</small>
          </div>
        </div>
        <p>Nothing becomes official memory until human review and the separate publication gate are complete.</p>
      </aside>
    </div>
  );
}
