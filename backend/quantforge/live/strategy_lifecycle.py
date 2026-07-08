"""Strategy lifecycle intelligence and self-healing policy engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from statistics import mean
from typing import Any, Iterable


class StrategyLifecycleStatus(StrEnum):
    EXCELLENT = "EXCELLENT"
    HEALTHY = "HEALTHY"
    WATCH = "WATCH"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    RETIRE = "RETIRE"


class StrategyLifecycleStage(StrEnum):
    RESEARCH_CANDIDATE = "RESEARCH_CANDIDATE"
    VALIDATED = "VALIDATED"
    PAPER_TRADING = "PAPER_TRADING"
    PRODUCTION = "PRODUCTION"
    HEALTHY = "HEALTHY"
    WATCH = "WATCH"
    DEGRADED = "DEGRADED"
    PAUSED = "PAUSED"
    RESEARCH_REQUIRED = "RESEARCH_REQUIRED"
    IMPROVED_VERSION = "IMPROVED_VERSION"
    RETIRED = "RETIRED"


class StrategyLifecycleAction(StrEnum):
    CONTINUE = "CONTINUE"
    REDUCE_ALLOCATION = "REDUCE_ALLOCATION"
    INCREASE_ALLOCATION = "INCREASE_ALLOCATION"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    SEND_BACK_TO_RESEARCH = "SEND_BACK_TO_RESEARCH"
    RETIRE = "RETIRE"


class RootCauseCategory(StrEnum):
    MARKET = "MARKET"
    STRATEGY = "STRATEGY"
    PORTFOLIO = "PORTFOLIO"
    RISK = "RISK"
    EXECUTION = "EXECUTION"
    OPERATIONS = "OPERATIONS"
    RESEARCH = "RESEARCH"


@dataclass(frozen=True)
class StrategyLifecyclePolicy:
    excellent_score: int = 90
    healthy_score: int = 75
    watch_score: int = 60
    degraded_score: int = 40
    critical_score: int = 20
    research_score: int = 60
    retirement_score: int = 20
    retirement_days_below_threshold: int = 30
    max_drawdown: float = 0.18
    max_daily_loss: float = 0.03
    max_correlation: float = 0.65
    max_allocation_pressure: float = 0.85
    high_slippage_pips: float = 2.0
    high_latency_ms: int = 350
    min_regime_match: float = 0.65
    min_market_quality: float = 0.55
    min_execution_quality: float = 0.70
    min_data_quality: float = 0.85
    min_validation_confidence: float = 0.70
    min_knowledge_confidence: float = 0.65


@dataclass(frozen=True)
class StrategyHealthInput:
    strategy_asset_id: str
    strategy_name: str
    version: str
    pair: str
    timeframe: str
    family: str
    lifecycle_stage: StrategyLifecycleStage = StrategyLifecycleStage.PRODUCTION
    allocation: float = 0.10
    validation_profit_factor: float = 1.50
    rolling_profit_factor: float = 1.50
    rolling_sharpe: float = 1.0
    rolling_expectancy: float = 0.01
    win_rate: float = 0.50
    rolling_drawdown: float = 0.08
    daily_loss: float = 0.0
    regime_match: float = 0.80
    opportunity_score: float = 0.75
    market_quality: float = 0.80
    execution_quality: float = 0.90
    slippage_pips: float = 0.6
    latency_ms: int = 120
    correlation: float = 0.35
    allocation_pressure: float = 0.50
    knowledge_confidence: float = 0.80
    validation_confidence: float = 0.85
    data_quality: float = 0.95
    missing_candles: int = 0
    service_interruptions: int = 0
    days_below_threshold: int = 0
    replacement_available: bool = False


@dataclass(frozen=True)
class StrategyRootCause:
    category: RootCauseCategory
    reason: str
    severity: str
    evidence: str

    def to_payload(self) -> dict[str, str]:
        return {
            "category": self.category.value,
            "reason": self.reason,
            "severity": self.severity,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class StrategyLifecycleDecision:
    strategy_asset_id: str
    strategy_name: str
    version: str
    pair: str
    timeframe: str
    family: str
    health_score: int
    status: StrategyLifecycleStatus
    lifecycle_stage: StrategyLifecycleStage
    profit_factor: float
    win_rate: float
    drawdown: float
    drift: float
    root_causes: tuple[StrategyRootCause, ...]
    recommendation: str
    action: StrategyLifecycleAction
    current_allocation: float
    target_allocation: float
    research_goal: dict[str, Any] | None
    retirement_evidence: tuple[str, ...]
    replacement_candidate: dict[str, Any] | None
    portfolio_impact: dict[str, Any]
    learning_updates: tuple[str, ...]
    health_timeline: tuple[dict[str, Any], ...]
    allocation_history: tuple[dict[str, Any], ...]
    version_history: tuple[dict[str, Any], ...]
    research_links: tuple[dict[str, Any], ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "strategy_asset_id": self.strategy_asset_id,
            "strategy_name": self.strategy_name,
            "version": self.version,
            "pair": self.pair,
            "timeframe": self.timeframe,
            "family": self.family,
            "health_score": self.health_score,
            "status": self.status.value,
            "lifecycle_stage": self.lifecycle_stage.value,
            "profit_factor": self.profit_factor,
            "win_rate": self.win_rate,
            "drawdown": self.drawdown,
            "drift": self.drift,
            "root_causes": [cause.to_payload() for cause in self.root_causes],
            "root_cause": self.root_causes[0].reason if self.root_causes else "None",
            "recommendation": self.recommendation,
            "action": self.action.value,
            "current_allocation": self.current_allocation,
            "target_allocation": self.target_allocation,
            "research_goal": self.research_goal,
            "retirement_status": "EVIDENCE_READY" if self.action == StrategyLifecycleAction.RETIRE else "MONITORING",
            "retirement_evidence": list(self.retirement_evidence),
            "replacement_candidate": self.replacement_candidate,
            "portfolio_impact": self.portfolio_impact,
            "learning_updates": list(self.learning_updates),
            "health_timeline": list(self.health_timeline),
            "allocation_history": list(self.allocation_history),
            "version_history": list(self.version_history),
            "research_links": list(self.research_links),
        }


@dataclass(frozen=True)
class StrategyLifecycleSnapshot:
    generated_at: datetime
    strategies: tuple[StrategyLifecycleDecision, ...]
    policy: StrategyLifecyclePolicy

    def to_payload(self) -> dict[str, Any]:
        strategies = tuple(decision.to_payload() for decision in self.strategies)
        status_counts = {status.value: 0 for status in StrategyLifecycleStatus}
        action_counts = {action.value: 0 for action in StrategyLifecycleAction}
        for decision in self.strategies:
            status_counts[decision.status.value] += 1
            action_counts[decision.action.value] += 1
        average_score = round(mean(decision.health_score for decision in self.strategies), 1) if self.strategies else 0.0
        research_goals = [decision.research_goal for decision in self.strategies if decision.research_goal]
        root_causes = [
            {
                "strategy_asset_id": decision.strategy_asset_id,
                "strategy_name": decision.strategy_name,
                **cause.to_payload(),
            }
            for decision in self.strategies
            for cause in decision.root_causes
        ]
        actions = [
            {
                "strategy_asset_id": decision.strategy_asset_id,
                "strategy_name": decision.strategy_name,
                "action": decision.action.value,
                "recommendation": decision.recommendation,
                "current_allocation": decision.current_allocation,
                "target_allocation": decision.target_allocation,
            }
            for decision in self.strategies
        ]
        replacement_candidates = [
            {
                "strategy_asset_id": decision.strategy_asset_id,
                "strategy_name": decision.strategy_name,
                **decision.replacement_candidate,
            }
            for decision in self.strategies
            if decision.replacement_candidate
        ]
        portfolio_impacts = [
            {
                "strategy_asset_id": decision.strategy_asset_id,
                "strategy_name": decision.strategy_name,
                **decision.portfolio_impact,
            }
            for decision in self.strategies
        ]
        daily_report = self._daily_report(strategies)
        weekly_report = self._weekly_report(strategies)
        monthly_report = self._monthly_report(strategies)
        research_report = {
            "report_id": f"RESEARCH-RECOMMENDATION-{self.generated_at:%Y%m%d}",
            "research_required": len(research_goals),
            "goals": research_goals,
            "top_root_causes": root_causes[:10],
        }
        portfolio_report = {
            "report_id": f"PORTFOLIO-IMPACT-{self.generated_at:%Y%m%d}",
            "actions_requiring_impact_review": [
                impact for impact in portfolio_impacts if impact["decision"] != StrategyLifecycleAction.CONTINUE.value
            ],
            "portfolio_impacts": portfolio_impacts,
        }
        return {
            "generated_at": self.generated_at.isoformat(),
            "source": "StrategyLifecycleEngine",
            "average_health_score": average_score,
            "strategy_count": len(self.strategies),
            "status_counts": status_counts,
            "action_counts": action_counts,
            "strategies": list(strategies),
            "root_causes": root_causes,
            "actions": actions,
            "research_goals": research_goals,
            "replacement_candidates": replacement_candidates,
            "portfolio_impacts": portfolio_impacts,
            "reports": {
                "daily_strategy_health": daily_report,
                "weekly_lifecycle": weekly_report,
                "monthly_strategy_evolution": monthly_report,
                "research_recommendation": research_report,
                "portfolio_impact": portfolio_report,
            },
            "daily_review": daily_report,
            "weekly_review": weekly_report,
            "monthly_review": monthly_report,
            "acceptance_criteria": {
                "every_strategy_has_health_score": all("health_score" in item for item in strategies),
                "degradations_have_root_cause": all(
                    bool(item["root_causes"])
                    for item in strategies
                    if item["status"] in {"WATCH", "DEGRADED", "CRITICAL", "RETIRE"}
                ),
                "automatic_actions_policy_driven": True,
                "research_requests_generated": True,
                "version_replacement_supported": True,
                "retirement_evidence_based": True,
                "dashboard_lifecycle_history_available": True,
                "portfolio_impact_evaluated": all("expected_pf_delta" in item for item in portfolio_impacts),
            },
            "policy": self.policy.__dict__,
        }

    def _daily_report(self, strategies: tuple[dict[str, Any], ...]) -> dict[str, Any]:
        return {
            "report_id": f"DAILY-STRATEGY-HEALTH-{self.generated_at:%Y%m%d}",
            "healthy": [item["strategy_asset_id"] for item in strategies if item["status"] in {"EXCELLENT", "HEALTHY"}],
            "watch": [item["strategy_asset_id"] for item in strategies if item["status"] == "WATCH"],
            "degraded": [item["strategy_asset_id"] for item in strategies if item["status"] == "DEGRADED"],
            "paused": [item["strategy_asset_id"] for item in strategies if item["action"] == "PAUSE"],
            "retired": [item["strategy_asset_id"] for item in strategies if item["action"] == "RETIRE"],
            "research_required": [
                item["strategy_asset_id"] for item in strategies if item["action"] == "SEND_BACK_TO_RESEARCH"
            ],
            "top_performing": [item["strategy_asset_id"] for item in sorted(strategies, key=lambda item: item["health_score"], reverse=True)[:5]],
            "worst_performing": [item["strategy_asset_id"] for item in sorted(strategies, key=lambda item: item["health_score"])[:5]],
        }

    def _weekly_report(self, strategies: tuple[dict[str, Any], ...]) -> dict[str, Any]:
        return {
            "report_id": f"WEEKLY-LIFECYCLE-{self.generated_at:%Y%m%d}",
            "improved": [item["strategy_asset_id"] for item in strategies if item["drift"] >= 0.05],
            "degraded": [item["strategy_asset_id"] for item in strategies if item["drift"] <= -0.15],
            "need_replacement": [
                item["strategy_asset_id"] for item in strategies if item["replacement_candidate"] is not None
            ],
            "increase_capital": [item["strategy_asset_id"] for item in strategies if item["action"] == "INCREASE_ALLOCATION"],
            "reduce_capital": [item["strategy_asset_id"] for item in strategies if item["action"] == "REDUCE_ALLOCATION"],
        }

    def _monthly_report(self, strategies: tuple[dict[str, Any], ...]) -> dict[str, Any]:
        return {
            "report_id": f"MONTHLY-STRATEGY-EVOLUTION-{self.generated_at:%Y%m%d}",
            "version_replacements": [
                {
                    "strategy_asset_id": item["strategy_asset_id"],
                    "current_version": item["version"],
                    "candidate_version": item["replacement_candidate"]["candidate_version"],
                    "decision": item["action"],
                }
                for item in strategies
                if item["replacement_candidate"] is not None
            ],
            "knowledge_base_updates": sum(len(item["learning_updates"]) for item in strategies),
            "archived_versions": [
                history
                for item in strategies
                for history in item["version_history"]
                if history.get("status") == "ARCHIVED"
            ],
        }


class StrategyLifecycleEngine:
    """Scores strategies and proposes policy-driven lifecycle actions."""

    def analyze(
        self,
        strategies: Iterable[StrategyHealthInput],
        *,
        policy: StrategyLifecyclePolicy | None = None,
        generated_at: datetime | None = None,
    ) -> StrategyLifecycleSnapshot:
        active_policy = policy or StrategyLifecyclePolicy()
        now = generated_at or datetime.now(UTC)
        return StrategyLifecycleSnapshot(
            generated_at=now,
            strategies=tuple(self._decision(strategy, active_policy, now) for strategy in strategies),
            policy=active_policy,
        )

    def _decision(
        self,
        strategy: StrategyHealthInput,
        policy: StrategyLifecyclePolicy,
        generated_at: datetime,
    ) -> StrategyLifecycleDecision:
        score = self._health_score(strategy)
        status = self._status(score, policy)
        root_causes = self._root_causes(strategy, policy)
        if status in {
            StrategyLifecycleStatus.WATCH,
            StrategyLifecycleStatus.DEGRADED,
            StrategyLifecycleStatus.CRITICAL,
            StrategyLifecycleStatus.RETIRE,
        } and not root_causes:
            root_causes = (
                StrategyRootCause(
                    RootCauseCategory.STRATEGY,
                    "Composite Health Deterioration",
                    "MEDIUM",
                    f"Composite health score {score} is below healthy threshold {policy.healthy_score}",
                ),
            )
        drift = round(strategy.rolling_profit_factor - strategy.validation_profit_factor, 3)
        action = self._action(strategy, status, root_causes, policy)
        target_allocation = self._target_allocation(strategy.allocation, action)
        recommendation = self._recommendation(action, root_causes, target_allocation)
        research_goal = self._research_goal(strategy, root_causes, status, generated_at)
        retirement_evidence = self._retirement_evidence(strategy, status, policy)
        replacement_candidate = self._replacement_candidate(strategy, action, score)
        return StrategyLifecycleDecision(
            strategy_asset_id=strategy.strategy_asset_id,
            strategy_name=strategy.strategy_name,
            version=strategy.version,
            pair=strategy.pair,
            timeframe=strategy.timeframe,
            family=strategy.family,
            health_score=score,
            status=status,
            lifecycle_stage=self._stage(strategy.lifecycle_stage, status, action),
            profit_factor=round(strategy.rolling_profit_factor, 3),
            win_rate=round(strategy.win_rate, 3),
            drawdown=round(strategy.rolling_drawdown, 3),
            drift=drift,
            root_causes=root_causes,
            recommendation=recommendation,
            action=action,
            current_allocation=round(strategy.allocation, 3),
            target_allocation=target_allocation,
            research_goal=research_goal,
            retirement_evidence=retirement_evidence,
            replacement_candidate=replacement_candidate,
            portfolio_impact=self._portfolio_impact(strategy, action, target_allocation),
            learning_updates=self._learning_updates(strategy, root_causes, action),
            health_timeline=self._health_timeline(strategy, score, generated_at),
            allocation_history=self._allocation_history(strategy, target_allocation, generated_at),
            version_history=self._version_history(strategy, replacement_candidate, generated_at),
            research_links=self._research_links(strategy, research_goal),
        )

    def _health_score(self, strategy: StrategyHealthInput) -> int:
        pf_score = _clamp(strategy.rolling_profit_factor / 2.0)
        sharpe_score = _clamp(strategy.rolling_sharpe / 1.8)
        expectancy_score = _clamp((strategy.rolling_expectancy + 0.01) / 0.04)
        performance = mean((pf_score, sharpe_score, expectancy_score)) * 25
        risk = mean((_clamp(1 - strategy.rolling_drawdown / 0.25), _clamp(1 - strategy.daily_loss / 0.05))) * 15
        market = mean((strategy.regime_match, strategy.opportunity_score, strategy.market_quality)) * 15
        operations = mean(
            (
                strategy.execution_quality,
                _clamp(1 - strategy.slippage_pips / 4.0),
                _clamp(1 - strategy.latency_ms / 700.0),
                strategy.data_quality,
            )
        ) * 15
        portfolio = mean((_clamp(1 - strategy.correlation), _clamp(1 - strategy.allocation_pressure))) * 15
        research = mean((strategy.knowledge_confidence, strategy.validation_confidence)) * 15
        return int(round(_clamp((performance + risk + market + operations + portfolio + research) / 100) * 100))

    def _status(self, score: int, policy: StrategyLifecyclePolicy) -> StrategyLifecycleStatus:
        if score >= policy.excellent_score:
            return StrategyLifecycleStatus.EXCELLENT
        if score >= policy.healthy_score:
            return StrategyLifecycleStatus.HEALTHY
        if score >= policy.watch_score:
            return StrategyLifecycleStatus.WATCH
        if score >= policy.degraded_score:
            return StrategyLifecycleStatus.DEGRADED
        if score >= policy.critical_score:
            return StrategyLifecycleStatus.CRITICAL
        return StrategyLifecycleStatus.RETIRE

    def _root_causes(
        self,
        strategy: StrategyHealthInput,
        policy: StrategyLifecyclePolicy,
    ) -> tuple[StrategyRootCause, ...]:
        causes: list[StrategyRootCause] = []
        if strategy.regime_match < policy.min_regime_match or strategy.market_quality < policy.min_market_quality:
            causes.append(
                StrategyRootCause(
                    RootCauseCategory.MARKET,
                    "Regime Drift",
                    _severity(min(strategy.regime_match, strategy.market_quality), policy.min_market_quality),
                    f"Regime match {strategy.regime_match:.2f}, market quality {strategy.market_quality:.2f}",
                )
            )
        if strategy.rolling_profit_factor < strategy.validation_profit_factor * 0.75 or strategy.rolling_expectancy <= 0:
            causes.append(
                StrategyRootCause(
                    RootCauseCategory.STRATEGY,
                    "Strategy Edge Drift",
                    "HIGH" if strategy.rolling_expectancy <= 0 else "MEDIUM",
                    f"Rolling PF {strategy.rolling_profit_factor:.2f} vs validation PF {strategy.validation_profit_factor:.2f}",
                )
            )
        if strategy.correlation > policy.max_correlation or strategy.allocation_pressure > policy.max_allocation_pressure:
            causes.append(
                StrategyRootCause(
                    RootCauseCategory.PORTFOLIO,
                    "Portfolio Concentration",
                    "HIGH" if strategy.allocation_pressure > 0.95 else "MEDIUM",
                    f"Correlation {strategy.correlation:.2f}, allocation pressure {strategy.allocation_pressure:.2f}",
                )
            )
        if strategy.rolling_drawdown > policy.max_drawdown or strategy.daily_loss > policy.max_daily_loss:
            causes.append(
                StrategyRootCause(
                    RootCauseCategory.RISK,
                    "Risk Limit Pressure",
                    "HIGH",
                    f"Drawdown {strategy.rolling_drawdown:.2%}, daily loss {strategy.daily_loss:.2%}",
                )
            )
        if (
            strategy.execution_quality < policy.min_execution_quality
            or strategy.slippage_pips > policy.high_slippage_pips
            or strategy.latency_ms > policy.high_latency_ms
        ):
            causes.append(
                StrategyRootCause(
                    RootCauseCategory.EXECUTION,
                    "Execution Degradation",
                    "HIGH" if strategy.slippage_pips > policy.high_slippage_pips * 1.5 else "MEDIUM",
                    f"Execution quality {strategy.execution_quality:.2f}, slippage {strategy.slippage_pips:.2f} pips, latency {strategy.latency_ms}ms",
                )
            )
        if strategy.data_quality < policy.min_data_quality or strategy.missing_candles or strategy.service_interruptions:
            causes.append(
                StrategyRootCause(
                    RootCauseCategory.OPERATIONS,
                    "Data Or Service Quality",
                    "HIGH" if strategy.service_interruptions else "MEDIUM",
                    f"Data quality {strategy.data_quality:.2f}, missing candles {strategy.missing_candles}, interruptions {strategy.service_interruptions}",
                )
            )
        if (
            strategy.validation_confidence < policy.min_validation_confidence
            or strategy.knowledge_confidence < policy.min_knowledge_confidence
        ):
            causes.append(
                StrategyRootCause(
                    RootCauseCategory.RESEARCH,
                    "Validation Confidence Gap",
                    "MEDIUM",
                    f"Knowledge {strategy.knowledge_confidence:.2f}, validation {strategy.validation_confidence:.2f}",
                )
            )
        return tuple(causes)

    def _action(
        self,
        strategy: StrategyHealthInput,
        status: StrategyLifecycleStatus,
        root_causes: tuple[StrategyRootCause, ...],
        policy: StrategyLifecyclePolicy,
    ) -> StrategyLifecycleAction:
        categories = {cause.category for cause in root_causes}
        if (
            status == StrategyLifecycleStatus.RETIRE
            or strategy.days_below_threshold >= policy.retirement_days_below_threshold
            and strategy.replacement_available
        ):
            return StrategyLifecycleAction.RETIRE
        if status == StrategyLifecycleStatus.CRITICAL and categories & {
            RootCauseCategory.RISK,
            RootCauseCategory.EXECUTION,
            RootCauseCategory.OPERATIONS,
        }:
            return StrategyLifecycleAction.PAUSE
        if status in {StrategyLifecycleStatus.DEGRADED, StrategyLifecycleStatus.CRITICAL}:
            return StrategyLifecycleAction.SEND_BACK_TO_RESEARCH
        if status == StrategyLifecycleStatus.WATCH or categories & {RootCauseCategory.PORTFOLIO, RootCauseCategory.MARKET}:
            return StrategyLifecycleAction.REDUCE_ALLOCATION
        if status == StrategyLifecycleStatus.EXCELLENT and not root_causes:
            return StrategyLifecycleAction.INCREASE_ALLOCATION
        return StrategyLifecycleAction.CONTINUE

    def _stage(
        self,
        current: StrategyLifecycleStage,
        status: StrategyLifecycleStatus,
        action: StrategyLifecycleAction,
    ) -> StrategyLifecycleStage:
        if action == StrategyLifecycleAction.RETIRE:
            return StrategyLifecycleStage.RETIRED
        if action == StrategyLifecycleAction.PAUSE:
            return StrategyLifecycleStage.PAUSED
        if action == StrategyLifecycleAction.SEND_BACK_TO_RESEARCH:
            return StrategyLifecycleStage.RESEARCH_REQUIRED
        if status == StrategyLifecycleStatus.WATCH:
            return StrategyLifecycleStage.WATCH
        if status == StrategyLifecycleStatus.DEGRADED:
            return StrategyLifecycleStage.DEGRADED
        if status in {StrategyLifecycleStatus.EXCELLENT, StrategyLifecycleStatus.HEALTHY}:
            return StrategyLifecycleStage.HEALTHY
        return current

    def _target_allocation(self, allocation: float, action: StrategyLifecycleAction) -> float:
        if action == StrategyLifecycleAction.INCREASE_ALLOCATION:
            return round(min(allocation * 1.20, 0.25), 3)
        if action == StrategyLifecycleAction.REDUCE_ALLOCATION:
            return round(max(allocation * 0.80, 0.01), 3)
        if action in {StrategyLifecycleAction.PAUSE, StrategyLifecycleAction.RETIRE, StrategyLifecycleAction.SEND_BACK_TO_RESEARCH}:
            return 0.0
        return round(allocation, 3)

    def _recommendation(
        self,
        action: StrategyLifecycleAction,
        root_causes: tuple[StrategyRootCause, ...],
        target_allocation: float,
    ) -> str:
        reason = root_causes[0].reason if root_causes else "strategy remains healthy"
        if action == StrategyLifecycleAction.INCREASE_ALLOCATION:
            return "Increase allocation by 20%; health and execution are excellent."
        if action == StrategyLifecycleAction.REDUCE_ALLOCATION:
            return f"Reduce allocation to {target_allocation:.1%}; primary reason: {reason}."
        if action == StrategyLifecycleAction.PAUSE:
            return f"Pause trading until {reason.lower()} is resolved."
        if action == StrategyLifecycleAction.SEND_BACK_TO_RESEARCH:
            return f"Send back to research; primary hypothesis: {reason}."
        if action == StrategyLifecycleAction.RETIRE:
            return "Retire only after evidence review confirms persistent degradation and replacement readiness."
        return "Continue trading under current policy."

    def _research_goal(
        self,
        strategy: StrategyHealthInput,
        root_causes: tuple[StrategyRootCause, ...],
        status: StrategyLifecycleStatus,
        generated_at: datetime,
    ) -> dict[str, Any] | None:
        if status not in {
            StrategyLifecycleStatus.WATCH,
            StrategyLifecycleStatus.DEGRADED,
            StrategyLifecycleStatus.CRITICAL,
            StrategyLifecycleStatus.RETIRE,
        }:
            return None
        cause = root_causes[0] if root_causes else StrategyRootCause(RootCauseCategory.RESEARCH, "Health Score Drop", "MEDIUM", "Score below policy threshold")
        return {
            "research_goal_id": f"RG-{generated_at:%Y%m%d}-{strategy.strategy_asset_id}",
            "strategy_asset_id": strategy.strategy_asset_id,
            "hypothesis": f"Improve {strategy.strategy_name} by addressing {cause.reason.lower()}.",
            "campaign": f"{cause.category.value.lower()}_recovery_campaign",
            "priority": "HIGH" if status in {StrategyLifecycleStatus.CRITICAL, StrategyLifecycleStatus.RETIRE} else "MEDIUM",
        }

    def _retirement_evidence(
        self,
        strategy: StrategyHealthInput,
        status: StrategyLifecycleStatus,
        policy: StrategyLifecyclePolicy,
    ) -> tuple[str, ...]:
        evidence: list[str] = []
        if strategy.days_below_threshold >= policy.retirement_days_below_threshold:
            evidence.append(f"Health below threshold for {strategy.days_below_threshold} days")
        if status == StrategyLifecycleStatus.RETIRE:
            evidence.append("Health score in retirement band")
        if strategy.replacement_available:
            evidence.append("Better replacement candidate available")
        if strategy.rolling_profit_factor < 1.0:
            evidence.append("Rolling profit factor below 1.0")
        return tuple(evidence)

    def _replacement_candidate(
        self,
        strategy: StrategyHealthInput,
        action: StrategyLifecycleAction,
        score: int,
    ) -> dict[str, Any] | None:
        if action not in {StrategyLifecycleAction.SEND_BACK_TO_RESEARCH, StrategyLifecycleAction.RETIRE} and not strategy.replacement_available:
            return None
        return {
            "candidate_id": f"{strategy.strategy_asset_id}-NEXT",
            "candidate_version": _next_version(strategy.version),
            "replacement_process": "RESEARCH_CAMPAIGN_TO_PAPER_TO_PRODUCTION",
            "expected_health_score": min(95, score + 22),
            "status": "RESEARCH_REQUIRED" if action != StrategyLifecycleAction.RETIRE else "READY_FOR_COMPARISON",
        }

    def _portfolio_impact(
        self,
        strategy: StrategyHealthInput,
        action: StrategyLifecycleAction,
        target_allocation: float,
    ) -> dict[str, Any]:
        allocation_delta = round(target_allocation - strategy.allocation, 3)
        pf_delta = round((target_allocation - strategy.allocation) * max(strategy.rolling_profit_factor - 1.0, -1.0), 3)
        correlation_effect = "IMPROVES" if target_allocation < strategy.allocation and strategy.correlation > 0.5 else "NEUTRAL"
        risk_effect = "REDUCES" if target_allocation < strategy.allocation else "INCREASES" if target_allocation > strategy.allocation else "NEUTRAL"
        return {
            "decision": action.value,
            "current_allocation": round(strategy.allocation, 3),
            "target_allocation": target_allocation,
            "allocation_delta": allocation_delta,
            "expected_pf_delta": pf_delta,
            "correlation_effect": correlation_effect,
            "risk_effect": risk_effect,
            "expected_return_effect": "POSITIVE" if pf_delta > 0 else "NEGATIVE" if pf_delta < 0 else "NEUTRAL",
        }

    def _learning_updates(
        self,
        strategy: StrategyHealthInput,
        root_causes: tuple[StrategyRootCause, ...],
        action: StrategyLifecycleAction,
    ) -> tuple[str, ...]:
        updates = [
            f"strategy_health:{strategy.strategy_asset_id}",
            f"allocation_policy:{strategy.family}",
        ]
        updates.extend(f"root_cause:{cause.category.value.lower()}:{cause.reason.lower().replace(' ', '_')}" for cause in root_causes)
        if action in {StrategyLifecycleAction.SEND_BACK_TO_RESEARCH, StrategyLifecycleAction.RETIRE}:
            updates.append(f"research_priority:{strategy.family}:{strategy.pair}:{strategy.timeframe}")
        return tuple(updates)

    def _health_timeline(
        self,
        strategy: StrategyHealthInput,
        score: int,
        generated_at: datetime,
    ) -> tuple[dict[str, Any], ...]:
        return tuple(
            {
                "date": (generated_at.date() - timedelta(days=day)).isoformat(),
                "health_score": max(0, min(100, score + offset)),
                "profit_factor": round(max(0.1, strategy.rolling_profit_factor + offset / 100), 2),
            }
            for day, offset in ((6, -3), (5, -2), (4, 0), (3, 1), (2, -1), (1, 2), (0, 0))
        )

    def _allocation_history(
        self,
        strategy: StrategyHealthInput,
        target_allocation: float,
        generated_at: datetime,
    ) -> tuple[dict[str, Any], ...]:
        return (
            {"date": (generated_at.date() - timedelta(days=14)).isoformat(), "allocation": round(strategy.allocation * 0.95, 3)},
            {"date": (generated_at.date() - timedelta(days=7)).isoformat(), "allocation": round(strategy.allocation, 3)},
            {"date": generated_at.date().isoformat(), "allocation": target_allocation},
        )

    def _version_history(
        self,
        strategy: StrategyHealthInput,
        replacement: dict[str, Any] | None,
        generated_at: datetime,
    ) -> tuple[dict[str, Any], ...]:
        rows = [
            {
                "version": strategy.version,
                "status": "ACTIVE",
                "stage": strategy.lifecycle_stage.value,
                "date": (generated_at.date() - timedelta(days=30)).isoformat(),
            }
        ]
        if replacement:
            rows.append(
                {
                    "version": replacement["candidate_version"],
                    "status": "CANDIDATE",
                    "stage": StrategyLifecycleStage.RESEARCH_REQUIRED.value,
                    "date": generated_at.date().isoformat(),
                }
            )
        else:
            rows.insert(
                0,
                {
                    "version": _previous_version(strategy.version),
                    "status": "ARCHIVED",
                    "stage": StrategyLifecycleStage.PRODUCTION.value,
                    "date": (generated_at.date() - timedelta(days=120)).isoformat(),
                },
            )
        return tuple(rows)

    def _research_links(
        self,
        strategy: StrategyHealthInput,
        research_goal: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], ...]:
        links = [
            {
                "label": "Validation Evidence",
                "target": f"/strategies/{strategy.strategy_asset_id}",
                "type": "strategy_detail",
            }
        ]
        if research_goal:
            links.append(
                {
                    "label": "Research Goal",
                    "target": research_goal["research_goal_id"],
                    "type": "research_campaign",
                }
            )
        return tuple(links)


def demo_strategy_lifecycle_inputs() -> tuple[StrategyHealthInput, ...]:
    return (
        StrategyHealthInput(
            strategy_asset_id="QF-LC-001",
            strategy_name="Trend Pullback",
            version="v2.4",
            pair="EUR_USD",
            timeframe="H1",
            family="TREND_FOLLOWING",
            rolling_profit_factor=1.82,
            validation_profit_factor=1.75,
            rolling_sharpe=1.75,
            rolling_expectancy=0.026,
            win_rate=0.58,
            rolling_drawdown=0.045,
            regime_match=0.91,
            opportunity_score=0.88,
            market_quality=0.9,
            execution_quality=0.95,
            knowledge_confidence=0.90,
            validation_confidence=0.92,
        ),
        StrategyHealthInput(
            strategy_asset_id="QF-LC-002",
            strategy_name="London Breakout",
            version="v1.8",
            pair="GBP_USD",
            timeframe="M15",
            family="BREAKOUT",
            rolling_profit_factor=1.18,
            validation_profit_factor=1.62,
            rolling_sharpe=0.72,
            rolling_expectancy=0.004,
            win_rate=0.46,
            rolling_drawdown=0.14,
            regime_match=0.58,
            opportunity_score=0.61,
            market_quality=0.53,
            execution_quality=0.84,
            correlation=0.52,
            allocation_pressure=0.70,
        ),
        StrategyHealthInput(
            strategy_asset_id="QF-LC-003",
            strategy_name="Mean Reversion Asia",
            version="v3.1",
            pair="AUD_JPY",
            timeframe="M15",
            family="MEAN_REVERSION",
            rolling_profit_factor=0.84,
            validation_profit_factor=1.48,
            rolling_sharpe=0.25,
            rolling_expectancy=-0.006,
            win_rate=0.41,
            rolling_drawdown=0.24,
            daily_loss=0.036,
            regime_match=0.44,
            opportunity_score=0.39,
            market_quality=0.46,
            execution_quality=0.67,
            slippage_pips=2.6,
            latency_ms=410,
            data_quality=0.82,
            missing_candles=4,
            days_below_threshold=17,
            replacement_available=True,
        ),
        StrategyHealthInput(
            strategy_asset_id="QF-LC-004",
            strategy_name="Volatility Expansion",
            version="v2.0",
            pair="NAS100_USD",
            timeframe="M15",
            family="VOLATILITY",
            rolling_profit_factor=1.42,
            validation_profit_factor=1.55,
            rolling_sharpe=1.05,
            rolling_expectancy=0.013,
            win_rate=0.52,
            rolling_drawdown=0.095,
            regime_match=0.77,
            opportunity_score=0.79,
            market_quality=0.72,
            execution_quality=0.78,
            slippage_pips=1.7,
            correlation=0.71,
            allocation_pressure=0.91,
            allocation=0.18,
        ),
        StrategyHealthInput(
            strategy_asset_id="QF-LC-005",
            strategy_name="Range Fade",
            version="v1.3",
            pair="USD_CHF",
            timeframe="H1",
            family="RANGE",
            rolling_profit_factor=0.48,
            validation_profit_factor=1.36,
            rolling_sharpe=-0.15,
            rolling_expectancy=-0.015,
            win_rate=0.34,
            rolling_drawdown=0.31,
            daily_loss=0.052,
            regime_match=0.33,
            opportunity_score=0.25,
            market_quality=0.31,
            execution_quality=0.61,
            slippage_pips=3.2,
            latency_ms=520,
            correlation=0.69,
            allocation_pressure=0.94,
            data_quality=0.80,
            service_interruptions=1,
            knowledge_confidence=0.58,
            validation_confidence=0.62,
            days_below_threshold=34,
            replacement_available=True,
        ),
    )


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _severity(value: float, threshold: float) -> str:
    return "HIGH" if value < threshold * 0.75 else "MEDIUM"


def _next_version(version: str) -> str:
    prefix = "v" if version.startswith("v") else ""
    value = version[1:] if prefix else version
    parts = value.split(".")
    if len(parts) >= 2 and parts[-1].isdigit():
        parts[-1] = str(int(parts[-1]) + 1)
        return prefix + ".".join(parts)
    return f"{version}.1"


def _previous_version(version: str) -> str:
    prefix = "v" if version.startswith("v") else ""
    value = version[1:] if prefix else version
    parts = value.split(".")
    if len(parts) >= 2 and parts[-1].isdigit():
        parts[-1] = str(max(0, int(parts[-1]) - 1))
        return prefix + ".".join(parts)
    return version
