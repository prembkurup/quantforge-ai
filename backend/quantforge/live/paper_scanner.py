from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
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
    max_open_positions: int = 30
    max_trades_per_day: int = 60
    dry_run: bool = False


@dataclass(frozen=True, slots=True)
class PaperFeatureVector:
    feature_vector_id: str
    pair: str
    timeframe: str
    candle_time: str
    instrument: str
    features: dict[str, Any]
    feature_versions: dict[str, str]
    calculation_versions: dict[str, str]


@dataclass(frozen=True, slots=True)
class PaperRegimeResult:
    regime: str
    confidence: float
    features_used: tuple[str, ...]
    reason: str


@dataclass(frozen=True, slots=True)
class StrategyAssetSelectionResult:
    selected_strategy_asset: str
    selection_reason: str
    alternative_candidates: tuple[str, ...]
    rejection_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GateResult:
    status: str
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PaperSignalRecord:
    signal_id: str
    strategy_asset_id: str
    pair: str
    timeframe: str
    candle_time: str
    signal_type: str
    confidence: float
    reason_codes: tuple[str, ...]
    feature_vector_id: str
    signal_key: str


@dataclass(frozen=True, slots=True)
class PaperOrderRecord:
    order_id: str
    signal_id: str
    strategy_asset_id: str
    pair: str
    timeframe: str
    candle_time: str
    status: str
    execution_path: str
    units: float


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
    feature_vector: PaperFeatureVector | None = None
    regime_result: PaperRegimeResult | None = None
    strategy_selection: StrategyAssetSelectionResult | None = None
    trade_eligibility: GateResult | None = None
    risk_result: GateResult | None = None
    rejection_reasons: tuple[str, ...] = ()


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
    orders_blocked: int
    open_positions: int
    execution_path: str
    skip_reasons: dict[str, int]
    pair_results: tuple[PairScanResult, ...]
    paper_scanner_run: dict[str, Any] = field(default_factory=dict)
    paper_signals: tuple[PaperSignalRecord, ...] = ()
    paper_orders: tuple[PaperOrderRecord, ...] = ()
    paper_positions: tuple[dict[str, Any], ...] = ()
    closed_paper_positions: tuple[dict[str, Any], ...] = ()
    signals: tuple[TradingSignal, ...] = ()
    executions: tuple[ExecutionReceipt, ...] = ()
    positions: tuple[PositionSnapshot, ...] = ()


class ProcessedCandleStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def seen(self, pair: str, timeframe: str, candle_time: str) -> bool:
        return self._key(pair, timeframe) in self._load().get(candle_time, [])

    def last_processed_time(self, pair: str, timeframe: str) -> str:
        key = self._key(pair, timeframe)
        times = sorted(candle_time for candle_time, keys in self._load().items() if key in keys)
        return times[-1] if times else ""

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
        changed = self._enrich_open_positions(payload)
        if changed:
            self._save(payload)
        return tuple(position for position in payload.get("positions", []) if position.get("status") == "OPEN")

    def list_closed(self, *, limit: int = 100) -> tuple[dict[str, Any], ...]:
        payload = self._load()
        closed = [position for position in payload.get("positions", []) if position.get("status") == "CLOSED"]
        return tuple(sorted(closed, key=lambda item: str(item.get("closed_at") or item.get("updated_at") or ""), reverse=True)[:limit])

    def has_open(self, pair: str, timeframe: str) -> bool:
        return any(
            position.get("instrument") == pair and position.get("timeframe") == timeframe
            for position in self.list_open()
        )

    def add_many(
        self,
        positions: tuple[PositionSnapshot, ...],
        signals: tuple[PaperSignalRecord, ...],
        price_by_pair_timeframe: dict[str, float],
        conversion_prices: dict[str, float] | None = None,
    ) -> None:
        payload = self._load()
        existing = {
            str(position.get("position_id")): position
            for position in payload.get("positions", [])
            if position.get("position_id")
        }
        now = datetime.now(UTC).isoformat(timespec="seconds")
        for position in positions:
            signal = _signal_for_position(position, signals)
            timeframe = signal.timeframe if signal else ""
            entry_time = _iso(signal.candle_time) if signal else now
            entry_price = price_by_pair_timeframe.get(_pair_timeframe_key(position.instrument, timeframe), 0.0)
            take_profit, stop_loss = _default_exit_prices(entry_price, signal.signal_type if signal else "")
            floating_pl = _position_pl_account_currency(
                position.instrument,
                entry_price,
                entry_price,
                position.units,
                signal.signal_type if signal else "",
                conversion_prices=conversion_prices,
                fallback=position.floating_pl,
            )
            existing[position.position_id] = {
                "position_id": position.position_id,
                "strategy_asset_id": signal.strategy_asset_id if signal else position.strategy_id,
                "pair": position.instrument,
                "instrument": position.instrument,
                "timeframe": timeframe,
                "direction": signal.signal_type if signal else "",
                "units": position.units,
                "entry_time": entry_time,
                "entry_price": entry_price,
                "open_price": entry_price,
                "close_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "status": "OPEN",
                "source_signal_id": signal.signal_id if signal else "",
                "source_candle_time": signal.candle_time if signal else "",
                "opened_at": entry_time,
                "created_at": now,
                "updated_at": now,
                "floating_pl": floating_pl,
                "p_l": floating_pl,
                "p_l_account_currency": floating_pl,
                "p_l_currency": "USD",
                "margin_used": position.margin_used,
                "exposure": position.exposure,
            }
        payload["positions"] = sorted(existing.values(), key=lambda item: str(item.get("opened_at", "")))
        self._save(payload)

    def mark_to_market(
        self,
        price_by_pair_timeframe: dict[str, float],
        candle_by_pair_timeframe: dict[str, dict[str, Any]] | None = None,
        candle_history_by_pair_timeframe: dict[str, list[dict[str, Any]]] | None = None,
        conversion_prices: dict[str, float] | None = None,
    ) -> None:
        payload = self._load()
        now = datetime.now(UTC).isoformat(timespec="seconds")
        changed = self._enrich_open_positions(payload)
        candle_by_pair_timeframe = candle_by_pair_timeframe or {}
        candle_history_by_pair_timeframe = candle_history_by_pair_timeframe or {}
        for position in payload.get("positions", []):
            changed = _normalize_position_pl(position, conversion_prices=conversion_prices) or changed
            if position.get("status") != "OPEN":
                continue
            pair = str(position.get("pair") or position.get("instrument") or "")
            timeframe = str(position.get("timeframe") or "")
            monitor_timeframe = _paper_position_monitor_timeframe(position)
            monitor_key = _pair_timeframe_key(pair, monitor_timeframe)
            key = monitor_key if monitor_key in price_by_pair_timeframe else _pair_timeframe_key(pair, timeframe)
            close_price = price_by_pair_timeframe.get(key)
            if close_price is None:
                continue
            entry_price = _float_or_zero(position.get("entry_price") or position.get("open_price"))
            direction = str(position.get("direction") or "")
            units = _float_or_zero(position.get("units"))
            candle = candle_by_pair_timeframe.get(key, {})
            candles = candle_history_by_pair_timeframe.get(key, [candle] if candle else [])
            exit_price, exit_reason, exit_candle = _exit_price_for_candles(position, candles)
            if exit_price is not None:
                realized_pl = _position_pl_account_currency(
                    pair,
                    entry_price,
                    exit_price,
                    units,
                    direction,
                    conversion_prices=conversion_prices,
                )
                position["close_price"] = exit_price
                position["current_price"] = exit_price
                position["floating_pl"] = realized_pl
                position["p_l"] = realized_pl
                position["p_l_account_currency"] = realized_pl
                position["p_l_currency"] = "USD"
                position["status"] = "CLOSED"
                position["close_reason"] = exit_reason
                position["close_timeframe"] = monitor_timeframe if key == monitor_key else timeframe
                position["closed_at"] = _iso(exit_candle.get("time")) if exit_candle.get("time") else now
                position["updated_at"] = now
                changed = True
                continue
            floating_pl = _position_pl_account_currency(
                pair,
                entry_price,
                close_price,
                units,
                direction,
                conversion_prices=conversion_prices,
                fallback=_float_or_zero(position.get("floating_pl")),
            )
            position["close_price"] = close_price
            position["current_price"] = close_price
            position["price_timeframe"] = monitor_timeframe if key == monitor_key else timeframe
            position["floating_pl"] = floating_pl
            position["p_l"] = floating_pl
            position["p_l_account_currency"] = floating_pl
            position["p_l_currency"] = "USD"
            position["updated_at"] = now
            changed = True
        if changed:
            self._save(payload)

    def _enrich_open_positions(self, payload: dict[str, Any]) -> bool:
        changed = False
        now = datetime.now(UTC).isoformat(timespec="seconds")
        for position in payload.get("positions", []):
            if position.get("status") != "OPEN":
                continue
            changed = _enrich_open_position(position, now) or changed
        return changed

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


class ProcessedSignalStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def seen(self, signal_key: str) -> bool:
        return signal_key in set(self._load().get("signal_keys", []))

    def mark(self, signal_key: str) -> None:
        payload = self._load()
        keys = set(payload.get("signal_keys", []))
        keys.add(signal_key)
        payload["signal_keys"] = sorted(keys)
        self._save(payload)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"signal_keys": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


class StrategyAssetSelector:
    def __init__(self, repository: StrategyAssetRepository) -> None:
        self.repository = repository

    def select(self, pair: str, timeframe: str, regime: str) -> tuple[ApprovedStrategyAsset | None, StrategyAssetSelectionResult]:
        candidates = tuple(asset for asset in self.repository.list() if asset.pair == pair and asset.timeframe == timeframe)
        rejection_reasons: list[str] = []
        deployable = tuple(asset for asset in candidates if asset.deployable)
        if len(deployable) < len(candidates):
            rejection_reasons.append("STATUS_NOT_PAPER_OR_PRODUCTION_ELIGIBLE")
        exact = tuple(asset for asset in deployable if asset.market_regime.upper() == regime.upper())
        if not exact and deployable:
            rejection_reasons.append("MARKET_REGIME_MISMATCH")
        pool = exact
        if not pool:
            return None, StrategyAssetSelectionResult(
                selected_strategy_asset="",
                selection_reason="NO_COMPATIBLE_APPROVED_STRATEGY",
                alternative_candidates=tuple(asset.strategy_asset_id for asset in deployable[:5]),
                rejection_reasons=tuple(rejection_reasons or ["NO_PAIR_TIMEFRAME_CANDIDATE"]),
            )
        selected = sorted(pool, key=lambda asset: asset.approved_at, reverse=True)[0]
        alternatives = tuple(asset.strategy_asset_id for asset in pool if asset.strategy_asset_id != selected.strategy_asset_id)
        return selected, StrategyAssetSelectionResult(
            selected_strategy_asset=selected.strategy_asset_id,
            selection_reason=f"Matched {pair} {timeframe} {regime} approved Strategy Asset.",
            alternative_candidates=alternatives[:5],
            rejection_reasons=tuple(rejection_reasons),
        )


