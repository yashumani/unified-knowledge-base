import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode
} from "react";
import {
  CopilotKit,
  useAgent,
  useAgentContext,
  useCopilotKit,
  useFrontendTool
} from "@copilotkit/react-core/v2";
import { randomUUID } from "@copilotkit/shared";
import { z } from "zod";
import type { ContextPack, ContextPackRequest } from "../types";

const RUNTIME_URL = String(import.meta.env.VITE_COPILOTKIT_RUNTIME_URL || "").trim();
const RUNTIME_TOKEN = String(import.meta.env.VITE_COPILOTKIT_RUNTIME_TOKEN || "").trim();
const AGENT_ID = String(import.meta.env.VITE_COPILOTKIT_AGENT_ID || "default").trim() || "default";

const SECTION_VALUES = [
  "chat",
  "sources",
  "enrich",
  "review",
  "publish",
  "memory",
  "operations",
  "activity",
  "help"
] as const;

const MODE_VALUES = [
  "default",
  "executive_insight",
  "metric_definition",
  "lineage",
  "governance_review",
  "debug"
] as const;

const SOURCE_VALUES = [
  "text",
  "files",
  "folder",
  "zip",
  "google_drive",
  "crawl4ai",
  "git",
  "object_store"
] as const;

type CopilotNarrativeRequest = {
  question: string;
  contextPack: ContextPack;
  domain: string;
  mode: ContextPackRequest["mode"];
};

type CopilotGatewayValue = {
  enabled: boolean;
  running: boolean;
  ready: boolean;
  agentId: string;
  runtimeUrl: string | null;
  runGovernedNarrative: (request: CopilotNarrativeRequest) => Promise<string | null>;
};

const disabledValue: CopilotGatewayValue = {
  enabled: false,
  running: false,
  ready: false,
  agentId: AGENT_ID,
  runtimeUrl: null,
  runGovernedNarrative: async () => null
};

const CopilotGatewayContext = createContext<CopilotGatewayValue>(disabledValue);

export function CopilotKitGateway({ children }: { children: ReactNode }) {
  if (!RUNTIME_URL) {
    return <CopilotGatewayContext.Provider value={disabledValue}>{children}</CopilotGatewayContext.Provider>;
  }

  const headers = RUNTIME_TOKEN ? { Authorization: `Bearer ${RUNTIME_TOKEN}` } : undefined;
  return (
    <CopilotKit
      runtimeUrl={RUNTIME_URL}
      agent={AGENT_ID}
      headers={headers}
      useSingleEndpoint={false}
      showDevConsole={false}
      onError={({ error }) => console.error("CopilotKit runtime error", error)}
    >
      <ConnectedCopilotGateway>{children}</ConnectedCopilotGateway>
    </CopilotKit>
  );
}

export function useCopilotKitGateway(): CopilotGatewayValue {
  return useContext(CopilotGatewayContext);
}

function ConnectedCopilotGateway({ children }: { children: ReactNode }) {
  const { agent, isReady } = useAgent({ agentId: AGENT_ID });
  const { copilotkit } = useCopilotKit();
  const [locationState, setLocationState] = useState(() => currentWorkspaceLocation());

  useEffect(() => {
    const update = () => setLocationState(currentWorkspaceLocation());
    window.addEventListener("popstate", update);
    window.addEventListener("ukb:workspace-location", update);
    return () => {
      window.removeEventListener("popstate", update);
      window.removeEventListener("ukb:workspace-location", update);
    };
  }, []);

  const agentContext = useMemo(
    () => ({
      ...locationState,
      runtime: RUNTIME_URL,
      agent_id: AGENT_ID,
      public_static_host: window.location.hostname.endsWith("github.io")
    }),
    [locationState]
  );

  useAgentContext({
    description:
      "Current Unified Knowledge Base workspace state. This is read-only navigation context and never an authorization decision.",
    value: agentContext
  });

  useFrontendTool(
    {
      name: "navigate_ai_brain",
      description:
        "Navigate to a safe Unified Knowledge Base workspace section. This tool changes the browser view only; it does not approve, publish, or mutate knowledge.",
      parameters: z.object({
        section: z.enum(SECTION_VALUES).describe("The workspace section to open")
      }),
      handler: async ({ section }) => {
        navigateWorkspace(section);
        return { status: "navigated", section };
      }
    },
    []
  );

  useFrontendTool(
    {
      name: "open_ingestion_channel",
      description:
        "Open a governed source-ingestion channel so the user can preview evidence and create review candidates.",
      parameters: z.object({
        source: z.enum(SOURCE_VALUES).describe("The ingestion channel to open")
      }),
      handler: async ({ source }) => {
        const url = new URL(window.location.href);
        url.searchParams.delete("page");
        url.searchParams.delete("view");
        url.searchParams.set("section", "sources");
        url.searchParams.set("source", source);
        commitWorkspaceUrl(url);
        return { status: "opened", section: "sources", source };
      }
    },
    []
  );

  useFrontendTool(
    {
      name: "configure_brain_query",
      description:
        "Set the visible query mode and business domain in Brain Chat. This changes UI state only; UKB still performs authorization and retrieval.",
      parameters: z.object({
        mode: z.enum(MODE_VALUES).optional().describe("The governed Context Pack mode"),
        domain: z.string().trim().max(120).optional().describe("The business domain filter")
      }),
      handler: async ({ mode, domain }) => {
        window.dispatchEvent(
          new CustomEvent("ukb:copilot-query-config", {
            detail: { mode, domain }
          })
        );
        navigateWorkspace("chat");
        return { status: "configured", mode: mode ?? null, domain: domain ?? null };
      }
    },
    []
  );

  useFrontendTool(
    {
      name: "open_context_inspector",
      description:
        "Open the governed Context, Sources, or Governance inspector in the current UI.",
      parameters: z.object({
        tab: z.enum(["context", "sources", "governance"]).default("context")
      }),
      handler: async ({ tab }) => {
        window.dispatchEvent(
          new CustomEvent("ukb:copilot-context-inspector", {
            detail: { open: true, tab }
          })
        );
        return { status: "opened", tab };
      }
    },
    []
  );

  const runGovernedNarrative = useCallback(
    async ({ question, contextPack, domain, mode }: CopilotNarrativeRequest): Promise<string | null> => {
      const startingMessageCount = agent.messages.length;
      const compactPack = compactContextPack(contextPack);
      const instruction = [
        "Create the analyst-facing response for the question below.",
        "The supplied UKB Context Pack has already passed authorization-first retrieval and is the factual boundary.",
        "Do not add facts that are absent from the pack. Preserve access decisions, citations, caveats, missing context, and conflicts.",
        "Use the UKB MCP tools only when more governed lineage or context is necessary. Never call approval, publication, policy-change, deletion, or cache-invalidation tools.",
        `Question: ${question}`,
        `Visible domain: ${domain || "all authorized domains"}`,
        `Context mode: ${mode}`,
        `Governed Context Pack JSON: ${JSON.stringify(compactPack)}`
      ].join("\n\n");

      if (!isReady) return null;

      agent.addMessage({
        id: randomUUID(),
        role: "user",
        content: instruction
      });

      await copilotkit.runAgent({ agent });
      const candidates = await waitForAssistantMessages(agent, startingMessageCount);
      for (const message of candidates) {
        if (message.role !== "assistant") continue;
        const content = extractMessageText(message.content);
        if (content) return content;
      }
      return null;
    },
    [agent, copilotkit, isReady]
  );

  const value = useMemo<CopilotGatewayValue>(
    () => ({
      enabled: true,
      running: agent.isRunning,
      ready: isReady,
      agentId: AGENT_ID,
      runtimeUrl: RUNTIME_URL,
      runGovernedNarrative
    }),
    [agent.isRunning, isReady, runGovernedNarrative]
  );

  return <CopilotGatewayContext.Provider value={value}>{children}</CopilotGatewayContext.Provider>;
}

