from pathlib import Path

from notion_sync_lib import rich_text_to_markdown, download_image

HEADING_PREFIX = {"heading_1": "#", "heading_2": "##", "heading_3": "###"}


def _list_children(notion, block_id: str) -> list[dict]:
    blocks = []
    cursor = None
    while True:
        response = notion.blocks.children.list(block_id=block_id, start_cursor=cursor)
        blocks.extend(response["results"])
        if not response.get("has_more"):
            break
        cursor = response["next_cursor"]
    return blocks


def _render_block(notion, block: dict, assets_dir: Path, image_counter: list[int], indent: str) -> list[str]:
    block_type = block["type"]
    data = block.get(block_type, {})
    lines: list[str] = []

    if block_type in HEADING_PREFIX:
        prefix = HEADING_PREFIX[block_type]
        lines.append(f"{indent}{prefix} {rich_text_to_markdown(data.get('rich_text', []))}")
    elif block_type == "paragraph":
        text = rich_text_to_markdown(data.get("rich_text", []))
        if text:
            lines.append(f"{indent}{text}")
    elif block_type == "bulleted_list_item":
        lines.append(f"{indent}- {rich_text_to_markdown(data.get('rich_text', []))}")
    elif block_type == "numbered_list_item":
        lines.append(f"{indent}1. {rich_text_to_markdown(data.get('rich_text', []))}")
    elif block_type == "to_do":
        box = "x" if data.get("checked") else " "
        lines.append(f"{indent}- [{box}] {rich_text_to_markdown(data.get('rich_text', []))}")
    elif block_type == "quote":
        lines.append(f"{indent}> {rich_text_to_markdown(data.get('rich_text', []))}")
    elif block_type == "code":
        lang = data.get("language", "")
        code_text = rich_text_to_markdown(data.get("rich_text", []))
        lines.append(f"{indent}```{lang}")
        lines.append(code_text)
        lines.append(f"{indent}```")
    elif block_type == "divider":
        lines.append(f"{indent}---")
    elif block_type == "callout":
        lines.append(f"{indent}> {rich_text_to_markdown(data.get('rich_text', []))}")
    elif block_type == "image":
        url = data["external"]["url"] if data["type"] == "external" else data["file"]["url"]
        image_counter[0] += 1
        ext = Path(url.split("?")[0]).suffix or ".png"
        filename = f"image-{image_counter[0]}{ext}"
        download_image(url, assets_dir, filename)
        caption = rich_text_to_markdown(data.get("caption", []))
        lines.append(f"{indent}![{caption}](images/{filename})")
    else:
        # Unsupported block type: skip rather than guess at rendering.
        return lines

    if block.get("has_children") and block_type not in ("image",):
        child_indent = indent + ("  " if block_type in ("bulleted_list_item", "numbered_list_item", "to_do") else "")
        for child in _list_children(notion, block["id"]):
            lines.extend(_render_block(notion, child, assets_dir, image_counter, child_indent))

    return lines


def page_to_markdown(notion, page_id: str, assets_dir: Path) -> str:
    image_counter = [0]
    lines: list[str] = []
    for block in _list_children(notion, page_id):
        lines.extend(_render_block(notion, block, assets_dir, image_counter, ""))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
