import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type FormEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
  type RefObject
} from "react";
import { API_BASE } from "../api/brainClient";
import { useBrainState, REVIEWER } from "../hooks/useBrainState";
import type { ContextPack, ContextPackRequest } from "../types";
import { ActivityLedger } from "./ActivityLedger";
import { ObsidianGraphView } from "./ObsidianGraphView";
import { EnrichStep } from "./steps/EnrichStep";
import { PublishStep } from "./steps/PublishStep";
import { ReviewStep } from "./steps/ReviewStep";
import { IngestionStudio } from "./workspace/IngestionStudio";

export type BrainSection =
  | "chat"
  | "sources"
  | "enrich"
  | "review"
  | "publish"
  | "memory"
  | "operations"
  | "activity"
  | "help";

type ThemeMode = "light" | "dark";
type ContextTab = "context" | "sources" | "governance";
type ComposerMode = ContextPackRequest["mode"];

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  pack?: ContextPack;
  createdAt: string;
};

type OperationsStatus = {
  tenant_id: string;
  subject: string;
  auth_method: string;
  quality_assessments: number;
  quarantined_sources: number;
  active_assignments: number;
  active_subscriptions: number;
  retrieval_feedback: number;
  capabilities: string[];
};

type IconName =
  | "activity"
  | "archive"
  | "arrow"
  | "brain"
  | "check"
  | "chevron"
  | "close"
  | "database"
  | "file"
  | "help"
  | "home"
  | "layers"
  | "menu"
  | "message"
  | "moon"
  | "network"
  | "panel"
  | "plus"
  | "review"
  | "search"
  | "send"
  | "settings"
  | "shield"
  | "sparkles"
  | "sun"
  | "upload"
  | "user"
  | "wand";

const SECTION_LABELS: Record<BrainSection, string> = {
  chat: "Brain Chat",
  sources: "Sources",
  enrich: "Enrichment",
  review: "Review queue",
  publish: "Published memory",
  memory: "Memory graph",
  operations: "Knowledge operations",
  activity: "Audit activity",
  help: "Help & guides"
};

const SECTION_META: Record<Exclude<BrainSection, "chat">, { title: string; copy: string; icon: IconName }> = {
  sources: {
    title: "Bring trusted context into the brain.",
    copy: "Collect files, folders, Drive content, crawled pages, repositories, and containers without bypassing governance.",
    icon: "upload"
  },
  enrich: {
    title: "Turn evidence into reviewable structure.",
    copy: "Use local Ollama as an advisory worker while deterministic checks and source lineage remain visible.",
    icon: "wand"
  },
  review: {
    title: "Let people decide what the organization knows.",
    copy: "Inspect evidence, AI findings, ownership, and risk before approving or requesting changes.",
    icon: "review"
  },
  publish: {
    title: "Publish official memory deliberately.",
    copy: "Keep approval separate from publication so only explicit, attributable decisions become retrievable knowledge.",
    icon: "check"
  },
  memory: {
    title: "Explore the governed memory graph.",
    copy: "Trace sources, candidates, published objects, relationships, confidence, and status without losing provenance.",
    icon: "network"
  },
  operations: {
    title: "Operate the knowledge supply chain.",
    copy: "Monitor identity, quality, human review, connector refresh, and retrieval evaluation from one control plane.",
    icon: "layers"
  },
  activity: {
    title: "Follow every governance decision.",
    copy: "Review the attributable trail for enrichment, approval, publication, rejection, and requested changes.",
    icon: "activity"
  },
  help: {
    title: "Understand the complete AI Brain workflow.",
    copy: "Use concise guidance for ingestion, governance, local AI, memory recall, and private-runtime deployment.",
    icon: "help"
  }
};

const MODE_LABELS: Record<ComposerMode, string> = {
  default: "Default",
  executive_insight: "Executive insight",
  metric_definition: "Metric definition",
  lineage: "Lineage",
  governance_review: "Governance review",
  debug: "Debug"
};

const SUGGESTIONS: Array<{ title: string; prompt: string; mode: ComposerMode; icon: IconName }> = [
  {
    title: "Explain a metric",
    prompt: "What does Incident Resolution Time mean, who owns it, and which sources define it?",
    mode: "metric_definition",
    icon: "database"
  },
  {
    title: "Investigate a change",
    prompt: "Why did incident resolution time increase and what approved context should an analyst consider?",
    mode: "executive_insight",
    icon: "sparkles"
  },
  {
    title: "Trace provenance",
    prompt: "Show the source lineage and approved evidence behind the current resolution-time definition.",
    mode: "lineage",
    icon: "network"
  },
  {
    title: "Check governance",
    prompt: "What context is missing, conflicting, stale, or excluded before an AI should answer?",
    mode: "governance_review",
    icon: "shield"
  }
];

const DEMO_OPERATIONS: OperationsStatus = {
  tenant_id: "synthetic-pilot",
  subject: "demo.governance.admin",
  auth_method: "browser-demo",
  quality_assessments: 18,
  quarantined_sources: 2,
  active_assignments: 6,
  active_subscriptions: 4,
  retrieval_feedback: 27,
  capabilities: [
    "oidc_tenant_context",
    "knowledge_quality_firewall",
    "review_assignments",
    "continuous_source_refresh",
    "explainable_reranking"
  ]
};

