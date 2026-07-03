from datetime import datetime, timezone

from quantforge.config.settings import get_settings
from quantforge.database.session import get_engine
from quantforge.market_data.oanda import OandaCandleClient
from quantforge.market_data.repository import PostgresCandleRepository


def main() -> None:
    settings = get_settings()
    client = OandaCandleClient(settings.oanda_api_url, settings.oanda_api_token)

    instrument = "EUR_USD"
    granularity = "M5"
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 2, tzinfo=timezone.utc)

    candles = client.fetch_candles(instrument, granularity, start, end)
    engine = get_engine()
    with engine.begin() as connection:
        repository = PostgresCandleRepository(connection)
        saved = repository.upsert_candles(candles)

    print(f"saved={saved} instrument={instrument} granularity={granularity}")


if __name__ == "__main__":
    main()
