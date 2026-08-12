# Demo Slide Outline

Deck: `docs/demo/demo-slides.html`

## Slide 1 — A governed AI Brain for enterprise context

Message: This is not a chatbot. It is a reusable context runtime for AI applications.

Speaker note: Use the phrase “compile context” early. The audience should understand that the brain is produced from source evidence and governance, not improvised at answer time.

## Slide 2 — A query result is not intelligence

Message: Data access alone creates fragile AI answers.

Speaker note: Use the example of a warehouse returning a number. The missing context is the real product problem: definition, owner, caveats, access, freshness, and drivers.

## Slide 3 — Separate the platform from each brain

Message: The core runtime is stable; every team can generate its own brain package.

Speaker note: Introduce the npm starter as the developer experience for creating a domain brain.

## Slide 4 — From raw context to approved knowledge

Message: AI classification is not the approval step. It creates candidates for review.

Speaker note: Emphasize evidence-first design and the review gate.

## Slide 5 — Every team can extend the brain safely

Message: Plugins are extension points, not governance bypasses.

Speaker note: Point to connector, parser, extractor, validator, retriever, policy, and exporter as the main plugin capabilities.

## Slide 6 — AI accelerates the brain, but does not define it

Message: Offline-first operation is essential for constrained enterprise environments.

Speaker note: Explain the four modes: offline_no_model, local_ai, hosted_ai, hybrid.

## Slide 7 — One brain, many ways to use it

Message: REST, MCP, SDK, and npm starter each serve a different consumer.

Speaker note: Restate that API is the platform backend and MCP is the agent interface.

## Slide 8 — Trust comes from reviewable state

Message: The platform manages truth through state, review decisions, and audit events.

Speaker note: Highlight that official knowledge has a lifecycle.

## Slide 9 — Show the brain being created, reviewed, and consumed

Message: The live demo should prove that generated context becomes approved context and then powers a context pack.

Speaker note: Use `docs/DEMO_GUIDE.md` for the live commands.

## Slide 10 — Turn the scaffold into a usable platform

Message: The next waves are durability, UI, retrieval, and GitLab deployment.

Speaker note: Close with the product bet and engineering bet.