function sectionFromLocation(): BrainSection {
  if (typeof window === "undefined") return "chat";
  const params = new URLSearchParams(window.location.search);
  if (params.get("view") === "operations") return "operations";
  const explicit = params.get("section") as BrainSection | null;
  if (explicit && explicit in SECTION_LABELS) return explicit;
  const legacyPage = params.get("page");
  const legacyMap: Record<string, BrainSection> = {
    home: "chat",
    ingest: "sources",
    enrich: "enrich",
    review: "review",
    publish: "publish",
    compose: "chat",
    memory: "memory",
    activity: "activity",
    help: "help"
  };
  return legacyPage ? legacyMap[legacyPage] ?? "chat" : "chat";
}

function initialTheme(): ThemeMode {
  if (typeof window === "undefined") return "dark";
  const stored = window.localStorage.getItem("ukb-openwebui-theme");
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function messageId(prefix: string) {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
}

export function OpenWebUIBrainApp({
  onOpenAdvanced,
  onOpenGuided
}: {
  onOpenAdvanced: () => void;
  onOpenGuided: () => void;
}) {
  const brain = useBrainState();
  const [section, setSection] = useState<BrainSection>(sectionFromLocation);
  const [theme, setTheme] = useState<ThemeMode>(initialTheme);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [contextOpen, setContextOpen] = useState(true);
  const [contextTab, setContextTab] = useState<ContextTab>("context");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sidebarSearch, setSidebarSearch] = useState("");
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<ComposerMode>("executive_insight");
  const [domain, setDomain] = useState("support");
  const [asking, setAsking] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [enrichingId, setEnrichingId] = useState<string | null>(null);
  const [operations, setOperations] = useState<OperationsStatus>(DEMO_OPERATIONS);
  const [operationsLive, setOperationsLive] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const brandMarkUrl = `${import.meta.env.BASE_URL}ai-brain-mark.svg`;

  useEffect(() => {
    document.body.classList.add("owui-active");
    return () => document.body.classList.remove("owui-active");
  }, []);

  useEffect(() => {
    window.localStorage.setItem("ukb-openwebui-theme", theme);
  }, [theme]);

  useEffect(() => {
    const update = () => setSection(sectionFromLocation());
    window.addEventListener("popstate", update);
    return () => window.removeEventListener("popstate", update);
  }, []);

  useEffect(() => {
    if (!pendingQuestion || !brain.contextPack || brain.contextPack.question !== pendingQuestion) return;
    setMessages((current) => [
      ...current,
      {
        id: messageId("assistant"),
        role: "assistant",
        content: brain.contextPack?.answer_guidance ?? "The governed context pack is ready.",
        pack: brain.contextPack,
        createdAt: new Date().toISOString()
      }
    ]);
    setPendingQuestion(null);
    setAsking(false);
    setContextOpen(true);
    setContextTab("context");
  }, [brain.contextPack, pendingQuestion]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, asking]);

  useEffect(() => {
    const apiToken = String(import.meta.env.VITE_UKB_API_TOKEN || "");
    if (!API_BASE || !apiToken) {
      setOperations(DEMO_OPERATIONS);
      setOperationsLive(false);
      return;
    }
    const controller = new AbortController();
    fetch(`${API_BASE}/v1/knowledge-operations/status`, {
      headers: { Authorization: `Bearer ${apiToken}` },
      signal: controller.signal
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(String(response.status));
        return response.json() as Promise<OperationsStatus>;
      })
      .then((payload) => {
        setOperations(payload);
        setOperationsLive(true);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setOperations(DEMO_OPERATIONS);
          setOperationsLive(false);
        }
      });
    return () => controller.abort();
  }, []);

  const recentChats = useMemo(() => {
    const generated = brain.objects.slice(0, 5).map((object) => ({
      id: object.id,
      title: object.title,
      subtitle: object.domain || "Published memory"
    }));
    return generated.length
      ? generated
      : [
          { id: "metric", title: "Incident Resolution Time", subtitle: "Metric definition" },
          { id: "lineage", title: "Resolution-time lineage", subtitle: "Evidence trace" },
          { id: "coverage", title: "Context coverage review", subtitle: "Governance" }
        ];
  }, [brain.objects]);

  const navigationItems = useMemo(
    () =>
      [
        { section: "chat" as const, label: "Brain Chat", icon: "message" as const, count: null },
        { section: "sources" as const, label: "Sources", icon: "upload" as const, count: brain.sources.length },
        { section: "enrich" as const, label: "Enrichment", icon: "wand" as const, count: brain.stats.enrichedReviews },
        { section: "review" as const, label: "Review queue", icon: "review" as const, count: brain.reviewItems.length },
        { section: "publish" as const, label: "Published memory", icon: "database" as const, count: brain.objects.length },
        { section: "memory" as const, label: "Memory graph", icon: "network" as const, count: brain.graph.nodes.length }
      ].filter((item) => item.label.toLowerCase().includes(sidebarSearch.trim().toLowerCase())),
    [
      brain.graph.nodes.length,
      brain.objects.length,
      brain.reviewItems.length,
      brain.sources.length,
      brain.stats.enrichedReviews,
      sidebarSearch
    ]
  );

  function navigate(next: BrainSection) {
    const url = new URL(window.location.href);
    url.searchParams.delete("page");
    url.searchParams.delete("view");
    if (next === "operations") url.searchParams.set("view", "operations");
    else if (next !== "chat") url.searchParams.set("section", next);
    else url.searchParams.delete("section");
    url.hash = "";
    window.history.pushState({}, "", url);
    setSection(next);
    setMobileSidebarOpen(false);
  }

  function newChat() {
    setMessages([]);
    setQuestion("");
    setPendingQuestion(null);
    setAsking(false);
    navigate("chat");
    window.setTimeout(() => textareaRef.current?.focus(), 0);
  }

  async function submitQuestion(event?: FormEvent) {
    event?.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || asking) return;
    const request: ContextPackRequest = {
      question: trimmed,
      user_id: "ui.consumer",
      domains: domain.trim() ? [domain.trim()] : [],
      mode
    };
    setMessages((current) => [
      ...current,
      {
        id: messageId("user"),
        role: "user",
        content: trimmed,
        createdAt: new Date().toISOString()
      }
    ]);
    setQuestion("");
    setAsking(true);
    setPendingQuestion(trimmed);
    try {
      await brain.askBrain(request);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: messageId("assistant"),
          role: "assistant",
          content: error instanceof Error ? error.message : "The governed context request failed.",
          createdAt: new Date().toISOString()
        }
      ]);
      setPendingQuestion(null);
      setAsking(false);
    }
  }

  function useSuggestion(prompt: string, nextMode: ComposerMode) {
    navigate("chat");
    setQuestion(prompt);
    setMode(nextMode);
    window.setTimeout(() => textareaRef.current?.focus(), 0);
  }

  function handleComposerKeyDown(event: ReactKeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submitQuestion();
    }
  }

  async function runEnrichment(reviewItemId: string) {
    setEnrichingId(reviewItemId);
    try {
      await brain.enrichReview(reviewItemId);
    } finally {
      setEnrichingId(null);
    }
  }

  const shellClasses = [
    "owui-shell",
    `owui-theme-${theme}`,
    sidebarCollapsed ? "is-sidebar-collapsed" : "",
    contextOpen ? "is-context-open" : "",
    mobileSidebarOpen ? "is-mobile-sidebar-open" : ""
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={shellClasses} data-theme={theme}>
      <a className="owui-skip-link" href="#owui-main">Skip to main content</a>
      <div className="owui-mobile-scrim" onClick={() => setMobileSidebarOpen(false)} aria-hidden="true" />

      <aside className="owui-sidebar" aria-label="AI Brain navigation">
        <div className="owui-sidebar-top">
          <button
            type="button"
            className="owui-brand"
            onClick={() => navigate("chat")}
            aria-label="Open Brain Chat"
          >
            <span className="owui-brand-mark"><img src={brandMarkUrl} alt="" /></span>
            <span className="owui-brand-copy"><strong>AI Brain</strong><small>Unified Knowledge Base</small></span>
          </button>
          <button
            type="button"
            className="owui-icon-button owui-collapse-button"
            onClick={() => setSidebarCollapsed((current) => !current)}
            aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <Icon name="panel" />
          </button>
        </div>

        <button type="button" className="owui-new-chat" onClick={newChat}>
          <Icon name="plus" /><span>New brain chat</span>
        </button>

        <label className="owui-sidebar-search">
          <Icon name="search" />
          <input
            value={sidebarSearch}
            onChange={(event) => setSidebarSearch(event.target.value)}
            placeholder="Search workspace"
            aria-label="Search AI Brain workspace"
          />
        </label>

        <nav className="owui-primary-nav" aria-label="Primary workspace">
          <p>Workspace</p>
          {navigationItems.map((item) => (
            <button
              key={item.section}
              type="button"
              className={section === item.section ? "is-active" : ""}
              onClick={() => navigate(item.section)}
              aria-current={section === item.section ? "page" : undefined}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
              {typeof item.count === "number" && <small>{item.count}</small>}
            </button>
          ))}
        </nav>

        <div className="owui-recent-list">
          <div className="owui-sidebar-group-heading"><span>Recent memory</span><button type="button" aria-label="Recent memory options">•••</button></div>
          {recentChats.map((chat) => (
            <button key={chat.id} type="button" onClick={() => useSuggestion(`Explain ${chat.title} using approved context.`, "default")}>
              <span>{chat.title}</span><small>{chat.subtitle}</small>
            </button>
          ))}
        </div>

        <nav className="owui-secondary-nav" aria-label="Governance tools">
          <button type="button" className={section === "operations" ? "is-active" : ""} onClick={() => navigate("operations")}>
            <Icon name="layers" /><span>Knowledge operations</span>
          </button>
          <button type="button" className={section === "activity" ? "is-active" : ""} onClick={() => navigate("activity")}>
            <Icon name="activity" /><span>Audit activity</span>
          </button>
          <button type="button" className={section === "help" ? "is-active" : ""} onClick={() => navigate("help")}>
            <Icon name="help" /><span>Help & guides</span>
          </button>
        </nav>

        <div className="owui-sidebar-footer">
          <button type="button" className="owui-profile" onClick={() => setSettingsOpen(true)}>
            <span className="owui-avatar"><Icon name="user" /></span>
            <span><strong>{brain.demoMode ? "Demo administrator" : "Governed user"}</strong><small>{brain.demoMode ? "Synthetic workspace" : brain.environment}</small></span>
            <Icon name="settings" />
          </button>
        </div>
      </aside>

      <section className="owui-center-column">
        <header className="owui-topbar">
          <div className="owui-topbar-left">
            <button type="button" className="owui-icon-button owui-mobile-menu" onClick={() => setMobileSidebarOpen(true)} aria-label="Open navigation">
              <Icon name="menu" />
            </button>
            <button type="button" className="owui-model-selector" onClick={() => navigate("chat")}>
              <span className="owui-model-icon"><Icon name="brain" /></span>
              <span><strong>Governed AI Brain</strong><small>{brain.aiStatus.provider} · {brain.aiStatus.model}</small></span>
              <Icon name="chevron" />
            </button>
          </div>
          <div className="owui-topbar-actions">
            <span className={`owui-runtime-pill ${brain.demoMode ? "is-demo" : "is-live"}`}>
              <span />{brain.loading ? "Checking" : brain.demoMode ? "Browser demo" : "Private runtime"}
            </span>
            <button type="button" className="owui-icon-button" onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))} aria-label={`Use ${theme === "dark" ? "light" : "dark"} theme`}>
              <Icon name={theme === "dark" ? "sun" : "moon"} />
            </button>
            <button type="button" className={`owui-icon-button ${contextOpen ? "is-active" : ""}`} onClick={() => setContextOpen((current) => !current)} aria-label="Toggle context panel">
              <Icon name="panel" />
            </button>
          </div>
        </header>

        <main className="owui-main" id="owui-main">
          {section === "chat" ? (
            <ChatWorkspace
              messages={messages}
              asking={asking}
              contextPack={brain.contextPack}
              demoMode={brain.demoMode}
              error={brain.error}
              suggestions={SUGGESTIONS}
              onSuggestion={useSuggestion}
              chatEndRef={chatEndRef}
            />
          ) : (
            <WorkspaceSurface
              section={section}
              brain={brain}
              operations={operations}
              operationsLive={operationsLive}
              enrichingId={enrichingId}
              onRunEnrichment={runEnrichment}
              onNavigate={navigate}
            />
          )}
        </main>

        {section === "chat" && (
          <form className="owui-composer-wrap" onSubmit={submitQuestion}>
            <div className="owui-composer-tools">
              <button type="button" onClick={() => navigate("sources")}><Icon name="plus" /><span>Add source</span></button>
              <button type="button" onClick={() => setContextOpen(true)}><Icon name="shield" /><span>Context coverage</span></button>
              <span><Icon name="brain" />{brain.aiStatus.local_only ? "Local-only model" : brain.aiStatus.mode}</span>
            </div>
            <div className="owui-composer" id="brain-composer">
              <button type="button" className="owui-attach" onClick={() => navigate("sources")} aria-label="Attach or ingest a source"><Icon name="plus" /></button>
              <textarea
                ref={textareaRef}
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={handleComposerKeyDown}
                rows={1}
                placeholder="Ask the governed AI Brain"
                aria-label="Ask the governed AI Brain"
              />
              <div className="owui-composer-controls">
                <label>
                  <span className="visually-hidden">Context mode</span>
                  <select value={mode} onChange={(event) => setMode(event.target.value as ComposerMode)} aria-label="Context mode">
                    {Object.entries(MODE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                  </select>
                </label>
                <label>
                  <span className="visually-hidden">Business domain</span>
                  <input value={domain} onChange={(event) => setDomain(event.target.value)} aria-label="Business domain" title="Business domain" />
                </label>
                <button type="submit" className="owui-send" disabled={!question.trim() || asking} aria-label="Send question">
                  {asking ? <span className="owui-spinner" /> : <Icon name="arrow" />}
                </button>
              </div>
            </div>
            <p>AI output is advisory. Only human-approved, published memory is treated as organizational knowledge.</p>
          </form>
        )}
      </section>

      <aside className="owui-context-panel" aria-label="Governed context panel">
        <header>
          <div><strong>Context</strong><small>{brain.contextPack ? brain.contextPack.context_pack_id : "No pack selected"}</small></div>
          <button type="button" className="owui-icon-button" onClick={() => setContextOpen(false)} aria-label="Close context panel"><Icon name="close" /></button>
        </header>
        <div className="owui-context-tabs" role="tablist" aria-label="Context details">
          {(["context", "sources", "governance"] as ContextTab[]).map((tab) => (
            <button key={tab} type="button" role="tab" aria-selected={contextTab === tab} className={contextTab === tab ? "is-active" : ""} onClick={() => setContextTab(tab)}>
              {tab === "context" ? "Context" : tab === "sources" ? "Sources" : "Governance"}
            </button>
          ))}
        </div>
        <ContextPanelContent
          tab={contextTab}
          pack={brain.contextPack}
          provider={`${brain.aiStatus.provider} · ${brain.aiStatus.model}`}
          demoMode={brain.demoMode}
          stats={brain.stats}
          sourcesCount={brain.sources.length}
          onNavigate={navigate}
        />
      </aside>

      {settingsOpen && (
        <SettingsDialog
          theme={theme}
          onTheme={setTheme}
          provider={`${brain.aiStatus.provider} · ${brain.aiStatus.model}`}
          environment={brain.demoMode ? "Browser demo" : brain.environment}
          onClose={() => setSettingsOpen(false)}
          onOpenAdvanced={onOpenAdvanced}
          onOpenGuided={onOpenGuided}
        />
      )}
    </div>
  );
}

