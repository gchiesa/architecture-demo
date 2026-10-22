---
id: "40096cd6-5ae0-819b-ad6c-f8b9db6815be"
title: "Notion-to-GitHub Docs Sync Pipeline"
status: "Published"
created_time: "2026-10-21T11:08:00.000Z"
last_edited_time: "2026-10-21T11:08:00.000Z"
notion_url: "https://app.notion.com/p/Notion-to-GitHub-Docs-Sync-Pipeline-40096cd65ae0819bad6cf8b9db6815be"
doc_url: "https://architecture-demo.g-c.dev/design-docs/platform/notion-to-github-docs-sync-pipeline/"
content_hash: "da503a35135ccdd16e31c6368f6e84e2a7281a62a53f3b0b228119ec3c607682"
type: "Design Doc"
area: "Platform"
---
## Overview

JCP Architects author ADRs and Design Docs in Notion. A scheduled GitHub Action mirrors published documents into this repository as Markdown, rendered as a browsable site with docsify.

## Goals

- Notion remains the single authoring surface for architects.
- Documents only sync once they are marked <b>Published</b> and flagged <b>Ready to Sync</b>.
- The resulting folder structure in git reflects each document's Type and Scope (ADR: global / area / component; Design Doc: area).

## Design

A Python script (<code>scripts/sync_notion.py</code>), run via <code>mise run sync-notion</code>, queries the ADR and Design Doc data sources for pages flagged Ready to Sync, converts their blocks to Markdown, and writes them under <code>ADR/</code> or <code>design-docs/</code> following the Scope/Area/Component routing rules. A second script regenerates <code>_sidebar.md</code> for docsify navigation.

## Alternatives Considered

- <b>victornpb/notion-jam</b> (third-party GitHub Action): rejected because it only supports a single flat property filter and cannot route documents into different folders based on Scope/Area/Component.
- <b>True two-way Notion↔GitHub sync</b>: rejected for now; tooling in this space is still immature for unattended CI use. One-way, Notion-authored sync is simpler and matches the "Notion is the source of truth for architecture docs" model.