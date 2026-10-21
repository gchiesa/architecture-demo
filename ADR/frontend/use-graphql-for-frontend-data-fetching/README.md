---
id: "40096cd6-5ae0-8162-a5f2-e55509da500e"
title: "Use GraphQL for Frontend Data Fetching"
status: "Published"
created_time: "2026-10-21T11:07:00.000Z"
last_edited_time: "2026-10-21T11:07:00.000Z"
notion_url: "https://app.notion.com/p/Use-GraphQL-for-Frontend-Data-Fetching-40096cd65ae08162a5f2e55509da500e"
docsify_url: "https://architecture-demo.g-c.dev/#/ADR/frontend/use-graphql-for-frontend-data-fetching/README"
type: "ADR"
scope: "Area"
area: "Frontend"
---
## Context

Frontend teams currently call a mix of REST endpoints per page, leading to over-fetching, under-fetching, and duplicated client-side aggregation logic across apps in the Frontend area.

## Decision

All new Frontend-area applications query data through a shared <b>GraphQL gateway</b> instead of calling REST endpoints directly. Existing REST-based apps are migrated opportunistically.

## Consequences

- Clients request exactly the fields they need, reducing payload size.
- A single gateway schema becomes the shared contract across Frontend apps.
- Teams need to learn GraphQL query patterns and caching behavior.
- The gateway becomes a new critical-path dependency that must be monitored closely.