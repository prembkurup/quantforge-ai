from pathlib import Path

from quantforge.config.settings import get_settings
from quantforge.integrations.monday import get_monday_client


DEFAULT_TASKS_BOARD_ID = "5029670566"
ROADMAP_GROUP_NAME = "QuantForge AI Roadmap"
PLAN_PATH = Path("docs/monday-plan.md")


def load_initial_items(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    in_initial_items = False
    items: list[str] = []

    for line in lines:
        if line.strip() == "## Initial Items":
            in_initial_items = True
            continue
        if in_initial_items and line.startswith("## "):
            break
        if in_initial_items and line.startswith("- "):
            items.append(line[2:].strip().rstrip("."))

    if not items:
        raise RuntimeError(f"No roadmap items found in {path}.")
    return items


def ensure_group(board_id: str, group_name: str) -> dict[str, str]:
    client = get_monday_client()
    board = client.board(board_id)
    for group in board["groups"]:
        if group["title"].strip().casefold() == group_name.casefold():
            return group
    return client.create_group(board_id, group_name)


def main() -> None:
    settings = get_settings()
    board_id = settings.monday_board_id or DEFAULT_TASKS_BOARD_ID
    client = get_monday_client()
    group = ensure_group(board_id, ROADMAP_GROUP_NAME)
    group_id = group["id"]
    roadmap_items = load_initial_items(PLAN_PATH)

    existing_names = {
        item["name"].strip().casefold()
        for item in client.board_items(board_id)
        if item["group"]["id"] == group_id
    }

    created: list[dict[str, str]] = []
    skipped: list[str] = []
    for item_name in roadmap_items:
        if item_name.casefold() in existing_names:
            skipped.append(item_name)
            continue
        created.append(client.create_item(board_id, group_id, item_name))

    print(f"board_id={board_id}")
    print(f"group={group['title']} ({group_id})")
    print(f"created={len(created)}")
    print(f"skipped={len(skipped)}")
    for item in created:
        print(f"created_item={item['id']} {item['name']}")


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
