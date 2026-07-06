from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any


class EvolutionAction(StrEnum):
    INCREASE_ALLOCATION = "INCREASE_ALLOCATION"
    REDUCE_ALLOCATION = "REDUCE_ALLOCATION"
    SUSPEND = "SUSPEND"
    RETIRE = "RETIRE"
    REOPTIMIZE = "REOPTIMIZE"
    RETURN_TO_RESEARCH = "RETURN_TO_RESEARCH"
    MAINTAIN = "MAINTAIN"


@dataclass(frozen=True, slots=True)
class TradePerformanceInput:
    trade_id: str
    strategy_id: str
    strategy_family: str
    instrument: str
    session: str
    market_regime: str
    features: tuple[str, ...]
    entry_plugin: str
    exit_plugin: str
    risk_plugin: str
    allocation_decision: str
    profit_loss: float
    risk_used: float
    accepted: bool
    expected_profit: float


@dataclass(frozen=True, slots=True)
class PortfolioDecisionInput:
    decision_id: str
    reason: str
    expected_benefit: float
    actual_benefit: float
    risk_impact: float
    correlation_impact: float
    capital_impact: float


@dataclass(frozen=True, slots=True)
class AttributionRow:
    category: str
    item: str
    contribution: float
    contribution_percent: float
    evidence_count: int


@dataclass(frozen=True, slots=True)
class PerformanceAttribution:
    total_profit_loss: float
    strategy: tuple[AttributionRow, ...]
    session: tuple[AttributionRow, ...]
    market_regime: tuple[AttributionRow, ...]
    currency: tuple[AttributionRow, ...]
    feature: tuple[AttributionRow, ...]
    plugin: tuple[AttributionRow, ...]
    risk: tuple[AttributionRow, ...]
    portfolio_allocation: tuple[AttributionRow, ...]


@dataclass(frozen=True, slots=True)
class ContinuousLearningUpdate:
    knowledge_records_written: int
    feature_rankings: tuple[AttributionRow, ...]
    plugin_rankings: tuple[AttributionRow, ...]
    strategy_rankings: tuple[AttributionRow, ...]
    market_regime_statistics: tuple[AttributionRow, ...]
    session_statistics: tuple[AttributionRow, ...]
    portfolio_statistics: tuple[AttributionRow, ...]
    hypothesis_confidence: dict[str, float]
    knowledge_updates: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResearchPriority:
    priority_id: str
    theme: str
    action: str
    budget_weight: float
    reason: str
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StrategyEvolutionRecommendation:
    strategy_id: str
    action: EvolutionAction
    confidence: float
    reason: str


@dataclass(frozen=True, slots=True)
class PortfolioEvolutionRecommendation:
    decision_id: str
    action: EvolutionAction
    reason: str
    expected_impact: float


@dataclass(frozen=True, slots=True)
class LearningDecisionQualityMetrics:
    decision_accuracy: float
    opportunity_accuracy: float
    trade_acceptance_quality: float
    trade_rejection_quality: float
    risk_decision_quality: float
    portfolio_decision_quality: float


