# Workplace-Safe Example Policy

This public scaffold must use only neutral, synthetic examples.

Do not use examples that look like they came from a current or former employer, client, internal project, customer segment, business unit, dashboard, planning workflow, product line, operating ritual, or proprietary process.

## Approved general demo domain

Use this neutral sample domain for general UI demonstrations:

```text
Domain: support
Primary metric: Incident Resolution Time
Report: SLA Review Dashboard
Owner: Support Operations
Rule: SLA Review Window
Related metrics: First Response Time, Reopen Rate, Ticket Backlog
```

## Approved synthetic industry reference packs

A feature may include a generic industry reference pack when the user explicitly requests that domain and all of the following controls hold:

- no employer, carrier, client, vendor, or customer name;
- no copied metric definition, dashboard, source-system name, threshold, target, or operating procedure;
- no real data, screenshots, schema exports, credentials, or internal terminology;
- a conspicuous synthetic label;
- content created from generic public domain concepts rather than workplace experience.

The Talk2Data telecommunications example under `examples/talk2data-telecom/` is such a synthetic contract-test fixture. It exists to validate Domain Pack classification and tenant-memory behavior, not to describe a real telecommunications company.

## Avoid in public examples

- employer names
- client names
- proprietary product names
- real industry-specific employer workflows
- metric names or definitions copied from internal work
- internal dashboard or source-system names
- planning or reporting processes that resemble real work
- real customer, employee, vendor, network, or operational data
- screenshots of private systems

## Replacement pattern

When ordinary documentation needs a sample KPI, use:

```text
Incident Resolution Time is the average elapsed time from incident creation to resolved status for product support cases, excluding duplicate incidents and customer-wait periods. It appears in the SLA Review Dashboard and is owned by Support Operations. Recently resolved incidents may need 24 hours for quality review tags to settle.
```

This is synthetic and intentionally generic.
