from quantforge.integrations.monday import get_monday_client


def main() -> None:
    client = get_monday_client()
    boards = client.boards()

    print("monday boards")
    for board in boards:
        print(f"{board['id']}\t{board['name']}\t{board['state']}\t{board['board_kind']}")


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
