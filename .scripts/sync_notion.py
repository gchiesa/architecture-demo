# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "notion-client>=3.1.0,<4",
#   "requests>=2.31.0",
#   "pyyaml>=6.0",
# ]
# ///
import os
import shutil
import sys
from pathlib import Path

from notion_client import Client

from notion_sync_lib import (
    REPO_ROOT,
    build_doc_url,
    content_hash,
    fetch_page_headings,
    fetch_page_markdown,
    get_property_value,
    get_status,
    get_title,
    load_sections,
    load_site_base_url,
    localize_images,
    notion_property_name,
    resolve_template,
    rewrite_notion_links_to_repo,
    slugify,
    to_frontmatter,
)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"Missing required env var {name}", file=sys.stderr)
        sys.exit(1)
    return value


def query_ready_to_sync(notion: Client, data_source_id: str) -> list[dict]:
    pages: list[dict] = []
    cursor = None
    while True:
        response = notion.data_sources.query(
            data_source_id=data_source_id,
            filter={"property": "Sync", "select": {"equals": "Ready to Sync"}},
            start_cursor=cursor,
        )
        pages.extend(response["results"])
        if not response.get("has_more"):
            break
        cursor = response["next_cursor"]
    return pages


def build_context(section: dict, properties: dict) -> dict:
    """Frontmatter-field values read off a page's Notion properties, keyed by
    the snake_case name declared in `frontmatter_properties`. Each entry maps
    to a Notion property of the same name (e.g. `target_release` ->
    `Target Release`); the property's type decides how it's extracted."""
    return {
        prop: get_property_value(properties, notion_property_name(prop))
        for prop in section.get("frontmatter_properties", [])
    }


def dest_dir(section: dict, properties: dict, context: dict) -> Path:
    slug = slugify(get_title(properties))
    group_value = context.get(section["group_by"])
    segment_template = resolve_template(
        section.get("path_templates"), section.get("default_path_template"), group_value, context
    )
    if segment_template is None:
        raise ValueError(
            f"{section['label']} page '{get_title(properties)}' has unrecognized "
            f"{section['group_by']}: {group_value}"
        )
    # Templates may contain "/" to nest into subdirectories (e.g. "area/{area}"
    # vs "component/{component}", to keep same-named areas and components from
    # colliding in the same folder) - slugify each segment independently so
    # the "/" survives as a path separator rather than being collapsed to "-".
    segments = [slugify(part) for part in segment_template.split("/")]
    return Path(section["root"], *segments, slug)


def fetch_section_pages(notion: Client, notion_secret: str, section: dict) -> list[dict]:
    """Pass 1 for one section: query Ready-to-Sync pages and fetch each
    one's raw markdown + heading map, without writing or rewriting links
    yet - that needs the full cross-section registry, built after every
    section has been fetched (see `main`)."""
    data_source_id = require_env(section["notion_data_source_env"])
    pages = query_ready_to_sync(notion, data_source_id)
    fetched = []
    for page in pages:
        context = build_context(section, page["properties"])
        dest = dest_dir(section, page["properties"], context)
        fetched.append(
            {
                "page": page,
                "page_id": page["id"].replace("-", ""),
                "section": section,
                "dest": dest,
                "context": context,
                "markdown": fetch_page_markdown(notion_secret, page["id"]),
                "headings": fetch_page_headings(notion_secret, page["id"]),
            }
        )
    return fetched


def render_page(entry: dict, site_base_url: str, registry: dict[str, dict]) -> None:
    page = entry["page"]
    dest = entry["dest"]
    title = get_title(page["properties"])
    full_dest_dir = REPO_ROOT / dest
    full_dest_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = full_dest_dir / "resources"
    doc_url = build_doc_url(site_base_url, dest)

    body = rewrite_notion_links_to_repo(entry["markdown"], entry["page_id"], dest, doc_url, registry)
    body = localize_images(body, assets_dir)

    frontmatter = to_frontmatter(
        {
            "id": page["id"],
            "title": title,
            "status": get_status(page["properties"]),
            "created_time": page["created_time"],
            "last_edited_time": page["last_edited_time"],
            "notion_url": page["url"],
            "doc_url": doc_url,
            "content_hash": content_hash(body),
            "type": entry["section"]["type"],
            **entry["context"],
        }
    )

    (full_dest_dir / "README.md").write_text(frontmatter + body, encoding="utf-8")
    print(f'Synced "{title}" -> {dest}/README.md')


def remove_stale_docs(root: Path, expected_dirs: set[Path]) -> int:
    """Delete any previously-synced doc under `root` whose directory is not
    in `expected_dirs` (unsynced, moved to a new path, or deleted in Notion)."""
    full_root = REPO_ROOT / root
    if not full_root.exists():
        return 0

    removed = 0
    for readme in sorted(full_root.rglob("README.md")):
        doc_dir = readme.parent
        if doc_dir.relative_to(REPO_ROOT) not in expected_dirs:
            print(f"Removing stale doc {doc_dir.relative_to(REPO_ROOT)}")
            shutil.rmtree(doc_dir)
            removed += 1

    _prune_empty_dirs(full_root)
    return removed


def _prune_empty_dirs(root: Path) -> None:
    for dirpath in sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda p: -len(p.parts)):
        if not any(dirpath.iterdir()):
            dirpath.rmdir()


def main() -> None:
    notion_secret = require_env("NOTION_SECRET")
    notion = Client(auth=notion_secret)
    site_base_url = load_site_base_url()
    sections = load_sections()

    # Pass 1: fetch every Ready-to-Sync page across all sections first, so
    # the link registry below reflects the full current set before any
    # page's links get rewritten - a page in one section may link to a page
    # in another, or be processed before/after the page it links to.
    all_fetched = []
    for section in sections:
        all_fetched.extend(fetch_section_pages(notion, notion_secret, section))

    registry = {
        entry["page_id"]: {
            "dest_dir": entry["dest"],
            "doc_url": build_doc_url(site_base_url, entry["dest"]),
            "headings": entry["headings"],
        }
        for entry in all_fetched
    }

    # Pass 2: rewrite links against the complete registry and write files.
    dest_dirs_by_section: dict[str, list[Path]] = {}
    for entry in all_fetched:
        render_page(entry, site_base_url, registry)
        dest_dirs_by_section.setdefault(entry["section"]["key"], []).append(entry["dest"])

    for section in sections:
        dest_dirs = dest_dirs_by_section.get(section["key"], [])
        removed = remove_stale_docs(Path(section["root"]), set(dest_dirs))
        print(f"{section['label']}: {len(dest_dirs)} synced, {removed} stale removed.")


if __name__ == "__main__":
    main()
