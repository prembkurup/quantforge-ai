from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from quantforge.research.knowledge_base import (
    Hypothesis,
    KnowledgeEngine,
    KnowledgeObjectType,
    KnowledgeRepository,
    KnowledgeScore,
    RecommendationLevel,
)


class OrchestrationDecision(StrEnum):
    RUN_EXPERIMENT = "run_experiment"
    REFINE_HYPOTHESIS = "refine_hypothesis"
    SKIP_KNOWN_FAILURE = "skip_known_failure"
    COLLECT_MORE_EVIDENCE = "collect_more_evidence"


@dataclass(frozen=True, slots=True)
class ResearchContext:
    instrument: str
    timeframe: str
    market_regime: str
    session: str | None = None
    features: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ResearchOrchestrationRequest:
    hypothesis_id: str
    hypothesis_statement: str
    context: ResearchContext
    objective: str = "maximize_validated_edge"
    required_features: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResearchExperimentPlan:
    decision: OrchestrationDecision
    hypothesis_id: str
    objective: str
    recommended_features: tuple[str, ...]
    recommended_plugins: tuple[str, ...]
    recommended_regimes: tuple[str, ...]
    blocked_plugins: tuple[str, ...]
    constraints: dict[str, Any]
    next_experiments: tuple[str, ...]
    reasons: tuple[str, ...]
    hypothesis_status: str
    confidence: float


class ResearchOrchestrator:
    """Coordinates pre-strategy research decisions.

    The orchestrator is intentionally upstream of Strategy Factory. It does not
    generate strategies; it decides what research should be attempted, skipped,
    constrained, or refined using hypothesis state and institutional knowledge.
    """

    def __init__(self, knowledge_engine: KnowledgeEngine | None = None) -> None:
        self._knowledge_engine = knowledge_engine or KnowledgeEngine()

    @property
    def knowledge_engine(self) -> KnowledgeEngine:
        return self._knowledge_engine

    def plan(self, request: ResearchOrchestrationRequest) -> ResearchExperimentPlan:
        hypothesis = self._ensure_hypothesis(request)
        best_features = self._knowledge_engine.recommendations.best_features(self._knowledge_engine.repository)
        best_plugins = self._knowledge_engine.recommendations.best_plugins(self._knowledge_engine.repository)
        best_regimes = self._knowledge_engine.recommendations.best_regimes(self._knowledge_engine.repository)
        blocked_plugins = self._blocked_plugins(self._knowledge_engine.repository)
        next_experiments = self._knowledge_engine.recommendations.recommend_next_experiments(
            self._knowledge_engine.repository
        )

        reasons = self._reasons(request, hypothesis, best_features, best_plugins, best_regimes, blocked_plugins)
        decision = self._decision(hypothesis, best_plugins, blocked_plugins)

        return ResearchExperimentPlan(
            decision=decision,
            hypothesis_id=request.hypothesis_id,
            objective=request.objective,
            recommended_features=tuple(score.object_id for score in best_features),
            recommended_plugins=tuple(score.object_id for score in best_plugins),
            recommended_regimes=tuple(score.object_id for score in best_regimes),
            blocked_plugins=blocked_plugins,
            constraints={
                "instrument": request.context.instrument,
                "timeframe": request.context.timeframe,
                "market_regime": request.context.market_regime,
                "session": request.context.session,
                "required_features": request.required_features,
                "avoid_plugins": blocked_plugins,
            },
            next_experiments=next_experiments,
            reasons=tuple(reasons),
            hypothesis_status=hypothesis.status.value,
            confidence=hypothesis.confidence,
        )

    def dashboard_payload(self, request: ResearchOrchestrationRequest) -> dict[str, Any]:
        plan = self.plan(request)
        return {
            "decision": plan.decision.value,
            "hypothesis_id": plan.hypothesis_id,
            "hypothesis_status": plan.hypothesis_status,
            "confidence": plan.confidence,
            "recommended_features": list(plan.recommended_features),
            "recommended_plugins": list(plan.recommended_plugins),
            "recommended_regimes": list(plan.recommended_regimes),
            "blocked_plugins": list(plan.blocked_plugins),
            "constraints": plan.constraints,
            "next_experiments": list(plan.next_experiments),
            "reasons": list(plan.reasons),
        }

    def _ensure_hypothesis(self, request: ResearchOrchestrationRequest) -> Hypothesis:
        hypothesis = self._knowledge_engine.repository.hypothesis(request.hypothesis_id)
        if hypothesis is not None:
            return hypothesis

        hypothesis = Hypothesis(
            hypothesis_id=request.hypothesis_id,
            statement=request.hypothesis_statement,
        )
        self._knowledge_engine.repository.upsert_hypothesis(hypothesis)
        return hypothesis

    def _blocked_plugins(self, repository: KnowledgeRepository) -> tuple[str, ...]:
        scores = self._knowledge_engine.scoring.score_repository(repository, KnowledgeObjectType.PLUGIN)
        return tuple(score.object_id for score in scores if score.recommendation == RecommendationLevel.IGNORE)

    def _decision(
        self,
        hypothesis: Hypothesis,
        best_plugins: tuple[KnowledgeScore, ...],
        blocked_plugins: tuple[str, ...],
    ) -> OrchestrationDecision:
        if hypothesis.status.value == "rejected" and hypothesis.confidence >= 0.75:
            return OrchestrationDecision.SKIP_KNOWN_FAILURE
        if not best_plugins and blocked_plugins:
            return OrchestrationDecision.SKIP_KNOWN_FAILURE
        if not best_plugins:
            return OrchestrationDecision.COLLECT_MORE_EVIDENCE
        if hypothesis.status.value in {"proposed", "mixed"} and hypothesis.confidence < 0.5:
            return OrchestrationDecision.REFINE_HYPOTHESIS
        return OrchestrationDecision.RUN_EXPERIMENT

    def _reasons(
        self,
        request: ResearchOrchestrationRequest,
        hypothesis: Hypothesis,
        best_features: tuple[KnowledgeScore, ...],
        best_plugins: tuple[KnowledgeScore, ...],
        best_regimes: tuple[KnowledgeScore, ...],
        blocked_plugins: tuple[str, ...],
    ) -> list[str]:
        reasons = [
            f"Hypothesis status is {hypothesis.status.value} with confidence {hypothesis.confidence}.",
            f"Context is {request.context.instrument} {request.context.timeframe} {request.context.market_regime}.",
        ]
        if best_features:
            reasons.append("Knowledge Base recommends features: " + ", ".join(score.object_id for score in best_features))
        if best_plugins:
            reasons.append("Knowledge Base recommends plugins: " + ", ".join(score.object_id for score in best_plugins))
        if best_regimes:
            reasons.append("Knowledge Base recommends regimes: " + ", ".join(score.object_id for score in best_regimes))
        if blocked_plugins:
            reasons.append("Known weak plugins are blocked: " + ", ".join(blocked_plugins))
        if request.required_features:
            reasons.append("Request requires features: " + ", ".join(request.required_features))
        return reasons