@dataclass(frozen=True, slots=True)
class DailyLearningReport:
    report_id: str
    trading_day: str
    daily_attribution: dict[str, float]
    strategy_contribution: tuple[AttributionRow, ...]
    session_contribution: tuple[AttributionRow, ...]
    feature_contribution: tuple[AttributionRow, ...]
    portfolio_contribution: tuple[AttributionRow, ...]
    knowledge_updates: tuple[str, ...]
    research_recommendations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WeeklyResearchReview:
    review_id: str
    research_effectiveness: float
    strategy_evolution: tuple[StrategyEvolutionRecommendation, ...]
    portfolio_evolution: tuple[PortfolioEvolutionRecommendation, ...]
    knowledge_growth: int
    feature_importance_changes: tuple[str, ...]
    plugin_performance: tuple[AttributionRow, ...]
    operational_observations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MonthlyIntelligenceReview:
    review_id: str
    long_term_trends: tuple[str, ...]
    portfolio_quality: float
    market_regime_evolution: tuple[AttributionRow, ...]
    research_productivity: float
    knowledge_base_maturity: float
    recommendations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PerformanceLearningSnapshot:
    attribution: PerformanceAttribution
    learning: ContinuousLearningUpdate
    research_priorities: tuple[ResearchPriority, ...]
    strategy_evolution: tuple[StrategyEvolutionRecommendation, ...]
    portfolio_evolution: tuple[PortfolioEvolutionRecommendation, ...]
    decision_quality: LearningDecisionQualityMetrics
    daily_report: DailyLearningReport
    weekly_review: WeeklyResearchReview
    monthly_review: MonthlyIntelligenceReview
    timestamp: datetime

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        for row in payload["strategy_evolution"]:
            row["action"] = str(row["action"])
        for row in payload["portfolio_evolution"]:
            row["action"] = str(row["action"])
        for row in payload["weekly_review"]["strategy_evolution"]:
            row["action"] = str(row["action"])
        for row in payload["weekly_review"]["portfolio_evolution"]:
            row["action"] = str(row["action"])
        payload["timestamp"] = self.timestamp.isoformat()
        return payload


