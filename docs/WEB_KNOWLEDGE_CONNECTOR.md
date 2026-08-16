# Web Knowledge Connector

The Web Knowledge Connector converts a configured URL into preserved source evidence and a human-review candidate. It is not an unrestricted crawler.

```text
configured URL
  -> source policy
  -> robots check
  -> bounded fetch
  -> original evidence preservation
  -> text extraction
  -> local Ollama enrichment
  -> human review
  -> approved knowledge
  -> Zvec projection
```

## Default configuration

URL collection stays disabled until approved hosts are configured.

```text
UKB_WEB_CONNECTOR_ENABLED=false
UKB_WEB_ALLOWED_HOSTS=
```

After governance review, administrators may configure exact hosts or scoped subdomain patterns. A global wildcard is not supported.

## Current controls

- HTTP and HTTPS sources only.
- Explicit hosts and ports.
- Redirect, response-size, and content-type limits.
- Robots-policy enforcement, configurable to fail closed.
- Original response preservation with a content digest.
- Canonical URLs checked against the same source policy.
- Local AI creates suggestions only.
- Human approval is required before publication.

## API

```text
GET  /connectors/web/status
POST /ingestion/web
```

The capture response contains source evidence, a review item, and private artifact metadata. It never publishes knowledge directly.

## Evidence metadata

```text
requested URL
final URL
canonical URL
content type
object key and internal URI
content digest
byte size
retrieval time
discovered links
```

## Current scope

This release captures one page per request. Recursive crawling, sitemaps, feeds, authenticated portals, browser rendering, and scheduled recrawls remain future connector plugins.

Production collection should run with controlled outbound networking and per-connector quotas. Private-network collection should use a separate internal connector with an explicit internal source policy.
