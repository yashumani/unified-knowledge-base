# Documentation Index

This repository is being shaped as a reusable platform for building governed AI Brains. The documentation is organized around seven jobs: understand the architecture, run the demo, configure local Ollama enrichment, host with GitHub as the control plane, keep examples workplace-safe, extend the platform, and prepare for enterprise deployment.

## Start here

| Document | Purpose |
|---|---|
| `README.md` | Repository overview, quick start, and maturity boundary. |
| `docs/ARCHITECTURE.md` | System architecture from sources to context packs. |
| `docs/BRAIN_STARTER_KIT.md` | How users create their own domain brain packages. |
| `docs/PLUGIN_ARCHITECTURE.md` | How connectors, parsers, extractors, validators, retrievers, policy plugins, and exporters fit together. |
| `docs/OFFLINE_FIRST_AI.md` | How the platform works with no hosted AI, local AI, hosted AI, or hybrid AI. |
| `docs/API_VS_MCP.md` | Why the REST API is the platform backend and MCP is the LLM/agent adapter. |

## AI enrichment

| Document | Purpose |
|---|---|
| `docs/OLLAMA_LOCAL_LLM.md` | Local Ollama setup, Docker Compose instructions, model pulls, provider config, and testing commands for UKB. |
| `docs/LLM_FEATURE_ARCHITECTURE.md` | Architecture, provider modes, API endpoints, UI behavior, and governance boundaries for LLM-powered enrichment. |

## GitHub hosting and deployment

| Document | Purpose |
|---|---|
| `docs/GITHUB_HOSTING_MODEL.md` | GitHub Pages, GHCR, GitHub Actions, self-hosted runner, production Compose, and runtime-boundary model. |
| `docs/GITHUB_PAGES_DEPLOYMENT.md` | Static React UI deployment on GitHub Pages. |
| `docs/GITLAB_DEPLOYMENT.md` | GitLab/Linux/Docker deployment model for private enterprise environments. |

## Workplace-safe examples

| Document | Purpose |
|---|---|
| `docs/WORKPLACE_SAFE_EXAMPLES.md` | Public-repo policy for synthetic examples and forbidden workplace-derived context. |
| `docs/EXAMPLE_DOMAIN.md` | Approved neutral support-operations demo domain. |

## Demo materials

| Asset | Purpose |
|---|---|
| `docs/DEMO_GUIDE.md` | Live demo script, commands, and fallback flow. |
| `docs/UI_CONSOLE_END_TO_END.md` | Click-by-click UI console walkthrough from context submission through approved context pack. |
| `docs/ARCHITECTURE_STORYBOARD.md` | Narrative map for explaining the platform in a meeting. |
| `docs/demo/demo-slides.html` | Offline browser-based slide deck for repository use. |
| `docs/demo/slides-outline.md` | Slide-by-slide speaker guide. |
| `docs/demo/animated-diagrams.html` | Offline animated diagrams for browser-based walkthroughs. |
| `docs/demo/README.md` | How to use the demo assets. |

A PowerPoint presenter export can be generated outside the repository when needed. The committed, reviewable slide deck is the offline HTML deck so the repository remains text-first and Git-friendly.

## Diagrams

| Diagram | Purpose |
|---|---|
| `docs/diagrams/brain-runtime.mmd` | Mermaid diagram for the runtime architecture. |
| `docs/diagrams/plugin-lifecycle.mmd` | Mermaid diagram for plugin-to-review lifecycle. |
| `docs/diagrams/offline-first-modes.mmd` | Mermaid diagram for deterministic, local AI, hosted AI, and hybrid operation. |

## UI and frontend

| Document | Purpose |
|---|---|
| `docs/REACT_UI.md` | React console architecture, graph view boundary, local run commands, and next UI iterations. |
| `docs/UI_FRAMER_REDESIGN.md` | Framer-inspired design direction, adopted UI patterns, and future design work. |
| `docs/UI_CONSOLE_END_TO_END.md` | Full UI workflow for submit, review, approve, graph inspection, and context-pack generation. |

## Governance and security

| Document | Purpose |
|---|---|
| `docs/GOVERNANCE_WORKFLOW.md` | Human review lifecycle and review states. |
| `docs/SECURITY_MODEL.md` | Access control and retrieval-time security principles. |
| `SECURITY.md` | Public repository safety boundary and production hardening expectations. |

## Product direction

| Document | Purpose |
|---|---|
| `docs/PRODUCT_REQUIREMENTS.md` | MVP product requirements. |
| `docs/ROADMAP.md` | Phased roadmap. |
| `docs/CONTEXT_PACK.md` | Context pack contract. |

## Documentation principle

Documentation should preserve the product boundary:

```text
Source context -> candidate knowledge -> human review -> approved brain -> context pack
```

Do not describe AI-generated candidates as official knowledge until the human review step has approved and published them.
