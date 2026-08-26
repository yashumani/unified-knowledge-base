# OpenWebUI-Inspired AI Brain Interface

## Purpose

Unified Knowledge Base needs to feel like an AI application people can use every day, not a presentation website with a workflow embedded inside it.

The v0.6 interface adapts the strongest interaction patterns of Open WebUI to the governed AI Brain use case:

- Persistent sidebar navigation
- Chat-first primary workspace
- Compact model and runtime selector
- Bottom prompt composer with source and governance tools
- Right-side context and evidence inspector
- Responsive drawers on smaller screens
- Light and dark appearance modes
- Clear separation between ordinary user work and administrative controls

Reference material:

- https://www.openwebui.com/
- https://docs.openwebui.com/features/workspace/
- https://docs.openwebui.com/features/workspace/knowledge/
- https://github.com/open-webui/open-webui

## Originality boundary

This implementation is an original React and CSS design.

It does not copy Open WebUI branding, logos, illustrations, screenshots, component source, or proprietary enterprise assets. It translates high-level interaction patterns into Unified Knowledge Base concepts and reuses only this repository's existing AI Brain mark and governed application services.

## Product mapping

| Open WebUI pattern | Unified Knowledge Base adaptation |
|---|---|
| New Chat | New Brain Chat |
| Chat history | Recent governed-memory questions |
| Model picker | Governed AI Brain and local provider status |
| Workspace | Sources, enrichment, review, publication, memory graph |
| Knowledge | Governed source ingestion and published memory |
| Tools | Context coverage, provenance, connector refresh, operations |
| Chat controls | Context, sources, and governance side panel |
| Settings | Theme, runtime identity, guided workflow, advanced console |

## Default information architecture

```text
AI Brain
├── Brain Chat
├── Sources
├── Enrichment
├── Review queue
├── Published memory
├── Memory graph
├── Knowledge operations
├── Audit activity
└── Help and guides
```

The earlier guided and advanced experiences remain available as secondary routes. The default route is now the daily-use application shell.

## Brain Chat contract

Brain Chat does not call an unrestricted chatbot endpoint.

```text
Question
→ authenticated user and tenant context
→ requested business domain and mode
→ authorized published-memory retrieval
→ provenance and coverage checks
→ governed Context Pack
→ advisory response presentation
```

The right context panel exposes:

- Access decision
- Composite confidence
- Confidence factors
- Approved memory objects
- Evidence and citations
- Missing context
- Conflicts
- Caveats
- Recommended follow-up questions

## Governance workflows

The new shell preserves the full product boundary:

```text
Source evidence
→ deterministic quality firewall
→ advisory local Ollama enrichment
→ assigned human review
→ explicit approval
→ separate publication
→ authorized retrieval
→ Context Coverage Receipt
```

The UI changes navigation and presentation. It does not allow the model to approve, publish, modify authorization policy, or become canonical storage.

## Responsive behavior

### Desktop

- Persistent left sidebar
- Center work area
- Optional right context panel
- Collapsible navigation
- Full source and review workspaces

### Tablet

- Narrower sidebar
- Context panel becomes an overlay drawer
- Workspace actions remain in the page header

### Phone

- Sidebar becomes a modal drawer
- Brain Chat opens unobstructed, with the context inspector closed until requested
- Context inspector becomes a right drawer
- Composer stays above the safe-area inset
- Secondary mode and domain controls collapse to reduce clutter
- Source, review, graph, and operations surfaces use contained internal scrolling

## Accessibility

The interface includes:

- Skip link
- Semantic navigation landmarks
- Named buttons and controls
- Keyboard-visible focus rings
- Reduced-motion support
- Color-independent status text
- Responsive layouts without horizontal document overflow

## Routes

| Route | Experience |
|---|---|
| `/` | Brain Chat |
| `?section=sources` | Governed source ingestion |
| `?section=enrich` | Local AI enrichment |
| `?section=review` | Human review queue |
| `?section=publish` | Publication gate and published memory |
| `?section=memory` | Obsidian-style memory graph |
| `?view=operations` | Knowledge operations |
| `?section=activity` | Audit activity |
| `?section=help` | End-to-end guide |
| `?view=guided` | Simplified guided workflow |
| `?view=advanced` | Advanced console |

Legacy `?page=` links are translated to their equivalent new section.

## Public-site boundary

GitHub Pages can demonstrate the complete interface and deterministic browser workflow. It cannot host PostgreSQL, Ollama, Zvec, Graphiti, private connectors, or OIDC.

When the private API is not configured, the UI labels all operational and chat state as synthetic. When the private API is configured, the same surfaces read tenant-filtered runtime state through the governed backend.
