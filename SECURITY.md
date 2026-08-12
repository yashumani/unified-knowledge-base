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

## Production security expectations

Before production use, add:

- SSO/OIDC
- role-based access control
- source ACL inheritance
- object-level security
- retrieval-time filtering
- audit logs
- secret management
- container scanning
- dependency scanning
- network restrictions
- MCP origin validation and authentication
