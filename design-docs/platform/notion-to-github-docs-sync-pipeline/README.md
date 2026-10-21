---
id: "40096cd6-5ae0-819b-ad6c-f8b9db6815be"
title: "Notion-to-GitHub Docs Sync Pipeline"
status: "Published"
created_time: "2026-10-21T11:08:00.000Z"
last_edited_time: "2026-10-21T11:08:00.000Z"
notion_url: "https://app.notion.com/p/Notion-to-GitHub-Docs-Sync-Pipeline-40096cd65ae0819bad6cf8b9db6815be"
type: "Design Doc"
area: "Platform"
---
## Overview

JCP Architects author ADRs and Design Docs in Notion. A scheduled GitHub Action mirrors published documents into this repository as Markdown, rendered as a browsable site with docsify.

## Goals

- Notion remains the single authoring surface for architects.

- Documents only sync once they are marked **Published** and flagged **Ready to Sync**.

- The resulting folder structure in git reflects each document's Type and Scope (ADR: global / area / component; Design Doc: area).

## Design

A Python script (`scripts/sync_notion.py`), run via `mise run sync-notion`, queries the ADR and Design Doc data sources for pages flagged Ready to Sync, converts their blocks to Markdown, and writes them under `ADR/` or `design-docs/` following the Scope/Area/Component routing rules. A second script regenerates `_sidebar.md` for docsify navigation.

## Alternatives Considered

- **victornpb/notion-jam** (third-party GitHub Action): rejected because it only supports a single flat property filter and cannot route documents into different folders based on Scope/Area/Component.

- **True two-way Notion↔GitHub sync**: rejected for now; tooling in this space is still immature for unattended CI use. One-way, Notion-authored sync is simpler and matches the "Notion is the source of truth for architecture docs" model.
