from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any


class PortfolioIntelligenceStatus(StrEnum):
    READY = "READY"
    WATCH = "WATCH"
    REBALANCE_REQUIRED = "REBALANCE_REQUIRED"
    PAUSED = "PAUSED"


class PortfolioLifecycleStage(StrEnum):
    CANDIDATE = "CANDIDATE"
    PAPER = "PAPER"
    PRODUCTION_READY = "PRODUCTION_READY"
    DEGRADED = "DEGRADED"
    RETIRED = "RETIRED"


@dataclass(frozen=True, slots=True)
class PortfolioStrategyInput:
    strategy_asset_id: str
    family: str
    instrument: str
    timeframe: str
    market_regime: str
    target_weight: float
    validation_profit_factor: float
    validation_drawdown: float
    live_profit_factor: float
    live_drawdown: float
    confidence: float
    recent_trades: int
    average_slippage_pips: float = 0.2


@dataclass(frozen=True, slots=True)
class PortfolioPolicy:
    max_strategy_weight: float = 0.16
    max_instrument_weight: float = 0.28
    max_family_weight: float = 0.35
    max_average_correlation: float = 0.38
    max_profit_factor_drift: float = 0.18
    max_drawdown_drift: float = 0.35
    min_production_strategies: int = 6
    min_family_count: int = 3
    min_regime_count: int = 3