class MultiPairPaperScanner:
    def __init__(
        self,
        candle_repository: LatestCandleRepository,
        *,
        config: PaperScannerConfig,
        strategy_repository: StrategyAssetRepository | None = None,
        processed_store: ProcessedCandleStore | None = None,
        signal_store: ProcessedSignalStore | None = None,
        position_store: PaperPositionStore | None = None,
        decision_store: DecisionTraceStore | None = None,
        engine: LiveTradingEngine | None = None,
    ) -> None:
        self.candles = candle_repository
        self.config = config
        self.selector = StrategyAssetSelector(strategy_repository or default_strategy_asset_repository())
        self.processed = processed_store or ProcessedCandleStore(default_processed_candles_file())
        self.signal_keys = signal_store or ProcessedSignalStore(default_processed_signals_file())
        self.positions = position_store or PaperPositionStore(default_paper_positions_file())
        self.decisions = decision_store or DecisionTraceStore(default_decision_trace_file())
        self.engine = engine or LiveTradingEngine()
        self.event_factory = ReplayEventFactory()

    def run(self) -> MultiPairPaperScannerResult:
        if not self.config.enabled:
            return self._empty("scanner_disabled")

        pair_results: list[PairScanResult] = []
        signals: list[TradingSignal] = []
        paper_signals: list[PaperSignalRecord] = []
        executions: list[ExecutionReceipt] = []
        paper_orders: list[PaperOrderRecord] = []
        new_positions: list[PositionSnapshot] = []
        candles_loaded = 0
        new_candles = 0
        events_processed = 0
        price_by_pair_timeframe: dict[str, float] = {}
        candle_by_pair_timeframe: dict[str, dict[str, Any]] = {}
        candle_history_by_pair_timeframe: dict[str, list[dict[str, Any]]] = {}
        conversion_prices: dict[str, float] = {}

        for pair in self.config.pairs[: self.config.max_pairs_per_scan]:
            for timeframe in self.config.timeframes:
                rows = self.candles.load_latest(
                    pair,
                    timeframe,
                    complete_only=True,
                    limit=max(1, self.config.candle_lookback),
                )
                candles_loaded += len(rows)
                if rows:
                    key = _pair_timeframe_key(pair, timeframe)
                    price_by_pair_timeframe[key] = _candle_close(rows[-1])
                    conversion_prices[pair] = _candle_close(rows[-1])
                    candle_by_pair_timeframe[key] = rows[-1]
                candle_check = self._validate_candles(pair, timeframe, rows)
                if candle_check.status != "ELIGIBLE":
                    candle_time = _iso(rows[-1]["time"]) if rows else ""
                    pair_results.append(
                        PairScanResult(
                            pair,
                            timeframe,
                            "SKIPPED",
                            candle_check.reasons[0],
                            candle_time,
                            trade_eligibility=candle_check,
                            rejection_reasons=candle_check.reasons,
                        )
                    )
                    continue
                row = rows[-1]
                candle_time = _iso(row["time"])

                event = self.event_factory.new_candle(row)
                feature = self.engine.features.build(event)
                if feature is None:
                    pair_results.append(PairScanResult(pair, timeframe, "SKIPPED", "feature_generation_failed", candle_time))
                    continue
                feature_trace = PaperFeatureVector(
                    feature_vector_id=f"FV-{pair}-{timeframe}-{_safe_key(candle_time)}",
                    pair=pair,
                    timeframe=timeframe,
                    candle_time=candle_time,
                    instrument=feature.instrument,
                    features=asdict(feature),
                    feature_versions={"live_feature_engine": "1.0.0"},
                    calculation_versions={"replay_event_factory": "1.0.0"},
                )
                regime = self.engine.regimes.detect(feature)
                regime_trace = PaperRegimeResult(
                    regime=regime.regime,
                    confidence=regime.confidence,
                    features_used=("trend_strength", "pullback_state"),
                    reason=f"trend_strength={feature.trend_strength:.4f}",
                )
                selected, selection_trace = self.selector.select(pair, timeframe, regime.regime)
                if selected is None:
                    self.processed.mark(pair, timeframe, candle_time)
                    pair_results.append(
                        PairScanResult(
                            pair,
                            timeframe,
                            "SKIPPED",
                            "no_compatible_approved_strategy",
                            candle_time,
                            feature_vector=feature_trace,
                            regime_result=regime_trace,
                            strategy_selection=selection_trace,
                            trade_eligibility=GateResult("NOT_ELIGIBLE", ("STRATEGY_NOT_SELECTED",)),
                            rejection_reasons=("STRATEGY_NOT_SELECTED",),
                        )
                    )
                    self._append_decision_trace(pair, timeframe, candle_time, "SKIPPED", feature_trace, regime_trace, selection_trace)
                    continue
                eligibility = self._trade_eligibility(pair, timeframe, candle_time, selected)
                if eligibility.status != "ELIGIBLE":
                    self.processed.mark(pair, timeframe, candle_time)
                    pair_results.append(
                        PairScanResult(
                            pair,
                            timeframe,
                            "BLOCKED",
                            eligibility.reasons[0],
                            candle_time,
                            strategy_asset_id=selected.strategy_asset_id,
                            feature_vector=feature_trace,
                            regime_result=regime_trace,
                            strategy_selection=selection_trace,
                            trade_eligibility=eligibility,
                            rejection_reasons=eligibility.reasons,
                        )
                    )
                    self._append_decision_trace(
                        pair, timeframe, candle_time, "BLOCKED", feature_trace, regime_trace, selection_trace, eligibility
                    )
                    continue

                new_candles += 1
                live_result = self.engine.run(strategy_asset_from_approved(selected), events=(event,), demo=False)
                events_processed += live_result.events_processed
                signal = live_result.signals[-1] if live_result.signals else None
                if signal is None:
                    self.processed.mark(pair, timeframe, candle_time)
                    pair_results.append(
                        PairScanResult(
                            pair,
                            timeframe,
                            "NO_SIGNAL",
                            "NO_SIGNAL",
                            candle_time,
                            strategy_asset_id=selected.strategy_asset_id,
                            feature_vector=feature_trace,
                            regime_result=regime_trace,
                            strategy_selection=selection_trace,
                            trade_eligibility=eligibility,
                            risk_result=GateResult("REJECTED", ("NO_SIGNAL",)),
                            rejection_reasons=("NO_SIGNAL",),
                        )
                    )
                    continue
                paper_signal = _paper_signal(selected.strategy_asset_id, signal, candle_time, feature_trace, regime_trace)
                if paper_signal.signal_type == "HOLD":
                    self.processed.mark(pair, timeframe, candle_time)
                    pair_results.append(
                        PairScanResult(
                            pair,
                            timeframe,
                            "NO_SIGNAL",
                            "HOLD",
                            candle_time,
                            strategy_asset_id=selected.strategy_asset_id,
                            signal_id=paper_signal.signal_id,
                            signal_action=paper_signal.signal_type,
                            feature_vector=feature_trace,
                            regime_result=regime_trace,
                            strategy_selection=selection_trace,
                            trade_eligibility=eligibility,
                            risk_result=GateResult("REJECTED", ("HOLD_SIGNAL",)),
                            rejection_reasons=("HOLD_SIGNAL",),
                        )
                    )
                    continue
                if self.signal_keys.seen(paper_signal.signal_key):
                    self.processed.mark(pair, timeframe, candle_time)
                    pair_results.append(
                        PairScanResult(
                            pair,
                            timeframe,
                            "SKIPPED",
                            "DUPLICATE_SIGNAL",
                            candle_time,
                            strategy_asset_id=selected.strategy_asset_id,
                            signal_id=paper_signal.signal_id,
                            signal_action=paper_signal.signal_type,
                            feature_vector=feature_trace,
                            regime_result=regime_trace,
                            strategy_selection=selection_trace,
                            trade_eligibility=eligibility,
                            risk_result=GateResult("REJECTED", ("DUPLICATE_SIGNAL",)),
                            rejection_reasons=("DUPLICATE_SIGNAL",),
                        )
                    )
                    continue
                risk_result = self._risk_and_exposure(pair, timeframe, paper_signal)
                if risk_result.status != "APPROVED":
                    self.processed.mark(pair, timeframe, candle_time)
                    pair_results.append(
                        PairScanResult(
                            pair,
                            timeframe,
                            "BLOCKED",
                            risk_result.reasons[0],
                            candle_time,
                            strategy_asset_id=selected.strategy_asset_id,
                            signal_id=paper_signal.signal_id,
                            signal_action=paper_signal.signal_type,
                            feature_vector=feature_trace,
                            regime_result=regime_trace,
                            strategy_selection=selection_trace,
                            trade_eligibility=eligibility,
                            risk_result=risk_result,
                            rejection_reasons=risk_result.reasons,
                        )
                    )
                    continue
                if self.config.dry_run:
                    self.processed.mark(pair, timeframe, candle_time)
                    pair_results.append(
                        PairScanResult(
                            pair,
                            timeframe,
                            "BLOCKED",
                            "DRY_RUN",
                            candle_time,
                            strategy_asset_id=selected.strategy_asset_id,
                            signal_id=paper_signal.signal_id,
                            signal_action=paper_signal.signal_type,
                            feature_vector=feature_trace,
                            regime_result=regime_trace,
                            strategy_selection=selection_trace,
                            trade_eligibility=eligibility,
                            risk_result=GateResult("REJECTED", ("DRY_RUN",)),
                            rejection_reasons=("DRY_RUN",),
                        )
                    )
                    self._append_decision_trace(
                        pair,
                        timeframe,
                        candle_time,
                        "BLOCKED",
                        feature_trace,
                        regime_trace,
                        selection_trace,
                        eligibility,
                        GateResult("REJECTED", ("DRY_RUN",)),
                        paper_signal,
                    )
                    continue
                signals.extend(live_result.signals)
                paper_signals.append(paper_signal)
                approved_executions = tuple(
                    execution for execution in live_result.executions if execution.status in {"filled", "submitted"}
                )
                executions.extend(approved_executions)
                new_positions.extend(live_result.positions)
                self.processed.mark(pair, timeframe, candle_time)
                self.signal_keys.mark(paper_signal.signal_key)
                receipt = approved_executions[-1] if approved_executions else None
                if receipt:
                    paper_orders.append(_paper_order(selected.strategy_asset_id, paper_signal, receipt))
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
                        signal_id=paper_signal.signal_id,
                        signal_action=paper_signal.signal_type,
                        execution_status=receipt.status if receipt else "",
                        order_id=receipt.order_id if receipt else "",
                        feature_vector=feature_trace,
                        regime_result=regime_trace,
                        strategy_selection=selection_trace,
                        trade_eligibility=eligibility,
                        risk_result=risk_result,
                    )
                )
                self._append_decision_trace(
                    pair,
                    timeframe,
                    candle_time,
                    status,
                    feature_trace,
                    regime_trace,
                    selection_trace,
                    eligibility,
                    risk_result,
                    paper_signal,
                    _paper_order(selected.strategy_asset_id, paper_signal, receipt) if receipt else None,
                )

        self.positions.add_many(tuple(new_positions), tuple(paper_signals), price_by_pair_timeframe, conversion_prices)
        candles_loaded += self._load_position_monitor_candles(
            price_by_pair_timeframe,
            candle_by_pair_timeframe,
            candle_history_by_pair_timeframe,
            conversion_prices,
        )
        self.positions.mark_to_market(
            price_by_pair_timeframe,
            candle_by_pair_timeframe,
            candle_history_by_pair_timeframe,
            conversion_prices,
        )
        open_position_records = self.positions.list_open()
        closed_position_records = self.positions.list_closed()
        open_positions = len(open_position_records)
        skip_reasons = dict(Counter(result.reason for result in pair_results if result.reason))
        orders_blocked = sum(result.status in {"BLOCKED", "SKIPPED", "NO_SIGNAL"} for result in pair_results)
        run_payload = {
            "run_id": f"PAPER-SCANNER-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            "mode": "paper-scanner",
            "pairs_loaded": min(len(self.config.pairs), self.config.max_pairs_per_scan),
            "timeframes_loaded": len(self.config.timeframes),
            "pair_timeframes_scanned": len(pair_results),
            "candles_loaded": candles_loaded,
            "new_candles": new_candles,
            "execution_path": self.config.execution_path,
            "orders_blocked": orders_blocked,
            "skip_reasons": skip_reasons,
        }
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
            orders_blocked=orders_blocked,
            open_positions=open_positions,
            execution_path=self.config.execution_path,
            skip_reasons=skip_reasons,
            pair_results=tuple(pair_results),
            paper_scanner_run=run_payload,
            paper_signals=tuple(paper_signals),
            paper_orders=tuple(paper_orders),
            paper_positions=open_position_records,
            closed_paper_positions=closed_position_records,
            signals=tuple(signals),
            executions=tuple(executions),
            positions=tuple(new_positions),
        )

    def _validate_candles(self, pair: str, timeframe: str, rows: list[dict[str, Any]]) -> GateResult:
        if pair not in self.config.pairs:
            return GateResult("NOT_ELIGIBLE", ("PAIR_NOT_ENABLED",))
        if timeframe not in self.config.timeframes:
            return GateResult("NOT_ELIGIBLE", ("TIMEFRAME_NOT_ENABLED",))
        if not rows:
            return GateResult("NOT_ELIGIBLE", ("CANDLE_MISSING",))
        if len(rows) < self.config.candle_lookback:
            return GateResult("NOT_ELIGIBLE", ("INSUFFICIENT_LOOKBACK",))
        latest = rows[-1]
        candle_time = _iso(latest["time"])
        if not bool(latest.get("is_complete", True)):
            return GateResult("NOT_ELIGIBLE", ("CANDLE_NOT_CLOSED",))
        if self.processed.seen(pair, timeframe, candle_time):
            return GateResult("NOT_ELIGIBLE", ("CANDLE_ALREADY_PROCESSED",))
        last_processed = self.processed.last_processed_time(pair, timeframe)
        if last_processed and candle_time <= last_processed:
            return GateResult("NOT_ELIGIBLE", ("CANDLE_NOT_NEWER_THAN_LAST_PROCESSED",))
        if _has_major_gap(rows, timeframe):
            return GateResult("NOT_ELIGIBLE", ("RECENT_LOOKBACK_GAP",))
        return GateResult("ELIGIBLE")

    def _load_position_monitor_candles(
        self,
        price_by_pair_timeframe: dict[str, float],
        candle_by_pair_timeframe: dict[str, dict[str, Any]],
        candle_history_by_pair_timeframe: dict[str, list[dict[str, Any]]],
        conversion_prices: dict[str, float],
    ) -> int:
        candles_loaded = 0
        open_pairs = sorted(
            {
                str(position.get("pair") or position.get("instrument") or "")
                for position in self.positions.list_open()
                if position.get("pair") or position.get("instrument")
            }
        )
        for pair in open_pairs:
            rows = self.candles.load_latest(
                pair,
                "M1",
                complete_only=True,
                limit=max(180, self.config.candle_lookback),
            )
            candles_loaded += len(rows)
            if not rows:
                continue
            key = _pair_timeframe_key(pair, "M1")
            price_by_pair_timeframe[key] = _candle_close(rows[-1])
            conversion_prices[pair] = _candle_close(rows[-1])
            candle_by_pair_timeframe[key] = rows[-1]
            candle_history_by_pair_timeframe[key] = rows
        return candles_loaded

    def _trade_eligibility(
        self,
        pair: str,
        timeframe: str,
        candle_time: str,
        selected: ApprovedStrategyAsset,
    ) -> GateResult:
        reasons: list[str] = []
        if pair not in self.config.pairs:
            reasons.append("PAIR_NOT_ENABLED")
        if timeframe not in self.config.timeframes:
            reasons.append("TIMEFRAME_NOT_ENABLED")
        if selected.pair != pair or selected.timeframe != timeframe:
            reasons.append("STRATEGY_PAIR_TIMEFRAME_MISMATCH")
        if self.positions.has_open(pair, timeframe):
            reasons.append("CONFLICTING_PAPER_POSITION")
        if self.config.execution_path != "OANDA_PAPER":
            reasons.append("BROKER_PRACTICE_CONNECTION_NOT_ALLOWED")
        if not candle_time:
            reasons.append("CANDLE_TIME_MISSING")
        return GateResult("NOT_ELIGIBLE" if reasons else "ELIGIBLE", tuple(reasons))

    def _risk_and_exposure(self, pair: str, timeframe: str, signal: PaperSignalRecord) -> GateResult:
        reasons: list[str] = []
        open_positions = self.positions.list_open()
        if len(open_positions) >= self.config.max_open_positions:
            reasons.append("MAX_OPEN_POSITIONS_EXCEEDED")
        if self.positions.has_open(pair, timeframe):
            reasons.append("PAIR_EXPOSURE_ALREADY_OPEN")
        if self.signal_keys.seen(signal.signal_key):
            reasons.append("DUPLICATE_ORDER_FOR_CANDLE_STRATEGY")
        if signal.signal_type not in {"BUY", "SELL", "EXIT"}:
            reasons.append("NO_ACTIONABLE_SIGNAL")
        return GateResult("REJECTED" if reasons else "APPROVED", tuple(reasons))

    def _append_decision_trace(
        self,
        pair: str,
        timeframe: str,
        candle_time: str,
        status: str,
        feature: PaperFeatureVector | None,
        regime: PaperRegimeResult | None,
        selection: StrategyAssetSelectionResult | None,
        eligibility: GateResult | None = None,
        risk: GateResult | None = None,
        signal: PaperSignalRecord | None = None,
        order: PaperOrderRecord | None = None,
    ) -> None:
        self.decisions.append(
            {
                "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "pair": pair,
                "timeframe": timeframe,
                "candle_time": candle_time,
                "status": status,
                "feature_vector": asdict(feature) if feature else {},
                "regime_result": asdict(regime) if regime else {},
                "strategy_selection": asdict(selection) if selection else {},
                "trade_eligibility": asdict(eligibility) if eligibility else {},
                "risk_result": asdict(risk) if risk else {},
                "signal": asdict(signal) if signal else {},
                "order": asdict(order) if order else {},
            }
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
            orders_blocked=1,
            open_positions=len(self.positions.list_open()),
            execution_path=self.config.execution_path,
            skip_reasons={reason: 1},
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
        max_open_positions=int(payload.get("max_open_positions", 30)),
        max_trades_per_day=int(payload.get("max_trades_per_day", 60)),
        dry_run=bool(payload.get("dry_run", False)),
    )


