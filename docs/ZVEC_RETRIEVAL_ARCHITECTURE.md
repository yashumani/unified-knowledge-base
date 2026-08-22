# Zvec Retrieval Architecture

Unified Knowledge Base uses Zvec as a **derived local retrieval index**, not as the authoritative database.

```text
PostgreSQL / SQLite
  approved objects, reviews, access metadata, versions, audit
        |
        | approved projection
        v
Zvec
  full-text index and structured retrieval filters
        |
        v
RetrievalService
  ranking, fallback, authoritative-object lookup, context-pack input
```

## Product boundary

- PostgreSQL or SQLite remains the source of truth.
- The private object store preserves original evidence.
- Zvec contains a rebuildable projection of published knowledge objects.
- Candidate, rejected, and changes-requested objects are not indexed.
- Search results are mapped back to the authoritative store and checked for published status again.
- Ollama receives governed context packs after retrieval; it does not browse the corpus directly.

## Full-text-first design

The first implementation indexes title, summary, aliases, owner, type, domain, and approved source excerpts. Filters cover domain, object type, sensitivity, and review status.

Dense and sparse vectors remain optional future recall lanes. They must never override authorization, approval state, exact identifiers, source authority, or version validity.

## Runtime modes

```text
UKB_SEARCH_BACKEND=zvec
UKB_ZVEC_PATH=./.ukb/zvec/approved-knowledge
UKB_ZVEC_COLLECTION_NAME=ukb_approved_knowledge
```

The deterministic fallback is selected with:

```text
UKB_SEARCH_BACKEND=memory
```

When Zvec cannot initialize or query, the resilient wrapper keeps approved-object retrieval available through the deterministic index.

## API

```text
GET  /search/status
POST /search/rebuild
POST /brain/search
```

Search responses expose the object ID, score, active engine, match reasons, and the full approved knowledge object.

## Synchronization and recovery

The current MVP synchronizes the approved-object projection when the published set changes and keeps one shared index instance in the API process.

The production evolution should use a PostgreSQL transactional outbox and one index worker. The index remains disposable and can be rebuilt without changing review state, evidence, ownership, or audit history.

## Accuracy contract

UKB does not promise perfect semantic retrieval. It treats these as non-negotiable requirements:

```text
unauthorized objects never become candidates
unpublished objects never become candidates
every returned object has source evidence
every result exposes ranking reasons
low-confidence or missing-context requests may abstain
```

Retrieval quality should be measured using a gold question set, Recall@K, reciprocal rank, citation precision, correct-version rate, conflict detection, and zero permission leakage.

## Current limitations

- Indexing is object-level; evidence chunks are the next parser milestone.
- The current writer model is designed for one API process.
- Durable outbox synchronization and full restart cleanup remain future work.
- Vector retrieval is intentionally disabled in this first implementation.
