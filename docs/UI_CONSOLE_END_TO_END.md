# UI Console End-to-End Guide

## Purpose

This guide shows how to use the React UI console to move context through the full governed AI Brain lifecycle:

```text
submit context -> review candidate -> approve knowledge -> inspect graph -> request context pack
```

The UI is an adapter over the FastAPI runtime. It should help people operate the workflow, but it must not bypass governance. Official knowledge still requires human approval before it is used as published brain context.

## Example boundary

Use only the neutral support-operations sample domain in public demos.

```text
Domain: support
Metric: Incident Resolution Time
Report: SLA Review Dashboard
Rule: SLA Review Window
Owner: Support Operations
Related metrics: First Response Time, Reopen Rate, Ticket Backlog
```

Do not use workplace, employer, client, product-line, dashboard, planning, financial, customer, or proprietary examples in this repository or in the public GitHub Pages demo.

## Two ways to use the console

### 1. Static GitHub Pages demo

Open the deployed UI:

```text
https://yashumani.github.io/unified-knowledge-base/
```

This mode is useful for explaining the workflow and graph view. If the FastAPI backend is not available to the browser, the UI falls back to bundled synthetic demo data.

What works in demo mode:

```text
view demo graph
filter graph
inspect nodes
simulate context submission
simulate approve/reject actions
simulate context-pack output
```

What does not persist in demo mode:

```text
submissions
review actions
published objects
context-pack requests
audit events
```

Refreshing the browser resets the demo state.

### 2. Backend-connected local mode

Use this mode when you want the UI to call the FastAPI backend and process real local scaffold state.

Terminal 1: start the API.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,mcp]"
make run
```

Terminal 2: start the React UI.

```bash
npm install
npm run web:dev
```

Open:

```text
http://localhost:5173
```

Expected backend:

```text
http://localhost:8000
```

The UI calls `VITE_UKB_API_BASE_URL` when configured. Without that variable, local development defaults to `http://localhost:8000`.

## Console layout

The UI has five main areas.

| Area | Purpose |
|---|---|
| Status card | Shows whether the UI is connected to the API or using offline demo data. |
| Stats cards | Shows published objects, review queue count, graph nodes, and graph edges. |
| AI Brain Map | Obsidian-style graph of sources, review items, candidate objects, and published objects. |
| Workbench panels | Context submission, review queue, context-pack explorer, and published objects. |
| Node detail panel | Shows selected graph-node metadata, status, confidence, sensitivity, and relationships. |

## End-to-end walkthrough

### Step 1 — Confirm the mode

At the top-right of the UI, check the status card.

If it says:

```text
Connected
```

the UI is calling the backend.

If it says:

```text
Offline demo
```

the UI is using synthetic local state.

For a real local end-to-end workflow, use connected mode.

### Step 2 — Submit source context

In the **Context ingestion** panel, enter the neutral support sample.

Recommended values:

```text
Title: Incident Resolution Time Definition
Domain: support
Source type: Document
```

Context:

```text
Incident Resolution Time is the average elapsed time from incident creation to resolved status for product support cases, excluding duplicate incidents and customer-wait periods. It appears in the SLA Review Dashboard and is owned by Support Operations. Recently resolved incidents may need 24 hours for quality review tags to settle.
```

Click:

```text
Submit for review
```

Expected result:

```text
A new item appears in the Review queue.
The graph gains source evidence, review item, and candidate object nodes.
The candidate is not official yet.
```

Governance meaning:

```text
The compiler created candidate knowledge.
The candidate still requires human review.
The candidate should not be treated as published truth.
```

### Step 3 — Inspect the graph before approval

Go to **AI Brain Map**.

Use these controls:

| Control | Use |
|---|---|
| Search box | Filter nodes by name, type, domain, or status. |
| All nodes | Show all evidence, review, candidate, and published nodes. |
| Review/candidates | Focus on unapproved review workflow nodes. |
| Sources | Focus on source evidence. |
| Local graph | Show the selected node and immediate neighbors. |
| `+` / `-` | Zoom in and out. |
| Reset | Reset zoom, pan, and local graph mode. |

Click the candidate node.

Expected node detail:

```text
Type: candidate_object or Metric
Status: human_review_required
Domain: support
Confidence: generated classifier score
Metadata: candidate object payload
```

Important interpretation:

```text
Confidence is a review signal, not approval.
A high-confidence candidate still requires human approval.
```

### Step 4 — Approve or reject the candidate

In the **Review queue** panel, read the candidate summary.

You have two choices:

```text
Approve
Reject
```

For the happy path, click:

```text
Approve
```

Expected result:

```text
The item leaves the Review queue.
The object appears under Approved knowledge objects.
The graph updates so the object is treated as published.
The stats cards update.
```