def default_paper_scanner_config_file() -> Path:
    return _repo_root() / "config" / "paper_scanner.json"


def default_processed_candles_file() -> Path:
    return _repo_root() / "var" / "paper_scanner_processed_candles.json"


def default_processed_signals_file() -> Path:
    return _repo_root() / "var" / "paper_scanner_processed_signals.json"


def default_paper_positions_file() -> Path:
    return _repo_root() / "var" / "paper_positions.json"


def default_decision_trace_file() -> Path:
    return _repo_root() / "var" / "paper_scanner_decision_traces.jsonl"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat()
    text = str(value)
    try:
        timestamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC).isoformat()


def _pair_timeframe_key(pair: str, timeframe: str) -> str:
    return f"{pair}:{timeframe}"


def _signal_for_position(position: PositionSnapshot, signals: tuple[PaperSignalRecord, ...]) -> PaperSignalRecord | None:
    position_id = str(position.position_id).lower()
    for signal in signals:
        signal_order_id = f"pos_paper_{signal.signal_id.lower().replace(':', '_')}"
        if position_id == signal_order_id:
            return signal
    matching_strategy = [
        signal
        for signal in signals
        if signal.pair == position.instrument and signal.strategy_asset_id == position.strategy_id
    ]
    if len(matching_strategy) == 1:
        return matching_strategy[0]
    matching_pair = [signal for signal in signals if signal.pair == position.instrument]
    return matching_pair[0] if len(matching_pair) == 1 else None


