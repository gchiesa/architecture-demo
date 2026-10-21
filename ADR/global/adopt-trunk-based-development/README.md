---
id: "40096cd6-5ae0-8183-9f16-d9f6e5f55c6a"
title: "Adopt Trunk-Based Development"
status: "Published"
created_time: "2026-10-21T11:07:00.000Z"
last_edited_time: "2026-10-21T11:07:00.000Z"
notion_url: "https://app.notion.com/p/Adopt-Trunk-Based-Development-40096cd65ae081839f16d9f6e5f55c6a"
type: "ADR"
scope: "Global"
---
## Context

Teams across JCP maintain long-lived feature branches that diverge from `main` for days or weeks, causing painful merge conflicts and delaying integration feedback until late in the development cycle.

## Decision

All teams adopt **trunk-based development**: short-lived branches (less than one day old) merged into `main` behind feature flags when work is incomplete. No long-lived release or feature branches.

## Consequences

- Integration issues surface early, while context is still fresh.

- Feature flags become a first-class tool; teams need a lightweight flagging mechanism.

- CI must be fast and reliable, since every merge to `main` is a release candidate.

- Existing long-lived branches must be migrated or closed out over the next quarter.