function ChatWorkspace({
  messages,
  asking,
  contextPack,
  demoMode,
  error,
  suggestions,
  onSuggestion,
  chatEndRef
}: {
  messages: ChatMessage[];
  asking: boolean;
  contextPack: ContextPack | null;
  demoMode: boolean;
  error: string | null;
  suggestions: typeof SUGGESTIONS;
  onSuggestion: (prompt: string, mode: ComposerMode) => void;
  chatEndRef: RefObject<HTMLDivElement | null>;
}) {
  if (messages.length === 0 && !asking) {
    return (
      <div className="owui-chat-empty">
        <div className="owui-empty-mark"><Icon name="brain" /></div>
        <p className="owui-empty-kicker">Governed organizational intelligence</p>
        <h1>What should the AI Brain understand?</h1>
        <p className="owui-empty-copy">
          Ask for definitions, lineage, investigation context, or coverage. The response is assembled only from authorized, published memory.
        </p>
        {error && <div className="owui-inline-notice"><Icon name="shield" /><span>{error}</span></div>}
        <div className="owui-suggestion-grid">
          {suggestions.map((suggestion) => (
            <button key={suggestion.title} type="button" onClick={() => onSuggestion(suggestion.prompt, suggestion.mode)}>
              <span className="owui-suggestion-icon"><Icon name={suggestion.icon} /></span>
              <span><strong>{suggestion.title}</strong><small>{suggestion.prompt}</small></span>
              <Icon name="arrow" />
            </button>
          ))}
        </div>
        <div className="owui-empty-status">
          <span><i className={demoMode ? "is-demo" : "is-live"} />{demoMode ? "Synthetic browser state" : "Connected private runtime"}</span>
          <span><Icon name="shield" />Authorization before retrieval</span>
          <span><Icon name="network" />Citations and coverage receipt</span>
        </div>
      </div>
    );
  }

  return (
    <div className="owui-chat-thread" aria-live="polite">
      <div className="owui-chat-thread-inner">
        {messages.map((message) => (
          <article key={message.id} className={`owui-message is-${message.role}`}>
            <div className="owui-message-avatar">{message.role === "assistant" ? <Icon name="brain" /> : <Icon name="user" />}</div>
            <div className="owui-message-content">
              <div className="owui-message-heading"><strong>{message.role === "assistant" ? "AI Brain" : "You"}</strong><small>{new Date(message.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</small></div>
              <p>{message.content}</p>
              {message.pack && <PackSummary pack={message.pack} />}
            </div>
          </article>
        ))}
        {asking && (
          <article className="owui-message is-assistant is-thinking">
            <div className="owui-message-avatar"><Icon name="brain" /></div>
            <div className="owui-message-content">
              <div className="owui-message-heading"><strong>AI Brain</strong><small>Building governed context</small></div>
              <div className="owui-thinking"><span /><span /><span /></div>
              <p>Searching authorized memory partitions, checking provenance, and preparing a Context Coverage Receipt.</p>
            </div>
          </article>
        )}
        {!asking && contextPack && messages.length === 0 && <PackSummary pack={contextPack} />}
        <div ref={chatEndRef} />
      </div>
    </div>
  );
}

function PackSummary({ pack }: { pack: ContextPack }) {
  return (
    <div className="owui-pack-summary">
      <div className="owui-pack-summary-head">
        <span className={`owui-access-badge is-${pack.access_decision}`}><Icon name={pack.access_decision === "allowed" ? "check" : "shield"} />{pack.access_decision}</span>
        <span>{Math.round(pack.confidence * 100)}% confidence</span>
        <span>{pack.retrieval_engine ?? "governed retrieval"}</span>
      </div>
      <div className="owui-pack-metrics">
        <div><strong>{pack.knowledge_objects.length}</strong><span>approved objects</span></div>
        <div><strong>{pack.citations?.length ?? pack.evidence.length}</strong><span>citations</span></div>
        <div><strong>{pack.missing_context.length}</strong><span>missing partitions</span></div>
        <div><strong>{pack.conflicts?.length ?? 0}</strong><span>conflicts</span></div>
      </div>
      {pack.ai_guidance && <div className="owui-pack-guidance"><Icon name="sparkles" /><span>{pack.ai_guidance}</span></div>}
      {pack.caveats.length > 0 && <div className="owui-pack-caveat"><Icon name="shield" /><span>{pack.caveats.join(" · ")}</span></div>}
    </div>
  );
}

function WorkspaceSurface({
  section,
  brain,
  operations,
  operationsLive,
  enrichingId,
  onRunEnrichment,
  onNavigate
}: {
  section: Exclude<BrainSection, "chat">;
  brain: ReturnType<typeof useBrainState>;
  operations: OperationsStatus;
  operationsLive: boolean;
  enrichingId: string | null;
  onRunEnrichment: (id: string) => Promise<void>;
  onNavigate: (section: BrainSection) => void;
}) {
  const meta = SECTION_META[section];
  return (
    <div className="owui-workspace-surface">
      <header className="owui-surface-header">
        <div className="owui-surface-icon"><Icon name={meta.icon} /></div>
        <div><p>{SECTION_LABELS[section]}</p><h1>{meta.title}</h1><span>{meta.copy}</span></div>
        <div className="owui-surface-actions">
          {section !== "help" && <button type="button" onClick={() => onNavigate("help")}><Icon name="help" />Guide</button>}
          {section !== "sources" && <button type="button" className="is-primary" onClick={() => onNavigate("sources")}><Icon name="plus" />Add source</button>}
        </div>
      </header>
      <div className="owui-surface-body">
        {section === "sources" && (
          <IngestionStudio demoMode={brain.demoMode} onSubmitContext={brain.submitContext} onCompleted={() => onNavigate("enrich")} />
        )}
        {section === "enrich" && (
          <EnrichStep items={brain.reviewItems} aiStatus={brain.aiStatus} onEnrich={onRunEnrichment} enrichingId={enrichingId} demoMode={brain.demoMode} />
        )}
        {section === "review" && (
          <ReviewStep
            items={brain.reviewItems}
            reviewer={REVIEWER}
            onApprove={brain.approveReview}
            onReject={brain.rejectReview}
            onRequestChanges={brain.requestChanges}
            onRevise={brain.reviseReview}
            demoMode={brain.demoMode}
          />
        )}
        {section === "publish" && (
          <PublishStep approvedItems={brain.approvedItems} objects={brain.objects} onPublish={brain.publishReview} demoMode={brain.demoMode} />
        )}
        {section === "memory" && <ObsidianGraphView graph={brain.graph} />}
        {section === "operations" && <OperationsView status={operations} live={operationsLive} brain={brain} />}
        {section === "activity" && <ActivityLedger records={brain.ledger} />}
        {section === "help" && <HelpView onNavigate={onNavigate} />}
      </div>
    </div>
  );
}

function OperationsView({ status, live, brain }: { status: OperationsStatus; live: boolean; brain: ReturnType<typeof useBrainState> }) {
  const cards: Array<{ icon: IconName; title: string; value: string; copy: string; tone: string }> = [
    { icon: "user", title: "Identity", value: status.auth_method, copy: `${status.subject} · ${status.tenant_id}`, tone: "blue" },
    { icon: "shield", title: "Quality firewall", value: String(status.quarantined_sources), copy: `${status.quality_assessments} assessments evaluated`, tone: "amber" },
    { icon: "review", title: "Reviewer operations", value: String(status.active_assignments || brain.reviewItems.length), copy: "Assigned, attributable human decisions", tone: "violet" },
    { icon: "archive", title: "Source refresh", value: String(status.active_subscriptions), copy: "Checksum-aware connector subscriptions", tone: "green" },
    { icon: "search", title: "Recall evaluation", value: String(status.retrieval_feedback), copy: "Feedback observations and safe abstention", tone: "rose" }
  ];
  return (
    <div className="owui-operations-view">
      <div className="owui-operations-banner">
        <span className={live ? "is-live" : "is-demo"}><i />{live ? "Live tenant state" : "Synthetic preview"}</span>
        <strong>{status.capabilities.length}/5 control planes active</strong>
        <p>Operational controls surround the model so evidence quality, human decisions, source freshness, and retrieval behavior remain governable.</p>
      </div>
      <div className="owui-operations-grid">
        {cards.map((card) => (
          <article key={card.title} className={`owui-operation-card is-${card.tone}`}>
            <span><Icon name={card.icon} /></span>
            <div><p>{card.title}</p><strong>{card.value}</strong><small>{card.copy}</small></div>
          </article>
        ))}
      </div>
      <section className="owui-operating-loop">
        <header><p>Governed knowledge supply chain</p><h2>Every source earns its place in memory.</h2></header>
        <ol>
          {[
            ["Collect", "Capture evidence and preserve its original form."],
            ["Screen", "Accept, warn, quarantine, or reject before model use."],
            ["Enrich", "Let local Ollama propose structure, never authority."],
            ["Govern", "Assign people to review, discuss, approve, and publish."],
            ["Recall", "Retrieve authorized memory with citations and coverage."],
            ["Maintain", "Refresh sources, supersede facts, and evaluate recall."]
          ].map(([title, copy], index) => <li key={title}><span>{index + 1}</span><div><strong>{title}</strong><p>{copy}</p></div></li>)}
        </ol>
      </section>
    </div>
  );
}

function HelpView({ onNavigate }: { onNavigate: (section: BrainSection) => void }) {
  return (
    <div className="owui-help-view">
      <section className="owui-help-steps">
        <h2>End-to-end workflow</h2>
        <div>
          {[
            ["1", "Submit evidence", "Choose a source, set governance metadata, preview extraction, and create candidates.", "sources" as BrainSection],
            ["2", "Enrich locally", "Use schema-validated local AI to classify and structure evidence for review.", "enrich" as BrainSection],
            ["3", "Review and decide", "Inspect evidence, risks, ownership, and AI findings before a human decision.", "review" as BrainSection],
            ["4", "Publish memory", "A separate publisher turns approved candidates into official retrievable memory.", "publish" as BrainSection],
            ["5", "Recall safely", "Brain Chat searches authorized partitions and returns citations, caveats, and coverage.", "chat" as BrainSection]
          ].map(([number, title, copy, destination]) => (
            <button key={number} type="button" onClick={() => onNavigate(destination as BrainSection)}>
              <span>{number}</span><div><strong>{title}</strong><p>{copy}</p></div><Icon name="arrow" />
            </button>
          ))}
        </div>
      </section>
      <section className="owui-faq-grid">
        {[
          ["Does the LLM publish knowledge?", "No. AI creates proposals and review guidance. Human approval and explicit publication remain separate controls."],
          ["Where does the local model run?", "Ollama belongs behind the private FastAPI runtime. GitHub Pages never calls a local model directly."],
          ["What is authoritative?", "PostgreSQL and preserved source evidence are authoritative. Zvec and Graphiti are rebuildable retrieval projections."],
          ["What happens when context is incomplete?", "The Context Coverage Receipt exposes missing, stale, unavailable, excluded, conflicting, or superseded knowledge."],
          ["Can this support many tenants?", "Tenant identity, role, classification, policy, domain, entity, metric, and effective date are enforced before content is returned."],
          ["Why does the public site show demo data?", "GitHub Pages is static. Real persistence, OIDC, Ollama, connectors, and governed mutations require the private runtime."]
        ].map(([question, answer]) => <article key={question}><Icon name="help" /><div><h3>{question}</h3><p>{answer}</p></div></article>)}
      </section>
    </div>
  );
}

function ContextPanelContent({
  tab,
  pack,
  provider,
  demoMode,
  stats,
  sourcesCount,
  onNavigate
}: {
  tab: ContextTab;
  pack: ContextPack | null;
  provider: string;
  demoMode: boolean;
  stats: ReturnType<typeof useBrainState>["stats"];
  sourcesCount: number;
  onNavigate: (section: BrainSection) => void;
}) {
  if (!pack) {
    return (
      <div className="owui-context-empty">
        <span className="owui-context-empty-icon"><Icon name="layers" /></span>
        <h2>No context pack yet</h2>
        <p>Ask a question in Brain Chat to see retrieved memory, citations, coverage, and governance decisions here.</p>
        <dl>
          <div><dt>Provider</dt><dd>{provider}</dd></div>
          <div><dt>Runtime</dt><dd>{demoMode ? "Synthetic demo" : "Connected"}</dd></div>
          <div><dt>Published memory</dt><dd>{stats.published}</dd></div>
          <div><dt>Source evidence</dt><dd>{sourcesCount}</dd></div>
        </dl>
        <button type="button" onClick={() => onNavigate("sources")}><Icon name="plus" />Add trusted context</button>
      </div>
    );
  }

  if (tab === "sources") {
    const citations = pack.citations ?? [];
    return (
      <div className="owui-context-scroll">
        <div className="owui-context-section-head"><span><Icon name="file" /></span><div><strong>Evidence and citations</strong><small>{citations.length || pack.evidence.length} retrieved references</small></div></div>
        <div className="owui-citation-list">
          {citations.length
            ? citations.map((citation, index) => (
                <article key={citation.citation_id}><span>{index + 1}</span><div><strong>{citation.title}</strong><small>{citation.locator ?? citation.source_id}</small><p>“{citation.quote}”</p></div></article>
              ))
            : pack.evidence.map((source, index) => (
                <article key={source.source_id}><span>{index + 1}</span><div><strong>{source.title}</strong><small>{source.source_type} · {source.domain}</small><p>{source.content_excerpt}</p></div></article>
              ))}
        </div>
        <button type="button" className="owui-panel-action" onClick={() => onNavigate("sources")}><Icon name="upload" />Manage sources</button>
      </div>
    );
  }

  if (tab === "governance") {
    return (
      <div className="owui-context-scroll">
        <div className={`owui-governance-decision is-${pack.access_decision}`}><Icon name={pack.access_decision === "allowed" ? "check" : "shield"} /><div><strong>{pack.access_decision === "allowed" ? "Authorized context" : "Access denied"}</strong><small>{pack.mode}</small></div></div>
        <ContextList title="Missing context" items={pack.missing_context} empty="No required partitions reported missing." icon="layers" />
        <ContextList title="Conflicts" items={pack.conflicts ?? []} empty="No conflicting approved knowledge reported." icon="shield" />
        <ContextList title="Caveats" items={pack.caveats} empty="No additional caveats." icon="help" />
        <ContextList title="Recommended follow-ups" items={pack.recommended_followups} empty="No follow-up questions suggested." icon="arrow" />
      </div>
    );
  }

  const factors = pack.confidence_factors;
  return (
    <div className="owui-context-scroll">
      <div className="owui-confidence-card">
        <div className="owui-confidence-ring" style={{ "--confidence": `${Math.round(pack.confidence * 100) * 3.6}deg` } as CSSProperties}>
          <span><strong>{Math.round(pack.confidence * 100)}%</strong><small>confidence</small></span>
        </div>
        <div><strong>Context pack ready</strong><small>{pack.retrieval_engine ?? "governed retrieval"}</small><p>{pack.answer_guidance}</p></div>
      </div>
      {factors && (
        <div className="owui-factor-list">
          <FactorBar label="Retrieval" value={factors.retrieval} />
          <FactorBar label="Evidence coverage" value={factors.evidence_coverage} />
          <FactorBar label="Source authority" value={factors.source_authority} />
          <FactorBar label="Freshness" value={factors.freshness} />
          <FactorBar label="Conflict penalty" value={Math.max(0, 1 - factors.conflict_penalty)} />
        </div>
      )}
      <div className="owui-object-list">
        <div className="owui-context-section-head"><span><Icon name="database" /></span><div><strong>Approved objects</strong><small>{pack.knowledge_objects.length} used for this request</small></div></div>
        {pack.knowledge_objects.map((object) => <article key={object.id}><span><Icon name="file" /></span><div><strong>{object.title}</strong><small>{object.type} · {object.domain} · v{object.version ?? 1}</small><p>{object.summary}</p></div></article>)}
      </div>
    </div>
  );
}

function ContextList({ title, items, empty, icon }: { title: string; items: string[]; empty: string; icon: IconName }) {
  return (
    <section className="owui-context-list-section">
      <header><Icon name={icon} /><strong>{title}</strong><span>{items.length}</span></header>
      {items.length ? <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul> : <p>{empty}</p>}
    </section>
  );
}

function FactorBar({ label, value }: { label: string; value: number }) {
  const percent = Math.round(value * 100);
  return <div><header><span>{label}</span><strong>{percent}%</strong></header><div><i style={{ width: `${percent}%` }} /></div></div>;
}

function SettingsDialog({
  theme,
  onTheme,
  provider,
  environment,
  onClose,
  onOpenAdvanced,
  onOpenGuided
}: {
  theme: ThemeMode;
  onTheme: (theme: ThemeMode) => void;
  provider: string;
  environment: string;
  onClose: () => void;
  onOpenAdvanced: () => void;
  onOpenGuided: () => void;
}) {
  return (
    <div className="owui-dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="owui-settings-dialog" role="dialog" aria-modal="true" aria-labelledby="owui-settings-title" onMouseDown={(event) => event.stopPropagation()}>
        <header><div><p>Workspace preferences</p><h2 id="owui-settings-title">Settings</h2></div><button type="button" className="owui-icon-button" onClick={onClose} aria-label="Close settings"><Icon name="close" /></button></header>
        <div className="owui-settings-body">
          <section><h3>Appearance</h3><p>Choose the interface theme for this browser.</p><div className="owui-theme-options"><button type="button" className={theme === "light" ? "is-active" : ""} onClick={() => onTheme("light")}><Icon name="sun" />Light</button><button type="button" className={theme === "dark" ? "is-active" : ""} onClick={() => onTheme("dark")}><Icon name="moon" />Dark</button></div></section>
          <section><h3>Runtime</h3><dl><div><dt>Environment</dt><dd>{environment}</dd></div><div><dt>AI provider</dt><dd>{provider}</dd></div><div><dt>API base</dt><dd>{API_BASE || "Not configured"}</dd></div></dl></section>
          <section><h3>Experience</h3><div className="owui-settings-actions"><button type="button" onClick={onOpenGuided}><Icon name="sparkles" />Open guided workflow</button><button type="button" onClick={onOpenAdvanced}><Icon name="settings" />Open advanced console</button></div></section>
          <section className="owui-settings-boundary"><Icon name="shield" /><div><strong>Governance boundary</strong><p>The interface may simplify navigation, but it never gives the LLM authority to approve, publish, or bypass retrieval policy.</p></div></section>
        </div>
      </section>
    </div>
  );
}

function Icon({ name, className = "" }: { name: IconName; className?: string }) {
  const paths: Record<IconName, ReactNode> = {
    activity: <><path d="M4 12h3l2-6 4 12 2-6h5" /></>,
    archive: <><path d="M4 7h16v13H4z" /><path d="M3 4h18v3H3zM9 11h6" /></>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6" /></>,
    brain: <><path d="M9.5 4.5A3.5 3.5 0 0 0 6 8v1a3 3 0 0 0 0 6v1a3.5 3.5 0 0 0 3.5 3.5c1 0 1.8-.4 2.5-1V5.5c-.7-.6-1.5-1-2.5-1Z" /><path d="M14.5 4.5A3.5 3.5 0 0 1 18 8v1a3 3 0 0 1 0 6v1a3.5 3.5 0 0 1-3.5 3.5c-1 0-1.8-.4-2.5-1V5.5c.7-.6 1.5-1 2.5-1ZM8 10h4M12 14h4" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    chevron: <path d="m9 10 3 3 3-3" />,
    close: <><path d="m6 6 12 12M18 6 6 18" /></>,
    database: <><ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" /></>,
    file: <><path d="M6 3h8l4 4v14H6z" /><path d="M14 3v5h5M9 13h6M9 17h5" /></>,
    help: <><circle cx="12" cy="12" r="9" /><path d="M9.7 9a2.4 2.4 0 1 1 3.5 2.1c-.8.4-1.2.9-1.2 1.9M12 17h.01" /></>,
    home: <><path d="m3 11 9-8 9 8" /><path d="M5 10v11h14V10M9 21v-7h6v7" /></>,
    layers: <><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="m3 12 9 5 9-5M3 16l9 5 9-5" /></>,
    menu: <><path d="M4 7h16M4 12h16M4 17h16" /></>,
    message: <><path d="M4 5h16v12H8l-4 4V5Z" /><path d="M8 9h8M8 13h5" /></>,
    moon: <path d="M20 15.5A8.5 8.5 0 0 1 8.5 4 8.5 8.5 0 1 0 20 15.5Z" />,
    network: <><circle cx="6" cy="6" r="2" /><circle cx="18" cy="6" r="2" /><circle cx="12" cy="18" r="2" /><path d="m8 7 3 9M16 7l-3 9M8 6h8" /></>,
    panel: <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M9 4v16" /></>,
    plus: <><path d="M12 5v14M5 12h14" /></>,
    review: <><path d="M6 3h12v18H6z" /><path d="m9 9 2 2 4-4M9 15h6" /></>,
    search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
    send: <><path d="m3 3 18 9-18 9 4-9-4-9Z" /><path d="M7 12h14" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6 1.7 1.7 0 0 0 10 3V2.8h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9A1.7 1.7 0 0 0 21 10h.2v4H21a1.7 1.7 0 0 0-1.6 1Z" /></>,
    shield: <><path d="M12 3 4 6v5c0 5 3.3 8.5 8 10 4.7-1.5 8-5 8-10V6l-8-3Z" /><path d="m9 12 2 2 4-4" /></>,
    sparkles: <><path d="m12 3 1.2 3.8L17 8l-3.8 1.2L12 13l-1.2-3.8L7 8l3.8-1.2L12 3ZM5 14l.8 2.2L8 17l-2.2.8L5 20l-.8-2.2L2 17l2.2-.8L5 14ZM19 13l.7 1.8 1.8.7-1.8.7L19 18l-.7-1.8-1.8-.7 1.8-.7L19 13Z" /></>,
    sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
    upload: <><path d="M12 16V4M7 9l5-5 5 5" /><path d="M4 15v5h16v-5" /></>,
    user: <><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></>,
    wand: <><path d="m4 20 11-11M13 5l2-2 6 6-2 2-6-6Z" /><path d="M5 4v3M3.5 5.5h3M19 15v4M17 17h4" /></>
  };
  return <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}
