# Governed File Ingestion

## Current scope

Unified Knowledge Base can preserve and extract UTF-8 text-oriented files:

```text
.txt
.md / .markdown
.sql
.csv
.json
.yaml / .yml
```

## Workflow

```text
upload
  -> validate filename, extension, encoding, and size
  -> preserve original bytes in the private object store
  -> extract normalized text
  -> create source evidence and a candidate object
  -> run local Ollama enrichment or deterministic fallback
  -> place the candidate in the human review queue
```

The upload endpoint never publishes knowledge automatically.

## API

```text
POST /ingestion/files
GET  /sources
GET  /sources/{source_id}
```

The multipart upload accepts a file plus submitter, domain, sensitivity, optional title, and comma-separated tags.

## Storage boundary

The API returns an internal URI such as:

```text
object://local/sources/<source-id>/<digest>.md
```

It does not expose the host filesystem path. The production object-store directory is mounted as a private API volume.

## Limits

Default limits:

```text
maximum original file size: 10 MB
maximum extracted text: 250,000 characters
encoding: UTF-8
```

Binary content and unsupported extensions are rejected before AI enrichment.

## UI

The React console mounts an upload panel below the main dashboard. It checks backend health and remains disabled when the static GitHub Pages build cannot reach the governed API.

## Deferred formats

PDF, DOCX, PPTX, XLSX, images, OCR, and layout-aware extraction require dedicated parser plugins and source-span mapping before they should enter the approved brain workflow.
