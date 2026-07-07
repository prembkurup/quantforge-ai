from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from quantforge.live.engine import ExecutionReceipt, LiveTradingEngine, PositionSnapshot, TradingSignal
from quantforge.live.replay import ReplayEventFactory
from quantforge.research.strategy_assets import (
    ApprovedStrategyAsset,
    StrategyAssetRepository,
    default_strategy_asset_repository,
    strategy_asset_from_approved,
)


class LatestCandleRepository(Protocol):
    def load_latest(
        self,
        pair_name: str,
        granularity: str,
        *,
        complete_only: bool = True,
        limit: int = 300,
    ) -> list[dict[str, Any]]:
        ...


@dataclass(frozen=True, slots=True)
class PaperScannerConfig:
    enabled: bool
    pairs: tuple[str, ...]
    timeframes: tuple[str, ...]
    max_pairs_per_scan: int
    execution_path: str = "OANDA_PAPER"
    candle_lookback: int = 2


@dataclass(frozen=True, slots=True)
class PairScanResult:
    pair: str
    timeframe: str
    status: str
    reason: str
    candle_time: str = ""
    strategy_asset_id: str = ""
    signal_id: str = ""
    signal_action: str = ""
    execution_status: str = ""
    order_id: str = ""


@dataclass(frozen=True, slots=True)
class MultiPairPaperScannerResult:
    updated_at: str
    mode: str
    connected: bool
    pairs_loaded: int
    timeframes_loaded: int
    pair_timeframes_scanned: int
    candles_loaded: int
    new_candles: int
    events_processed: int
    signals_generated: int
    orders_executed: int
    open_positions: int
    execution_path: str
    pair_results: tuple[PairScanResult, ...]
    signals: tuple[TradingSignal, ...] = ()
    executions: tuple[ExecutionReceipt, ...] = ()
    positions: tuple[PositionSnapshot, ...] = ()


class ProcessedCandleStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def seen(self, pair: str, timeframe: str, candle_time: str) -> bool:
        return self._key(pair, timeframe) in self._load().get(candle_time, [])

    def mark(self, pair: str, timeframe: str, candle_time: str) -> None:
        payload = self._load()
        key = self._key(pair, timeframe)
        seen = set(payload.get(candle_time, []))
        seen.add(key)
        payload[candle_time] = sorted(seen)
        self._save(payload)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _key(pair: str, timeframe: str) -> str:
        return f"{pair}:{timeframe}"


class PaperPositionStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def list_open(self) -> tuple[dict[str, Any], ...]:
        payload = self._load()
        return tuple(position for position in payload.get("positions", []) if position.get("status") == "OPEN")

    def has_open(self, pair: str, timeframe: str) -> bool:
        return any(
            position.get("instrument") == pair and position.get("timeframe") == timeframe
            for position in self.list_open()
        )

    def add_many(self, positions: tuple[PositionSnapshot, ...], signal_by_pair: dict[str, TradingSignal]) -> None:
        payload = self._load()
        existing = {
            str(position.get("position_id")): position
            for position in payload.get("positions", [])
            if position.get("position_id")
        }
        now = datetime.now(UTC).isoformat(timespec="seconds")
        for position in positions:
            signal = signal_by_pair.get(position.instrument)
            existing[position.position_id] = {
                **asdict(position),
                "timeframe": signal.feature_vector.timeframe if signal else "",
                "signal_id": signal.signal_id if signal else "",
                "status": "OPEN",
                "opened_at": now,
            }
        payload["positions"] = sorted(existing.values(), key=lambda item: str(item.get("opened_at", "")))
        self._save(payload)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"positions": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


class DecisionTraceStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True, default=str) + "\n")


class StrategyAssetSelector:
    def __init__(self, repository: StrategyAssetRepository) -> None:
        self.repository = repository

    def select(self, pair: str, timeframe: str, regime: str) -> ApprovedStrategyAsset | None:
        candidates = tuple(
            asset
            for asset in self.repository.list()
            if asset.deployable and asset.pair == pair and asset.timeframe == timeframe
        )
        exact = tuple(asset for asset in candidates if asset.market_regime.upper() == regime.upper())
        pool = exact or candidates
        if not pool:
            return None
        return sorted(pool, key=lambda asset: asset.approved_at, reverse=True)[0]


