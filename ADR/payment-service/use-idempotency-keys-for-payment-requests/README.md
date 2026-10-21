---
id: "40096cd6-5ae0-81aa-8dcd-d8c9e8e4e54e"
title: "Use Idempotency Keys for Payment Requests"
status: "Published"
created_time: "2026-10-21T11:07:00.000Z"
last_edited_time: "2026-10-21T11:07:00.000Z"
notion_url: "https://app.notion.com/p/Use-Idempotency-Keys-for-Payment-Requests-40096cd65ae081aa8dcdd8c9e8e4e54e"
type: "ADR"
scope: "Component"
component: "payment-service"
---
## Context

`payment-service` occasionally receives duplicate charge requests when clients retry after a timeout, risking double-charging customers.

## Decision

Every charge-creation request to `payment-service` must include a client-generated **idempotency key**. The service stores the key alongside the resulting transaction and returns the original result for any repeated key within a 24-hour window.

## Consequences

- Retried requests are safe by construction; no double charges.

- Clients must generate and persist a unique key per logical payment attempt.

- `payment-service` needs a dedicated idempotency-key store with TTL-based cleanup.

- Non-idempotent legacy callers must be updated before this is enforced strictly.