def _safe_key(value: str) -> str:
    return value.replace(":", "").replace("+", "p").replace("-", "").replace(".", "")


def _candle_close(row: dict[str, Any]) -> float:
    return _float_or_zero(row.get("close_price") or row.get("mid_c") or row.get("close"))


def _float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _enrich_open_position(position: dict[str, Any], updated_at: str) -> bool:
    changed = False
    pair = str(position.get("pair") or position.get("instrument") or "")
    if pair and not position.get("pair"):
        position["pair"] = pair
        changed = True
    if pair and not position.get("instrument"):
        position["instrument"] = pair
        changed = True

    for target, fallback in (
        ("strategy_asset_id", "strategy_id"),
        ("source_signal_id", "signal_id"),
        ("entry_time", "opened_at"),
        ("created_at", "opened_at"),
    ):
        if not position.get(target) and position.get(fallback):
            position[target] = position[fallback]
            changed = True

    source_candle_time = str(position.get("source_candle_time") or "")
    if source_candle_time:
        normalized_source_time = _iso(source_candle_time)
        for target in ("entry_time", "opened_at"):
            if position.get(target) != normalized_source_time:
                position[target] = normalized_source_time
                changed = True

    direction = _infer_position_direction(position)
    if direction and position.get("direction") != direction:
        position["direction"] = direction
        changed = True

    close_price = _first_positive_price(position, "close_price", "current_price", "entry_price", "open_price")
    if close_price > 0:
        for target in ("close_price", "current_price"):
            if _float_or_zero(position.get(target)) <= 0:
                position[target] = close_price
                changed = True

    entry_price = _first_positive_price(position, "entry_price", "open_price")
    if entry_price <= 0:
        entry_price = _reconstruct_entry_price(position, close_price, direction)
    if entry_price > 0:
        for target in ("entry_price", "open_price"):
            if _float_or_zero(position.get(target)) <= 0:
                position[target] = entry_price
                changed = True

    if entry_price > 0:
        take_profit, stop_loss = _default_exit_prices(entry_price, direction)
        for target, value in (("take_profit", take_profit), ("stop_loss", stop_loss)):
            if value is not None and _float_or_zero(position.get(target)) <= 0:
                position[target] = value
                changed = True

    if changed:
        position["updated_at"] = updated_at
    return changed


