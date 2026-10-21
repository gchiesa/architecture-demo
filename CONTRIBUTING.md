# Contributing / repo tooling

This file is for people working on the sync pipeline itself, not for the
docsify-rendered documentation (see `README.md` / the live site for that).

## Layout

- `.scripts/` — Python sync/sidebar scripts (run via `uv`, PEP 723 inline deps)
- `.ci/scripts/` — thin shell wrappers invoked by `mise` tasks
- `mise.toml` — `mise run sync-notion`, `mise run gen-sidebar`
- `sidebar.yaml` — single source of config for both the sync routing and the
  docsify sidebar; see the comments at the top of the file

The leading dots on `.scripts/` and `.ci/` are intentional: everything else at
the repo root is actual documentation content (`ADR/`, `design-docs/`, ...),
and these two are hidden from a casual directory listing to keep that clean.

## MCP servers (`.mcp.json`)

This repo declares project-scoped MCP servers for Notion and GitHub, so any
Claude Code session opened in this repo (including the `new-doc-type` skill)
has them available without per-person setup.

- **Notion** (`https://mcp.notion.com/mcp`) — Notion's hosted MCP server.
  Authenticates via OAuth; on first use, run `/mcp` in Claude Code and follow
  the browser prompt. No token/env var needed.
- **GitHub** (`https://api.githubcopilot.com/mcp/`) — GitHub's hosted MCP
  server. OAuth is **not** currently usable here: Claude Code's OAuth flow
  requires authorization-server metadata discovery (RFC 8414) that this
  endpoint doesn't support, so the connection fails with an
  "Incompatible auth server" error. Use a GitHub personal access token
  instead:

  ```bash
  export GITHUB_PERSONAL_ACCESS_TOKEN="<your PAT, repo + workflow scopes>"
  ```

  Set it in your shell profile or Claude Code's env config so it's available
  whenever Claude Code starts; `.mcp.json` references it as
  `${GITHUB_PERSONAL_ACCESS_TOKEN}`, it is never written to the file itself.

## Adding a new document type

Use the `new-doc-type` skill (`.claude/skills/new-doc-type/SKILL.md`) rather
than doing this by hand — it researches a sensible property schema, creates
the Notion database, wires it into `sidebar.yaml`, and offers to trigger the
sync workflow.
