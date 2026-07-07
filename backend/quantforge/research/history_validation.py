from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

from quantforge.research.strategy_assets import ApprovedStrategyAsset, StrategyAssetRepository


class HistoricalValidationStatus(StrEnum):
    QUEUED = "Queued"
    WAITING = "Waiting"
    LOADING_DATA = "Loading Data"
    RUNNING = "Running"
    CALCULATING_METRICS = "Calculating Metrics"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    NEEDS_RESEARCH = "Needs Research"


class HistoricalValidationState(StrEnum):
    DISABLED = "DISABLED"
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"


DEFAULT_PAIR_SPREAD_PIPS: dict[str, float] = {
    "AUD_CAD": 1.8,
    "AUD_CHF": 1.9,
    "AUD_JPY": 1.6,
    "AUD_NZD": 2.1,
    "AUD_USD": 1.0,
    "CAD_CHF": 1.9,
    "CAD_JPY": 1.6,
    "CHF_JPY": 2.2,
    "EUR_AUD": 1.6,
    "EUR_CAD": 1.7,
    "EUR_CHF": 1.5,
    "EUR_GBP": 1.0,
    "EUR_JPY": 1.1,
    "EUR_NZD": 2.5,
    "EUR_USD": 0.8,
    "GBP_AUD": 2.2,
    "GBP_CAD": 2.4,
    "GBP_CHF": 2.3,
    "GBP_JPY": 2.0,
    "GBP_NZD": 3.0,
    "GBP_USD": 1.1,
    "NAS100_USD": 2.0,
    "NZD_CAD": 2.4,
    "NZD_CHF": 2.4,
    "NZD_JPY": 1.9,
    "NZD_USD": 1.2,
    "SPX500_USD": 0.5,
    "USD_CAD": 1.2,
    "USD_CHF": 1.2,
    "USD_JPY": 0.9,
}


@dataclass(frozen=True, slots=True)
class HistoricalValidationConfig:
    enabled: bool = True
    max_concurrent: int = 6
    batch_size: int = 6
    years: int = 10
    starting_balance: float = 100_000.0
    spread_pips: float = 1.2
    slippage_pips: float = 0.2
    pip_value: float = 10.0
    pair_spreads: dict[str, float] = field(default_factory=dict)
    min_profit_factor: float = 1.35
    max_drawdown: float = 0.20
    min_win_rate: float = 0.45
    min_trades: int = 100


@dataclass(frozen=True, slots=True)
class HistoricalValidationPaths:
    queue_file: Path
    status_file: Path
    results_file: Path
    improvements_file: Path


@dataclass(frozen=True, slots=True)
class HistoricalValidationQueueItem:
    validation_id: str
    strategy_asset_id: str
    research_program_id: str
    pair: str
    timeframe: str
    dataset_id: str
    priority: float
    status: HistoricalValidationStatus
    queued_at: str
    started_at: str = ""
    completed_at: str = ""
    retry_count: int = 0
    estimated_start_time: str = ""


@dataclass(frozen=True, slots=True)
class HistoricalValidationResult:
    validation_id: str
    strategy_asset_id: str
    research_program_id: str
    pair: str
    timeframe: str
    historical_period: str
    trades: int
    gross_profit: float
    execution_cost: float
    execution_cost_per_trade: float
    spread_pips: float
    slippage_pips: float
    net_profit: float
    profit_factor: float
    win_rate: float
    expectancy: float
    max_drawdown: float
    sharpe_ratio: float
    recovery_factor: float
    average_trade: float
    exposure: float
    result: str
    validation_timestamp: str
    strategy_family: str
    regime: str


@dataclass(frozen=True, slots=True)
class HistoricalValidationImprovement:
    improvement_id: str
    validation_id: str
    strategy_asset_id: str
    research_program_id: str
    pair: str
    timeframe: str
    reason_code: str
    message: str
    created_at: str
    status: str = "REQUESTED"


