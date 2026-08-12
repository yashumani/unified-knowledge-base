# Documentation Index

This repository is being shaped as a reusable platform for building governed AI Brains. The documentation is organized around four jobs: understand the architecture, run the demo, extend the platform, and prepare for enterprise deployment.

## Start here

| Document | Purpose |
|---|---|
| `README.md` | Repository overview, quick start, and maturity boundary. |
| `docs/ARCHITECTURE.md` | System architecture from sources to context packs. |
| `docs/BRAIN_STARTER_KIT.md` | How users create their own domain brain packages. |
| `docs/PLUGIN_ARCHITECTURE.md` | How connectors, parsers, extractors, validators, retrievers, policy plugins, and exporters fit together. |
| `docs/OFFLINE_FIRST_AI.md` | How the platform works with no hosted AI, local AI, hosted AI, or hybrid AI. |
| `docs/API_VS_MCP.md` | Why the REST API is the platform backend and MCP is the LLM/agent adapter. |

## Demo materials

| Asset | Purpose |
|---|---|
| `docs/DEMO_GUIDE.md` | Live demo script, commands, and fallback flow. |
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
| `docs/GITLAB_DEPLOYMENT.md` | GitLab/Linux/Docker deployment model. |

## Documentation principle

Documentation should preserve the product boundary:

```text
Source context -> candidate knowledge -> human review -> approved brain -> context pack
```

Do not describe AI-generated candidates as official knowledge until the human review step has approved and published them.
