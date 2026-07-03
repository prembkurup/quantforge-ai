from typing import Any, Protocol

import pandas as pd

from quantforge.domain import PluginCategory


class ComponentPlugin(Protocol):
    plugin_key: str
    name: str
    version: str
    category: PluginCategory

    def parameter_space(self) -> list[dict[str, Any]]:
        """Return component parameters to explore."""


class MarketRegimePlugin(ComponentPlugin, Protocol):
    category: PluginCategory

    def classify(self, features: pd.DataFrame, parameters: dict[str, Any]) -> str:
        """Return the current market regime."""


class EntryModelPlugin(ComponentPlugin, Protocol):
    def entry_signal(self, features: pd.DataFrame, parameters: dict[str, Any]) -> dict[str, Any]:
        """Return an entry signal payload."""


class ConfirmationPlugin(ComponentPlugin, Protocol):
    def confirm(self, features: pd.DataFrame, signal: dict[str, Any], parameters: dict[str, Any]) -> bool:
        """Confirm or reject an entry signal."""


class ExitModelPlugin(ComponentPlugin, Protocol):
    def exit_signal(self, features: pd.DataFrame, position: dict[str, Any], parameters: dict[str, Any]) -> dict[str, Any]:
        """Return exit instructions for an open position."""


class RiskModelPlugin(ComponentPlugin, Protocol):
    def risk_check(self, signal: dict[str, Any], account_state: dict[str, Any], parameters: dict[str, Any]) -> bool:
        """Approve or block a signal before execution."""


class PositionSizingPlugin(ComponentPlugin, Protocol):
    def size_position(self, signal: dict[str, Any], account_state: dict[str, Any], parameters: dict[str, Any]) -> float:
        """Calculate order units for an approved signal."""