class MultiPairPaperScanner:
    def __init__(
        self,
        candle_repository: LatestCandleRepository,
        *,
        config: PaperScannerConfig,
        strategy_repository: StrategyAssetRepository | None = None,
        processed_store: ProcessedCandleStore | None = None,
        position_store: PaperPositionStore | None = None,
        decision_store: DecisionTraceStore | None = None,
        engine: LiveTradingEngine | None = None,
    ) -> None:
        self.candles = candle_repository
        self.config = config
        self.selector = StrategyAssetSelector(strategy_repository or default_strategy_asset_repository())
        self.processed = processed_store or ProcessedCandleStore(default_processed_candles_file())
        self.positions = position_store or PaperPositionStore(default_paper_positions_file())
        self.decisions = decision_store or DecisionTraceStore(default_decision_trace_file())
        self.engine = engine or LiveTradingEngine()
        self.event_factory = ReplayEventFactory()

    def run(self) -> MultiPairPaperScannerResult:
        if not self.config.enabled:
            return self._empty("scanner_disabled")

        pair_results: list[PairScanResult] = []
        signals: list[TradingSignal] = []
        executions: list[ExecutionReceipt] = []
        new_positions: list[PositionSnapshot] = []
        candles_loaded = 0
        new_candles = 0
        events_processed = 0

        for pair in self.config.pairs[: self.config.max_pairs_per_scan]:
            for timeframe in self.config.timeframes:
                rows = self.candles.load_latest(
                    pair,
                    timeframe,
                    complete_only=True,
                    limit=max(1, self.config.candle_lookback),
                )
                candles_loaded += len(rows)
                if not rows:
                    pair_results.append(PairScanResult(pair, timeframe, "SKIPPED", "no_closed_candle"))
                    continue
                row = rows[-1]
                candle_time = _iso(row["time"])
                if not bool(row.get("is_complete", True)):
                    pair_results.append(PairScanResult(pair, timeframe, "SKIPPED", "latest_candle_incomplete", candle_time))
                    continue
                if self.processed.seen(pair, timeframe, candle_time):
                    pair_results.append(PairScanResult(pair, timeframe, "SKIPPED", "candle_already_processed", candle_time))
                    continue
                if self.positions.has_open(pair, timeframe):
                    self.processed.mark(pair, timeframe, candle_time)
                    pair_results.append(PairScanResult(pair, timeframe, "BLOCKED", "existing_open_position", candle_time))
                    continue

                event = self.event_factory.new_candle(row)
                feature = self.engine.features.build(event)
                if feature is None:
                    pair_results.append(PairScanResult(pair, timeframe, "SKIPPED", "feature_generation_failed", candle_time))
                    continue
                regime = self.engine.regimes.detect(feature)
                selected = self.selector.select(pair, timeframe, regime.regime)
                if selected is None:
                    self.processed.mark(pair, timeframe, candle_time)
                    pair_results.append(PairScanResult(pair, timeframe, "SKIPPED", "no_compatible_approved_strategy", candle_time))
                    continue

                new_candles += 1
                live_result = self.engine.run(strategy_asset_from_approved(selected), events=(event,), demo=False)
                events_processed += live_result.events_processed
                signals.extend(live_result.signals)
                approved_executions = tuple(
                    execution for execution in live_result.executions if execution.status in {"filled", "submitted"}
                )
                executions.extend(approved_executions)
                new_positions.extend(live_result.positions)
                self.processed.mark(pair, timeframe, candle_time)
                signal = live_result.signals[-1] if live_result.signals else None
                receipt = approved_executions[-1] if approved_executions else None
                status = "ORDER_EXECUTED" if receipt else "BLOCKED"
                reason = receipt.status if receipt else "risk_or_signal_blocked"
                pair_results.append(
                    PairScanResult(
                        pair=pair,
                        timeframe=timeframe,
                        status=status,
                        reason=reason,
                        candle_time=candle_time,
                        strategy_asset_id=selected.strategy_asset_id,
                        signal_id=signal.signal_id if signal else "",
                        signal_action=signal.action.value if signal else "",
                        execution_status=receipt.status if receipt else "",
                        order_id=receipt.order_id if receipt else "",
                    )
                )
                self.decisions.append(
                    {
                        "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
                        "pair": pair,
                        "timeframe": timeframe,
                        "candle_time": candle_time,
                        "regime": regime.regime,
                        "strategy_asset_id": selected.strategy_asset_id,
                        "signal": asdict(signal) if signal else {},
                        "execution": asdict(receipt) if receipt else {},
                        "status": status,
                    }
                )

        signal_by_pair = {signal.instrument: signal for signal in signals}
        self.positions.add_many(tuple(new_positions), signal_by_pair)
        open_positions = len(self.positions.list_open())
        return MultiPairPaperScannerResult(
            updated_at=datetime.now(UTC).isoformat(timespec="seconds"),
            mode="paper-scanner",
            connected=True,
            pairs_loaded=min(len(self.config.pairs), self.config.max_pairs_per_scan),
            timeframes_loaded=len(self.config.timeframes),
            pair_timeframes_scanned=len(pair_results),
            candles_loaded=candles_loaded,
            new_candles=new_candles,
            events_processed=events_processed,
            signals_generated=len(signals),
            orders_executed=len(executions),
            open_positions=open_positions,
            execution_path=self.config.execution_path,
            pair_results=tuple(pair_results),
            signals=tuple(signals),
            executions=tuple(executions),
            positions=tuple(new_positions),
        )

    def _empty(self, reason: str) -> MultiPairPaperScannerResult:
        return MultiPairPaperScannerResult(
            updated_at=datetime.now(UTC).isoformat(timespec="seconds"),
            mode="paper-scanner",
            connected=False,
            pairs_loaded=0,
            timeframes_loaded=0,
            pair_timeframes_scanned=0,
            candles_loaded=0,
            new_candles=0,
            events_processed=0,
            signals_generated=0,
            orders_executed=0,
            open_positions=len(self.positions.list_open()),
            execution_path=self.config.execution_path,
            pair_results=(PairScanResult("", "", "SKIPPED", reason),),
        )


def load_paper_scanner_config(path: Path | None = None) -> PaperScannerConfig:
    config_path = path or default_paper_scanner_config_file()
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    return PaperScannerConfig(
        enabled=bool(payload.get("enabled", False)),
        pairs=tuple(str(item).upper() for item in payload.get("pairs", [])),
        timeframes=tuple(str(item).upper() for item in payload.get("timeframes", [])),
        max_pairs_per_scan=int(payload.get("max_pairs_per_scan", 30)),
        execution_path=str(payload.get("execution_path", "OANDA_PAPER")),
        candle_lookback=int(payload.get("candle_lookback", 2)),
    )


def default_paper_scanner_config_file() -> Path:
    return _repo_root() / "config" / "paper_scanner.json"


def default_processed_candles_file() -> Path:
    return _repo_root() / "var" / "paper_scanner_processed_candles.json"


def default_paper_positions_file() -> Path:
    return _repo_root() / "var" / "paper_positions.json"


def default_decision_trace_file() -> Path:
    return _repo_root() / "var" / "paper_scanner_decision_traces.jsonl"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
