from sqlalchemy import text

from quantforge.config.settings import get_settings
from quantforge.database.session import get_engine


def main() -> None:
    settings = get_settings()
    engine = get_engine()
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT
                    current_database() AS database_name,
                    current_user AS user_name,
                    version() AS postgres_version
                """
            )
        ).mappings().one()

    print("database connection ok")
    print(f"environment={settings.environment}")
    print(f"database={row['database_name']}")
    print(f"user={row['user_name']}")
    print(f"postgres={row['postgres_version'].split(',')[0]}")


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
