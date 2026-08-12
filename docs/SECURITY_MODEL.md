# Security Model

## Principle

Filter before the model sees context.

The model should never receive data the user is not allowed to access.

## Controls

### 1. Source ACL inheritance

Extracted knowledge inherits permissions from its source unless a stricter policy is applied.

### 2. Object-level access

Every knowledge object has:

```text
sensitivity
allowed_roles
denied_roles
domain
owner
status
```

### 3. Retrieval-time filtering

The context pack builder must filter by identity and role before adding objects or evidence.

### 4. Human review gate

AI-created candidates are not official until approved.

### 5. Sensitive data detection

Future parser stages should flag:

```text
PII
PHI
financial confidential data
credentials
customer identifiers
employee data
legal privileged material
```

### 6. Audit logs

Track:

```text
who requested context
what objects were retrieved
what sources were used
what action was taken
whether access was denied
```

### 7. Public repo warning

This repository is public/personal. Use only synthetic examples.

Do not add employer documents, exports, metrics, dashboards, credentials, screenshots, or proprietary rules.
