# Documentation Index

This repository is a reusable platform for building governed AI Brains. The documentation is organized around architecture, local AI, deployment, governance, Talk2Data integration, demonstrations, and production operations.

## Start here

| Document | Purpose |
|---|---|
| `README.md` | Repository overview, quick start, and maturity boundary. |
| `docs/ARCHITECTURE.md` | System architecture from sources to context packs. |
| `docs/AI_BRAIN_ARCHITECTURE_V2.md` | Durable evidence, governance, retrieval, identity, jobs, and recovery architecture. |
| `docs/BRAIN_STARTER_KIT.md` | How users create their own domain brain packages. |
| `docs/PLUGIN_ARCHITECTURE.md` | How connectors, parsers, extractors, validators, retrievers, policies, and exporters fit together. |
| `docs/OFFLINE_FIRST_AI.md` | Deterministic, local-AI, hosted-AI, and hybrid operation. |
| `docs/API_VS_MCP.md` | Why REST is the platform backend and MCP is an adapter. |

## Talk2Data governed memory

| Document | Purpose |
|---|---|
| `docs/TALK2DATA_INTEGRATION.md` | Consumer integration flow, domain classification, authorized memory, and Context Coverage Receipts. |
| `docs/TALK2DATA_DOMAIN_PACK.md` | Versioned Tenant Domain Pack and telecommunications example. |
| `docs/TALK2DATA_MEMORY_CONTRACT.md` | Typed temporal memory, canonical episodes, provenance, and supersession. |
| `docs/TALK2DATA_GRAPHITI_ADAPTER.md` | Replaceable Graphiti boundary and canonical-storage rules. |
| `docs/TALK2DATA_OBSIDIAN.md` | Obsidian frontmatter validation and governed promotion. |
| `docs/openapi-talk2data.json` | Focused typed API contract used by Talk2Data consumers. |

## AI enrichment

| Document | Purpose |
|---|---|
| `docs/OLLAMA_LOCAL_LLM.md` | Local Ollama setup, Docker Compose instructions, model pulls, and testing. |
| `docs/LLM_FEATURE_ARCHITECTURE.md` | Provider modes, APIs, UI behavior, and governance boundaries. |

## GitHub hosting and deployment

| Document | Purpose |
|---|---|
| `docs/GITHUB_HOSTING_MODEL.md` | GitHub Pages, GHCR, Actions, self-hosted runners, and runtime boundaries. |
| `docs/GITHUB_PAGES_DEPLOYMENT.md` | Static React UI deployment on GitHub Pages. |
| `docs/PRIVATE_RUNTIME_PILOT.md` | Fail-closed staging configuration, self-hosted deployment, acceptance probes, recovery tests, and go/no-go criteria. |
| `docs/GITLAB_DEPLOYMENT.md` | GitLab/Linux/Docker deployment model for private enterprise environments. |
| `deploy/staging.env.example` | Secret-free private-pilot environment template. |

## Workplace-safe examples

| Document | Purpose |
|---|---|
| `docs/WORKPLACE_SAFE_EXAMPLES.md` | Public-repo policy for synthetic examples and forbidden workplace-derived context. |
| `docs/EXAMPLE_DOMAIN.md` | Approved neutral support-operations demo domain. |
| `examples/talk2data-telecom/` | Synthetic telecommunications Domain Pack and governed-memory examples. |

## Demo materials

| Asset | Purpose |
|---|---|
| `docs/DEMO_GUIDE.md` | Live demo script, commands, and fallback flow. |
| `docs/UI_CONSOLE_END_TO_END.md` | Advanced-console walkthrough from source submission through context pack. |
| `docs/UI_GUIDED_EXPERIENCE.md` | Guided Source → Approve → Ask experience. |
| `docs/ARCHITECTURE_STORYBOARD.md` | Narrative map for explaining the platform. |
| `docs/demo/demo-slides.html` | Offline browser-based slide deck. |
| `docs/demo/slides-outline.md` | Slide-by-slide speaker guide. |
| `docs/demo/animated-diagrams.html` | Offline animated diagrams. |
| `docs/demo/README.md` | How to use the demo assets. |

## Diagrams

| Diagram | Purpose |
|---|---|
| `docs/diagrams/brain-runtime.mmd` | Runtime architecture. |
| `docs/diagrams/plugin-lifecycle.mmd` | Plugin-to-review lifecycle. |
| `docs/diagrams/offline-first-modes.mmd` | Deterministic, local-AI, hosted-AI, and hybrid modes. |

## UI and frontend

| Document | Purpose |
|---|---|
| `docs/OPENWEBUI_DESIGN_ADAPTATION.md` | Chat-first OpenWebUI-inspired information architecture, route map, responsive behavior, and originality boundary. |
| `docs/REACT_UI.md` | React console architecture, routes, and graph-view boundary. |
| `docs/UI_GUIDED_EXPERIENCE.md` | Guided-versus-advanced information architecture. |
| `docs/UI_EDITORIAL_REDESIGN.md` | Editorial design system and originality boundary. |
| `docs/UI_CONSOLE_END_TO_END.md` | Full advanced workflow. |

## Governance and security

| Document | Purpose |
|---|---|
| `docs/GOVERNANCE_WORKFLOW.md` | Review, approval, publication, revision, and audit lifecycle. |
| `docs/SECURITY_MODEL.md` | Identity, tenant isolation, authorization, and retrieval-time filtering. |
| `SECURITY.md` | Public-repository safety boundary and production hardening expectations. |

## Product direction

| Document | Purpose |
|---|---|
| `docs/PRODUCT_REQUIREMENTS.md` | Product requirements and acceptance boundary. |
| `docs/ROADMAP.md` | Current release state and remaining milestones. |
| `docs/CONTEXT_PACK.md` | Context-pack contract. |

## Documentation principle

Documentation must preserve the product boundary:

```text
Source evidence
→ candidate knowledge
→ advisory AI enrichment
→ human approval
→ explicit publication
→ authorized retrieval
→ governed context pack
```

AI-generated candidates are not official knowledge until the governed human publication transition succeeds.
