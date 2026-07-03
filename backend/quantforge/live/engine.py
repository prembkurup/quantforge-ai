from quantforge.execution.oanda import OandaExecutionClient
from quantforge.strategies.plugin import StrategyPlugin


class LiveTradingEngine:
    """Runs approved strategies only and delegates orders to execution adapters."""

    def __init__(self, execution_client: OandaExecutionClient) -> None:
        self._execution = execution_client

    def register_strategy(self, strategy: StrategyPlugin) -> None:
        raise NotImplementedError("Approved strategy loading will be implemented after candidate validation.")

