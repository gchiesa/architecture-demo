# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

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


def build_adr_section() -> list[str]:
    files = find_readmes(REPO_ROOT / "ADR")
    groups: dict[str, list[tuple[str, Path]]] = {}
    for file in files:
        fm = parse_frontmatter(file.read_text(encoding="utf-8"))
        scope = fm.get("scope")
        if scope == "Global":
            label = "Global"
        elif scope == "Area":
            label = f"Area: {fm.get('area', 'unknown')}"
        elif scope == "Component":
            label = f"Component: {fm.get('component', 'unknown')}"
        else:
            label = "Other"
        title = fm.get("title", file.parent.name)
        groups.setdefault(label, []).append((title, file.relative_to(REPO_ROOT)))

    if not groups:
        return []

    lines = ["- ADR"]
    for label in sorted(groups):
        lines.append(f"  - {label}")
        for title, rel_path in sorted(groups[label]):
            lines.append(f"    - [{title}]({rel_path.as_posix()})")
    return lines


def build_design_doc_section() -> list[str]:
    files = find_readmes(REPO_ROOT / "design-docs")
    groups: dict[str, list[tuple[str, Path]]] = {}
    for file in files:
        fm = parse_frontmatter(file.read_text(encoding="utf-8"))
        label = f"Area: {fm.get('area', 'unknown')}"
        title = fm.get("title", file.parent.name)
        groups.setdefault(label, []).append((title, file.relative_to(REPO_ROOT)))

    if not groups:
        return []

    lines = ["- Design Docs"]
    for label in sorted(groups):
        lines.append(f"  - {label}")
        for title, rel_path in sorted(groups[label]):
            lines.append(f"    - [{title}]({rel_path.as_posix()})")
    return lines


def main() -> None:
    lines = ["- [Home](/)"]
    lines.extend(build_adr_section())
    lines.extend(build_design_doc_section())
    (REPO_ROOT / "_sidebar.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote _sidebar.md with {len(lines)} lines.")


if __name__ == "__main__":
    main()