class PerformanceLearningEngine:
    def analyze(
        self,
        trades: tuple[TradePerformanceInput, ...],
        portfolio_decisions: tuple[PortfolioDecisionInput, ...],
        *,
        trading_day: date | None = None,
    ) -> PerformanceLearningSnapshot:
        trading_day = trading_day or datetime.now(UTC).date()
        timestamp = datetime.now(UTC)
        attribution = self._attribution(trades)
        learning = self._learning(attribution)
        priorities = self._research_priorities(attribution)
        strategy_evolution = self._strategy_evolution(attribution.strategy)
        portfolio_evolution = self._portfolio_evolution(portfolio_decisions)
        quality = self._decision_quality(trades, portfolio_decisions)
        daily_report = self._daily_report(trading_day, attribution, learning, priorities)
        weekly_review = WeeklyResearchReview(
            review_id=f"LEARNING-WEEK-{trading_day:%Y%W}",
            research_effectiveness=round(_positive_share(attribution.strategy), 4),
            strategy_evolution=strategy_evolution,
            portfolio_evolution=portfolio_evolution,
            knowledge_growth=learning.knowledge_records_written,
            feature_importance_changes=tuple(f"{row.item}: {row.contribution_percent:+.1f}%" for row in learning.feature_rankings[:5]),
            plugin_performance=learning.plugin_rankings,
            operational_observations=(
                "London and overlap sessions remain the strongest learning source.",
                "Risk plugin contribution is positive when volatility filters remain active.",
            ),
        )
        monthly_review = MonthlyIntelligenceReview(
            review_id=f"INTEL-MONTH-{trading_day:%Y%m}",
            long_term_trends=(
                "Trend and volatility evidence remain constructive.",
                "Ranging regime requires more selective mean-reversion research.",
            ),
            portfolio_quality=quality.portfolio_decision_quality,
            market_regime_evolution=attribution.market_regime,
            research_productivity=round(sum(item.budget_weight for item in priorities), 4),
            knowledge_base_maturity=round(min(1.0, learning.knowledge_records_written / 20.0), 4),
            recommendations=tuple(priority.action for priority in priorities),
        )
        return PerformanceLearningSnapshot(
            attribution=attribution,
            learning=learning,
            research_priorities=priorities,
            strategy_evolution=strategy_evolution,
            portfolio_evolution=portfolio_evolution,
            decision_quality=quality,
            daily_report=daily_report,
            weekly_review=weekly_review,
            monthly_review=monthly_review,
            timestamp=timestamp,
        )

    def _attribution(self, trades: tuple[TradePerformanceInput, ...]) -> PerformanceAttribution:
        total = round(sum(trade.profit_loss for trade in trades), 4)
        return PerformanceAttribution(
            total_profit_loss=total,
            strategy=_rows("strategy", _group(trades, lambda trade: trade.strategy_id), total),
            session=_rows("session", _group(trades, lambda trade: trade.session), total),
            market_regime=_rows("market_regime", _group(trades, lambda trade: trade.market_regime), total),
            currency=_rows("currency", _group(trades, lambda trade: trade.instrument.split("_")[0]), total),
            feature=_rows("feature", _multi_group(trades, lambda trade: trade.features), total),
            plugin=_rows(
                "plugin",
                _multi_group(trades, lambda trade: (trade.entry_plugin, trade.exit_plugin, trade.risk_plugin)),
                total,
            ),
            risk=_rows("risk", _group(trades, lambda trade: "efficient_risk" if trade.profit_loss >= trade.risk_used else "inefficient_risk"), total),
            portfolio_allocation=_rows("portfolio_allocation", _group(trades, lambda trade: trade.allocation_decision), total),
        )

    def _learning(self, attribution: PerformanceAttribution) -> ContinuousLearningUpdate:
        updates = (
            "feature_rankings_updated",
            "plugin_rankings_updated",
            "strategy_rankings_updated",
            "regime_statistics_updated",
            "session_statistics_updated",
            "portfolio_statistics_updated",
            "hypothesis_confidence_updated",
        )
        return ContinuousLearningUpdate(
            knowledge_records_written=sum(len(getattr(attribution, field)) for field in (
                "strategy",
                "session",
                "market_regime",
                "feature",
                "plugin",
                "portfolio_allocation",
            )),
            feature_rankings=_positive_first(attribution.feature),
            plugin_rankings=_positive_first(attribution.plugin),
            strategy_rankings=_positive_first(attribution.strategy),
            market_regime_statistics=_positive_first(attribution.market_regime),
            session_statistics=_positive_first(attribution.session),
            portfolio_statistics=_positive_first(attribution.portfolio_allocation),
            hypothesis_confidence={
                "trend_continuation": _confidence(attribution.market_regime, "Trending"),
                "mean_reversion_selectivity": _confidence(attribution.market_regime, "Ranging"),
                "volatility_breakout": _confidence(attribution.feature, "Volatility"),
            },
            knowledge_updates=updates,
        )

    def _research_priorities(self, attribution: PerformanceAttribution) -> tuple[ResearchPriority, ...]:
        priorities: list[ResearchPriority] = []
        regime_map = {row.item: row for row in attribution.market_regime}
        feature_map = {row.item: row for row in attribution.feature}
        if regime_map.get("Ranging", AttributionRow("", "", 0, 0, 0)).contribution < 0:
            priorities.append(
                ResearchPriority(
                    "RP-RANGE-001",
                    "mean_reversion",
                    "Increase ranging-regime mean-reversion research.",
                    0.35,
                    "Ranging regime attribution is negative.",
                    ("ranging_underperformance", "session_filter_review"),
                )
            )
        if feature_map.get("Volatility", AttributionRow("", "", 0, 0, 0)).contribution > 0:
            priorities.append(
                ResearchPriority(
                    "RP-VOL-001",
                    "volatility",
                    "Increase optimization budget for volatility-aware strategies.",
                    0.30,
                    "Volatility feature contribution is positive.",
                    ("volatility_feature_positive", "breakout_templates_active"),
                )
            )
        priorities.append(
            ResearchPriority(
                "RP-PORT-001",
                "portfolio_rotation",
                "Evaluate capital rotation between trend and volatility sleeves.",
                0.20,
                "Portfolio allocation attribution is measurable and positive.",
                ("allocation_decision_trace", "portfolio_attribution"),
            )
        )
        return tuple(priorities)

    def _strategy_evolution(self, rows: tuple[AttributionRow, ...]) -> tuple[StrategyEvolutionRecommendation, ...]:
        recommendations: list[StrategyEvolutionRecommendation] = []
        for row in rows:
            if row.contribution_percent >= 15:
                action = EvolutionAction.INCREASE_ALLOCATION
                reason = "Strategy is a material positive contributor."
            elif row.contribution_percent < 0:
                action = EvolutionAction.REOPTIMIZE
                reason = "Strategy contribution is negative and needs research review."
            else:
                action = EvolutionAction.MAINTAIN
                reason = "Strategy remains useful but not dominant."
            recommendations.append(
                StrategyEvolutionRecommendation(row.item, action, min(abs(row.contribution_percent) / 30, 1.0), reason)
            )
        return tuple(recommendations)

    def _portfolio_evolution(
        self, decisions: tuple[PortfolioDecisionInput, ...]
    ) -> tuple[PortfolioEvolutionRecommendation, ...]:
        recommendations: list[PortfolioEvolutionRecommendation] = []
        for decision in decisions:
            net = decision.actual_benefit - max(decision.risk_impact, 0.0) - max(decision.correlation_impact, 0.0)
            action = EvolutionAction.INCREASE_ALLOCATION if net > 0 else EvolutionAction.REDUCE_ALLOCATION
            recommendations.append(
                PortfolioEvolutionRecommendation(
                    decision.decision_id,
                    action,
                    "Actual benefit exceeded risk and correlation costs." if net > 0 else "Risk or correlation cost exceeded realized benefit.",
                    round(net, 4),
                )
            )
        return tuple(recommendations)

    def _decision_quality(
        self,
        trades: tuple[TradePerformanceInput, ...],
        decisions: tuple[PortfolioDecisionInput, ...],
    ) -> LearningDecisionQualityMetrics:
        accepted = tuple(trade for trade in trades if trade.accepted)
        rejected = tuple(trade for trade in trades if not trade.accepted)
        good_accepts = sum(1 for trade in accepted if trade.profit_loss >= 0)
        good_rejects = sum(1 for trade in rejected if trade.expected_profit <= 0)
        portfolio_good = sum(1 for decision in decisions if decision.actual_benefit >= decision.expected_benefit * 0.75)
        return LearningDecisionQualityMetrics(
            decision_accuracy=round((good_accepts + good_rejects) / max(len(trades), 1), 4),
            opportunity_accuracy=round(sum(1 for trade in trades if (trade.expected_profit >= 0) == (trade.profit_loss >= 0)) / max(len(trades), 1), 4),
            trade_acceptance_quality=round(good_accepts / max(len(accepted), 1), 4),
            trade_rejection_quality=round(good_rejects / max(len(rejected), 1), 4),
            risk_decision_quality=round(sum(1 for trade in trades if trade.risk_used <= max(abs(trade.profit_loss), 1.0)) / max(len(trades), 1), 4),
            portfolio_decision_quality=round(portfolio_good / max(len(decisions), 1), 4),
        )

    def _daily_report(
        self,
        trading_day: date,
        attribution: PerformanceAttribution,
        learning: ContinuousLearningUpdate,
        priorities: tuple[ResearchPriority, ...],
    ) -> DailyLearningReport:
        return DailyLearningReport(
            report_id=f"LEARNING-DAILY-{trading_day:%Y%m%d}",
            trading_day=trading_day.isoformat(),
            daily_attribution={
                "total_profit_loss": attribution.total_profit_loss,
                "strategy_items": len(attribution.strategy),
                "feature_items": len(attribution.feature),
                "plugin_items": len(attribution.plugin),
            },
            strategy_contribution=attribution.strategy,
            session_contribution=attribution.session,
            feature_contribution=attribution.feature,
            portfolio_contribution=attribution.portfolio_allocation,
            knowledge_updates=learning.knowledge_updates,
            research_recommendations=tuple(priority.action for priority in priorities),
        )


