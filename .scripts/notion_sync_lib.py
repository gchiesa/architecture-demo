import hashlib
import json
import os
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

# Notion's Markdown Content API renders an internal link to another page (or
# to a block within a page) as a page-relative path - confirmed empirically
# via a live round-trip, e.g. `/p/40096cd65ae081839f16d9f6e5f55c6a?pvs=25` or
# `/p/<page-id>?v=...&pvs=25#<block-id>` for a link into a specific section.
# No host, no scheme - a host prefix is tolerated below in case some other
# Notion surface ever emits one, but the bare form is what actually occurs.
NOTION_INTERNAL_LINK_RE = re.compile(
    r"\[(?P<text>[^\]]*)\]\("
    r"(?:https?://(?:www\.notion\.so|app\.notion\.com))?"
    r"/p/(?P<page_id>[0-9a-f]{32})"
    r"(?:\?[^)\s#]*)?"
    r"(?:#(?P<block_id>[0-9a-f]{32}))?"
    r"\)"
)

# An ordinary markdown link (not an image - `(?<!!)` excludes `![...](...)`),
# used by the GitHub -> Notion push-back direction to find links authored in
# the repo (relative paths to another doc, or `#anchor` fragments) that need
# converting back into Notion's own link form before being pushed.
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[(?P<text>[^\]]*)\]\((?P<href>[^)\s]+)\)")

HEADING_BLOCK_TYPES = {"heading_1", "heading_2", "heading_3"}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


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


def parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    match = FRONTMATTER_RE.match(raw)
    if not match:
        return {}, raw
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, raw_value = line.partition(":")
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value.startswith('"') and raw_value.endswith('"'):
            raw_value = raw_value[1:-1]
        fields[key] = raw_value
    return fields, match.group(2)


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


def slugify_heading(text: str) -> str:
    """Approximates VitePress's heading anchor slug (markdown-it-anchor's
    default: lowercase, strip punctuation, spaces to hyphens). Dedup across
    a page's headings is handled by the caller (`fetch_page_headings`), not
    here, since it needs the full page's heading order."""
    slug = re.sub(r"<[^>]+>", "", text).strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return slug or "section"


def notion_page_url(page_id: str, block_id: str | None = None) -> str:
    """Absolute fallback link for a Notion page/block with no resolvable
    repo-local mirror - always a working Notion deep link. Deliberately NOT
    the bare `/p/...` path Notion's own API emits: that form has no host, so
    left as-is it would be broken the moment it's viewed outside Notion's
    app (on GitHub's file render or the built site)."""
    url = f"https://app.notion.com/p/{page_id}"
    return f"{url}#{block_id}" if block_id else url


def notion_internal_link(page_id: str, block_id: str | None = None) -> str:
    """The relative `/p/<id>[#<block>]` link form Notion's Markdown Content
    API itself emits (confirmed via a live round-trip) - used when pushing a
    link back into Notion, which is the form it already understands."""
    href = f"/p/{page_id}"
    return f"{href}#{block_id}" if block_id else href


