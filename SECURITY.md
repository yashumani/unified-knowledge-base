# Security Policy

## Public repository warning

This repository is a personal/public scaffold. Do not commit:

- employer documents
- private dashboards
- production data
- customer or employee information
- access tokens
- service account credentials
- proprietary metric definitions
- screenshots of internal systems
- confidential business rules

Use synthetic examples here. Move the scaffold into a private GitLab environment before connecting real sources.

## Reporting security issues

Open a private advisory or contact the repository owner directly. Do not publish exploit details in a public issue.

## What the scaffold enforces today

- Shared-secret auth on every route except `/health`, enforced by default and
  compared in constant time. The server logs a warning while the token is still
  the shipped default or while `UKB_REQUIRE_AUTH` is false.
- Sensitivity filtering at retrieval time, applied before a context pack is
  composed, and applied identically to `/brain/objects`, `/brain/graph`, and the
  MCP adapter so no endpoint routes around it.
- Clearance bound to the authenticated principal, not to the client-supplied
  `user_id` in a request body.
- Approval blocked over MCP by default, so an LLM agent cannot publish knowledge.
- Audit events on submission, review decisions, context-pack requests, and
  blocked MCP approvals, across the REST, CLI, and MCP adapters.

### Known limits

- The API token is one shared secret, not user identity. Every holder shares
  `UKB_DEFAULT_USER_CLEARANCE` unless listed in `UKB_USER_CLEARANCES`.
- `VITE_UKB_API_TOKEN` is inlined into the React bundle at build time. A public
  build must not carry a live token; use demo mode or wait for SSO.
- The store is in-memory. Nothing survives a restart and there is no encryption
  at rest.

## Production security expectations

Before production use, add:

- SSO/OIDC to replace the shared token
- role-based access control wired to the roles in `knowledge/access/roles.yaml`
- source ACL inheritance
- object-level security
- audit log persistence and retention
- secret management
- container scanning
- dependency scanning
- network restrictions
- MCP origin validation and authentication