class HistoricalValidationEngine:
    def __init__(
        self,
        *,
        asset_repository: StrategyAssetRepository,
        paths: HistoricalValidationPaths,
        config: HistoricalValidationConfig | None = None,
    ) -> None:
        self.asset_repository = asset_repository
        self.paths = paths
        self.config = config or HistoricalValidationConfig()

    def status(self) -> dict[str, Any]:
        self.ensure_queue()
        queue = self.queue()
        results = self.results()
        running = [item for item in queue if item["status"] in {"Loading Data", "Running", "Calculating Metrics"}]
        queued = [item for item in queue if item["status"] in {"Queued", "Waiting"}]
        failed = [item for item in results if item["result"] == "FAIL"]
        passed = [item for item in results if item["result"] == "PASS"]
        current = running[0] if running else queued[0] if queued else None
        next_item = queued[1] if len(queued) > 1 else None
        total = len(queue)
        completed = len(results)
        status = {
            "enabled": self.config.enabled,
            "state": self._state(queue, running),
            "balance_sheet": self.balance_sheet(results),
            "current_pair": current["pair"] if current else "",
            "current_timeframe": current["timeframe"] if current else "",
            "current_batch": current,
            "progress": {"completed": completed, "total": total},
            "overall_completion_pct": round((completed / total) * 100, 2) if total else 0.0,
            "estimated_remaining_minutes": max(0, len(queued)) * 4,
            "next": next_item,
            "running_validations": len(running),
            "queued_validations": len(queued),
            "completed_validations": completed,
            "passed_validations": len(passed),
            "failed_validations": len(failed),
            "improvement_requests": len(self.improvements()),
            "average_validation_duration_seconds": self._average_duration_seconds(queue),
            "queue_length": len(queued),
            "recent_results": results[-10:][::-1],
            "recent_improvement_requests": self.improvements()[-10:][::-1],
            "timestamp": _now(),
        }
        self._write_json(self.paths.status_file, status)
        return status

    def balance_sheet(self, results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        rows = self.results() if results is None else results
        completed = len(rows)
        passed = [item for item in rows if item.get("result") == "PASS"]
        failed = [item for item in rows if item.get("result") == "FAIL"]
        net_profit = round(sum(self._cost_adjusted_net_profit(item) for item in rows), 2)
        gross_profit = round(sum(float(item.get("gross_profit", item.get("net_profit", 0.0))) for item in rows), 2)
        execution_cost = round(sum(self._execution_cost_for_result(item) for item in rows), 2)
        ending_equity = round(self.config.starting_balance + net_profit, 2)
        max_drawdown = max((float(item.get("max_drawdown", 0.0)) for item in rows), default=0.0)
        weighted_trades = sum(int(item.get("trades", 0)) for item in rows)
        weighted_spread = (
            sum(self._spread_pips_for_result(item) * int(item.get("trades", 0)) for item in rows) / weighted_trades
            if weighted_trades
            else self.config.spread_pips
        )
        gross_profit_proxy = sum(max(0.0, self._cost_adjusted_net_profit(item)) for item in rows)
        gross_loss_proxy = abs(sum(min(0.0, self._cost_adjusted_net_profit(item)) for item in rows))
        aggregate_profit_factor = (
            round(gross_profit_proxy / gross_loss_proxy, 2)
            if gross_loss_proxy
            else round(max((float(item.get("profit_factor", 0.0)) for item in rows), default=0.0), 2)
        )
        pass_rate = round((len(passed) / completed) * 100, 2) if completed else 0.0
        promotion_readiness = "PROMOTE" if completed and net_profit > 0 and not failed else "HOLD"
        if failed:
            promotion_readiness = "NEEDS_RESEARCH"
        return {
            "paper_balance": round(self.config.starting_balance, 2),
            "paper_equity": ending_equity,
            "gross_profit": gross_profit,
            "spread_slippage_cost": execution_cost,
            "historical_pl": net_profit,
            "total_pl": net_profit,
            "open_validations": len(self.running()),
            "closed_validations": completed,
            "passed_validations": len(passed),
            "failed_validations": len(failed),
            "pass_rate_pct": pass_rate,
            "drawdown": round(max_drawdown, 4),
            "aggregate_profit_factor": aggregate_profit_factor,
            "total_trades": weighted_trades,
            "spread_model": "PAIR_SPECIFIC",
            "spread_pips": round(weighted_spread, 4),
            "slippage_pips": self.config.slippage_pips,
            "execution_cost_per_trade": round(((weighted_spread + self.config.slippage_pips) * self.config.pip_value), 2),
            "promotion_readiness": promotion_readiness,
            "expected_vs_actual_deviation": round(abs(100.0 - pass_rate) / 100.0, 4) if completed else 0.0,
        }

    def queue(self) -> list[dict[str, Any]]:
        return list(_load_json(self.paths.queue_file).get("queue", []))

    def running(self) -> list[dict[str, Any]]:
        return [
            item
            for item in self.queue()
            if item["status"] in {"Loading Data", "Running", "Calculating Metrics"}
        ]

    def results(self) -> list[dict[str, Any]]:
        return list(_load_json(self.paths.results_file).get("results", []))

    def result(self, validation_id: str) -> dict[str, Any]:
        for item in self.results():
            if item["validation_id"] == validation_id:
                return item
        raise KeyError(validation_id)

    def improvements(self) -> list[dict[str, Any]]:
        return list(_load_json(self.paths.improvements_file).get("improvements", []))

    def spread_profile(self) -> list[dict[str, Any]]:
        spreads = {**DEFAULT_PAIR_SPREAD_PIPS, **self.config.pair_spreads}
        return [
            {
                "pair": pair,
                "spread_pips": spread,
                "slippage_pips": self.config.slippage_pips,
                "execution_cost_per_trade": round((spread + self.config.slippage_pips) * self.config.pip_value, 2),
            }
            for pair, spread in sorted(spreads.items())
        ]

    def ensure_queue(self) -> list[dict[str, Any]]:
        payload = _load_json(self.paths.queue_file)
        existing = list(payload.get("queue", []))
        existing_ids = {item["validation_id"] for item in existing}
        assets = sorted(
            self.asset_repository.list(),
            key=lambda asset: (_pair_rank(asset.pair), _timeframe_rank(asset.timeframe), asset.strategy_asset_id),
        )
        now = _now()
        additions: list[dict[str, Any]] = []
        for asset in assets:
            validation_id = _validation_id(asset)
            if validation_id in existing_ids:
                continue
            additions.append(
                _payload(
                    HistoricalValidationQueueItem(
                        validation_id=validation_id,
                        strategy_asset_id=asset.strategy_asset_id,
                        research_program_id=_research_program_id(asset),
                        pair=asset.pair,
                        timeframe=asset.timeframe,
                        dataset_id=asset.source_job_id or f"DS-{asset.pair}-{asset.timeframe}",
                        priority=_priority(asset),
                        status=HistoricalValidationStatus.QUEUED,
                        queued_at=now,
                        estimated_start_time=(datetime.now(UTC) + timedelta(minutes=(len(existing) + len(additions)) * 4)).isoformat(),
                    )
                )
            )
        if additions:
            queue = sorted(existing + additions, key=lambda item: (-float(item["priority"]), item["pair"], _timeframe_rank(item["timeframe"])))
            self._write_json(self.paths.queue_file, {"version": 1, "queue": queue})
            return queue
        if not self.paths.queue_file.exists():
            self._write_json(self.paths.queue_file, {"version": 1, "queue": existing})
        return existing

    def run_next_batch(self) -> dict[str, Any]:
        self.ensure_queue()
        if not self.config.enabled:
            return self.status()
        queue = self.queue()
        active = [item for item in queue if item["status"] in {"Loading Data", "Running", "Calculating Metrics"}]
        capacity = max(0, self.config.max_concurrent - len(active))
        limit = min(self.config.batch_size, capacity)
        if limit == 0:
            return self.status()

        selected = [item for item in queue if item["status"] in {"Queued", "Waiting"}][:limit]
        if not selected:
            return self.status()

        by_id = {asset.strategy_asset_id: asset for asset in self.asset_repository.list()}
        results = self.results()
        improvements = self.improvements()
        updated: list[dict[str, Any]] = []
        now = _now()
        for item in queue:
            selected_match = next((candidate for candidate in selected if candidate["validation_id"] == item["validation_id"]), None)
            if selected_match is None:
                updated.append(item)
                continue
            asset = by_id.get(str(item["strategy_asset_id"]))
            if asset is None:
                updated_item = {**item, "status": HistoricalValidationStatus.FAILED.value, "started_at": now, "completed_at": now}
                updated.append(updated_item)
                continue
            started_at = _now()
            result = self._simulate_validation(asset, item["validation_id"])
            completed_at = result.validation_timestamp
            final_status = HistoricalValidationStatus.COMPLETED if result.result == "PASS" else HistoricalValidationStatus.NEEDS_RESEARCH
            updated.append({**item, "status": final_status.value, "started_at": started_at, "completed_at": completed_at})
            results.append(_payload(result))
            if result.result == "FAIL":
                improvements.append(_payload(self._improvement_for(result)))

        self._write_json(self.paths.queue_file, {"version": 1, "queue": updated})
        self._write_json(self.paths.results_file, {"version": 1, "results": _dedupe(results, "validation_id")[-1000:]})
        self._write_json(
            self.paths.improvements_file,
            {"version": 1, "improvements": _dedupe(improvements, "improvement_id")[-1000:]},
        )
        return self.status()

    def _simulate_validation(self, asset: ApprovedStrategyAsset, validation_id: str) -> HistoricalValidationResult:
        digest = int(hashlib.sha1(validation_id.encode("utf-8")).hexdigest()[:8], 16)
        trades = 120 + digest % 520
        gross_profit_factor = max(0.8, min(2.8, asset.profit_factor - 0.25 + (digest % 70) / 100))
        win_rate = round(0.38 + (digest % 28) / 100, 2)
        max_drawdown = round(max(0.04, min(0.35, asset.max_drawdown + (digest % 16) / 100)), 3)
        gross_expectancy = (gross_profit_factor - 1.0) * 14.0
        gross_profit = round(gross_expectancy * trades, 2)
        spread_pips = self._spread_pips_for_pair(asset.pair)
        execution_cost_per_trade = round((spread_pips + self.config.slippage_pips) * self.config.pip_value, 2)
        execution_cost = round(execution_cost_per_trade * trades, 2)
        net_profit = round(gross_profit - execution_cost, 2)
        expectancy = round(net_profit / max(1, trades), 2)
        profit_factor = round(max(0.1, gross_profit_factor - (execution_cost_per_trade / 100.0)), 2)
        sharpe = round(max(0.1, profit_factor - max_drawdown * 2.0), 2)
        recovery = round(net_profit / max(1.0, max_drawdown * 10_000), 2)
        passed = (
            trades >= self.config.min_trades
            and profit_factor >= self.config.min_profit_factor
            and win_rate >= self.config.min_win_rate
            and max_drawdown <= self.config.max_drawdown
            and expectancy > 0
        )
        return HistoricalValidationResult(
            validation_id=validation_id,
            strategy_asset_id=asset.strategy_asset_id,
            research_program_id=_research_program_id(asset),
            pair=asset.pair,
            timeframe=asset.timeframe,
            historical_period=f"last_{self.config.years}_years",
            trades=trades,
            gross_profit=gross_profit,
            execution_cost=execution_cost,
            execution_cost_per_trade=execution_cost_per_trade,
            spread_pips=spread_pips,
            slippage_pips=self.config.slippage_pips,
            net_profit=net_profit,
            profit_factor=profit_factor,
            win_rate=win_rate,
            expectancy=expectancy,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            recovery_factor=recovery,
            average_trade=round(net_profit / max(1, trades), 2),
            exposure=round(0.08 + (digest % 22) / 100, 2),
            result="PASS" if passed else "FAIL",
            validation_timestamp=_now(),
            strategy_family=asset.strategy_family,
            regime=asset.market_regime,
        )

    def _execution_cost_for_result(self, item: dict[str, Any]) -> float:
        if "execution_cost" in item:
            return float(item.get("execution_cost", 0.0))
        return int(item.get("trades", 0)) * (self._spread_pips_for_result(item) + self.config.slippage_pips) * self.config.pip_value

    def _cost_adjusted_net_profit(self, item: dict[str, Any]) -> float:
        if "execution_cost" in item:
            return float(item.get("net_profit", 0.0))
        return float(item.get("net_profit", 0.0)) - self._execution_cost_for_result(item)

    def _spread_pips_for_result(self, item: dict[str, Any]) -> float:
        if "spread_pips" in item:
            return float(item.get("spread_pips", self.config.spread_pips))
        return self._spread_pips_for_pair(str(item.get("pair", "")))

    def _spread_pips_for_pair(self, pair: str) -> float:
        return self.config.pair_spreads.get(pair, DEFAULT_PAIR_SPREAD_PIPS.get(pair, self.config.spread_pips))

    def _improvement_for(self, result: HistoricalValidationResult) -> HistoricalValidationImprovement:
        reason_code = "STRATEGY_DEGRADATION"
        if result.max_drawdown > self.config.max_drawdown:
            reason_code = "EXCESSIVE_DRAWDOWN"
        elif result.profit_factor < self.config.min_profit_factor:
            reason_code = "LOW_PROFIT_FACTOR"
        elif result.win_rate < self.config.min_win_rate:
            reason_code = "LOW_WIN_RATE"
        elif result.trades < self.config.min_trades:
            reason_code = "INSUFFICIENT_TRADES"
        return HistoricalValidationImprovement(
            improvement_id=f"imp_{result.validation_id}",
            validation_id=result.validation_id,
            strategy_asset_id=result.strategy_asset_id,
            research_program_id=result.research_program_id,
            pair=result.pair,
            timeframe=result.timeframe,
            reason_code=reason_code,
            message=f"Historical validation failed for {result.pair} {result.timeframe}; request new autonomous research.",
            created_at=result.validation_timestamp,
        )

    def _state(self, queue: list[dict[str, Any]], running: list[dict[str, Any]]) -> str:
        if not self.config.enabled:
            return HistoricalValidationState.DISABLED.value
        if running:
            return HistoricalValidationState.RUNNING.value
        if queue and all(item["status"] in {"Completed", "Needs Research", "Failed", "Cancelled"} for item in queue):
            return HistoricalValidationState.COMPLETE.value
        return HistoricalValidationState.IDLE.value

    def _average_duration_seconds(self, queue: list[dict[str, Any]]) -> float:
        durations: list[float] = []
        for item in queue:
            if not item.get("started_at") or not item.get("completed_at"):
                continue
            try:
                started = datetime.fromisoformat(str(item["started_at"]).replace("Z", "+00:00"))
                completed = datetime.fromisoformat(str(item["completed_at"]).replace("Z", "+00:00"))
            except ValueError:
                continue
            durations.append((completed - started).total_seconds())
        return round(sum(durations) / len(durations), 2) if durations else 0.0

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def default_historical_validation_paths(repo_root: Path) -> HistoricalValidationPaths:
    return HistoricalValidationPaths(
        queue_file=repo_root / "var" / "history_validation_queue.json",
        status_file=repo_root / "var" / "history_validation_status.json",
        results_file=repo_root / "var" / "history_validation_results.json",
        improvements_file=repo_root / "var" / "history_validation_improvements.json",
    )


def historical_validation_config_from_env() -> HistoricalValidationConfig:
    return HistoricalValidationConfig(
        enabled=_env_bool("HISTORICAL_VALIDATION_ENABLED", True),
        max_concurrent=_env_int("HISTORICAL_VALIDATION_MAX_CONCURRENT", 6),
        batch_size=_env_int("HISTORICAL_VALIDATION_BATCH_SIZE", 6),
        years=_env_int("HISTORICAL_VALIDATION_YEARS", 10),
        starting_balance=_env_float("HISTORICAL_VALIDATION_STARTING_BALANCE", 100_000.0),
        spread_pips=_env_float("HISTORICAL_VALIDATION_SPREAD_PIPS", 1.2),
        slippage_pips=_env_float("HISTORICAL_VALIDATION_SLIPPAGE_PIPS", 0.2),
        pip_value=_env_float("HISTORICAL_VALIDATION_PIP_VALUE", 10.0),
        pair_spreads=_pair_spreads_from_env(),
    )


def _validation_id(asset: ApprovedStrategyAsset) -> str:
    return f"hv_{asset.pair}_{asset.timeframe}_{hashlib.sha1(asset.strategy_asset_id.encode('utf-8')).hexdigest()[:10]}"


def _research_program_id(asset: ApprovedStrategyAsset) -> str:
    return str(asset.strategy_definition.get("research_program_id") or f"RP-{asset.pair}-{asset.timeframe}")


def _priority(asset: ApprovedStrategyAsset) -> float:
    return round((3.0 - asset.profit_factor) + asset.max_drawdown + _timeframe_rank(asset.timeframe) * 0.05, 4)


def _pair_rank(pair: str) -> str:
    return pair


def _timeframe_rank(timeframe: str) -> int:
    return {"M5": 0, "M15": 1, "H1": 2, "H4": 3}.get(timeframe, 99)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _payload(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: _payload(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_payload(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _payload(item) for key, item in value.items()}
    return value


def _dedupe(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    by_id = {str(row[key]): row for row in rows}
    return list(by_id.values())


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _pair_spreads_from_env() -> dict[str, float]:
    value = os.getenv("HISTORICAL_VALIDATION_PAIR_SPREADS_JSON")
    if not value:
        return DEFAULT_PAIR_SPREAD_PIPS
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return DEFAULT_PAIR_SPREAD_PIPS
    if not isinstance(payload, dict):
        return DEFAULT_PAIR_SPREAD_PIPS
    parsed: dict[str, float] = {}
    for pair, spread in payload.items():
        try:
            parsed[str(pair).upper()] = float(spread)
        except (TypeError, ValueError):
            continue
    return {**DEFAULT_PAIR_SPREAD_PIPS, **parsed}
