from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import requests


@dataclass(frozen=True, slots=True)
class OandaCandle:
    instrument: str
    granularity: str
    time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    complete: bool


class OandaCandleClient:
    """Small OANDA candles API client for historical OHLCV ingestion."""

    def __init__(self, api_url: str, api_token: str | None) -> None:
        self._api_url = api_url.rstrip("/")
        self._api_token = api_token

    def fetch_candles(
        self,
        instrument: str,
        granularity: str,
        start: datetime,
        end: datetime,
        price: str = "M",
    ) -> list[OandaCandle]:
        headers = {}
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"

        params = {
            "from": _format_oanda_time(start),
            "to": _format_oanda_time(end),
            "granularity": granularity,
            "price": price,
        }
        response = requests.get(
            f"{self._api_url}/instruments/{instrument}/candles",
            headers=headers,
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        return [_parse_candle(instrument, granularity, item) for item in payload.get("candles", [])]


def _format_oanda_time(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_candle(instrument: str, granularity: str, item: dict[str, Any]) -> OandaCandle:
    midpoint = item["mid"]
    return OandaCandle(
        instrument=instrument,
        granularity=granularity,
        time=datetime.fromisoformat(item["time"].replace("Z", "+00:00")),
        open=Decimal(midpoint["o"]),
        high=Decimal(midpoint["h"]),
        low=Decimal(midpoint["l"]),
        close=Decimal(midpoint["c"]),
        volume=Decimal(str(item.get("volume", 0))),
        complete=bool(item.get("complete", False)),
    )
