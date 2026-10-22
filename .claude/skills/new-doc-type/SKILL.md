---
name: new-doc-type
description: Bootstrap a new Notion-authored document type for this repo (like ADR or Design Doc) - creates the Notion database with a researched property schema, wires it into sidebar.yaml, and offers to trigger the sync workflow.
---

# Adding a new document type

This repo syncs Notion databases into this git repo as markdown, rendered by
VitePress. Each document *type* (ADR, Design Doc, ...) is one Notion database
plus one entry in `sidebar.yaml` that tells `.scripts/sync_notion.py` how to
route synced pages into folders and `.vitepress/sidebar.mjs` how to group
them in the sidebar (computed at build time, not a static file). This skill
adds a new one end to end.

Read `sidebar.yaml`'s header comment first — it documents every field this
skill writes. Read `CONTRIBUTING.md` for the MCP/auth setup this skill
depends on (Notion MCP via OAuth, GitHub MCP via `GITHUB_PERSONAL_ACCESS_TOKEN`).

## Step 1 — Get the document type name

If the user didn't name it in their request, ask. Examples: "RFC",
"Runbook", "Post-mortem". Use their exact capitalization for the Notion
database title and the frontmatter `type` field; derive a lowercase,
hyphenated folder name from it for `root` (e.g. "Post-mortem" → `post-mortems`).

## Step 2 — Research a property schema

WebSearch for the document type's established best-practice structure, e.g.
"RFC document template fields best practices" or "runbook document Notion
template properties". Look for what a team typically tracks for that
document type beyond prose content — things like owner, severity, decision
date, related systems, review cadence. Pull together a short proposed list
(aim for 2-5 properties; this is a lightweight tracking schema, not an
exhaustive one) with a Notion property type for each (`select`, `multi_select`,
`person`, `date`, `url`, `rich_text`, `number`, `checkbox`).

Every document type also needs, non-negotiably, three more properties with
these **exact** names and types (the sync scripts hardcode them):

- `Doc name` — title
- `Status` — status, with groups `Draft (to_do)`, `In Review (in_progress)`,
  `Published (complete)`, `Outdated (complete)` — matches every existing
  database in this repo; keep it consistent unless the user asks otherwise
- `Sync` — select, with exactly one option `Ready to Sync`

## Step 3 — Decide the grouping strategy

Ask the user (don't assume) which pattern fits this type, using the two
existing databases as reference:

- **Scope-based** (like ADR): a `Scope` select (`Global` / `Area` / `Component`)
  plus `Area` and `Component` select properties, each only meaningful when
  `Scope` matches. Folder: `global`, `{area}`, or `{component}`.
- **Single grouping field** (like Design Doc): one select property (often
  `Area`, but could be `Team`, `System`, whatever fits), one folder segment
  per value.
- **Flat, no grouping**: every doc lands directly under `root`. Simplest; fine
  for small, rarely-expanding sets.

## Step 4 — Confirm with the user

Use AskUserQuestion (or just ask directly) to present: the full proposed
property list (plumbing + researched + grouping), the folder root, and the
sidebar label. Let them edit before creating anything in Notion — this is a
live workspace change, don't skip confirmation.

## Step 5 — Create the Notion database

Use `mcp__notion__notion-create-database` with a `CREATE TABLE` DDL
statement, e.g. for a Scope-based type:

```sql
CREATE TABLE "RFC" (
  "Doc name" TITLE,
  "Scope" SELECT('Global':blue, 'Area':purple, 'Component':orange),
  "Area" SELECT(),
  "Component" SELECT(),
  "Status" STATUS('Draft':gray:to_do, 'In Review':blue:in_progress, 'Published':green:complete, 'Outdated':brown:complete),
  "Sync" SELECT('Ready to Sync':green)
)
```

Add the researched properties as additional columns in the same statement.
`SELECT()` with no options is valid — Notion select options are added later
via `ALTER COLUMN ... SET SELECT(...)` once real values are known (adding an
option up front for a value you already know about, e.g. `Area` values the
user listed, is fine and saves a step).

The tool result includes a `<data-source url="{{collection://<uuid>}}">`
block — that `collection://<uuid>` is the ID you need next.

## Step 6 — Add the GitHub secret and wire the workflow

Tell the user the new data source ID and the secret name it needs
(`<TYPE_IN_SCREAMING_SNAKE>_DATA_SOURCE_ID`, e.g. `RFC_DATA_SOURCE_ID`). Ask
before running anything — this writes to shared GitHub repo config. If they
confirm, run:

```bash
gh secret set RFC_DATA_SOURCE_ID --body "<the collection:// uuid, no prefix>"
```

Setting the secret alone is not enough — `.github/workflows/sync_notion.yml`
only forwards secrets it explicitly lists under the sync step's `env:`. Add
the new one there too (and update the step name's doc-type list), or the
workflow will fail with `Missing required env var ..._DATA_SOURCE_ID` even
though the secret exists.

## Step 7 — Wire it into `sidebar.yaml`

Append a new entry to the `sections:` list using the field reference in the
file's header comment. Use the Edit tool for a targeted insertion — don't
regenerate the whole file programmatically, that would destroy the existing
comments. Match the style of the existing `adr`/`design-doc` entries exactly.

After editing, run `mise run gen-sidebar` to confirm the YAML parses and the
sidebar computes without error (it's expected to show zero new entries for
this type, since nothing has synced yet).

## Step 8 — The Notion "ready to sync" automation

Notion Automations can't be created via the API. Tell the user to set this
up by hand, once, in the new database:

1. Open the new database → `⋯` menu → **Automations** → **New automation**
2. Trigger: *When* **Status** *is edited* and *is* **Published**
3. Action: *Edit property* → set **Sync** to **Ready to Sync**

## Step 9 — Commit and offer to sync

Show the user the `sidebar.yaml` diff and ask whether to commit/push it
(follow this repo's established pattern — don't push without asking). Once
it's on `main`, offer to trigger the workflow to test end-to-end:

```bash
gh workflow run sync_notion.yml
```

Then check the run (`gh run list --workflow sync_notion.yml`, `gh run view
<id> --log`) and report whether it succeeded, same as past debugging in this
repo — the new section will sync zero documents until the user actually
creates and publishes a page in the new database, which is expected, not a
failure.
