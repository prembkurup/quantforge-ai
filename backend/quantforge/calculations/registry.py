from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class CalculationCategory(StrEnum):
    INDICATOR = "indicator"
    STATISTICAL = "statistical"
    PRICE_ACTION = "price_action"
    PATTERN = "pattern"
    MARKET_STRUCTURE = "market_structure"
    VOLATILITY = "volatility"
    SESSION = "session"
    LIQUIDITY = "liquidity"
    CUSTOM_PLUGIN = "custom_plugin"


@dataclass(frozen=True, slots=True)
class CalculationSpec:
    key: str
    category: CalculationCategory
    function: Callable[..., Any]
    description: str = ""
    default_parameters: dict[str, Any] = field(default_factory=dict)