@dataclass(frozen=True, slots=True)
class PortfolioHealth:
    status: PortfolioIntelligenceStatus
    score: int
    checks: dict[str, str]
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PortfolioCorrelationProfile:
    average_correlation: float
    matrix: tuple[tuple[float, ...], ...]
    labels: tuple[str, ...]
    clusters: dict[str, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class PortfolioAllocationDecision:
    approved: bool
    target_weights: dict[str, float]
    instrument_exposure: dict[str, float]
    family_exposure: dict[str, float]
    rebalance_actions: tuple[str, ...]
    trace_id: str


@dataclass(frozen=True, slots=True)
class PortfolioDriftReport:
    status: PortfolioIntelligenceStatus
    profit_factor_drift: dict[str, float]
    drawdown_drift: dict[str, float]
    degraded_strategies: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PortfolioStressResult:
    passed: bool
    scenarios: dict[str, dict[str, float | str]]
    worst_expected_drawdown: float
    capital_at_risk: float


@dataclass(frozen=True, slots=True)
class PortfolioKpis:
    strategy_count: int
    family_count: int
    instrument_count: int
    regime_count: int
    expected_profit_factor: float
    expected_drawdown: float
    average_confidence: float
    average_slippage_pips: float


@dataclass(frozen=True, slots=True)
class DailyPortfolioReview:
    review_id: str
    trading_day: str
    status: PortfolioIntelligenceStatus
    decisions: tuple[str, ...]
    watchlist: tuple[str, ...]
    next_actions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AllocationDecisionTrace:
    trace_id: str
    timestamp: datetime
    inputs: dict[str, Any]
    policy_checks: dict[str, str]
    decision: str
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PortfolioLifecycleState:
    portfolio_id: str
    stage: PortfolioLifecycleStage
    status: PortfolioIntelligenceStatus
    promotion_ready: bool
    retirement_candidates: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PortfolioAcceptanceCriteria:
    accepted: bool
    criteria: dict[str, str]
    missing: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PortfolioIntelligenceSnapshot:
    portfolio_id: str
    policy: PortfolioPolicy
    health: PortfolioHealth
    correlation: PortfolioCorrelationProfile
    allocation: PortfolioAllocationDecision
    drift: PortfolioDriftReport
    stress: PortfolioStressResult
    kpis: PortfolioKpis
    daily_review: DailyPortfolioReview
    decision_trace: AllocationDecisionTrace
    lifecycle: PortfolioLifecycleState
    acceptance: PortfolioAcceptanceCriteria
    timestamp: datetime

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["health"]["status"] = self.health.status.value
        payload["drift"]["status"] = self.drift.status.value
        payload["daily_review"]["status"] = self.daily_review.status.value
        payload["decision_trace"]["timestamp"] = self.decision_trace.timestamp.isoformat()
        payload["lifecycle"]["stage"] = self.lifecycle.stage.value
        payload["lifecycle"]["status"] = self.lifecycle.status.value
        payload["timestamp"] = self.timestamp.isoformat()
        return payload


class PortfolioIntelligenceEngine:
    def analyze(
        self,
        strategies: tuple[PortfolioStrategyInput, ...],
        *,
        portfolio_id: str = "QF-PORT-INTEL-001",
        policy: PortfolioPolicy | None = None,
        trading_day: date | None = None,
    ) -> PortfolioIntelligenceSnapshot:
        policy = policy or PortfolioPolicy()
        trading_day = trading_day or datetime.now(UTC).date()
        timestamp = datetime.now(UTC)
        normalized = self._normalize_weights(strategies)
        correlation = self._correlation(normalized)
        drift = self._drift(normalized, policy)
        allocation = self._allocation(normalized, policy, correlation, drift, timestamp)
        kpis = self._kpis(normalized)
        stress = self._stress(kpis, correlation)
        health = self._health(normalized, policy, correlation, allocation, drift, stress, kpis)
        trace = AllocationDecisionTrace(
            trace_id=allocation.trace_id,
            timestamp=timestamp,
            inputs={
                "portfolio_id": portfolio_id,
                "strategy_count": len(normalized),
                "total_weight": round(sum(item.target_weight for item in normalized), 4),
                "average_correlation": correlation.average_correlation,
            },
            policy_checks=health.checks,
            decision=health.status.value,
            evidence=tuple(health.reasons) or ("Portfolio accepted by all intelligence checks.",),
        )
        lifecycle = self._lifecycle(portfolio_id, health, drift)
        acceptance = self._acceptance(normalized, policy, health, stress)
        review = self._daily_review(portfolio_id, trading_day, health, drift, allocation)
        return PortfolioIntelligenceSnapshot(
            portfolio_id=portfolio_id,
            policy=policy,
            health=health,
            correlation=correlation,
            allocation=allocation,
            drift=drift,
            stress=stress,
            kpis=kpis,
            daily_review=review,
            decision_trace=trace,
            lifecycle=lifecycle,
            acceptance=acceptance,
            timestamp=timestamp,
        )

    def _normalize_weights(
        self, strategies: tuple[PortfolioStrategyInput, ...]
    ) -> tuple[PortfolioStrategyInput, ...]:
        total = sum(max(item.target_weight, 0.0) for item in strategies)
        if total <= 0:
            return strategies
        return tuple(
            PortfolioStrategyInput(
                **{
                    **asdict(item),
                    "target_weight": round(max(item.target_weight, 0.0) / total, 4),
                }
            )
            for item in strategies
        )

    def _correlation(
        self, strategies: tuple[PortfolioStrategyInput, ...]
    ) -> PortfolioCorrelationProfile:
        labels = tuple(item.strategy_asset_id for item in strategies)
        rows: list[tuple[float, ...]] = []
        total = 0.0
        pairs = 0
        for left in strategies:
            row: list[float] = []
            for right in strategies:
                value = 1.0 if left.strategy_asset_id == right.strategy_asset_id else self._pair_correlation(left, right)
                row.append(value)
                if left.strategy_asset_id < right.strategy_asset_id:
                    total += value
                    pairs += 1
            rows.append(tuple(row))
        clusters: dict[str, tuple[str, ...]] = {}
        for item in strategies:
            key = f"{item.family}:{item.market_regime}"
            clusters[key] = (*clusters.get(key, ()), item.strategy_asset_id)
        return PortfolioCorrelationProfile(
            average_correlation=round(total / pairs, 4) if pairs else 0.0,
            matrix=tuple(rows),
            labels=labels,
            clusters=clusters,
        )

    def _pair_correlation(self, left: PortfolioStrategyInput, right: PortfolioStrategyInput) -> float:
        score = 0.08
        if left.family == right.family:
            score += 0.22
        if left.instrument == right.instrument:
            score += 0.18
        if left.timeframe == right.timeframe:
            score += 0.08
        if left.market_regime == right.market_regime:
            score += 0.10
        return round(min(score, 0.88), 4)

    def _allocation(
        self,
        strategies: tuple[PortfolioStrategyInput, ...],
        policy: PortfolioPolicy,
        correlation: PortfolioCorrelationProfile,
        drift: PortfolioDriftReport,
        timestamp: datetime,
    ) -> PortfolioAllocationDecision:
        target_weights = {item.strategy_asset_id: item.target_weight for item in strategies}
        instrument_exposure = self._exposure(strategies, "instrument")
        family_exposure = self._exposure(strategies, "family")
        actions: list[str] = []
        for item in strategies:
            if item.target_weight > policy.max_strategy_weight:
                actions.append(f"Reduce {item.strategy_asset_id} below {policy.max_strategy_weight:.0%}.")
        for instrument, weight in instrument_exposure.items():
            if weight > policy.max_instrument_weight:
                actions.append(f"Trim {instrument} exposure from {weight:.0%}.")
        for family, weight in family_exposure.items():
            if weight > policy.max_family_weight:
                actions.append(f"Diversify {family} family exposure from {weight:.0%}.")
        if correlation.average_correlation > policy.max_average_correlation:
            actions.append("Reduce clustered strategies until average correlation is acceptable.")
        for strategy_id in drift.degraded_strategies:
            actions.append(f"Move {strategy_id} to watchlist until drift normalizes.")
        return PortfolioAllocationDecision(
            approved=not actions,
            target_weights=target_weights,
            instrument_exposure=instrument_exposure,
            family_exposure=family_exposure,
            rebalance_actions=tuple(actions),
            trace_id=f"ALLOC-{timestamp:%Y%m%d%H%M%S}",
        )

    def _drift(
        self, strategies: tuple[PortfolioStrategyInput, ...], policy: PortfolioPolicy
    ) -> PortfolioDriftReport:
        pf_drift: dict[str, float] = {}
        dd_drift: dict[str, float] = {}
        degraded: list[str] = []
        reasons: list[str] = []
        for item in strategies:
            pf_gap = max(item.validation_profit_factor - item.live_profit_factor, 0.0)
            pf_ratio = pf_gap / max(item.validation_profit_factor, 0.01)
            dd_gap = max(item.live_drawdown - item.validation_drawdown, 0.0)
            dd_ratio = dd_gap / max(item.validation_drawdown, 0.01)
            pf_drift[item.strategy_asset_id] = round(pf_ratio, 4)
            dd_drift[item.strategy_asset_id] = round(dd_ratio, 4)
            if pf_ratio > policy.max_profit_factor_drift or dd_ratio > policy.max_drawdown_drift:
                degraded.append(item.strategy_asset_id)
                reasons.append(f"{item.strategy_asset_id} live behavior has drifted from validation evidence.")
        status = PortfolioIntelligenceStatus.REBALANCE_REQUIRED if degraded else PortfolioIntelligenceStatus.READY
        return PortfolioDriftReport(status, pf_drift, dd_drift, tuple(degraded), tuple(reasons))

    def _stress(self, kpis: PortfolioKpis, correlation: PortfolioCorrelationProfile) -> PortfolioStressResult:
        correlation_penalty = max(correlation.average_correlation - 0.25, 0.0)
        scenarios = {
            "spread_shock": {"drawdown": round(kpis.expected_drawdown + 0.012, 4), "status": "PASS"},
            "correlation_spike": {
                "drawdown": round(kpis.expected_drawdown + correlation_penalty + 0.018, 4),
                "status": "PASS" if correlation.average_correlation <= 0.38 else "WATCH",
            },
            "three_loss_days": {"drawdown": round(kpis.expected_drawdown + 0.025, 4), "status": "PASS"},
        }
        worst = max(float(item["drawdown"]) for item in scenarios.values())
        return PortfolioStressResult(
            passed=worst <= 0.12,
            scenarios=scenarios,
            worst_expected_drawdown=round(worst, 4),
            capital_at_risk=round(worst * 100_000, 2),
        )

    def _kpis(self, strategies: tuple[PortfolioStrategyInput, ...]) -> PortfolioKpis:
        if not strategies:
            return PortfolioKpis(0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0)
        return PortfolioKpis(
            strategy_count=len(strategies),
            family_count=len({item.family for item in strategies}),
            instrument_count=len({item.instrument for item in strategies}),
            regime_count=len({item.market_regime for item in strategies}),
            expected_profit_factor=round(sum(item.validation_profit_factor * item.target_weight for item in strategies), 4),
            expected_drawdown=round(sum(item.validation_drawdown * item.target_weight for item in strategies), 4),
            average_confidence=round(sum(item.confidence for item in strategies) / len(strategies), 4),
            average_slippage_pips=round(sum(item.average_slippage_pips for item in strategies) / len(strategies), 4),
        )

    def _health(
        self,
        strategies: tuple[PortfolioStrategyInput, ...],
        policy: PortfolioPolicy,
        correlation: PortfolioCorrelationProfile,
        allocation: PortfolioAllocationDecision,
        drift: PortfolioDriftReport,
        stress: PortfolioStressResult,
        kpis: PortfolioKpis,
    ) -> PortfolioHealth:
        checks = {
            "strategy_count": "PASS" if len(strategies) >= policy.min_production_strategies else "FAIL",
            "family_diversity": "PASS" if kpis.family_count >= policy.min_family_count else "FAIL",
            "regime_coverage": "PASS" if kpis.regime_count >= policy.min_regime_count else "FAIL",
            "correlation": "PASS" if correlation.average_correlation <= policy.max_average_correlation else "FAIL",
            "allocation": "PASS" if allocation.approved else "FAIL",
            "drift": "PASS" if not drift.degraded_strategies else "FAIL",
            "stress": "PASS" if stress.passed else "FAIL",
        }
        reasons = tuple(f"{name} check failed." for name, result in checks.items() if result == "FAIL")
        if not reasons:
            return PortfolioHealth(PortfolioIntelligenceStatus.READY, 96, checks, ())
        if checks["stress"] == "FAIL" or checks["strategy_count"] == "FAIL":
            status = PortfolioIntelligenceStatus.PAUSED
        elif checks["allocation"] == "FAIL" or checks["drift"] == "FAIL":
            status = PortfolioIntelligenceStatus.REBALANCE_REQUIRED
        else:
            status = PortfolioIntelligenceStatus.WATCH
        score = max(35, 96 - (len(reasons) * 9))
        return PortfolioHealth(status, score, checks, reasons)

    def _daily_review(
        self,
        portfolio_id: str,
        trading_day: date,
        health: PortfolioHealth,
        drift: PortfolioDriftReport,
        allocation: PortfolioAllocationDecision,
    ) -> DailyPortfolioReview:
        decisions = (
            ("Portfolio can trade under current allocation.",)
            if health.status == PortfolioIntelligenceStatus.READY
            else ("Portfolio requires review before increasing exposure.",)
        )
        next_actions = allocation.rebalance_actions or ("Continue daily drift and exposure monitoring.",)
        return DailyPortfolioReview(
            review_id=f"PORT-REVIEW-{trading_day:%Y%m%d}",
            trading_day=trading_day.isoformat(),
            status=health.status,
            decisions=decisions,
            watchlist=drift.degraded_strategies,
            next_actions=next_actions,
        )

    def _lifecycle(
        self, portfolio_id: str, health: PortfolioHealth, drift: PortfolioDriftReport
    ) -> PortfolioLifecycleState:
        if health.status == PortfolioIntelligenceStatus.READY:
            stage = PortfolioLifecycleStage.PRODUCTION_READY
        elif drift.degraded_strategies:
            stage = PortfolioLifecycleStage.DEGRADED
        elif health.status == PortfolioIntelligenceStatus.PAUSED:
            stage = PortfolioLifecycleStage.CANDIDATE
        else:
            stage = PortfolioLifecycleStage.PAPER
        return PortfolioLifecycleState(
            portfolio_id=portfolio_id,
            stage=stage,
            status=health.status,
            promotion_ready=stage == PortfolioLifecycleStage.PRODUCTION_READY,
            retirement_candidates=drift.degraded_strategies,
        )

    def _acceptance(
        self,
        strategies: tuple[PortfolioStrategyInput, ...],
        policy: PortfolioPolicy,
        health: PortfolioHealth,
        stress: PortfolioStressResult,
    ) -> PortfolioAcceptanceCriteria:
        criteria = {
            "policy_defined": "PASS",
            "minimum_strategy_count": "PASS" if len(strategies) >= policy.min_production_strategies else "FAIL",
            "daily_review_generated": "PASS",
            "allocation_trace_present": "PASS",
            "stress_tests_pass": "PASS" if stress.passed else "FAIL",
            "portfolio_ready": "PASS" if health.status == PortfolioIntelligenceStatus.READY else "FAIL",
        }
        missing = tuple(name for name, result in criteria.items() if result == "FAIL")
        return PortfolioAcceptanceCriteria(not missing, criteria, missing)

    def _exposure(
        self, strategies: tuple[PortfolioStrategyInput, ...], field_name: str
    ) -> dict[str, float]:
        exposure: dict[str, float] = {}
        for item in strategies:
            key = str(getattr(item, field_name))
            exposure[key] = round(exposure.get(key, 0.0) + item.target_weight, 4)
        return exposure


def demo_portfolio_strategy_inputs() -> tuple[PortfolioStrategyInput, ...]:
    return (
        PortfolioStrategyInput("QF-PI-001", "trend", "EUR_USD", "M15", "trending", 0.11, 2.30, 0.052, 2.16, 0.057, 0.94, 42),
        PortfolioStrategyInput("QF-PI-002", "mean_reversion", "GBP_USD", "M15", "ranging", 0.10, 2.08, 0.061, 2.01, 0.063, 0.91, 38),
        PortfolioStrategyInput("QF-PI-003", "breakout", "USD_JPY", "H1", "breakout", 0.10, 2.24, 0.058, 2.19, 0.060, 0.93, 35),
        PortfolioStrategyInput("QF-PI-004", "momentum", "AUD_USD", "M15", "trending", 0.09, 2.18, 0.055, 2.05, 0.060, 0.92, 31),
        PortfolioStrategyInput("QF-PI-005", "volatility", "EUR_JPY", "H1", "volatile", 0.09, 2.12, 0.066, 2.00, 0.071, 0.90, 27),
        PortfolioStrategyInput("QF-PI-006", "trend", "GBP_JPY", "H4", "trending", 0.08, 2.36, 0.049, 2.24, 0.052, 0.95, 24),
        PortfolioStrategyInput("QF-PI-007", "breakout", "NZD_USD", "M15", "breakout", 0.08, 2.05, 0.060, 1.99, 0.061, 0.90, 29),
        PortfolioStrategyInput("QF-PI-008", "mean_reversion", "USD_CAD", "H1", "ranging", 0.07, 2.14, 0.057, 2.03, 0.060, 0.91, 22),
    )
