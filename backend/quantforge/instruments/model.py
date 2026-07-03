from dataclasses import dataclass
from enum import StrEnum


class AssetClass(StrEnum):
    FOREX = "forex"
    INDEX = "index"
    COMMODITY = "commodity"
    CRYPTO = "crypto"


@dataclass(frozen=True, slots=True)
class Instrument:
    symbol: str
    display_name: str
    asset_class: AssetClass = AssetClass.FOREX
    broker_symbol: str | None = None
    pip_location: int | None = None
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class Timeframe:
    code: str
    seconds: int
    is_active: bool = True