async function waitForAssistantMessages(
  agent: { messages: Array<{ role: string; content: unknown }> },
  startingMessageCount: number,
  timeoutMs = 5000
) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const candidates = agent.messages.slice(startingMessageCount).reverse();
    if (candidates.some((message) => message.role === "assistant" && extractMessageText(message.content))) {
      return candidates;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 25));
  }
  return agent.messages.slice(startingMessageCount).reverse();
}

function currentWorkspaceLocation() {
  const params = new URLSearchParams(window.location.search);
  return {
    section: params.get("section") || (params.get("view") === "operations" ? "operations" : "chat"),
    view: params.get("view") || "workspace",
    source_channel: params.get("source"),
    path: window.location.pathname
  };
}

function navigateWorkspace(section: (typeof SECTION_VALUES)[number]): void {
  const url = new URL(window.location.href);
  url.searchParams.delete("page");
  url.searchParams.delete("source");
  url.searchParams.delete("view");
  if (section === "operations") {
    url.searchParams.delete("section");
    url.searchParams.set("view", "operations");
  } else if (section === "chat") {
    url.searchParams.delete("section");
  } else {
    url.searchParams.set("section", section);
  }
  commitWorkspaceUrl(url);
}

function commitWorkspaceUrl(url: URL): void {
  url.hash = "";
  window.history.pushState({}, "", url);
  window.dispatchEvent(new PopStateEvent("popstate"));
  window.dispatchEvent(new Event("ukb:workspace-location"));
}

function compactContextPack(pack: ContextPack) {
  return {
    context_pack_id: pack.context_pack_id,
    question: pack.question,
    mode: pack.mode,
    access_decision: pack.access_decision,
    confidence: pack.confidence,
    confidence_factors: pack.confidence_factors,
    answer_guidance: pack.answer_guidance,
    ai_guidance: pack.ai_guidance,
    knowledge_objects: pack.knowledge_objects.map((object) => ({
      id: object.id,
      type: object.type,
      title: object.title,
      domain: object.domain,
      summary: object.summary,
      confidence: object.confidence,
      version: object.version,
      source_ids: object.source_ids,
      evidence_refs: object.evidence_refs
    })),
    citations: (pack.citations ?? []).map((citation) => ({
      citation_id: citation.citation_id,
      source_id: citation.source_id,
      title: citation.title,
      quote: citation.quote,
      locator: citation.locator
    })),
    evidence: pack.evidence.map((source) => ({
      source_id: source.source_id,
      title: source.title,
      source_type: source.source_type,
      domain: source.domain,
      content_excerpt: source.content_excerpt,
      source_uri: source.source_uri
    })),
    caveats: pack.caveats,
    conflicts: pack.conflicts ?? [],
    missing_context: pack.missing_context,
    recommended_followups: pack.recommended_followups,
    retrieval_engine: pack.retrieval_engine
  };
}

function extractMessageText(content: unknown): string {
  if (typeof content === "string") return content.trim();
  if (!Array.isArray(content)) return "";
  return content
    .map((item) => {
      if (typeof item === "string") return item;
      if (!item || typeof item !== "object") return "";
      const record = item as Record<string, unknown>;
      if (typeof record.text === "string") return record.text;
      if (typeof record.content === "string") return record.content;
      return "";
    })
    .filter(Boolean)
    .join("\n")
    .trim();
}
