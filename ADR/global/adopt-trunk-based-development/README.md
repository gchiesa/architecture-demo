---
id: "40096cd6-5ae0-8183-9f16-d9f6e5f55c6a"
title: "Adopt Trunk-Based Development"
status: "Published"
created_time: "2026-10-21T11:07:00.000Z"
last_edited_time: "2026-10-26T11:53:00.000Z"
notion_url: "https://app.notion.com/p/Adopt-Trunk-Based-Development-40096cd65ae081839f16d9f6e5f55c6a"
doc_url: "https://architecture-demo.g-c.dev/ADR/global/adopt-trunk-based-development/"
content_hash: "5bd4e4f8051d2270817cb5fb2b101bf5c217f8f7a7629b7c4c85c6b81b809b1c"
type: "ADR"
scope: "Global"
---
## Context

Teams across JCP maintain long-lived feature branches that diverge from <code>main</code> for days or weeks, causing painful merge conflicts and delaying integration feedback until late in the development cycle.

Link to the [Consequences](/p/40096cd65ae081839f16d9f6e5f55c6a?v=47a1529682dc421eabd3cdff16a70bd3&pvs=25#bda4c88823014a70a1d67d6cfe5582df)

## Decision

All teams adopt <b>trunk-based development</b>: short-lived branches (less than one day old) merged into <code>main</code> behind feature flags when work is incomplete. No long-lived release or feature branches.

## Long paragraph

- a
- b
- c
- d
- e
- f
- g
- h
- i
- j
- k

<p />

## Consequences

- Integration issues surface early, while context is still fresh.
- Feature flags become a first-class tool; teams need a lightweight flagging mechanism.
- CI must be fast and reliable, since every merge to <code>main</code> is a release candidate.
- Existing long-lived branches must be migrated or closed out over the next quarter.