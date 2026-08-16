# Guided and Advanced UI Experiences

Unified Knowledge Base now separates two distinct user needs:

```text
First-time user or product demo
  -> Guided experience

Operator, reviewer, administrator, or developer
  -> Advanced console
```

The split is intentional. Simplifying the first experience must not remove the governance controls needed for real operation.

## UX assessment of the original one-page console

The editorial redesign is effective as a product story and complete console, but browser testing showed that it was not the shortest end-to-end path for a first-time user.

Measured on the deployed design before this change:

| Signal | Desktop | Mobile |
|---|---:|---:|
| Full page height | about 15,402 px | about 19,597 px |
| Interactive elements | 70 | 70 |
| Buttons | 40 | 39 |
| Working pipeline span | about 6,919 px | about 8,341 px |

The full workflow also appeared twice: first as five explanatory process cards, then as five operational console sections. That repetition is useful for teaching and expert navigation, but it increases cognitive load during a simple product demonstration.

The browser test also found a continuity problem: after a new source was submitted, the enrichment and review panels retained the previously selected seeded candidate. A user could therefore submit one item and accidentally continue working on another. The advanced panels now focus the newest submitted candidate automatically.

## Default guided experience

The default GitHub Pages route is the guided experience:

```text
https://yashumani.github.io/unified-knowledge-base/
```

It exposes three user decisions:

```text
1. Add one source
2. Approve the candidate
3. Ask the approved brain
```

Under those three steps, UKB still performs the complete governed lifecycle:

```text
submit
-> enrich
-> human review
-> publish
-> compose context pack
```

The wrapper combines operations that do not require a human decision. It does not bypass them.

### Step 1 — Add source

The user sees one synthetic, workplace-safe source and one primary action.

Hidden defaults:

```text
domain: support
source type: document
sensitivity: internal
submitter: guided.demo
```

Those fields remain editable in the advanced console.

### Step 2 — Approve memory

AI enrichment runs automatically after submission. The user sees:

```text
candidate title
type
owner
candidate summary
AI review brief
first validation finding
```

The interface explicitly labels the brief as advisory. Publication still requires a human confirmation.

### Step 3 — Ask the brain

The user asks one prefilled question and receives a compact governed context pack showing:

```text
access decision
confidence
answer guidance
AI guidance
evidence
caveats
missing-context warnings
```

The result is context for a downstream AI application, not an untraceable generated answer.

## Advanced console

The complete console remains available at:

```text
https://yashumani.github.io/unified-knowledge-base/?view=advanced
```

It retains:

```text
all five pipeline stages
manual enrichment controls
multiple-candidate selection
approve, reject, and request-changes actions
reviewer comments
published-object browsing
context-pack modes
full evidence graph
node filters and local graph mode
governance ledger
FAQ and architecture explanation
```

A fixed “Guided demo” control returns to the simplified route.

## Why query-based routing is used

GitHub Pages is static hosting. A path such as `/advanced` may return a 404 when loaded directly unless additional fallback handling is added.

The query route keeps both experiences directly addressable while preserving normal in-page anchors:

```text
/                         guided
/?view=advanced           advanced
/?view=advanced#brain-map advanced graph deep link
```

## Interaction targets

The guided experience is designed around one primary action per stage:

```text
Create review candidate
Approve and publish this memory
Build the context pack
```

Publication uses a second, explicit confirmation because it changes official knowledge state. That is deliberate friction, not accidental complexity.

## Validation contract

The UI pull-request workflow validates:

```text
TypeScript and Vite build
GitHub Pages base path
guided desktop render
guided mobile render
advanced desktop render
advanced mobile render
required landmarks
no browser page errors
no horizontal overflow
complete guided source-to-context-pack workflow
rendered screenshots and build artifact
```

## Product rule

```text
Simple on top does not mean weak underneath.
```

The guided experience reduces interface decisions. The advanced experience preserves governance depth.
