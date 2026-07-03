from dataclasses import dataclass
from datetime import datetime
from typing import Any

from quantforge.core.types import Granularity
from quantforge.data.repository import CandleRepository
from quantforge.research.experiment import ExperimentDefinition
from quantforge.strategies.plugin import StrategyPlugin


@dataclass(frozen=True, slots=True)
class ResearchRunRequest:
    instrument: str
    granularity: Granularity
    start: datetime
    end: datetime
    experiment_key: str | None = None


class ResearchEngine:
    """Offline engine for strategy discovery and validation."""

    def __init__(self, candle_repository: CandleRepository) -> None:
        self._candles = candle_repository

    def run_experiment_plugin(
        self,
        plugin: StrategyPlugin,
        experiment: ExperimentDefinition,
    ) -> list[dict[str, Any]]:
        request = ResearchRunRequest(
            instrument=experiment.dataset.instrument,
            granularity=experiment.dataset.granularity,
            start=experiment.dataset.start,
            end=experiment.dataset.end,
            experiment_key=experiment.experiment_key,
        )
        results = self.run_plugin(plugin, request)
        for result in results:
            result["experiment_key"] = experiment.experiment_key
            result["dataset_key"] = experiment.dataset.dataset_key
            result["feature_set_key"] = experiment.feature_set.feature_set_key
            result["strategy_template_key"] = experiment.strategy_template_key
        return results

    def run_plugin(self, plugin: StrategyPlugin, request: ResearchRunRequest) -> list[dict[str, Any]]:
        candles = self._candles.load_window(
            request.instrument,
            request.granularity,
            request.start,
            request.end,
        )
        results: list[dict[str, Any]] = []
        for parameters in plugin.parameter_space():
            signal = plugin.generate_signal(candles.copy(), parameters)
            results.append(
                {
                    "plugin_key": plugin.plugin_key,
                    "plugin_version": plugin.version,
                    "parameters": parameters,
                    "signal": signal,
                }
            )
        return results
