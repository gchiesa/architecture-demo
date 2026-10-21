import json
import re
from pathlib import Path


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


def rich_text_to_markdown(rich_text: list[dict]) -> str:
    parts = []
    for t in rich_text:
        text = t.get("plain_text", "")
        annotations = t.get("annotations", {})
        href = t.get("href")
        if annotations.get("code"):
            text = f"`{text}`"
        if annotations.get("bold"):
            text = f"**{text}**"
        if annotations.get("italic"):
            text = f"*{text}*"
        if annotations.get("strikethrough"):
            text = f"~~{text}~~"
        if href:
            text = f"[{text}]({href})"
        parts.append(text)
    return "".join(parts)


def download_image(url: str, dest_dir: Path, filename: str) -> Path:
    import requests

    dest_dir.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    dest_path = dest_dir / filename
    dest_path.write_bytes(response.content)
    return dest_path
