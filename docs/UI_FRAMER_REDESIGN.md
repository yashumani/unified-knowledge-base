# Framer-Inspired UI Redesign

## Design direction

The React console uses an original implementation inspired by current Framer marketplace patterns for AI and SaaS products. The redesign does not copy Framer template assets or source files. It translates common, suitable patterns into the repository's own React/Vite codebase.

## Template inspiration category

The best fit for this product is a **dark, dashboard-led AI SaaS template** rather than a pure marketing landing page.

The UI console needs to communicate:

```text
enterprise trust
real-time operational state
governed workflow
graph-driven context
approval before publication
```

That maps better to Framer dashboard/SaaS templates than to consumer landing pages.

## Patterns adopted

### 1. Command-center shell

The app now uses a side navigation rail and a large command-center canvas.

Purpose:

```text
make the product feel like an operating console
separate navigation from workflow panels
support future routes without redesigning the page
```

### 2. Large product hero

The top hero is a product-grade introduction with:

```text
clear value proposition
primary workflow action
secondary graph action
runtime connection state
workflow timeline
```

### 3. Dashboard bento cards

The summary cards use bento-style spacing and compact metric labels:

```text
published objects
review queue
nodes
edges
```

### 4. Graph-first story

The graph is now framed as the visual trust layer, not a decorative widget.

The section copy emphasizes:

```text
trace source evidence
inspect review state
understand relationships
trust context packs only after review
```

### 5. Review inspector

The review queue now has a candidate inspector area instead of only inline approve/reject buttons.

This starts moving the UI toward a real governance workflow where a reviewer inspects the candidate before approving it.

### 6. Clear demo-mode boundary

The UI now has a stronger demo-mode banner and simulated-action labels.

This prevents users from mistaking static GitHub Pages demo state for backend-persisted workflow state.

## Color and visual language

The redesign uses:

```text
near-black background
cyan and violet AI/SaaS accent gradients
glass panels
fine grid background
glowed metric cards
rounded bento panels
high-contrast chips and badges
```

These choices are intended to feel modern without becoming visually noisy.

## UX principles

```text
1. The UI should reveal governance state at every step.
2. Demo mode should never be confused with connected mode.
3. The graph should explain source-to-context lineage.
4. Reviewers should inspect candidates before publishing them.
5. Context packs should feel like governed artifacts, not chat responses.
6. All examples must remain synthetic and workplace-safe.
```

## Files changed

```text
apps/web/src/App.tsx
apps/web/src/styles.css
docs/UI_FRAMER_REDESIGN.md
```

## Future UI work

The next UI phase should add:

```text
React Router routes
review detail drawer/modal
request-changes UI
edit-before-approval
keyboard-accessible graph node list
context-pack tabs
persistent graph layout
light/dark theme tokens
```
