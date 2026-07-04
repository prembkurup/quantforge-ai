from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from quantforge.config.settings import get_settings
from quantforge.market_data.coreui_repository import CoreUiCandleRepository, get_coreui_history_engine


def main() -> None:
    settings = get_settings()
    engine = get_coreui_history_engine()
    with engine.connect() as connection:
        repository = CoreUiCandleRepository(connection, settings.coreui_candle_table)
        latest_time = repository.latest_candle_time("EUR_USD", "M5")
        table = repository._table
        eur_usd_m5_rows = connection.execute(
            select(func.count())
            .select_from(table)
            .where(table.c.pair_name == "EUR_USD", table.c.granularity == "M5")
        ).scalar_one()

        sample_end = latest_time or datetime.now(UTC).replace(tzinfo=None)
        sample_start = sample_end - timedelta(hours=6)
        sample = repository.load_window("EUR_USD", "M5", sample_start, sample_end, limit=10)

    print("coreui candle source ok")
    print(f"table={settings.coreui_candle_table}")
    print(f"EUR_USD_M5_rows={eur_usd_m5_rows}")
    print(f"latest_EUR_USD_M5={latest_time}")
    print(f"sample_rows={len(sample)}")


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