def fetch_page_headings(notion_secret: str, page_id: str) -> dict[str, str]:
    """Walks a page's block tree and returns {heading_block_id: anchor_slug}.
    The flat Markdown Content API has no block ids in its output, so a
    link's `#<block_id>` fragment can only be resolved to a heading's text
    (and from there, its anchor slug) via the separate Blocks API."""
    import requests

    headings: list[tuple[str, str]] = []

    def walk(block_id: str, cursor: str | None = None) -> None:
        response = requests.get(
            f"https://api.notion.com/v1/blocks/{block_id}/children",
            headers={
                "Authorization": f"Bearer {notion_secret}",
                "Notion-Version": NOTION_API_VERSION,
            },
            params={"start_cursor": cursor} if cursor else {},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        for block in data["results"]:
            block_type = block["type"]
            if block_type in HEADING_BLOCK_TYPES:
                text = _rich_text_plain(block[block_type].get("rich_text", []))
                headings.append((block["id"].replace("-", ""), text))
            if block.get("has_children"):
                walk(block["id"])
        if data.get("has_more"):
            walk(block_id, data["next_cursor"])

    walk(page_id)

    slugs: dict[str, str] = {}
    seen: dict[str, int] = {}
    for block_id, text in headings:
        base = slugify_heading(text)
        count = seen.get(base, 0)
        seen[base] = count + 1
        slugs[block_id] = base if count == 0 else f"{base}-{count}"
    return slugs


def _rich_text_plain(rich_text: list[dict]) -> str:
    return "".join(t.get("plain_text", "") for t in rich_text)


def build_dest_relative_link(current_dir: Path, target_dir: Path, anchor: str | None) -> str:
    """A directory-relative link, deliberately not `.../README.md`: VitePress's
    `rewrites` config (`README.md` -> `index.md`) only changes where the
    source file itself builds to, not how its markdown link transform
    rewrites a literal `README.md` href - that just becomes `README.html`,
    which is never a real output file. A trailing-slash directory link
    resolves correctly post-build, and still lands on the right folder in
    GitHub's own file browser (one extra click to open the README there,
    not a broken link)."""
    rel = Path(os.path.relpath(target_dir, start=current_dir))
    href = "./" if rel == Path(".") else f"{rel.as_posix()}/"
    return f"{href}#{anchor}" if anchor else href


def rewrite_notion_links_to_repo(
    markdown: str,
    current_page_id: str,
    current_dest_dir: Path,
    current_doc_url: str,
    registry: dict[str, dict],
) -> str:
    """Rewrites Notion's internal `/p/<id>[#<block>]` links into relative
    repo links wherever the target is also synced this run, falling back to
    an absolute Notion URL for anything it can't resolve (unsynced/deleted
    target page, or a link to a non-heading block) - see the link-sync plan
    for the full rationale. `registry` maps a (dashless) Notion page id to
    `{dest_dir, doc_url, headings}` for every page synced this run."""

    def replace(match: re.Match) -> str:
        text = match.group("text")
        page_id = match.group("page_id")
        block_id = match.group("block_id")

        entry = registry.get(page_id)
        if entry is None:
            return f"[{text}]({notion_page_url(page_id, block_id)})"

        anchor = None
        if block_id:
            anchor = entry["headings"].get(block_id)
            if anchor is None:
                print(
                    f"Warning: link to {page_id}#{block_id} has no matching heading "
                    "in the synced doc, linking to the page instead"
                )

        if page_id == current_page_id:
            href = f"#{anchor}" if anchor else current_doc_url
        else:
            href = build_dest_relative_link(current_dest_dir, entry["dest_dir"], anchor)
        return f"[{text}]({href})"

    return NOTION_INTERNAL_LINK_RE.sub(replace, markdown)


def scan_local_doc_registry(roots: list[str]) -> dict[str, str]:
    """Maps each synced doc's repo-relative directory (posix str) to its
    Notion page id (dashless), read straight off frontmatter on disk - no
    Notion API calls needed, since every synced doc already carries its own
    `id`. Used by the GitHub -> Notion push-back direction to resolve a
    relative link in the repo to the Notion page it should point at."""
    registry: dict[str, str] = {}
    for root in roots:
        root_path = REPO_ROOT / root
        if not root_path.exists():
            continue
        for readme in root_path.rglob("README.md"):
            fields, _ = parse_frontmatter(readme.read_text(encoding="utf-8"))
            page_id = fields.get("id")
            if not page_id:
                continue
            rel_dir = readme.parent.relative_to(REPO_ROOT).as_posix()
            registry[rel_dir] = page_id.replace("-", "")
    return registry


def resolve_repo_link_target(
    href: str, current_dir: Path, local_registry: dict[str, str]
) -> tuple[str | None, str | None, bool]:
    """Classifies a markdown link's href found in a repo doc for the push-back
    direction. Returns `(target_page_id, anchor, recognized)`:
    - `recognized=False` means this isn't a doc link in scope for this
      feature (external URL, already a Notion-native `/p/...` link, or a
      relative path to something other than another doc's directory) - the
      caller must leave it untouched.
    - `recognized=True` with `target_page_id=None` means a bare `#anchor`
      (same-page link) - the caller resolves it against the current page.
    - `recognized=True` with `target_page_id=None` and `anchor=None` *and*
      the href was a non-empty, resolvable doc-directory path not in the
      registry means the target doc isn't currently synced - handled by the
      caller as "unresolved internal".

    Accepts both link forms a doc's body might contain: the directory-relative
    form `sync_notion.py` itself writes (e.g. `../other-doc/`, see
    `build_dest_relative_link`), and an explicit `.../README.md` path, in
    case a person hand-writes one.
    """
    path_part, _, fragment = href.partition("#")
    anchor = fragment or None

    if path_part == "":
        return None, anchor, True  # pure `#anchor`

    if path_part.startswith(("http://", "https://", "/p/")):
        return None, None, False  # external, or already Notion-native

    target_path = (current_dir / path_part).resolve()
    if target_path.name == "README.md":
        candidate_dir = target_path.parent
    elif target_path.is_dir() and (target_path / "README.md").exists():
        candidate_dir = target_path
    else:
        return None, None, False
    try:
        rel_dir = candidate_dir.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return None, None, False

    page_id = local_registry.get(rel_dir)
    if page_id is None:
        return "unresolved", anchor, True
    return page_id, anchor, True


def rewrite_repo_links_to_notion(
    markdown: str,
    current_page_id: str,
    current_dir: Path,
    local_registry: dict[str, str],
    notion_secret: str,
) -> str:
    """Rewrites repo-relative doc links and `#anchor` fragments back into
    Notion's own `/p/<id>[#<block>]` link form before a push, the mirror of
    `rewrite_notion_links_to_repo`. `current_page_id` and registry values are
    dashless Notion page ids."""
    heading_cache: dict[str, dict[str, str]] = {}

    def slug_to_block_id(page_id: str, slug: str) -> str | None:
        if page_id not in heading_cache:
            heading_cache[page_id] = fetch_page_headings(notion_secret, page_id)
        for block_id, s in heading_cache[page_id].items():
            if s == slug:
                return block_id
        return None

    def replace(match: re.Match) -> str:
        text, href = match.group("text"), match.group("href")
        target_id, anchor, recognized = resolve_repo_link_target(href, current_dir, local_registry)
        if not recognized:
            return match.group(0)

        if target_id == "unresolved":
            print(f"Warning: link '{href}' points at a doc that isn't currently synced, leaving it unchanged")
            return match.group(0)

        page_id = target_id or current_page_id
        block_id = None
        if anchor:
            block_id = slug_to_block_id(page_id, anchor)
            if block_id is None:
                print(f"Warning: no Notion heading matches anchor #{anchor} on page {page_id}, linking to the page instead")
        return f"[{text}]({notion_internal_link(page_id, block_id)})"

    return MARKDOWN_LINK_RE.sub(replace, markdown)


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
