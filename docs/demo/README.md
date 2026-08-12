# Demo Assets

This directory contains presentation and walkthrough materials for the Unified Knowledge Base AI Brain platform.

## Files

| File | Purpose |
|---|---|
| `demo-slides.html` | Offline browser-based slide deck for repository use. |
| `slides-outline.md` | Slide-by-slide guide with speaker notes. |
| `animated-diagrams.html` | Self-contained browser animations for architecture walkthroughs. |

A PowerPoint presenter export can be generated separately when needed. The committed repository keeps demo material text-first so changes can be reviewed cleanly in Git.

## Recommended demo order

1. Open `demo-slides.html` and present slides 1–4.
2. Open `animated-diagrams.html` to animate the compiler loop.
3. Return to slides 5–8 for plugins, offline-first AI, adapters, and governance.
4. Run the live commands from `docs/DEMO_GUIDE.md`.
5. Close with slides 9–10.

## Offline use

The animated HTML file has no CDN, npm, or external image dependency. It can be opened from the local filesystem in a locked-down environment.

## Safe demo boundary

Use synthetic examples only. Do not include workplace documents, private dashboards, internal metric definitions, credentials, customer data, or proprietary screenshots in the demo deck or animation files.