def demo_trade_performance_inputs() -> tuple[TradePerformanceInput, ...]:
    return (
        TradePerformanceInput("T-001", "QF-PI-001", "trend", "EUR_USD", "London", "Trending", ("Trend Strength", "Liquidity"), "ema_pullback", "atr_trailing", "volatility_guard", "trend_rotation", 840.0, 120.0, True, 520.0),
        TradePerformanceInput("T-002", "QF-PI-003", "breakout", "USD_JPY", "Overlap", "Breakout", ("Volatility", "Momentum"), "donchian_breakout", "time_exit", "volatility_guard", "breakout_sleeve", 610.0, 140.0, True, 480.0),
        TradePerformanceInput("T-003", "QF-PI-002", "mean_reversion", "GBP_USD", "Asian", "Ranging", ("Support Distance", "Liquidity"), "rsi_reversion", "mean_exit", "daily_loss_guard", "range_sleeve", -220.0, 110.0, True, 160.0),
        TradePerformanceInput("T-004", "QF-PI-005", "volatility", "EUR_JPY", "New York", "Volatile", ("Volatility", "Resistance Distance"), "atr_expansion", "atr_trailing", "volatility_guard", "volatility_sleeve", 390.0, 130.0, True, 260.0),
        TradePerformanceInput("T-005", "QF-PI-004", "momentum", "AUD_USD", "London", "Trending", ("Momentum", "Trend Strength"), "momentum_break", "time_exit", "daily_loss_guard", "trend_rotation", 280.0, 95.0, True, 210.0),
        TradePerformanceInput("T-006", "QF-PI-002", "mean_reversion", "GBP_USD", "Asian", "Ranging", ("Support Distance", "Momentum"), "rsi_reversion", "mean_exit", "daily_loss_guard", "range_sleeve", 0.0, 0.0, False, -90.0),
    )


