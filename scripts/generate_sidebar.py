# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyyaml>=6.0",
# ]
# ///
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "sidebar.yaml"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_frontmatter(content: str) -> dict:
    match = FRONTMATTER_RE.match(content)
    fields: dict[str, str] = {}
    if not match:
        return fields
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, raw_value = line.partition(":")
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value.startswith('"') and raw_value.endswith('"'):
            raw_value = raw_value[1:-1]
        fields[key] = raw_value
    return fields


def find_readmes(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.rglob("README.md"))


def load_sections() -> list[dict]:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    return config["sections"]


def group_label(section: dict, fm: dict) -> str:
    group_by = section["group_by"]
    value = fm.get(group_by)
    templates = section.get("group_label_templates") or {}
    template = templates.get(value, section.get("default_group_label_template", "{value}"))
    return template.format(value=value, **fm)


def build_section(section: dict) -> list[str]:
    files = find_readmes(REPO_ROOT / section["root"])
    groups: dict[str, list[tuple[str, Path]]] = {}
    for file in files:
        fm = parse_frontmatter(file.read_text(encoding="utf-8"))
        label = group_label(section, fm)
        title = fm.get("title", file.parent.name)
        groups.setdefault(label, []).append((title, file.relative_to(REPO_ROOT)))

    if not groups:
        return []

    lines = [f"- {section['label']}"]
    for label in sorted(groups):
        lines.append(f"  - {label}")
        for title, rel_path in sorted(groups[label]):
            lines.append(f"    - [{title}]({rel_path.as_posix()})")
    return lines


def main() -> None:
    lines = ["- [Home](/)"]
    for section in load_sections():
        lines.extend(build_section(section))
    (REPO_ROOT / "_sidebar.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote _sidebar.md with {len(lines)} lines.")


if __name__ == "__main__":
    main()
