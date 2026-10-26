# CLAUDE.md

Architecture reference for this repo's Notion -> GitHub -> VitePress sync
pipeline. Read this before touching `.scripts/`, `.vitepress/`,
`sidebar.yaml`, or any `.github/workflows/*.yml` here — it explains how the
pieces fit together so a change in one doesn't silently break another.

## What this repo is

A docs site (ADRs, Design Docs, PRDs) that's **authored in Notion** and
**published from GitHub**. Notion is the authoring surface (comments,
suggestions, databases, familiar editor); GitHub/VitePress is the published,
versioned, linkable artifact engineers actually read and link to from code
reviews, tickets, etc. The two stay in sync in both directions — see
[Two-way sync](#two-way-sync).

## The pipeline, end to end

```
Notion database (one per doc type: ADR, Design Doc, PRD, ...)
  │  page's "Status" -> Published, then "Sync" -> "Ready to Sync"
  ▼
sync_notion.yml  (daily cron + manual dispatch)
  │  .scripts/sync_notion.py reads sidebar.yaml to learn, per doc type:
  │  which Notion data source to query, which folder to write into, which
  │  Notion properties become frontmatter, and how to group docs that share
  │  the same "scope"/"area" into subfolders (see sidebar.yaml's header)
  │  -> writes/updates ADR/**/README.md, design-docs/**/README.md, PRD/**/README.md
  │  -> deletes any doc dir whose Notion page is no longer "Ready to Sync"
  │  -> opens a PR (main is protected), self-approves via a second token,
  │     auto-merges
  ▼
main branch updated
  │
  ├──> push_to_notion.yml (on push to main touching a synced README.md)
  │      .scripts/push_to_notion.py pushes body edits back to Notion —
  │      see Two-way sync below
  │
  └──> deploy_docs.yml (on push to main)
         mise run docs-build -> vitepress build -> .vitepress/dist
         -> actions/upload-pages-artifact + actions/deploy-pages
         -> live at https://architecture-demo.g-c.dev
```

Both `sync_notion.yml` and `push_to_notion.yml` commit through a PR instead
of pushing directly, because `main` is branch-protected. The PR is opened,
approved by a second identity (`PR_APPROVER_TOKEN`, a repo-admin PAT used
*only* for approval — see the comment above that step in `sync_notion.yml`),
and auto-merged, so no human has to click anything for a routine sync.

## Two-way sync

Notion is authoritative for a page's **properties** (Status, Scope, Area,
Owner, ...) and for its content the moment it's created or re-published.
Once a doc is synced to GitHub, its **body** can also be edited in GitHub
(e.g. a reviewer fixes a typo in a PR, or an engineer tightens wording) and
that edit flows back to Notion automatically:

1. A push to `main` touches `ADR/**/README.md`, `design-docs/**/README.md`,
   or `PRD/**/README.md`.
2. `push_to_notion.yml` runs `.scripts/push_to_notion.py` with the list of
   changed files.
3. For each file, it compares the body's `content_hash` (frontmatter field)
   against a freshly computed one. Unchanged bodies are skipped.
4. **Conflict guard**: it fetches the live Notion page and compares
   `last_edited_time`. If Notion was edited *after* the last pull into
   GitHub, the push is skipped with a GitHub Actions warning annotation
   instead of silently overwriting the Notion edit — this has to be
   resolved by hand (re-sync from Notion, or manually reconcile).
5. On success, it writes the new `content_hash` and `last_edited_time` back
   into the file's frontmatter (via the same auto-approved-PR pattern as
   the forward sync), so the next comparison is accurate.

**Out of scope for push-back, by design:**
- **Properties** (Scope, Area, Status, ...) — Notion stays authoritative for
  these; editing them in GitHub frontmatter has no effect on Notion.
- **Local images** — a doc whose body references `resources/` (downloaded
  at sync time, see `localize_images` in `notion_sync_lib.py`) is skipped
  with a warning; there's no safe way to hand Notion back a URL it can
  fetch that also works for a private repo.
- Commits from the sync bot itself don't re-trigger `push_to_notion.yml`
  (`if: github.event.head_commit.author.name != 'github-actions[bot]'`),
  otherwise every pull from Notion would immediately push right back.

## `sidebar.yaml`: the one file that drives routing *and* the site sidebar