def demo_portfolio_decision_inputs() -> tuple[PortfolioDecisionInput, ...]:
    return (
        PortfolioDecisionInput("PD-001", "Increase trend sleeve after positive London attribution.", 0.18, 0.24, 0.04, -0.03, 0.08),
        PortfolioDecisionInput("PD-002", "Reduce Asian mean-reversion allocation.", 0.08, 0.11, -0.02, -0.04, -0.03),
        PortfolioDecisionInput("PD-003", "Add volatility breakout sleeve for high-volatility sessions.", 0.12, 0.16, 0.03, 0.02, 0.05),
    )


def _group(
    trades: tuple[TradePerformanceInput, ...],
    key_func: Any,
) -> dict[str, tuple[float, int]]:
    grouped: dict[str, tuple[float, int]] = {}
    for trade in trades:
        key = str(key_func(trade))
        total, count = grouped.get(key, (0.0, 0))
        grouped[key] = (total + trade.profit_loss, count + 1)
    return grouped


def _multi_group(
    trades: tuple[TradePerformanceInput, ...],
    key_func: Any,
) -> dict[str, tuple[float, int]]:
    grouped: dict[str, tuple[float, int]] = {}
    for trade in trades:
        keys = tuple(str(key) for key in key_func(trade))
        share = trade.profit_loss / max(len(keys), 1)
        for key in keys:
            total, count = grouped.get(key, (0.0, 0))
            grouped[key] = (total + share, count + 1)
    return grouped


def _rows(category: str, grouped: dict[str, tuple[float, int]], total: float) -> tuple[AttributionRow, ...]:
    rows = [
        AttributionRow(
            category=category,
            item=item,
            contribution=round(value, 4),
            contribution_percent=round((value / total) * 100, 4) if total else 0.0,
            evidence_count=count,
        )
        for item, (value, count) in grouped.items()
    ]
    return tuple(sorted(rows, key=lambda row: row.contribution, reverse=True))


def _positive_first(rows: tuple[AttributionRow, ...]) -> tuple[AttributionRow, ...]:
    return tuple(sorted(rows, key=lambda row: row.contribution, reverse=True))


def _confidence(rows: tuple[AttributionRow, ...], item: str) -> float:
    match = next((row for row in rows if row.item == item), None)
    if match is None:
        return 0.5
    return round(max(0.1, min(0.99, 0.5 + (match.contribution_percent / 100))), 4)


def _positive_share(rows: tuple[AttributionRow, ...]) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if row.contribution >= 0) / len(rows)