def _infer_position_direction(position: dict[str, Any]) -> str:
    direction = str(position.get("direction") or "").upper()
    if direction in {"BUY", "SELL"}:
        return direction
    units = _float_or_zero(position.get("units"))
    if units > 0:
        return "BUY"
    if units < 0:
        return "SELL"
    return ""


def _first_positive_price(position: dict[str, Any], *keys: str) -> float:
    for key in keys:
        value = _float_or_zero(position.get(key))
        if value > 0:
            return value
    return 0.0


def _reconstruct_entry_price(position: dict[str, Any], close_price: float, direction: str) -> float:
    if close_price <= 0:
        return 0.0
    pair = str(position.get("pair") or position.get("instrument") or "")
    units = _effective_pl_units(pair, _float_or_zero(position.get("units")))
    floating_pl = _float_or_zero(position.get("p_l") or position.get("floating_pl"))
    if units <= 0 or floating_pl == 0 or direction not in {"BUY", "SELL"}:
        return close_price
    price_delta = floating_pl / units
    if direction == "SELL":
        return round(close_price + price_delta, 8)
    return round(close_price - price_delta, 8)


def _default_exit_prices(entry_price: float, direction: str) -> tuple[float | None, float | None]:
    if entry_price <= 0:
        return None, None
    normalized = direction.upper()
    if normalized == "SELL":
        return round(entry_price * 0.9980, 8), round(entry_price * 1.0010, 8)
    return round(entry_price * 1.0020, 8), round(entry_price * 0.9990, 8)


