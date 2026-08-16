# Editorial One-Page UI Redesign

## Reference and boundary

The public website redesign studies the design grammar of [Depo Budget](https://depobudget.com/): oversized direct headlines, editorial contrast, bright product cards, numbered storytelling, ticker bands, and conversational copy.

The implementation does **not** copy Depo's logo, screenshots, product copy, illustrations, source code, or proprietary assets. The UKB layout, colors, components, copy, interactions, and product visualizations are original and are built entirely from the existing React console state.

## Product story

The redesigned page explains Unified Knowledge Base in one continuous narrative:

```text
Give AI the right memory
  -> understand the five governance gates
  -> use the live console
  -> inspect the memory graph
  -> review the decision trail
  -> understand the architecture boundary
```

The marketing story and the working console are now one page instead of separate experiences.

## Adopted design patterns

- Cream editorial canvas with a black navigation and footer.
- Very large uppercase display typography using system fonts only.
- Acid-lime, cobalt, coral, lavender, and amber feature blocks.
- Hard two-pixel rules and offset shadows instead of glassmorphism.
- A moving capability ticker with reduced-motion fallback.
- A live runtime poster driven by actual UKB state.
- Five numbered process cards connected to the working pipeline.
- Full-width, color-coded workflow stages.
- Dark graph showcase with an evidence-first explanation.
- Large accordion questions and a direct final call to action.

## Preserved UX and accessibility

The redesign keeps the current functional and accessibility improvements:

- Keyboard-accessible workflow navigation.
- Visible focus treatment.
- Reduced-motion behavior.
- Explicit demo-mode warning.
- Human-review confirmations and comments.
- Accessible graph node list and keyboard-selectable SVG nodes.
- Graph legend using color and shape cues.
- Inspectable node details with raw metadata behind disclosure.
- Source-to-candidate-to-publication-to-context-pack ordering.

## Runtime boundary

The public GitHub Pages site remains a static React application. Without a configured backend it uses temporary, synthetic demo state. A connected deployment continues to use:

```text
React UI
  -> FastAPI governance runtime
    -> local Ollama enrichment
      -> authoritative storage and derived retrieval indexes
```

The website never calls Ollama directly from the browser.

## Validation

Before merge, run:

```bash
npm install --no-audit --no-fund
npm run web:build
```

After merge, verify the GitHub Pages workflow and test the live site at:

```text
https://yashumani.github.io/unified-knowledge-base/
```

Recommended responsive checks:

```text
1440 x 1000 desktop
1024 x 768 tablet
390 x 844 mobile
320 x 568 minimum supported width
```
