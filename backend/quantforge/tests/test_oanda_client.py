from datetime import datetime, timezone
from decimal import Decimal

from quantforge.market_data.oanda import OandaCandleClient


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "candles": [
                {
                    "time": "2024-01-01T00:00:00.000000000Z",
                    "mid": {"o": "1.1000", "h": "1.2000", "l": "1.0000", "c": "1.1500"},
                    "volume": 10,
                    "complete": True,
                }
            ]
        }


def test_oanda_client_parses_midpoint_candles(monkeypatch) -> None:
    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr("requests.get", fake_get)
    client = OandaCandleClient("https://example.test/v3", "token")
    candles = client.fetch_candles(
        "EUR_USD",
        "M5",
        datetime(2024, 1, 1, tzinfo=timezone.utc),
        datetime(2024, 1, 2, tzinfo=timezone.utc),
    )

    assert len(candles) == 1
    assert candles[0].instrument == "EUR_USD"
    assert candles[0].close == Decimal("1.1500")
