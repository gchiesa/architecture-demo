# Architecture Demo Docs

Engineering docs (ADRs, Design Docs, PRDs) authored in Notion and published
to this site. Browse the sidebar for the full list.

## How a doc gets here

1. **Write it in Notion**, in the database for its type (ADR, Design Doc,
   PRD, ...).
2. Set **Status** to `Published` and **Sync** to `Ready to Sync`. In each
   database this is wired as a one-click Notion automation: editing Status
   to `Published` flips Sync for you.
3. The next scheduled sync (daily) — or a maintainer manually running the
   `Sync Notion Articles to GitHub` GitHub Action — pulls the page into this
   repo as a `README.md` under `ADR/`, `design-docs/`, or `PRD/`, and the
   site rebuilds and redeploys automatically.

No GitHub access is needed to author or update a doc — Notion is the
editing surface.

## Editing after it's published

Once a doc is synced, its body can *also* be edited here in GitHub (e.g. a
reviewer suggests a wording fix in a PR). Any edit pushed to `main` is
pushed back to the originating Notion page automatically, so the two stay
in sync in both directions. A few things to know:

- **Properties stay Notion-owned.** Things like Status, Scope, Area, Owner
  live in the doc's frontmatter for display, but editing them here has no
  effect — change them in Notion.
- If the Notion page was edited more recently than the last sync, the
  push-back is skipped (to avoid clobbering it) and flagged on the GitHub
  Actions run — resolve it by re-syncing from Notion or reconciling by hand.

## Adding a new kind of document

Ask for the `new-doc-type` Claude Code skill (or run `/new-doc-type` if
you're set up with Claude Code in this repo). It creates the new Notion
database with a sensible property schema, wires it into the sync pipeline
and site sidebar, and offers to trigger a test sync — no manual YAML editing
required.

## For maintainers

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for repo tooling setup (MCP
servers, local commands) and [`CLAUDE.md`](CLAUDE.md) for how the sync
pipeline and site build fit together end to end.
