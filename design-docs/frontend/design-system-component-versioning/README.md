---
id: "40096cd6-5ae0-8101-adaa-fbb1806f2cf1"
title: "Design System Component Versioning"
status: "Published"
created_time: "2026-10-21T11:08:00.000Z"
last_edited_time: "2026-10-21T11:08:00.000Z"
notion_url: "https://app.notion.com/p/Design-System-Component-Versioning-40096cd65ae08101adaafbb1806f2cf1"
docsify_url: "https://architecture-demo.g-c.dev/#/design-docs/frontend/design-system-component-versioning/README"
type: "Design Doc"
area: "Frontend"
---
## Overview

Frontend teams consume a shared component library that currently ships as a single unversioned package, making breaking changes risky to roll out.

## Goals

- Allow component library changes to ship without forcing every consuming app to upgrade simultaneously.
- Give consuming teams a predictable upgrade path and changelog.
- Keep the number of actively supported versions small.

## Design

The component library adopts semantic versioning with major versions published as separate npm dist-tags (<code>latest</code>, <code>next</code>, and one previous major as <code>lts</code>). Breaking changes land only in a new major version behind the <code>next</code> tag until consuming teams have migrated, at which point it is promoted to <code>latest</code>.

## Alternatives Considered

- <b>Single unversioned package with feature flags per component</b>: rejected, since flagging every breaking visual change does not scale and clutters the component API.
- <b>Monorepo with per-app component forks</b>: rejected, since it reintroduces the duplication the shared library was meant to eliminate.