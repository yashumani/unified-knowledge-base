# UI review: pipeline-first restructure

Reviewed: `apps/web/src`, `docs/REACT_UI.md`, `docs/UI_FRAMER_REDESIGN.md`,
`docs/UI_CONSOLE_END_TO_END.md`.

## Why this change happened

The console showed every part of the product but not the process it exists to
demonstrate. Concretely, before this work:

- The five-step pipeline was rendered once, in the hero, as five identical
  static `<div>`s bound to no state. It looked like a progress tracker and
  tracked nothing.
- The pipeline existed in three unsynchronized places: that timeline, a side
  nav with different labels in a different order that led with the graph, and
  four panel ids. Step 5 was called "Compose" in one and "Context Pack" in
  another.
- Step 2, "Enrich", had no section, no anchor and no nav entry. It was a button
  inside the review inspector, behind a condition that hid it in demo mode.
- `.workbench` was a two-column grid, so the stages appeared on screen in the
  order 1, 3, 5, 4 — publish landed after compose.
- The graph rendered before step 1, so a first-time visitor met a dense node
  diagram before learning what was being graphed.
- The public GitHub Pages build has no API token and is therefore always in
  demo mode, and demo mode could not run enrichment at all
  (`enrichReview` was `if (demoMode) return;`). The showcase could never
  demonstrate step 2.

## What changed

**One source of truth.** `src/pipeline/steps.ts` declares each step's label,
heading, anchor, governance meaning and pure state predicates. The stepper,
side nav and every section heading render from it, so they cannot drift.

**Progress is derived, not decorative.** Each step resolves to
`locked | available | complete` from live data, separately from whether the
viewer is currently looking at it. A locked step is dimmed and states its
reason but stays clickable — a link that silently does nothing reads as a bug.

**An append-only decision ledger.** The review handlers destroyed their own
evidence: rejecting an item simply dropped it from the queue. Without a ledger
there was no way to define "Review is complete" and no trace that a rejection
happened. It also became the audit surface the governance docs describe and the
UI had never had.

**Demo mode runs the real offline provider.** `src/demo` is a port of
`ukb.ai.providers.noop`, `BrainCompiler`, and the retrieval/context-pack
services — the code the backend already runs in `offline_no_model` mode. The
demo is not simulating AI; it is executing the platform's own deterministic
provider in the browser.

**Reviewer actions completed where the backend already allowed it.**
Request-changes and a reviewer comment both existed end-to-end except in the
UI. Assign-owner and change-sensitivity were deliberately *not* added — see
below.

## Correctness issues found and fixed along the way

1. `refresh()` used `Promise.all` across four endpoints, so one failing route
   made the console announce "no backend connected" and display fabricated
   support-ops data while the server was healthy. Health alone now decides
   connected versus demo; the rest settle independently.
2. `graph` and `aiStatus` were initialised from demo fixtures, so a connected
   console rendered synthetic data before any fetch resolved.
3. `demoBrain.ts` declared `provider: "ollama"`, `model: "llama3.1"` and text
   reading "Local Ollama prepared…" on a build with no Ollama and no backend.
   This was live on the deployed site.
4. `askBrain` returned one canned pack for any question, listing evidence it
   had not retrieved — which made the most important honesty state in the
   product (an empty pack that says so) unreachable.
5. The Enrich step regressed from complete to locked when the queue drained,
   because the guard only counted briefs the viewer generated. Caught in the
   browser during wave 3.
6. `resetView()` cleared zoom, pan and local mode but not the search query or
   filter, so Reset on a filtered graph still showed an empty canvas.
7. The graph called `preventDefault()` in a React synthetic wheel handler,
   which is registered passively — it warned and did nothing. Zoom is now a
   native non-passive listener gated on ctrl/meta, so a plain wheel scrolls the
   page. This matters more now that the graph sits inside a long page.

## Accessibility

Fixed: the nested `<main>` (two main landmarks); heading hierarchy, with each
step's category kicker inside its `<h2>` so it joins the accessible name;
`aria-current="step"` on the stepper and side nav; the review list as a real
list of `aria-pressed` toggle buttons with selection styled distinctly from
hover (they were previously identical); a skip link; `role="alert"` on the
error notice, which was silent; a keyboard-navigable node list beside the graph
plus focusable SVG nodes; a legend with shape cues for node types, which were
colour-only with no legend anywhere; labels for the graph search and filter
controls and the `+`/`−` buttons; a global `prefers-reduced-motion` block; and
a shape difference for `.pulse`, which signalled connection state by colour
alone.

Verified in-browser: one main landmark, H1 followed by five ordered H2s, zero
unlabelled form controls, zero buttons without an accessible name.

## Deliberate non-changes

**Assign-owner and change-sensitivity were not implemented.** Both are edits.
`ReviewDecision` carries only `reviewed_by` and `comment`, and no mutation
endpoint exists, so a UI-only version would fabricate governance state — the
exact thing `docs/REACT_UI.md` forbids. Where an owner is missing, the console
instead prefills a request-changes comment asking for one, routing the gap
through a real governed action.

**Confidence is never rendered as a score.** `ReviewSignal` keeps one neutral
colour at every value and always carries the caption "Not an approval".
`docs/UI_CONSOLE_END_TO_END.md` is explicit that a high-confidence candidate
still requires human approval, so a green progress bar here would contradict
the product. This is the most tempting wrong move in any "improve the UI" pass.

**No new dependencies.** `apps/web/package.json` still lists exactly `react`
and `react-dom`. The stepper, scroll-spy, confirmations, relative times and
graph are all hand-rolled.

## Known limitations

- The page is roughly eleven viewports tall. The sticky rail makes every step
  one click away and the stepper is visible on first load without scrolling,
  but a shorter page would still be better. The available lever is collapsing
  long lists behind "show all".
- Scroll behaviour was verified through hash, focus and active-step changes
  rather than visually, because the automated browser pane does not composite
  frames. A human should confirm the smooth-scroll feel.
- The ledger is session-only in demo mode. In connected mode it should hydrate
  from `listAuditEvents()`, which is exposed on the client and still not called.
- Still open from earlier reviews: edit-before-approval, persistent graph
  layout positions, context-pack tabs and raw export, and light-theme tokens.

## Previewing the Pages build locally

`vite.config.ts` derives `base` from `GITHUB_PAGES`, and `vite preview` reads
the same config. So the env var must be set for **both** commands:

```bash
GITHUB_PAGES=true npm run web:build
cd apps/web && GITHUB_PAGES=true npx vite preview
# then open http://localhost:4173/unified-knowledge-base/
```

Running the preview without it serves with base `/`, so every request under
`/unified-knowledge-base/assets/` falls through to the SPA fallback and returns
`index.html` with `Content-Type: text/html`. The browser then refuses the module
script and the page renders blank — which looks exactly like a broken build but
is not. Confirmed by comparing the served bundle against disk: 263,224 bytes and
`text/javascript` when the variable is set, 555 bytes of HTML when it is not.

## Verification performed

`npm run web:build` clean; no raw hex outside `tokens.css`; dependencies
unchanged. In demo mode: the canonical sample text produces exactly two
findings (exclusion, medium; freshness, low), `request_changes`, and four
reviewer questions — matching `NoopProvider` exactly. An unrelated question
returns 20% confidence with populated `missing_context` instead of a confident
canned pack. Request-changes leaves the item in the queue with its own state
and writes a ledger entry. Reject and request-changes are blocked without a
comment; approve is not. Zero console errors.