def _position_pl_quote_currency(
    entry_price: float,
    close_price: float,
    units: float,
    direction: str,
    *,
    pair: str = "",
    fallback: float = 0.0,
) -> float:
    if entry_price <= 0 or close_price <= 0 or units == 0:
        return round(fallback, 4)
    multiplier = -1.0 if direction.upper() == "SELL" else 1.0
    return round((close_price - entry_price) * _effective_pl_units(pair, units) * multiplier, 4)


def _position_pl_account_currency(
    pair: str,
    entry_price: float,
    close_price: float,
    units: float,
    direction: str,
    *,
    conversion_prices: dict[str, float] | None = None,
    fallback: float = 0.0,
) -> float:
    quote_pl = _position_pl_quote_currency(entry_price, close_price, units, direction, pair=pair, fallback=fallback)
    conversion_rate = _quote_to_usd_rate(pair, close_price, conversion_prices or {})
    return round(quote_pl * conversion_rate, 4)


def _normalize_position_pl(position: dict[str, Any], *, conversion_prices: dict[str, float] | None = None) -> bool:
    if position.get("p_l_currency") == "USD" and position.get("p_l_account_currency") is not None:
        return False
    pair = str(position.get("pair") or position.get("instrument") or "")
    entry_price = _float_or_zero(position.get("entry_price") or position.get("open_price"))
    close_price = _float_or_zero(position.get("close_price") or position.get("current_price"))
    units = _float_or_zero(position.get("units"))
    direction = str(position.get("direction") or "")
    if pair == "" or entry_price <= 0 or close_price <= 0 or units == 0:
        return False
    quote_pl = _position_pl_quote_currency(entry_price, close_price, units, direction)
    account_pl = _position_pl_account_currency(
        pair,
        entry_price,
        close_price,
        units,
        direction,
        conversion_prices=conversion_prices,
    )
    position["p_l_quote_currency"] = quote_pl
    position["p_l_account_currency"] = account_pl
    position["p_l_currency"] = "USD"
    position["floating_pl"] = account_pl
    position["p_l"] = account_pl
    return True


