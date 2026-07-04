from quantforge.integrations.monday import get_monday_client


def main() -> None:
    client = get_monday_client()
    account = client.me()

    print("monday connection ok")
    print(f"user_id={account['id']}")
    print(f"name={account['name']}")
    print(f"email={account.get('email') or ''}")


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
