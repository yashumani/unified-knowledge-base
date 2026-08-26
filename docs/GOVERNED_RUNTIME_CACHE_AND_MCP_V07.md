# Governed Runtime, Conversation Caching, and MCP v0.7

## Purpose

Version 0.7 separates durable conversational memory from disposable performance caches and exposes the Unified AI Brain through a governed Model Context Protocol boundary.

```text
Open WebUI-adapted client / MCP client
                ↓
Authenticated or configured service principal
                ↓
Durable conversation state
                ↓
Tenant + permission + snapshot cache identity
                ↓
Authorized retrieval and governed Context Pack
                ↓
Citations, caveats, coverage, and cache receipt
```

Caches are optimizations. PostgreSQL and the canonical knowledge stores remain authoritative.

## Vocabulary

| Mechanism | Stores | Can skip the model? | Authoritative? |
|---|---|---:|---:|
| Conversation persistence | Messages, summaries, metadata | No | Yes |
| Exact response cache | A complete prior governed result | Yes | No |
| Tool-result cache | Read-only lineage/tool output | Usually | No |
| Retrieval cache | Permission- and snapshot-scoped retrieval output | No | No |
| Provider prompt cache | Reusable model prefix state | No | No |
| Per-request KV cache | Transformer attention tensors | No | No |

## Exact response cache identity

A cache hit requires the same effective inputs, including:

```text
tenant
subject and permission scope
model and provider
runtime prompt version
tool schema version
response schema version
access-policy version
knowledge snapshot
data snapshot
conversation-state hash
question, domain, mode, and locale
```

The cache key contains a SHA-256 digest rather than raw questions or retrieved content. A cached Context Pack is re-authorized before delivery.

Publishing or superseding knowledge changes the knowledge snapshot and therefore produces a natural miss. Tenant-specific invalidation never flushes another tenant's cache entries.

## Durable conversation state

Conversation records, messages, and cache receipts are stored separately from cache entries. The SQL migration creates:

```text
runtime_conversations
runtime_conversation_messages
runtime_cache_events
```

Redis loss or eviction cannot remove conversation history. Local demonstrations can use the in-memory repository; private runtimes should set:

```text
UKB_CONVERSATION_STORE_BACKEND=sqlalchemy
UKB_CACHE_BACKEND=redis
UKB_REDIS_URL=redis://redis:6379/0
```

## MCP governance contract

The MCP server is an adapter over the same application and runtime services used by other clients.

### Read and conversation tools

```text
runtime_status
start_conversation
list_conversations
get_conversation
ask_brain
search_brain
get_context_pack
get_source_lineage
```

### Contribution and governance tools

```text
submit_context
list_review_items
approve_review_item
publish_review_item
invalidate_cache
```

`submit_context` creates a governed review candidate. It cannot publish memory.

Approval, publication, and cache invalidation fail closed unless their explicit settings are enabled and the configured MCP principal has the corresponding role.

```text
UKB_MCP_ALLOW_APPROVAL=false
UKB_MCP_ALLOW_PUBLICATION=false
UKB_MCP_ALLOW_CACHE_INVALIDATION=false
```

### MCP identity

The default server uses a least-privilege service principal:

```text
UKB_MCP_SUBJECT=mcp-service
UKB_MCP_TENANT_ID=default
UKB_MCP_ROLES=consumer,submitter
UKB_MCP_CLEARANCE=internal
```

For a private deployment, place the Streamable HTTP endpoint behind the approved identity-aware reverse proxy or run separate tenant-bound service identities. The model prompt is never an authorization control.

## Transport

Local stdio remains the default:

```bash
python -m ukb.mcp.server
```

Private Streamable HTTP:

```bash
UKB_MCP_TRANSPORT=streamable-http \
UKB_MCP_HOST=0.0.0.0 \
UKB_MCP_PORT=8765 \
python -m ukb.mcp.server
```

Validate the real network transport:

```bash
python scripts/validate_mcp_transport.py \
  --url http://127.0.0.1:8765/mcp \
  --output mcp-validation.json
```

The validation performs an MCP initialize handshake, lists tools and resources, calls `runtime_status`, and creates a durable conversation.

## Redis failure behavior

`UKB_CACHE_FAIL_OPEN=true` makes Redis an optimization rather than an availability dependency. When Redis is unavailable, the runtime uses an in-process TTL cache and continues through the normal governed model/tool path. Production monitoring should alert on this fallback.

## Prompt and KV caching

The application records a deterministic prompt-prefix hash based on:

```text
runtime prompt version
tool schema version
response schema version
access-policy version
AI schema version
provider and model
```

Provider prompt caching and inference-engine KV caching remain provider/runtime concerns. Stable instructions and sorted tool schemas should precede dynamic identity, retrieved data, timestamps, and the current question.

## Ingestion experience

The Open WebUI-adapted Sources page now begins with a three-decision launchpad:

```text
Connect source
→ validate evidence quality
→ create review candidates
```

Users can choose paste, files, folder, ZIP, Drive, Crawl4AI, Git, or object storage. Safe defaults reduce the initial decision burden while the full governance, parser, chunking, duplicate, and classification controls remain available.

Every channel follows the same boundary:

```text
preserve original evidence
→ deterministic quality firewall
→ advisory AI enrichment
→ assigned human review
→ explicit approval
→ separate publication
```

## Operational metrics

The runtime exposes or records:

```text
cache lookups, hits, misses, writes, errors, and invalidations
conversation and message counts
cache namespace and backend
cache eligibility and miss reason
prompt-prefix hash
knowledge snapshot
response cache hit state
MCP transport and configured service identity
```

A high cache-hit rate is not a correctness target. Zero cross-tenant leakage, traceable evidence, current snapshots, and safe misses are the primary requirements.
