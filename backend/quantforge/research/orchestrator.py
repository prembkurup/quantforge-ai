from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from quantforge.research.knowledge_base import (
    ExperimentResultKnowledge,
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


class ResearchJobType(StrEnum):
    RESEARCH = "research"
    OPTIMIZATION = "optimization"
    BACKTEST = "backtest"
    VALIDATION = "validation"
    KNOWLEDGE_UPDATE = "knowledge_update"


class ResearchJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


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
    research_goal: str = "Improve Trend Pullback"
    objective: str = "maximize_validated_edge"
    required_features: tuple[str, ...] = ()
    candidate_templates: tuple[str, ...] = ()
    candidate_plugins: tuple[str, ...] = ()
    max_experiments: int = 14


@dataclass(frozen=True, slots=True)
class DatasetPlan:
    instruments: tuple[str, ...]
    timeframes: tuple[str, ...]
    date_range: str
    training_period: str
    validation_period: str


@dataclass(frozen=True, slots=True)
class FeaturePlan:
    selected_features: tuple[str, ...]
    required_features: tuple[str, ...]
    reason: str


@dataclass(frozen=True, slots=True)
class TemplatePlan:
    selected_templates: tuple[str, ...]
    selected_plugins: tuple[str, ...]
    blocked_plugins: tuple[str, ...]
    reason: str


@dataclass(frozen=True, slots=True)
class ParameterPlan:
    search_space: dict[str, tuple[Any, ...]]
    narrowed_by_knowledge: dict[str, Any]
    avoided_parameters: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResearchJob:
    job_id: str
    job_type: ResearchJobType
    depends_on: tuple[str, ...] = ()
    status: ResearchJobStatus = ResearchJobStatus.QUEUED


@dataclass(frozen=True, slots=True)
class ProgressSnapshot:
    queued: int
    running: int
    completed: int
    failed: int
    total: int


@dataclass(frozen=True, slots=True)
class OrchestratedResearchRun:
    research_goal: str
    experiment_count: int
    dataset: DatasetPlan
    features: FeaturePlan
    templates: TemplatePlan
    parameters: ParameterPlan
    jobs: tuple[ResearchJob, ...]
    progress: ProgressSnapshot


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
    research_run: OrchestratedResearchRun | None = None


class ResearchOrchestrator:
    """Coordinates the knowledge-driven research loop.

    The orchestrator is intentionally upstream of the Strategy Composer. It
    does not calculate indicators, backtest, or execute trades. It plans the
    dataset, features, regime-aware template choices, parameter ranges, jobs,
    result collection, and Knowledge Base update path.
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
        research_run = self._build_research_run(request, best_features, best_plugins, blocked_plugins)

        reasons = self._reasons(request, hypothesis, best_features, best_plugins, best_regimes, blocked_plugins)
        decision = self._decision(hypothesis, best_plugins, blocked_plugins)

        return ResearchExperimentPlan(
            decision=decision,
            hypothesis_id=request.hypothesis_id,
            objective=request.objective,
            recommended_features=research_run.features.selected_features,
            recommended_plugins=research_run.templates.selected_plugins,
            recommended_regimes=tuple(score.object_id for score in best_regimes),
            blocked_plugins=blocked_plugins,
            constraints={
                "instrument": request.context.instrument,
                "timeframe": request.context.timeframe,
                "market_regime": request.context.market_regime,
                "session": request.context.session,
                "required_features": request.required_features,
                "avoid_plugins": blocked_plugins,
                "dataset": _dataclass_payload(research_run.dataset),
                "templates": research_run.templates.selected_templates,
                "parameter_search": {
                    key: list(value) for key, value in research_run.parameters.search_space.items()
                },
            },
            next_experiments=next_experiments,
            reasons=tuple(reasons),
            hypothesis_status=hypothesis.status.value,
            confidence=hypothesis.confidence,
            research_run=research_run,
        )

    def run_research(self, request: ResearchOrchestrationRequest) -> OrchestratedResearchRun:
        return self.plan(request).research_run or self._empty_research_run(request)

    def collect_results(self, result: ExperimentResultKnowledge) -> tuple[Any, ...]:
        return self._knowledge_engine.collect_results(result)

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
            "research_run": _dataclass_payload(plan.research_run),
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

    def _build_research_run(
        self,
        request: ResearchOrchestrationRequest,
        best_features: tuple[KnowledgeScore, ...],
        best_plugins: tuple[KnowledgeScore, ...],
        blocked_plugins: tuple[str, ...],
    ) -> OrchestratedResearchRun:
        dataset = DatasetPlanner().plan(request)
        features = FeaturePlanner().plan(request, best_features)
        templates = TemplatePlanner(self._knowledge_engine).plan(request, best_plugins, blocked_plugins)
        parameters = ParameterPlanner(self._knowledge_engine).plan(request)
        experiment_count = request.max_experiments if templates.selected_templates else 0
        jobs = JobScheduler().schedule(request.hypothesis_id, experiment_count)
        return OrchestratedResearchRun(
            research_goal=request.research_goal,
            experiment_count=experiment_count,
            dataset=dataset,
            features=features,
            templates=templates,
            parameters=parameters,
            jobs=jobs,
            progress=ProgressMonitor().snapshot(jobs),
        )

    def _empty_research_run(self, request: ResearchOrchestrationRequest) -> OrchestratedResearchRun:
        jobs: tuple[ResearchJob, ...] = ()
        return OrchestratedResearchRun(
            research_goal=request.research_goal,
            experiment_count=0,
            dataset=DatasetPlanner().plan(request),
            features=FeaturePlan((), request.required_features, "No features selected."),
            templates=TemplatePlan((), (), (), "No templates selected."),
            parameters=ParameterPlan({}, {}, ()),
            jobs=jobs,
            progress=ProgressMonitor().snapshot(jobs),
        )

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


class DatasetPlanner:
    def plan(self, request: ResearchOrchestrationRequest) -> DatasetPlan:
        return DatasetPlan(
            instruments=(request.context.instrument,),
            timeframes=(request.context.timeframe,),
            date_range="last_24_months",
            training_period="first_18_months",
            validation_period="last_6_months",
        )


class FeaturePlanner:
    _REGIME_DEFAULTS = {
        "TRENDING": ("trend_strength", "pullback_state", "momentum_slope", "volatility_state"),
        "RANGING": ("range_position", "mean_reversion_pressure", "volatility_state", "session_state"),
        "HIGH_VOLATILITY": ("volatility_state", "atr_expansion", "risk_compression", "session_state"),
    }

    def plan(
        self,
        request: ResearchOrchestrationRequest,
        best_features: tuple[KnowledgeScore, ...],
    ) -> FeaturePlan:
        knowledge_features = tuple(score.object_id for score in best_features)
        defaults = self._REGIME_DEFAULTS.get(
            request.context.market_regime.upper(),
            ("trend_strength", "volatility_state"),
        )
        selected = _ordered_unique(request.required_features + knowledge_features + defaults)
        return FeaturePlan(
            selected_features=selected,
            required_features=request.required_features,
            reason="Features combine request requirements, Knowledge Base scores, and regime defaults.",
        )


class TemplatePlanner:
    def __init__(self, knowledge_engine: KnowledgeEngine) -> None:
        self._knowledge_engine = knowledge_engine

    def plan(
        self,
        request: ResearchOrchestrationRequest,
        best_plugins: tuple[KnowledgeScore, ...],
        blocked_plugins: tuple[str, ...],
    ) -> TemplatePlan:
        template_scores = self._knowledge_engine.scoring.score_repository(
            self._knowledge_engine.repository,
            KnowledgeObjectType.TEMPLATE,
        )
        knowledge_templates = tuple(
            score.object_id
            for score in template_scores
            if score.recommendation in {RecommendationLevel.HIGH, RecommendationLevel.MEDIUM}
        )
        selected_templates = _ordered_unique(
            request.candidate_templates + knowledge_templates + (self._fallback_template(request),)
        )
        selected_plugins = _ordered_unique(
            plugin
            for plugin in request.candidate_plugins + tuple(score.object_id for score in best_plugins)
            if plugin not in blocked_plugins
        )
        return TemplatePlan(
            selected_templates=selected_templates,
            selected_plugins=selected_plugins,
            blocked_plugins=blocked_plugins,
            reason="Template and plugin choices are constrained by Knowledge Base success and blocked failures.",
        )

    def _fallback_template(self, request: ResearchOrchestrationRequest) -> str:
        text = f"{request.research_goal} {request.hypothesis_statement} {request.context.market_regime}".lower()
        if "pullback" in text or "trend" in text:
            return "trend_pullback"
        if "range" in text or "reversion" in text:
            return "mean_reversion"
        if "breakout" in text:
            return "breakout"
        return "research_candidate"


class ParameterPlanner:
    def __init__(self, knowledge_engine: KnowledgeEngine) -> None:
        self._knowledge_engine = knowledge_engine

    def plan(self, request: ResearchOrchestrationRequest) -> ParameterPlan:
        unstable = self._knowledge_engine.recommendations.unstable_parameters(self._knowledge_engine.repository)
        avoided = tuple(score.object_id for score in unstable if score.recommendation == RecommendationLevel.IGNORE)
        narrowed: dict[str, Any] = {}
        search_space: dict[str, tuple[Any, ...]] = {}

        if "pullback" in request.hypothesis_statement.lower() or "trend" in request.research_goal.lower():
            search_space["ema_fast"] = (20, 30, 40, 50)
            search_space["ema_slow"] = (80, 100, 120, 150)
            narrowed["ema_fast"] = "Knowledge-guided 20-50 range instead of broad 5-200 sweep."
        else:
            search_space["lookback"] = (14, 20, 30, 50)

        if "rsi_threshold=30" not in avoided:
            search_space["rsi_threshold"] = (25, 30, 35)

        return ParameterPlan(
            search_space=search_space,
            narrowed_by_knowledge=narrowed,
            avoided_parameters=avoided,
        )


class JobScheduler:
    def schedule(self, hypothesis_id: str, experiment_count: int) -> tuple[ResearchJob, ...]:
        jobs: list[ResearchJob] = []
        for index in range(1, experiment_count + 1):
            research_id = f"{hypothesis_id}_research_{index:03d}"
            optimization_id = f"{hypothesis_id}_optimization_{index:03d}"
            backtest_id = f"{hypothesis_id}_backtest_{index:03d}"
            validation_id = f"{hypothesis_id}_validation_{index:03d}"
            jobs.extend(
                (
                    ResearchJob(research_id, ResearchJobType.RESEARCH),
                    ResearchJob(optimization_id, ResearchJobType.OPTIMIZATION, depends_on=(research_id,)),
                    ResearchJob(backtest_id, ResearchJobType.BACKTEST, depends_on=(optimization_id,)),
                    ResearchJob(validation_id, ResearchJobType.VALIDATION, depends_on=(backtest_id,)),
                )
            )
        validation_jobs = tuple(job.job_id for job in jobs if job.job_type == ResearchJobType.VALIDATION)
        jobs.append(ResearchJob(f"{hypothesis_id}_knowledge_update", ResearchJobType.KNOWLEDGE_UPDATE, validation_jobs))
        return tuple(jobs)


class ProgressMonitor:
    def snapshot(self, jobs: tuple[ResearchJob, ...]) -> ProgressSnapshot:
        return ProgressSnapshot(
            queued=sum(job.status == ResearchJobStatus.QUEUED for job in jobs),
            running=sum(job.status == ResearchJobStatus.RUNNING for job in jobs),
            completed=sum(job.status == ResearchJobStatus.COMPLETED for job in jobs),
            failed=sum(job.status == ResearchJobStatus.FAILED for job in jobs),
            total=len(jobs),
        )


def _ordered_unique(values: Any) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if value))


def _dataclass_payload(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "__dataclass_fields__"):
        payload: dict[str, Any] = {}
        for field_name in value.__dataclass_fields__:
            payload[field_name] = _dataclass_payload(getattr(value, field_name))
        return payload
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, tuple):
        return [_dataclass_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: _dataclass_payload(item) for key, item in value.items()}
    return value