Governance meaning:

```text
The human reviewer accepted the candidate.
The object is now published in the AI Brain runtime.
Context packs can use it as approved knowledge.
```

For a negative-path demo, submit a second candidate and click:

```text
Reject
```

Expected result:

```text
The item leaves the Review queue.
It does not appear as a published object.
It should not influence official context packs.
```

### Step 5 — Browse approved knowledge

Open the **Approved knowledge objects** panel.

Look for:

```text
Incident Resolution Time
```

Expected details:

```text
Type: Metric
Domain: support
Owner: Support Operations
Status: published
```

This confirms that the object passed through the review gate.

### Step 6 — Build a context pack

Open the **Context pack explorer** panel.

Use a neutral question such as:

```text
What context should I use to explain Incident Resolution Time?
```

Recommended values:

```text
Mode: Metric definition
```

Click:

```text
Build pack
```

Expected result:

```text
The UI shows access decision, confidence, answer guidance, evidence, and follow-up questions.
```

For an executive-style question, use:

```text
Why did Incident Resolution Time increase this week?
```

Recommended mode:

```text
Executive insight
```

Expected context-pack behavior:

```text
It should use approved knowledge.
It should include source evidence.
It should mention caveats if available.
It should recommend checking related driver metrics such as First Response Time, Reopen Rate, and Ticket Backlog.
```

The context pack is not the final answer. It is the governed context another AI app, BI copilot, notebook, or agent can use to produce a grounded answer.

### Step 7 — Re-check the graph after publication

Return to **AI Brain Map**.

Use:

```text
Published
```

Expected result:

```text
Published knowledge objects remain visible.
Review-only candidate nodes are hidden.
```

Select the published metric node.

Check:

```text
source evidence relationship
report relationship
rule/caveat relationship if available
confidence
status
sensitivity
```

The graph should tell a reviewable story:

```text
Where did this knowledge come from?
Who approved it?
What is it connected to?
What should consumers know before using it?
```

### Step 8 — Use the workflow as a governance demo

The main story to narrate is:

```text
The UI did not create official truth by itself.
The system accepted source context, created a candidate, required review, then published approved knowledge.
Only after approval did the object become reliable context for downstream AI applications.
```

Use this talk track:

1. A submitter provides context.
2. The compiler classifies it as candidate knowledge.
3. The reviewer inspects the candidate and source evidence.
4. Approval publishes the object into the brain.
5. The context-pack service composes approved knowledge and evidence.
6. The graph shows source-to-context lineage.

## Expected demo outcome

A successful UI walkthrough should prove:

```text
context can be submitted through the UI
candidate knowledge appears in the review queue
human review gates publication
approved knowledge appears in the brain store
context packs use approved knowledge and evidence
the graph explains the relationship between sources, candidates, reviews, and published objects
```

## Troubleshooting

### UI says Offline demo

Likely cause:

```text
FastAPI backend is not running or not reachable from the browser.
```

Fix:

```bash
make run
```

Then refresh the UI.

### UI cannot connect from GitHub Pages

Expected unless a hosted backend URL is configured.

GitHub Pages serves the static React app only. It does not host the FastAPI backend. To connect Pages to a real backend, build with:

```text
VITE_UKB_API_BASE_URL=https://your-approved-api-host.example.com
```

The backend must allow CORS from:

```text
https://yashumani.github.io
```

### Approving does not persist after refresh

If the UI is in offline demo mode, this is expected.

Use backend-connected mode for persistent runtime state within the running API process. Long-term durable persistence requires the planned Postgres storage layer.

### Context pack has low confidence

Likely causes:

```text
no approved matching objects
question terms do not match object terms
object is still in review state
source evidence was not attached
```

Fix:

```text
approve the candidate
ask using the same neutral metric/report terms
add clearer source context
```

## Current limitations

The UI is still a scaffold.

Current limitations:

```text
no authentication-aware reviewer identity
no edit-before-approval screen
no durable database yet
no persistent graph layout
no production role-based filtering
no hosted backend for the public Pages deployment
```

These are planned follow-up development waves.

## Definition of done for a live UI demo

Use this checklist before presenting:

- [ ] Public examples are synthetic and workplace-safe.
- [ ] UI loads in browser.
- [ ] Status card mode is understood: Connected or Offline demo.
- [ ] A context submission can be created.
- [ ] A candidate appears in the review queue.
- [ ] The candidate can be approved.
- [ ] The approved object appears in the published object list.
- [ ] The graph shows source, review, and published object relationships.
- [ ] A context pack can be generated.
- [ ] The explanation clearly states that Pages is static and the backend is separate.
