import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SIDEBAR_CONFIG_PATH = REPO_ROOT / "sidebar.yaml"

IMAGE_RE = re.compile(r"!\[([^\]]*)\]\((https?://[^)\s]+)\)")

NOTION_API_VERSION = "2026-03-11"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower().strip()).strip("-")
    return slug or "untitled"


def get_title(properties: dict, prop_name: str = "Doc name") -> str:
    prop = properties.get(prop_name) or {}
    return "".join(t["plain_text"] for t in prop.get("title", []))


def get_select(properties: dict, prop_name: str) -> str | None:
    prop = properties.get(prop_name) or {}
    select = prop.get("select")
    return select["name"] if select else None


def get_status(properties: dict, prop_name: str = "Status") -> str | None:
    prop = properties.get(prop_name) or {}
    status = prop.get("status")
    return status["name"] if status else None


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


def build_docsify_url(site_base_url: str, dest_dir: Path) -> str:
    return f"{site_base_url}/#/{(dest_dir / 'README').as_posix()}"


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


def localize_images(markdown: str, assets_dir: Path) -> str:
    counter = [0]

    def replace(match: re.Match) -> str:
        alt, url = match.group(1), match.group(2)
        counter[0] += 1
        ext = Path(urlsplit(url).path).suffix or ".png"
        filename = f"image-{counter[0]}{ext}"
        download_image(url, assets_dir, filename)
        return f"![{alt}](images/{filename})"

    return IMAGE_RE.sub(replace, markdown)
