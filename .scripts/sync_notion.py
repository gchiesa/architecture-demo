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
    fetch_page_markdown,
    get_property_value,
    get_status,
    get_title,
    load_sections,
    load_site_base_url,
    localize_images,
    notion_property_name,
    resolve_template,
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


def render_page(
    notion_secret: str, page: dict, dest: Path, extra_frontmatter: dict, site_base_url: str
) -> None:
    title = get_title(page["properties"])
    full_dest_dir = REPO_ROOT / dest
    full_dest_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = full_dest_dir / "resources"

    markdown = fetch_page_markdown(notion_secret, page["id"])
    body = localize_images(markdown, assets_dir)

    frontmatter = to_frontmatter(
        {
            "id": page["id"],
            "title": title,
            "status": get_status(page["properties"]),
            "created_time": page["created_time"],
            "last_edited_time": page["last_edited_time"],
            "notion_url": page["url"],
            "doc_url": build_doc_url(site_base_url, dest),
            "content_hash": content_hash(body),
            **extra_frontmatter,
        }
    )

    (full_dest_dir / "README.md").write_text(frontmatter + body, encoding="utf-8")
    print(f'Synced "{title}" -> {dest}/README.md')


def sync_section(notion: Client, notion_secret: str, section: dict, site_base_url: str) -> list[Path]:
    data_source_id = require_env(section["notion_data_source_env"])
    pages = query_ready_to_sync(notion, data_source_id)
    dest_dirs = []
    for page in pages:
        context = build_context(section, page["properties"])
        dest = dest_dir(section, page["properties"], context)
        render_page(notion_secret, page, dest, {"type": section["type"], **context}, site_base_url)
        dest_dirs.append(dest)
    return dest_dirs


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

    for section in load_sections():
        dest_dirs = sync_section(notion, notion_secret, section, site_base_url)
        removed = remove_stale_docs(Path(section["root"]), set(dest_dirs))
        print(f"{section['label']}: {len(dest_dirs)} synced, {removed} stale removed.")


if __name__ == "__main__":
    main()
