import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SIDEBAR_CONFIG_PATH = REPO_ROOT / "sidebar.yaml"

#   - shorthand: ![caption](url)
#   - tag form (used whenever the block has extra attributes, e.g. color -
#     this is what Notion's markdown_version "v2" actually emits for images):
#     <image source="url" ...other attrs.../> or <image source="url" ...>caption</image>
IMAGE_RE = re.compile(
    r'!\[(?P<alt1>[^\]]*)\]\((?P<url1>https?://[^)\s]+)\)'
    r'|<image\s+source="(?P<url2>https?://[^"]+)"[^>]*?(?:/>|>(?P<alt2>.*?)</image>)',
    re.DOTALL,
)

NOTION_API_VERSION = "2026-03-11"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower().strip()).strip("-")
    return slug or "untitled"


def get_title(properties: dict, prop_name: str = "Doc name") -> str:
    prop = properties.get(prop_name) or {}
    return "".join(t["plain_text"] for t in prop.get("title", []))


def get_status(properties: dict, prop_name: str = "Status") -> str | None:
    prop = properties.get(prop_name) or {}
    status = prop.get("status")
    return status["name"] if status else None


def notion_property_name(key: str) -> str:
    """Convert a snake_case config key (e.g. `target_release`) into the Notion
    property display name it's expected to match (`Target Release`)."""
    return key.replace("_", " ").title()


def get_property_value(properties: dict, prop_name: str):
    """Read a Notion property's value regardless of its type, returning a
    plain Python value (or list) suitable for frontmatter. Returns None for
    an empty/missing property or an unsupported type."""
    prop = properties.get(prop_name) or {}
    prop_type = prop.get("type")

    if prop_type == "title":
        return "".join(t["plain_text"] for t in prop.get("title", [])) or None
    if prop_type == "rich_text":
        return "".join(t["plain_text"] for t in prop.get("rich_text", [])) or None
    if prop_type == "select":
        select = prop.get("select")
        return select["name"] if select else None
    if prop_type == "multi_select":
        names = [o["name"] for o in prop.get("multi_select", [])]
        return names or None
    if prop_type == "status":
        status = prop.get("status")
        return status["name"] if status else None
    if prop_type == "people":
        names = [p.get("name") or p.get("id") for p in prop.get("people", [])]
        return ", ".join(names) or None
    if prop_type == "date":
        date = prop.get("date")
        return date["start"] if date else None
    if prop_type == "checkbox":
        return prop.get("checkbox")
    if prop_type == "number":
        return prop.get("number")
    if prop_type in ("url", "email", "phone_number"):
        return prop.get(prop_type)
    return None


def content_hash(body: str) -> str:
    """Fingerprint of a doc's body (frontmatter stripped), recorded in the
    `content_hash` frontmatter field after every successful sync in either
    direction. Comparing against it is how the GitHub -> Notion push-back
    script tells "actually edited since last sync" from "just re-synced"."""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def to_frontmatter(fields: dict) -> str:
    lines = ["---"]
    for key, value in fields.items():
        if value is None or value == "":
            continue
        lines.append(f"{key}: {json.dumps(value)}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def load_config() -> dict:
    return yaml.safe_load(SIDEBAR_CONFIG_PATH.read_text(encoding="utf-8"))


def load_sections() -> list[dict]:
    return load_config()["sections"]


def load_site_base_url() -> str:
    return load_config()["site_base_url"].rstrip("/")


def build_doc_url(site_base_url: str, dest_dir: Path) -> str:
    """VitePress gives `<dir>/README.md` a clean URL at `<dir>/` (README.md
    is treated like index.md for routing purposes)."""
    return f"{site_base_url}/{dest_dir.as_posix()}/"


class _DefaultingDict(dict):
    def __missing__(self, key):
        return "unknown"


def resolve_template(
    templates: dict | None, default_template: str | None, key: str | None, context: dict
) -> str | None:
    """Pick a template by exact `key` match in `templates`, falling back to
    `default_template`, then render it against `context` plus `{value}` = `key`."""
    template = (templates or {}).get(key, default_template)
    if template is None:
        return None
    ctx = _DefaultingDict(context)
    ctx["value"] = key if key is not None else "unknown"
    return template.format_map(ctx)


def download_image(url: str, dest_dir: Path, filename: str) -> Path:
    import requests

    dest_dir.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    dest_path = dest_dir / filename
    dest_path.write_bytes(response.content)
    return dest_path


def fetch_page_markdown(notion_secret: str, page_id: str) -> str:
    """Fetch a page's content via Notion's first-party Markdown Content API
    (GA Feb 2026), replacing manual block-by-block conversion."""
    import requests

    response = requests.get(
        f"https://api.notion.com/v1/pages/{page_id}/markdown",
        headers={
            "Authorization": f"Bearer {notion_secret}",
            "Notion-Version": NOTION_API_VERSION,
        },
        params={"markdown_version": "v2"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("truncated"):
        print(f"Warning: page {page_id} markdown was truncated ({len(data.get('unknown_block_ids', []))} block(s) omitted)")
    return data["markdown"]


def get_page(notion_secret: str, page_id: str) -> dict:
    import requests

    response = requests.get(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers={
            "Authorization": f"Bearer {notion_secret}",
            "Notion-Version": NOTION_API_VERSION,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def push_page_markdown(notion_secret: str, page_id: str, body: str) -> dict:
    """Replace a page's content with `body` via Notion's Markdown Content API
    (same v2 dialect `fetch_page_markdown` reads). Returns the API response,
    which may carry a `warnings` list (e.g. unsupported v2 syntax) even on
    success."""
    import requests

    response = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}/markdown",
        headers={
            "Authorization": f"Bearer {notion_secret}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json",
        },
        json={
            "type": "replace_content",
            "markdown_version": "v2",
            "replace_content": {
                "new_str": body,
            },
        },
        timeout=30,
    )
    if not response.ok:
        print(f"Notion API error {response.status_code}: {response.text}")
    response.raise_for_status()
    return response.json()


def localize_images(markdown: str, assets_dir: Path) -> str:
    counter = [0]

    def replace(match: re.Match) -> str:
        url = match.group("url1") or match.group("url2")
        alt = match.group("alt1") or match.group("alt2") or ""
        counter[0] += 1
        ext = Path(urlsplit(url).path).suffix or ".png"
        filename = f"image-{counter[0]}{ext}"
        download_image(url, assets_dir, filename)
        return f"![{alt}](resources/{filename})"

    return IMAGE_RE.sub(replace, markdown)