One `sections:` entry per document type (ADR, Design Doc, PRD). Each entry
tells `sync_notion.py` which Notion data source to pull from and how to lay
out synced files on disk, **and** tells `.vitepress/sidebar.mjs` how to
group those same files in the site's sidebar — same `group_by`,
`group_order`, and label templates drive both, so the file layout and the
navigation structure never drift apart. Read the comment block at the top
of `sidebar.yaml` for the full field reference before editing it.

The VitePress sidebar is **not** a static generated file (unlike the old
docsify `_sidebar.md`) — `.vitepress/sidebar.mjs` walks `ADR/`, `design-docs/`,
`PRD/` for `README.md` frontmatter and rebuilds the sidebar config fresh on
every `vitepress dev`/`build`. `mise run gen-sidebar` prints the computed
result without doing a full build — useful as a sanity check after editing
`sidebar.yaml` (e.g. from the `new-doc-type` skill).

## Adding a new document type

Don't hand-edit `sidebar.yaml` plus create the Notion database plus wire
the GitHub secrets separately — use the `new-doc-type` skill
(`.claude/skills/new-doc-type/SKILL.md`, invoke as `/new-doc-type`). It
researches a sensible property schema, creates the Notion database, wires
`sidebar.yaml`, adds the required GitHub secret, and offers to trigger a
sync to test it end to end.

## Repo layout

| Path | Purpose |
| --- | --- |
| `ADR/`, `design-docs/`, `PRD/` | Synced content — one `README.md` per doc, plus a `resources/` dir for any localized images. Treat these as **generated from Notion**: edit body text if you need to, but don't restructure folders by hand, `sync_notion.py` owns that layout. |
| `sidebar.yaml` | Sync routing + sidebar grouping config, one section per doc type. See above. |
| `.scripts/` | Python sync scripts (`sync_notion.py`, `push_to_notion.py`, `notion_sync_lib.py`), run via `uv` with PEP 723 inline deps — no separate install step. |
| `.ci/scripts/` | Thin shell wrappers invoked by `mise` tasks. |
| `.vitepress/` | VitePress config (`config.mts`), the dynamic sidebar builder (`sidebar.mjs`), and the theme (`theme/`) that renders each doc's frontmatter as a meta table + "Edit in Notion" link. |
| `mise.toml` | Task runner: `sync-notion`, `push-to-notion`, `gen-sidebar`, `docs-dev`, `docs-build`, `docs-preview`. |
| `.github/workflows/sync_notion.yml` | Notion -> GitHub, scheduled daily + manual dispatch. |
| `.github/workflows/push_to_notion.yml` | GitHub -> Notion, on push to main touching a synced doc. |
| `.github/workflows/deploy_docs.yml` | Builds the VitePress site and deploys it to GitHub Pages on push to main. |
| `.claude/skills/new-doc-type/` | The skill for adding a new Notion-authored doc type. |
| `.mcp.json` | Project-scoped Notion + GitHub MCP servers, available to any Claude Code session opened here (see `CONTRIBUTING.md`). |

## Gotchas worth knowing before you change something

- **Frontmatter is partly machine-owned.** `id`, `content_hash`,
  `last_edited_time`, `notion_url`, `doc_url` are written and read by the
  sync scripts — don't hand-edit them, you'll desync the conflict detection
  in `push_to_notion.py` or break the "Edit in Notion" link.
- **The custom domain (`architecture-demo.g-c.dev`) lives in `public/CNAME`**,
  which only lands in the *build output* (`.vitepress/dist`), not the repo
  root. GitHub Pages must be configured with **Settings → Pages → Source:
  GitHub Actions** for this to take effect — if Pages is set to the legacy
  "deploy from branch" mode instead, it'll try to serve the raw `main`
  branch directly and the custom domain won't resolve.
- **`README.md` stays the source filename** everywhere (so folders render
  nicely in GitHub's own file browser) but builds to `index.html` via the
  `rewrites` rule in `.vitepress/config.mts` — don't rename these to
  `index.md`, that would break `sync_notion.py`'s output path assumptions
  and GitHub's folder preview.
- **Sync automation commits are PR'd, not pushed directly**, because `main`
  is protected. If you add a new automated write path, follow the same
  open-PR / approve-with-second-token / auto-merge pattern already used in
  `sync_notion.yml` and `push_to_notion.yml` rather than trying to push
  straight to `main`.
