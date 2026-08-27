import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { BuiltInAgent, CopilotRuntime, InMemoryAgentRunner } from "@copilotkit/runtime/v2";
import { createCopilotNodeListener } from "@copilotkit/runtime/v2/node";

const port = numberFromEnv("COPILOTKIT_PORT", 8200);
const host = process.env.COPILOTKIT_HOST?.trim() || "0.0.0.0";
const basePath = normalizeBasePath(process.env.COPILOTKIT_BASE_PATH || "/api/copilotkit");
const model = process.env.COPILOTKIT_MODEL?.trim() || "llama3.1";
const mcpUrl = process.env.COPILOTKIT_MCP_URL?.trim() || "http://mcp:8765/mcp";
const runtimeToken = process.env.COPILOTKIT_RUNTIME_TOKEN?.trim();
const requireAuth = booleanFromEnv("COPILOTKIT_REQUIRE_AUTH", Boolean(runtimeToken));
const allowedOrigins = csvSet(
  process.env.COPILOTKIT_ALLOWED_ORIGINS ||
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
);

const SYSTEM_PROMPT = `
You are the agentic interaction layer for the Unified Knowledge Base (UKB), a governed AI Brain.

The UKB MCP server is the only authoritative path for organization-specific knowledge, source evidence,
conversation receipts, access decisions, and context coverage. You must use the governed MCP tools before
making a factual claim about the tenant's business. Never treat browser state, model memory, or previously
seen text as authorization or as official organizational knowledge.

Operating rules:
1. For a business question, call ask_brain or get_context_pack. Use search_brain or get_source_lineage only
   when additional discovery or provenance is necessary.
2. Preserve and clearly communicate access decisions, missing context, conflicts, caveats, source lineage,
   and Context Coverage Receipt information.
3. When governed evidence is absent, denied, stale, conflicting, or incomplete, qualify the response or
   abstain. Never invent a metric value, owner, policy, source, or business conclusion.
4. Frontend tools may navigate the OpenWebUI-adapted workspace, select a source channel, set a query mode,
   or open the context inspector. Frontend context is convenience state, not an authority boundary.
5. Do not approve, publish, reject, delete, change policy, or invalidate caches. Those remain explicit,
   attributable human governance operations in UKB. If a user asks for one, navigate them to the appropriate
   review or publication screen and explain the required human decision.
6. Keep responses concise and analyst-friendly. Cite the governed evidence returned by UKB and distinguish
   facts from hypotheses or recommendations.
`.trim();

const agent = new BuiltInAgent({
  model: `openai:${model}`,
  prompt: SYSTEM_PROMPT,
  maxSteps: numberFromEnv("COPILOTKIT_MAX_STEPS", 8),
  temperature: numberFromEnv("COPILOTKIT_TEMPERATURE", 0.1),
  maxOutputTokens: numberFromEnv("COPILOTKIT_MAX_OUTPUT_TOKENS", 1600),
  mcpServers: [{ type: "http", url: mcpUrl }],
});

const runtime = new CopilotRuntime({
  agents: { default: agent },
  runner: new InMemoryAgentRunner(),
});

const copilotListener = createCopilotNodeListener({
  runtime,
  basePath,
  cors: true,
});

const server = createServer((request, response) => {
  const requestUrl = new URL(request.url || "/", `http://${request.headers.host || "localhost"}`);

  if (requestUrl.pathname === "/health" || requestUrl.pathname === `${basePath}/health`) {
    writeJson(response, 200, {
      status: "ok",
      service: "ukb-copilot-runtime",
      model,
      mcp_url_configured: Boolean(mcpUrl),
      auth_required: requireAuth,
      base_path: basePath,
    });
    return;
  }

  if (!originAllowed(request)) {
    writeJson(response, 403, { error: "origin_not_allowed" });
    return;
  }

  if (request.method !== "OPTIONS" && requireAuth && !isAuthorized(request)) {
    response.setHeader("WWW-Authenticate", "Bearer");
    writeJson(response, 401, { error: "copilot_runtime_authentication_required" });
    return;
  }

  copilotListener(request, response);
});

server.listen(port, host, () => {
  console.log(
    JSON.stringify({
      event: "copilot_runtime_started",
      address: `http://${host}:${port}${basePath}`,
      model,
      mcp_url: mcpUrl,
      auth_required: requireAuth,
      allowed_origins: [...allowedOrigins],
    }),
  );
});

function originAllowed(request: IncomingMessage): boolean {
  const origin = request.headers.origin;
  if (!origin || allowedOrigins.has("*")) return true;
  return allowedOrigins.has(origin);
}

function isAuthorized(request: IncomingMessage): boolean {
  if (!runtimeToken) return false;
  return request.headers.authorization === `Bearer ${runtimeToken}`;
}

function writeJson(response: ServerResponse, status: number, payload: Record<string, unknown>): void {
  response.statusCode = status;
  response.setHeader("Content-Type", "application/json; charset=utf-8");
  response.setHeader("Cache-Control", "no-store");
  response.end(JSON.stringify(payload));
}

function normalizeBasePath(value: string): string {
  const normalized = `/${value.trim().replace(/^\/+|\/+$/g, "")}`;
  return normalized === "/" ? "/api/copilotkit" : normalized;
}

function csvSet(value: string): Set<string> {
  return new Set(value.split(",").map((item) => item.trim()).filter(Boolean));
}

function booleanFromEnv(name: string, fallback: boolean): boolean {
  const raw = process.env[name];
  if (raw === undefined) return fallback;
  return ["1", "true", "yes", "on"].includes(raw.trim().toLowerCase());
}

function numberFromEnv(name: string, fallback: number): number {
  const raw = Number(process.env[name]);
  return Number.isFinite(raw) ? raw : fallback;
}
