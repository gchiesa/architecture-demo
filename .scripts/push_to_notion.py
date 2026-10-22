# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests>=2.31.0",
#   "pyyaml>=6.0",
# ]
# ///
"""Push a synced doc's body back to its Notion page.

Runs on every push to main that touches a synced README.md (see
.github/workflows/push_to_notion.yml). This is the GitHub -> Notion half of
the sync; .scripts/sync_notion.py is the Notion -> GitHub half. Scope for
now: body only - frontmatter/properties stay Notion-authoritative, and docs
with local images are skipped (no safe way to hand Notion a URL it can
fetch that also works for a private repo), surfaced as a GitHub Actions
warning annotation rather than just a log line.
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from notion_sync_lib import REPO_ROOT, content_hash, get_page, push_page_markdown

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def parse_file(raw: str) -> tuple[dict, str]:
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


def set_frontmatter_field(raw: str, key: str, value: str) -> str:
    line_re = re.compile(rf"^{re.escape(key)}:.*$", re.MULTILINE)
    line = f'{key}: "{value}"'
    if line_re.search(raw):
        return line_re.sub(line, raw, count=1)
    return re.sub(r"\n---\n", f"\n{line}\n---\n", raw, count=1)


def warn(path: Path, message: str) -> None:
    """Emit a GitHub Actions warning annotation (shows up on the run summary
    and the diff, not just buried in the step log), falling back to a plain
    print outside of Actions."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::warning file={path}::{message}")
    else:
        print(f"WARNING {path}: {message}")


def process_file(path: Path, notion_secret: str) -> None:
    raw = path.read_text(encoding="utf-8")
    fields, body = parse_file(raw)

    page_id = fields.get("id")
    if not page_id:
        print(f"Skip {path}: no Notion page id in frontmatter")
        return

    if "resources/" in body:
        warn(path, "contains local image(s) - push-back of images to Notion isn't supported, skipping body sync")
        return

    new_hash = content_hash(body)
    if new_hash == fields.get("content_hash"):
        print(f"Skip {path}: body unchanged since last sync")
        return

    page = get_page(notion_secret, page_id)
    if page["last_edited_time"] != fields.get("last_edited_time"):
        warn(
            path,
            f"Notion page was edited ({page['last_edited_time']}) since the last pull "
            f"({fields.get('last_edited_time')}) - skipping to avoid overwriting it, resolve manually",
        )
        return

    result = push_page_markdown(notion_secret, page_id, body)
    for notion_warning in result.get("warnings", []):
        warn(path, f"Notion API warning: {notion_warning}")

    updated_page = get_page(notion_secret, page_id)
    raw = set_frontmatter_field(raw, "content_hash", new_hash)
    raw = set_frontmatter_field(raw, "last_edited_time", updated_page["last_edited_time"])
    path.write_text(raw, encoding="utf-8")
    print(f"Pushed {path} -> Notion page {page_id}")


def main() -> None:
    notion_secret = os.environ["NOTION_SECRET"]
    changed_files = sys.argv[1:]
    if not changed_files:
        print("No changed files passed, nothing to push")
        return

    for rel_path in changed_files:
        path = REPO_ROOT / rel_path
        if path.name != "README.md" or not path.exists():
            continue
        process_file(path, notion_secret)


if __name__ == "__main__":
    main()
