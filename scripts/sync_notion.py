# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "notion-client>=3.1.0,<4",
#   "requests>=2.31.0",
# ]
# ///
import os
import sys
from pathlib import Path

from notion_client import Client

from notion_blocks_to_md import page_to_markdown
from notion_sync_lib import get_select, get_status, get_title, slugify, to_frontmatter

REPO_ROOT = Path(__file__).resolve().parent.parent


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


def adr_dest_dir(properties: dict) -> Path:
    slug = slugify(get_title(properties))
    scope = get_select(properties, "Scope")
    if scope == "Global":
        return Path("ADR") / "global" / slug
    if scope == "Area":
        return Path("ADR") / slugify(get_select(properties, "Area") or "unknown-area") / slug
    if scope == "Component":
        return Path("ADR") / slugify(get_select(properties, "Component") or "unknown-component") / slug
    raise ValueError(f"ADR page '{get_title(properties)}' has unrecognized Scope: {scope}")


def design_doc_dest_dir(properties: dict) -> Path:
    slug = slugify(get_title(properties))
    area = get_select(properties, "Area") or "unknown-area"
    return Path("design-docs") / slugify(area) / slug


def render_page(notion: Client, page: dict, dest_dir: Path, extra_frontmatter: dict) -> None:
    title = get_title(page["properties"])
    full_dest_dir = REPO_ROOT / dest_dir
    full_dest_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = full_dest_dir / "images"

    body = page_to_markdown(notion, page["id"], assets_dir)

    frontmatter = to_frontmatter(
        {
            "id": page["id"],
            "title": title,
            "status": get_status(page["properties"]),
            "created_time": page["created_time"],
            "last_edited_time": page["last_edited_time"],
            "notion_url": page["url"],
            **extra_frontmatter,
        }
    )

    (full_dest_dir / "README.md").write_text(frontmatter + body, encoding="utf-8")
    print(f'Synced "{title}" -> {dest_dir}/README.md')


def sync_adr(notion: Client, data_source_id: str) -> int:
    pages = query_ready_to_sync(notion, data_source_id)
    for page in pages:
        dest_dir = adr_dest_dir(page["properties"])
        render_page(
            notion,
            page,
            dest_dir,
            {
                "type": "ADR",
                "scope": get_select(page["properties"], "Scope"),
                "area": get_select(page["properties"], "Area"),
                "component": get_select(page["properties"], "Component"),
            },
        )
    return len(pages)


def sync_design_docs(notion: Client, data_source_id: str) -> int:
    pages = query_ready_to_sync(notion, data_source_id)
    for page in pages:
        dest_dir = design_doc_dest_dir(page["properties"])
        render_page(
            notion,
            page,
            dest_dir,
            {
                "type": "Design Doc",
                "area": get_select(page["properties"], "Area"),
            },
        )
    return len(pages)


def main() -> None:
    notion_secret = require_env("NOTION_SECRET")
    adr_data_source_id = require_env("ADR_DATA_SOURCE_ID")
    design_doc_data_source_id = require_env("DESIGN_DOC_DATA_SOURCE_ID")

    notion = Client(auth=notion_secret)

    adr_count = sync_adr(notion, adr_data_source_id)
    design_doc_count = sync_design_docs(notion, design_doc_data_source_id)
    print(f"Done. {adr_count} ADR page(s), {design_doc_count} Design Doc page(s).")


if __name__ == "__main__":
    main()