def _quote_to_usd_rate(pair: str, close_price: float, conversion_prices: dict[str, float]) -> float:
    base, quote = _split_pair(pair)
    if quote in {"", "USD"}:
        return 1.0
    direct = conversion_prices.get(f"{quote}_USD")
    if direct and direct > 0:
        return direct
    inverse = conversion_prices.get(f"USD_{quote}")
    if inverse and inverse > 0:
        return 1.0 / inverse
    if base == "USD" and close_price > 0:
        return 1.0 / close_price
    return 1.0


def _effective_pl_units(pair: str, units: float) -> float:
    if _normalized_pair(pair) in {"NAS100_USD", "SPX500_USD"}:
        return abs(units) / 10_000.0
    return abs(units)


def _normalized_pair(pair: str) -> str:
    return pair.replace("/", "_").upper()


def _paper_position_monitor_timeframe(position: dict[str, Any]) -> str:
    return "M1"


def _split_pair(pair: str) -> tuple[str, str]:
    normalized = pair.replace("/", "_").upper()
    parts = normalized.split("_")
    if len(parts) >= 2:
        return parts[0], parts[1]
    if len(normalized) == 6:
        return normalized[:3], normalized[3:]
    return normalized, ""


def _exit_price_for_candle(position: dict[str, Any], candle: dict[str, Any]) -> tuple[float | None, str]:
    candle_time = candle.get("time")
    source_time = position.get("source_candle_time") or position.get("entry_time") or position.get("opened_at")
    if candle_time and source_time and _coerce_datetime(candle_time) <= _coerce_datetime(source_time):
        return None, ""
    direction = str(position.get("direction") or "").upper()
    stop_loss = _float_or_zero(position.get("stop_loss"))
    take_profit = _float_or_zero(position.get("take_profit"))
    high = _float_or_zero(candle.get("high_price") or candle.get("mid_h") or candle.get("high"))
    low = _float_or_zero(candle.get("low_price") or candle.get("mid_l") or candle.get("low"))
    if high <= 0 or low <= 0 or stop_loss <= 0 or take_profit <= 0:
        return None, ""
    if direction == "SELL":
        if high >= stop_loss:
            return stop_loss, "STOP_LOSS"
        if low <= take_profit:
            return take_profit, "TAKE_PROFIT"
    else:
        if low <= stop_loss:
            return stop_loss, "STOP_LOSS"
        if high >= take_profit:
            return take_profit, "TAKE_PROFIT"
    return None, ""


def _exit_price_for_candles(
    position: dict[str, Any],
    candles: list[dict[str, Any]],
) -> tuple[float | None, str, dict[str, Any]]:
    ordered = sorted(
        (candle for candle in candles if candle and candle.get("time")),
        key=lambda item: _coerce_datetime(item.get("time")),
    )
    for candle in ordered:
        exit_price, exit_reason = _exit_price_for_candle(position, candle)
        if exit_price is not None:
            return exit_price, exit_reason, candle
    return None, "", {}


def _paper_signal(
    strategy_asset_id: str,
    signal: TradingSignal,
    candle_time: str,
    feature: PaperFeatureVector,
    regime: PaperRegimeResult,
) -> PaperSignalRecord:
    signal_type = signal.action.value
    key = f"{strategy_asset_id}:{signal.instrument}:{signal.feature_vector.timeframe}:{candle_time}:{signal_type}"
    return PaperSignalRecord(
        signal_id=signal.signal_id,
        strategy_asset_id=strategy_asset_id,
        pair=signal.instrument,
        timeframe=signal.feature_vector.timeframe,
        candle_time=candle_time,
        signal_type=signal_type,
        confidence=regime.confidence,
        reason_codes=(signal.reason,),
        feature_vector_id=feature.feature_vector_id,
        signal_key=key,
    )


def _paper_order(strategy_asset_id: str, signal: PaperSignalRecord, receipt: ExecutionReceipt) -> PaperOrderRecord:
    return PaperOrderRecord(
        order_id=receipt.order_id,
        signal_id=signal.signal_id,
        strategy_asset_id=strategy_asset_id,
        pair=signal.pair,
        timeframe=signal.timeframe,
        candle_time=signal.candle_time,
        status=receipt.status,
        execution_path=receipt.broker,
        units=float(receipt.payload.get("units", 0) or 0),
    )


def _has_major_gap(rows: list[dict[str, Any]], timeframe: str) -> bool:
    expected = _timeframe_delta(timeframe)
    if expected is None or len(rows) < 2:
        return False
    for previous, current in zip(rows, rows[1:]):
        previous_time = _coerce_datetime(previous["time"])
        current_time = _coerce_datetime(current["time"])
        if current_time - previous_time > expected * 2:
            return True
    return False


def _timeframe_delta(timeframe: str) -> timedelta | None:
    value = timeframe.upper()
    if value.endswith("M") and value[:-1].isdigit():
        return timedelta(minutes=int(value[:-1]))
    if value.endswith("H") and value[:-1].isdigit():
        return timedelta(hours=int(value[:-1]))
    if value.startswith("M") and value[1:].isdigit():
        return timedelta(minutes=int(value[1:]))
    if value.startswith("H") and value[1:].isdigit():
        return timedelta(hours=int(value[1:]))
    return None


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        timestamp = value
    else:
        timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC)
