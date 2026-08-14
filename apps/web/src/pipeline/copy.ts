/**
 * All user-facing pipeline wording, kept apart from the state logic so it can
 * be reviewed as prose.
 *
 * The governance lines restate the doctrine the docs already commit to —
 * docs/UI_CONSOLE_END_TO_END.md pairs every walkthrough step with a
 * "Governance meaning" block, and docs/LLM_FEATURE_ARCHITECTURE.md states the
 * rule as: LLM output = suggestion, human review = approval, published brain
 * object = official context.
 */

export const GOVERNANCE_MEANING = {
  submit:
    "Submitted context is evidence, not knowledge. Nothing here is published, trusted, or reachable by an AI app until a human approves it.",
  enrich:
    "AI output is a suggestion. The brief helps a reviewer decide faster. It cannot approve, publish, or add a fact the source did not already contain.",
  review:
    "This is the approval gate, and it is the whole product. A human decision — approve, reject, or request changes — is what turns a candidate into governed knowledge.",
  publish:
    "Published objects are the official context. Each one carries an owner, a review status, its source evidence, and a sensitivity level.",
  compose:
    "A context pack is governed context for an AI app to reason over. It is not an answer, and it only ever draws on approved knowledge."
} as const;

export const LOCKED_REASON = {
  enrich: "Submit some context first — there is nothing to enrich yet.",
  review: "Nothing is waiting for review. Submit context to create a candidate.",
  publish: "Approve a candidate first. Publication is what approval does.",
  compose: "Approve knowledge first — context packs only draw on published objects."
} as const;

export const STEP_INTRO = {
  submit:
    "Paste synthetic source context. The compiler classifies it and produces a candidate object for review.",
  enrich:
    "Run the enrichment provider over a candidate to get a reviewer-facing brief: what it detected, what looks risky, and what to ask before approving.",
  review:
    "Inspect the candidate against its source evidence, then make a governed decision. Confidence is a signal to weigh, never a reason to skip the check.",
  publish:
    "Approved candidates become published brain objects. This is the only content a context pack is allowed to use.",
  compose:
    "Ask a question and get the governed context an AI app would receive — evidence, caveats, guidance and an access decision."
} as const;

export const ALL_STEPS_COMPLETE =
  "Every step is complete. Explore the brain map to see the lineage you just built.";
