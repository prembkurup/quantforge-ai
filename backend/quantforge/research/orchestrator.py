import json
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
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


class AlwaysOnResearchState(StrEnum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    IDLE = "IDLE"
    WAITING_FOR_SCHEDULE = "WAITING_FOR_SCHEDULE"
    CHECKING_COVERAGE = "CHECKING_COVERAGE"
    CHECKING_GUARDRAILS = "CHECKING_GUARDRAILS"
    LAUNCHING_JOBS = "LAUNCHING_JOBS"
    RUNNING_RESEARCH = "RUNNING_RESEARCH"
    PUBLISHING_RESULTS = "PUBLISHING_RESULTS"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"


class IdleReasonCode(StrEnum):
    WAITING_FOR_SCHEDULE = "WAITING_FOR_SCHEDULE"
    NO_USABLE_DATASETS = "NO_USABLE_DATASETS"
    NO_WEAK_COVERAGE = "NO_WEAK_COVERAGE"
    NO_STALE_PROGRAMS = "NO_STALE_PROGRAMS"
    INPUTS_UNCHANGED = "INPUTS_UNCHANGED"
    GUARDRAIL_BLOCKED = "GUARDRAIL_BLOCKED"
    QUEUE_STOPPED = "QUEUE_STOPPED"
    WORKER_STOPPED = "WORKER_STOPPED"
    RESEARCH_IN_PROGRESS = "RESEARCH_IN_PROGRESS"
    FINE_TUNING_GATED = "FINE_TUNING_GATED"
    MAX_JOBS_IN_FLIGHT = "MAX_JOBS_IN_FLIGHT"
    ERROR = "ERROR"
    MANUALLY_STOPPED = "MANUALLY_STOPPED"


@dataclass(frozen=True, slots=True)
class AlwaysOnResearchThresholds:
    min_assets_per_program: int = 1
    stale_after_hours: int = 6
    force_rerun_after_hours: int = 24
    max_jobs_per_pass: int = 12
    schedule_seconds: int = 900
    max_jobs_in_flight: int = 24
    target_families: int = 1
    target_regimes: int = 1


@dataclass(frozen=True, slots=True)
class AlwaysOnOrchestratorPaths:
    status_file: Path
    runs_file: Path
    idle_reasons_file: Path
    guardrails_file: Path
    history_validation_improvements_file: Path | None = None


@dataclass(frozen=True, slots=True)
class IdleReason:
    state: AlwaysOnResearchState
    reason_code: IdleReasonCode
    message: str
    last_checked_at: str
    next_check_at: str
    details: dict[str, Any]


@dataclass(frozen=True, slots=True)
class AlwaysOnRunRecord:
    run_id: str
    started_at: str
    finished_at: str
    state: AlwaysOnResearchState
    trigger: str
    datasets_checked: int
    programs_checked: int
    jobs_launched: int
    candidates_generated: int
    assets_approved: int
    candidates_rejected: int
    idle_reason_code: str | None
    errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AlwaysOnOrchestratorStatus:
    enabled: bool
    state: AlwaysOnResearchState
    running: bool
    last_run_id: str
    last_checked_at: str
    next_check_at: str
    idle_reason: IdleReason | None
    jobs_in_flight: int
    last_jobs_launched: int
    last_error: str | None
    totals: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ResearchProgramPriority:
    program_id: str
    pair: str
    timeframe: str
    priority: float
    days_since_last_run: float
    approved_assets: int
    asset_count_gap: int
    observed_families: int
    observed_regimes: int
    family_diversity_gap: int
    regime_diversity_gap: int
    rejection_rate: float
    stale: bool
    weak: bool


@dataclass(frozen=True, slots=True)
class GuardrailDecision:
    program_id: str
    pair: str
    timeframe: str
    blocked: bool
    reason_code: str
    message: str
    last_run_at: str
    checked_at: str


class FineTuningState(StrEnum):
    DISABLED = "DISABLED"
    MANUAL = "MANUAL"
    GATED = "GATED"
    WAITING_FOR_NEW_ASSETS = "WAITING_FOR_NEW_ASSETS"
    TRAINING = "TRAINING"
    EVALUATING = "EVALUATING"
    READY_TO_PROMOTE = "READY_TO_PROMOTE"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"


class AlwaysOnAutonomousResearchOrchestrator:
    """Coordinates recurring multi-market research passes above fan-out.

    This layer owns wake/check/launch/status persistence. It delegates actual
    candidate generation and Strategy Asset publication to the Milestone 23
    multi-market fan-out implementation.
    """

    def __init__(
        self,
        *,
        planned_jobs: tuple[Any, ...],
        full_history_state_file: Path,
        paths: AlwaysOnOrchestratorPaths,
        thresholds: AlwaysOnResearchThresholds | None = None,
        research_runner: Any | None = None,
    ) -> None:
        self.planned_jobs = planned_jobs
        self.full_history_state_file = full_history_state_file
        self.paths = paths
        self.thresholds = thresholds or AlwaysOnResearchThresholds()
        self.research_runner = research_runner or self._run_programs

    def run_once(self, *, trigger: str = "scheduler") -> AlwaysOnRunRecord:
        started = _utc_now()
        run_id = f"orch_{started.strftime('%Y%m%d_%H%M%S')}"
        previous_status = _load_json_file(self.paths.status_file)
        if not self._enabled(previous_status):
            idle_reason = IdleReason(
                state=AlwaysOnResearchState.STOPPED,
                reason_code=IdleReasonCode.MANUALLY_STOPPED,
                message="Always-on research orchestrator is disabled.",
                last_checked_at=started.isoformat(),
                next_check_at="",
                details={},
            )
            self._record_idle_reason(idle_reason)
            record = AlwaysOnRunRecord(
                run_id=run_id,
                started_at=started.isoformat(),
                finished_at=started.isoformat(),
                state=AlwaysOnResearchState.STOPPED,
                trigger=trigger,
                datasets_checked=0,
                programs_checked=0,
                jobs_launched=0,
                candidates_generated=0,
                assets_approved=0,
                candidates_rejected=0,
                idle_reason_code=IdleReasonCode.MANUALLY_STOPPED.value,
                errors=(),
            )
            self._record_run(record)
            self._persist_status(
                AlwaysOnResearchState.STOPPED,
                run_id=run_id,
                checked_at=started,
                idle_reason=idle_reason,
                jobs_in_flight=0,
                last_jobs_launched=0,
                last_error=None,
                totals={},
            )
            return record
        errors: list[str] = []
        idle_reason: IdleReason | None = None
        jobs_launched = 0
        candidates_generated = 0
        assets_before = 0
        assets_after = 0
        rejected_before = 0
        rejected_after = 0
        rows: tuple[Any, ...] = ()
        programs: tuple[Any, ...] = ()

        try:
            self._persist_status(
                AlwaysOnResearchState.CHECKING_COVERAGE,
                run_id=run_id,
                checked_at=started,
                idle_reason=None,
                jobs_in_flight=0,
                last_jobs_launched=0,
                last_error=None,
                totals={},
            )
            matrix, rows, programs, assets, rejected = self._snapshot()
            assets_before = len(assets)
            rejected_before = len(rejected)
            priorities = self.score_programs(rows, programs, assets, rejected, checked_at=started)
            improvement_requests = self._requested_improvements()
            targets = self._target_programs(programs, priorities, improvement_requests=improvement_requests)
            idle_reason = self._idle_reason_if_no_work(rows, programs, targets, started, improvement_requests)
            if idle_reason is None:
                self._persist_status(
                    AlwaysOnResearchState.CHECKING_GUARDRAILS,
                    run_id=run_id,
                    checked_at=started,
                    idle_reason=None,
                    jobs_in_flight=0,
                    last_jobs_launched=0,
                    last_error=None,
                    totals=self._totals_from_priorities(rows, programs, priorities, improvement_requests),
                )
                guardrails = self._guardrail_decisions(
                    rows,
                    targets,
                    assets,
                    rejected,
                    started,
                    previous_status,
                    improvement_requests=improvement_requests,
                )
                self._record_guardrails(guardrails)
                targets = tuple(
                    program
                    for program in targets
                    if not any(decision.program_id == program.program_id and decision.blocked for decision in guardrails)
                )
                idle_reason = self._guardrail_idle_reason(rows, programs, targets, guardrails, started, previous_status)
            if idle_reason is not None:
                self._record_idle_reason(idle_reason)
                finished = _utc_now()
                record = AlwaysOnRunRecord(
                    run_id=run_id,
                    started_at=started.isoformat(),
                    finished_at=finished.isoformat(),
                    state=idle_reason.state,
                    trigger=trigger,
                    datasets_checked=len(rows),
                    programs_checked=len(programs),
                    jobs_launched=0,
                    candidates_generated=0,
                    assets_approved=0,
                    candidates_rejected=0,
                    idle_reason_code=idle_reason.reason_code.value,
                    errors=(),
                )
                self._record_run(record)
                self._persist_status(
                    idle_reason.state,
                    run_id=run_id,
                    checked_at=started,
                    idle_reason=idle_reason,
                    jobs_in_flight=0,
                    last_jobs_launched=0,
                    last_error=None,
                    totals=self._totals_from_priorities(rows, programs, priorities, improvement_requests),
                )
                return record

            target_ids = {program.program_id for program in targets}
            launched_improvements = tuple(
                item for item in improvement_requests if _improvement_program_id(item) in target_ids
            )
            self._persist_status(
                AlwaysOnResearchState.LAUNCHING_JOBS,
                run_id=run_id,
                checked_at=started,
                idle_reason=None,
                jobs_in_flight=len(targets),
                last_jobs_launched=0,
                last_error=None,
                totals=self._totals_from_priorities(rows, programs, priorities, improvement_requests),
            )
            jobs_launched = len(targets)
            candidates_generated = sum(int(program.candidate_count) for program in targets)
            self._mark_improvements(launched_improvements, "RESEARCH_RUNNING", run_id=run_id, checked_at=started)
            self.research_runner(tuple(targets))
            self._mark_improvements(launched_improvements, "RESEARCHED", run_id=run_id, checked_at=_utc_now())
            _matrix, _rows, _programs, assets_after_rows, rejected_after_rows = self._snapshot()
            assets_after = len(assets_after_rows)
            rejected_after = len(rejected_after_rows)
            finished = _utc_now()
            finished_priorities = self.score_programs(_rows, _programs, assets_after_rows, rejected_after_rows, checked_at=finished)
            remaining_improvements = self._requested_improvements()
            record = AlwaysOnRunRecord(
                run_id=run_id,
                started_at=started.isoformat(),
                finished_at=finished.isoformat(),
                state=AlwaysOnResearchState.PUBLISHING_RESULTS,
                trigger=trigger,
                datasets_checked=len(rows),
                programs_checked=len(programs),
                jobs_launched=jobs_launched,
                candidates_generated=candidates_generated,
                assets_approved=max(0, assets_after - assets_before),
                candidates_rejected=max(0, rejected_after - rejected_before),
                idle_reason_code=None,
                errors=(),
            )
            self._record_run(record)
            self._persist_status(
                AlwaysOnResearchState.WAITING_FOR_SCHEDULE,
                run_id=run_id,
                checked_at=finished,
                idle_reason=self._waiting_for_schedule(finished, len(_rows), len(_programs)),
                jobs_in_flight=0,
                last_jobs_launched=jobs_launched,
                last_error=None,
                totals=self._totals_from_priorities(_rows, _programs, finished_priorities, remaining_improvements),
            )
            return record
        except Exception as exc:
            errors.append(str(exc))
            finished = _utc_now()
            idle_reason = IdleReason(
                state=AlwaysOnResearchState.ERROR,
                reason_code=IdleReasonCode.ERROR,
                message=f"Always-on research orchestrator failed: {exc}",
                last_checked_at=finished.isoformat(),
                next_check_at=self._next_check(finished).isoformat(),
                details={"errors": errors},
            )
            self._record_idle_reason(idle_reason)
            record = AlwaysOnRunRecord(
                run_id=run_id,
                started_at=started.isoformat(),
                finished_at=finished.isoformat(),
                state=AlwaysOnResearchState.ERROR,
                trigger=trigger,
                datasets_checked=len(rows),
                programs_checked=len(programs),
                jobs_launched=jobs_launched,
                candidates_generated=candidates_generated,
                assets_approved=0,
                candidates_rejected=0,
                idle_reason_code=IdleReasonCode.ERROR.value,
                errors=tuple(errors),
            )
            self._record_run(record)
            self._persist_status(
                AlwaysOnResearchState.ERROR,
                run_id=run_id,
                checked_at=finished,
                idle_reason=idle_reason,
                jobs_in_flight=0,
                last_jobs_launched=jobs_launched,
                last_error=str(exc),
                totals={},
            )
            return record

    def run_forever(self, *, sleep: Any = time.sleep) -> None:
        while True:
            record = self.run_once(trigger="scheduler")
            if record.state == AlwaysOnResearchState.ERROR:
                sleep(min(self.thresholds.schedule_seconds, 300))
                continue
            sleep(self.thresholds.schedule_seconds)

    def current_status(self) -> dict[str, Any]:
        payload = _load_json_file(self.paths.status_file)
        if payload:
            payload["enabled"] = self._enabled(payload)
            payload["last_run_at"] = payload.get("last_checked_at", "")
            payload["next_run_at"] = payload.get("next_check_at", "")
            payload["last_idle_reason_code"] = (payload.get("idle_reason") or {}).get("reason_code")
            payload.setdefault("last_error", None)
            return payload
        checked_at = _utc_now()
        idle_reason = IdleReason(
            state=AlwaysOnResearchState.STOPPED,
            reason_code=IdleReasonCode.MANUALLY_STOPPED,
            message="Always-on research orchestrator has not run yet.",
            last_checked_at=checked_at.isoformat(),
            next_check_at="",
            details={},
        )
        return _payload(
            AlwaysOnOrchestratorStatus(
                enabled=self._enabled(),
                state=AlwaysOnResearchState.STOPPED,
                running=False,
                last_run_id="",
                last_checked_at=checked_at.isoformat(),
                next_check_at="",
                idle_reason=idle_reason,
                jobs_in_flight=0,
                last_jobs_launched=0,
                last_error=None,
                totals={},
            )
        ) | {"last_run_at": checked_at.isoformat(), "next_run_at": "", "last_idle_reason_code": "MANUALLY_STOPPED"}

    def runs(self) -> list[dict[str, Any]]:
        return list(_load_json_file(self.paths.runs_file).get("runs", []))

    def idle_reasons(self) -> list[dict[str, Any]]:
        return list(_load_json_file(self.paths.idle_reasons_file).get("idle_reasons", []))

    def latest_idle_reason(self) -> dict[str, Any]:
        reasons = self.idle_reasons()
        return reasons[-1] if reasons else self.current_status().get("idle_reason", {})

    def guardrails(self) -> list[dict[str, Any]]:
        return list(_load_json_file(self.paths.guardrails_file).get("guardrails", []))

    def stop(self) -> dict[str, Any]:
        status = self.current_status()
        status["enabled"] = False
        status["state"] = AlwaysOnResearchState.STOPPED.value
        status["running"] = False
        status["last_idle_reason_code"] = IdleReasonCode.MANUALLY_STOPPED.value
        status["idle_reason"] = _payload(
            IdleReason(
                state=AlwaysOnResearchState.STOPPED,
                reason_code=IdleReasonCode.MANUALLY_STOPPED,
                message="Always-on research orchestrator was disabled manually.",
                last_checked_at=_utc_now().isoformat(),
                next_check_at="",
                details={},
            )
        )
        self._write_json(self.paths.status_file, status)
        return status

    def start(self) -> dict[str, Any]:
        status = self.current_status()
        now = _utc_now()
        status["enabled"] = True
        status["state"] = AlwaysOnResearchState.WAITING_FOR_SCHEDULE.value
        status["running"] = False
        status["next_check_at"] = now.isoformat()
        status["next_run_at"] = now.isoformat()
        status["idle_reason"] = _payload(self._waiting_for_schedule(now, 0, 0))
        status["last_idle_reason_code"] = IdleReasonCode.WAITING_FOR_SCHEDULE.value
        self._write_json(self.paths.status_file, status)
        return status

    def fine_tuning_status(self) -> dict[str, Any]:
        assets = self._snapshot()[3]
        latest_asset_at = max((asset.approved_at for asset in assets), default="")
        state = FineTuningState.GATED if assets else FineTuningState.WAITING_FOR_NEW_ASSETS
        return {
            "state": state.value,
            "mode": "manual",
            "latest_asset_at": latest_asset_at,
            "eligible_assets": len(assets),
            "message": "Fine-tuning is visible but remains gated/manual until promotion automation is enabled.",
            "last_checked_at": _utc_now().isoformat(),
        }

    def _snapshot(self) -> tuple[Any, tuple[Any, ...], tuple[Any, ...], tuple[Any, ...], tuple[Any, ...]]:
        from quantforge.research.multi_market import MultiMarketResearchPlanner, ResearchMatrixBuilder

        matrix = ResearchMatrixBuilder(self.planned_jobs, self.full_history_state_file)
        rows = matrix.rows()
        programs = MultiMarketResearchPlanner().plan(matrix.datasets())
        assets = matrix.asset_repository.list()
        rejected = matrix.rejection_repository.list()
        return matrix, rows, programs, assets, rejected

    def score_programs(
        self,
        rows: tuple[Any, ...],
        programs: tuple[Any, ...],
        assets: tuple[Any, ...],
        rejected: tuple[Any, ...],
        *,
        checked_at: datetime | None = None,
    ) -> tuple[ResearchProgramPriority, ...]:
        checked_at = checked_at or _utc_now()
        row_by_key = {(row.pair, row.timeframe): row for row in rows}
        priorities: list[ResearchProgramPriority] = []
        for program in programs:
            row = row_by_key[(program.dataset.pair, program.dataset.timeframe)]
            scoped_assets = tuple(
                asset for asset in assets if asset.pair == program.dataset.pair and asset.timeframe == program.dataset.timeframe
            )
            scoped_rejected = tuple(
                item for item in rejected if item.pair == program.dataset.pair and item.timeframe == program.dataset.timeframe
            )
            last_run_at = _latest_timestamp(
                tuple(asset.approved_at for asset in scoped_assets) + tuple(item.timestamp for item in scoped_rejected)
            )
            days_since_last_run = (
                (checked_at - last_run_at).total_seconds() / 86400 if last_run_at else self.thresholds.force_rerun_after_hours / 24
            )
            observed_families = len({asset.strategy_family for asset in scoped_assets})
            observed_regimes = len({asset.market_regime for asset in scoped_assets})
            asset_gap = max(0, self.thresholds.min_assets_per_program - row.approved_asset_count)
            family_gap = max(0, self.thresholds.target_families - observed_families)
            regime_gap = max(0, self.thresholds.target_regimes - observed_regimes)
            rejection_rate = round(len(scoped_rejected) / max(1, len(scoped_rejected) + len(scoped_assets)), 4)
            stale = bool(last_run_at and (checked_at - last_run_at) >= timedelta(hours=self.thresholds.stale_after_hours))
            weak = row.usable_for_research and (asset_gap > 0 or family_gap > 0 or regime_gap > 0)
            priority = round(days_since_last_run + asset_gap + family_gap + regime_gap - rejection_rate, 4)
            priorities.append(
                ResearchProgramPriority(
                    program_id=program.program_id,
                    pair=program.dataset.pair,
                    timeframe=program.dataset.timeframe,
                    priority=priority,
                    days_since_last_run=round(days_since_last_run, 4),
                    approved_assets=row.approved_asset_count,
                    asset_count_gap=asset_gap,
                    observed_families=observed_families,
                    observed_regimes=observed_regimes,
                    family_diversity_gap=family_gap,
                    regime_diversity_gap=regime_gap,
                    rejection_rate=rejection_rate,
                    stale=stale,
                    weak=weak,
                )
            )
        return tuple(sorted(priorities, key=lambda item: item.priority, reverse=True))

    def _target_programs(
        self,
        programs: tuple[Any, ...],
        priorities: tuple[ResearchProgramPriority, ...],
        *,
        improvement_requests: tuple[dict[str, Any], ...] = (),
    ) -> tuple[Any, ...]:
        program_by_id = {program.program_id: program for program in programs}
        improvement_target_ids = [
            program_id
            for program_id in (_improvement_program_id(item) for item in improvement_requests)
            if program_id in program_by_id
        ]
        threshold_target_ids = [
            priority.program_id
            for priority in priorities
            if priority.priority > 0 and (priority.weak or priority.stale)
        ]
        target_ids = list(dict.fromkeys(improvement_target_ids + threshold_target_ids))
        return tuple(program_by_id[program_id] for program_id in target_ids[: self.thresholds.max_jobs_per_pass])

    def _idle_reason_if_no_work(
        self,
        rows: tuple[Any, ...],
        programs: tuple[Any, ...],
        targets: tuple[Any, ...],
        checked_at: datetime,
        improvement_requests: tuple[dict[str, Any], ...] = (),
    ) -> IdleReason | None:
        usable = sum(row.usable_for_research for row in rows)
        weak = sum(row.usable_for_research and row.approved_asset_count < self.thresholds.min_assets_per_program for row in rows)
        blocked = sum(not row.usable_for_research for row in rows)
        details = {
            "usable_datasets": usable,
            "research_programs": len(programs),
            "coverage_pct": round((usable / len(rows)) * 100, 2) if rows else 0,
            "weak_programs": weak,
            "stale_programs": 0,
            "blocked_programs": blocked,
            "history_validation_improvement_requests": len(improvement_requests),
        }
        if not rows or usable == 0:
            return IdleReason(
                state=AlwaysOnResearchState.IDLE,
                reason_code=IdleReasonCode.NO_USABLE_DATASETS,
                message="No pair/timeframe datasets have completed all full-history research gates yet.",
                last_checked_at=checked_at.isoformat(),
                next_check_at=self._next_check(checked_at).isoformat(),
                details=details,
            )
        if not targets:
            return IdleReason(
                state=AlwaysOnResearchState.IDLE,
                reason_code=IdleReasonCode.NO_WEAK_COVERAGE,
                message="All pair/timeframe research programs currently meet coverage and productivity thresholds.",
                last_checked_at=checked_at.isoformat(),
                next_check_at=self._next_check(checked_at).isoformat(),
                details=details,
            )
        return None

    def _guardrail_idle_reason(
        self,
        rows: tuple[Any, ...],
        programs: tuple[Any, ...],
        targets: tuple[Any, ...],
        guardrails: tuple[GuardrailDecision, ...],
        checked_at: datetime,
        previous_status: dict[str, Any],
    ) -> IdleReason | None:
        jobs_in_flight = int(previous_status.get("jobs_in_flight", 0) or 0)
        if jobs_in_flight >= self.thresholds.max_jobs_in_flight:
            return IdleReason(
                state=AlwaysOnResearchState.BLOCKED,
                reason_code=IdleReasonCode.MAX_JOBS_IN_FLIGHT,
                message="Research launch is blocked because the orchestrator already has the maximum jobs in flight.",
                last_checked_at=checked_at.isoformat(),
                next_check_at=self._next_check(checked_at).isoformat(),
                details={
                    "datasets": len(rows),
                    "usable_datasets": sum(row.usable_for_research for row in rows),
                    "research_programs": len(programs),
                    "weak_programs": len(targets),
                    "stale_programs": 0,
                    "blocked_programs": sum(not row.usable_for_research for row in rows),
                    "jobs_in_flight": jobs_in_flight,
                    "max_jobs_in_flight": self.thresholds.max_jobs_in_flight,
                },
            )
        if guardrails and not targets:
            blocked = tuple(decision for decision in guardrails if decision.blocked)
            reason = blocked[0] if blocked else None
            return IdleReason(
                state=AlwaysOnResearchState.BLOCKED,
                reason_code=IdleReasonCode(str(reason.reason_code if reason else IdleReasonCode.GUARDRAIL_BLOCKED.value)),
                message=reason.message if reason else "All candidate research programs were blocked by guardrails.",
                last_checked_at=checked_at.isoformat(),
                next_check_at=self._next_check(checked_at).isoformat(),
                details={"blocked_programs": len(blocked), "guardrails": [_payload(item) for item in blocked[:20]]},
            )
        return None

    def _guardrail_decisions(
        self,
        rows: tuple[Any, ...],
        targets: tuple[Any, ...],
        assets: tuple[Any, ...],
        rejected: tuple[Any, ...],
        checked_at: datetime,
        previous_status: dict[str, Any],
        *,
        improvement_requests: tuple[dict[str, Any], ...] = (),
    ) -> tuple[GuardrailDecision, ...]:
        row_by_key = {(row.pair, row.timeframe): row for row in rows}
        improvement_program_ids = {_improvement_program_id(item) for item in improvement_requests}
        decisions: list[GuardrailDecision] = []
        jobs_in_flight = int(previous_status.get("jobs_in_flight", 0) or 0)
        for program in targets:
            row = row_by_key.get((program.dataset.pair, program.dataset.timeframe))
            last_run_at = _latest_timestamp(
                tuple(
                    asset.approved_at
                    for asset in assets
                    if asset.pair == program.dataset.pair and asset.timeframe == program.dataset.timeframe
                )
                + tuple(
                    item.timestamp
                    for item in rejected
                    if item.pair == program.dataset.pair and item.timeframe == program.dataset.timeframe
                )
            )
            blocked = False
            reason_code = "OK"
            message = "Research program passed launch guardrails."
            if row is None:
                blocked, reason_code, message = True, "NO_USABLE_DATASETS", "Research matrix row does not exist."
            elif not row.usable_for_research:
                blocked, reason_code, message = True, "NO_USABLE_DATASETS", "Dataset is not usable for research."
            elif jobs_in_flight >= self.thresholds.max_jobs_in_flight:
                blocked, reason_code, message = True, "MAX_JOBS_IN_FLIGHT", "Maximum in-flight research jobs reached."
            elif (
                program.program_id not in improvement_program_ids
                and last_run_at
                and checked_at - last_run_at < timedelta(hours=self.thresholds.stale_after_hours)
            ):
                blocked = True
                reason_code = "INPUTS_UNCHANGED"
                message = "Skipped because dataset and model inputs have not changed since last successful run."
            elif program.program_id in improvement_program_ids:
                message = "Historical validation requested new research for this pair/timeframe."
            decisions.append(
                GuardrailDecision(
                    program_id=program.program_id,
                    pair=program.dataset.pair,
                    timeframe=program.dataset.timeframe,
                    blocked=blocked,
                    reason_code=reason_code,
                    message=message,
                    last_run_at=last_run_at.isoformat() if last_run_at else "",
                    checked_at=checked_at.isoformat(),
                )
            )
        return tuple(decisions)

    def _waiting_for_schedule(self, checked_at: datetime, datasets: int, programs: int) -> IdleReason:
        return IdleReason(
            state=AlwaysOnResearchState.WAITING_FOR_SCHEDULE,
            reason_code=IdleReasonCode.WAITING_FOR_SCHEDULE,
            message="Research pass completed; orchestrator is waiting for the next scheduled wake-up.",
            last_checked_at=checked_at.isoformat(),
            next_check_at=self._next_check(checked_at).isoformat(),
            details={"usable_datasets": datasets, "research_programs": programs},
        )

    def _run_programs(self, programs: tuple[Any, ...]) -> None:
        from quantforge.research.multi_market import MultiMarketAutonomousResearchFanOut
        from quantforge.validation import StrategyValidationPlatform

        if not programs:
            return
        base_report = StrategyValidationPlatform().validate("QF-2026-M24-BASE")
        MultiMarketAutonomousResearchFanOut().run(
            programs=programs,
            base_report=base_report,
            source_workflow_id=f"Milestone 24 always-on orchestrator {_utc_now().isoformat()}",
        )

    def _persist_status(
        self,
        state: AlwaysOnResearchState,
        *,
        run_id: str,
        checked_at: datetime,
        idle_reason: IdleReason | None,
        jobs_in_flight: int,
        last_jobs_launched: int,
        last_error: str | None,
        totals: dict[str, Any],
    ) -> None:
        status = AlwaysOnOrchestratorStatus(
            enabled=self._enabled(),
            state=state,
            running=state
            in {
                AlwaysOnResearchState.CHECKING_COVERAGE,
                AlwaysOnResearchState.CHECKING_GUARDRAILS,
                AlwaysOnResearchState.LAUNCHING_JOBS,
                AlwaysOnResearchState.RUNNING_RESEARCH,
                AlwaysOnResearchState.PUBLISHING_RESULTS,
            },
            last_run_id=run_id,
            last_checked_at=checked_at.isoformat(),
            next_check_at=self._next_check(checked_at).isoformat() if state != AlwaysOnResearchState.ERROR else "",
            idle_reason=idle_reason,
            jobs_in_flight=jobs_in_flight,
            last_jobs_launched=last_jobs_launched,
            last_error=last_error,
            totals=totals,
        )
        payload = _payload(status)
        payload["last_run_at"] = payload["last_checked_at"]
        payload["next_run_at"] = payload["next_check_at"]
        payload["last_idle_reason_code"] = (payload.get("idle_reason") or {}).get("reason_code")
        self._write_json(self.paths.status_file, payload)

    def _record_run(self, record: AlwaysOnRunRecord) -> None:
        payload = _load_json_file(self.paths.runs_file)
        runs = list(payload.get("runs", []))
        runs.append(_payload(record))
        self._write_json(self.paths.runs_file, {"version": 1, "runs": runs[-500:]})

    def _record_idle_reason(self, reason: IdleReason) -> None:
        payload = _load_json_file(self.paths.idle_reasons_file)
        reasons = list(payload.get("idle_reasons", []))
        reasons.append(_payload(reason))
        self._write_json(self.paths.idle_reasons_file, {"version": 1, "idle_reasons": reasons[-500:]})

    def _record_guardrails(self, decisions: tuple[GuardrailDecision, ...]) -> None:
        payload = _load_json_file(self.paths.guardrails_file)
        guardrails = list(payload.get("guardrails", []))
        guardrails.extend(_payload(decision) for decision in decisions)
        self._write_json(self.paths.guardrails_file, {"version": 1, "guardrails": guardrails[-1000:]})

    def _requested_improvements(self) -> tuple[dict[str, Any], ...]:
        path = self.paths.history_validation_improvements_file
        if path is None:
            return ()
        improvements = _load_json_file(path).get("improvements", [])
        return tuple(
            item
            for item in improvements
            if str(item.get("status", "")).upper() == "REQUESTED"
            and item.get("pair")
            and item.get("timeframe")
        )

    def _mark_improvements(
        self,
        improvements: tuple[dict[str, Any], ...],
        status: str,
        *,
        run_id: str,
        checked_at: datetime,
    ) -> None:
        path = self.paths.history_validation_improvements_file
        if path is None or not improvements:
            return
        payload = _load_json_file(path)
        requested_ids = {str(item.get("improvement_id")) for item in improvements}
        rows = []
        for item in payload.get("improvements", []):
            if str(item.get("improvement_id")) not in requested_ids:
                rows.append(item)
                continue
            rows.append(
                {
                    **item,
                    "status": status,
                    "research_run_id": run_id,
                    "research_program_id": _improvement_program_id(item),
                    "research_updated_at": checked_at.isoformat(),
                }
            )
        self._write_json(path, {"version": 1, "improvements": rows})

    def _enabled(self, payload: dict[str, Any] | None = None) -> bool:
        if payload is not None and "enabled" in payload:
            return bool(payload["enabled"])
        current = _load_json_file(self.paths.status_file)
        if "enabled" in current:
            return bool(current["enabled"])
        configured = os.getenv("RESEARCH_ORCHESTRATOR_ENABLED")
        if configured is not None:
            return configured.lower() in {"1", "true", "yes", "on"}
        return True

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _next_check(self, checked_at: datetime) -> datetime:
        return checked_at + timedelta(seconds=self.thresholds.schedule_seconds)

    def _totals_from_priorities(
        self,
        rows: tuple[Any, ...],
        programs: tuple[Any, ...],
        priorities: tuple[ResearchProgramPriority, ...],
        improvement_requests: tuple[dict[str, Any], ...] = (),
    ) -> dict[str, Any]:
        usable = sum(row.usable_for_research for row in rows)
        return {
            "datasets": len(rows),
            "usable_datasets": usable,
            "research_programs": len(programs),
            "coverage_pct": round((usable / len(rows)) * 100, 2) if rows else 0,
            "weak_programs": sum(item.weak for item in priorities),
            "stale_programs": sum(item.stale for item in priorities),
            "approved_assets": sum(row.approved_asset_count for row in rows),
            "blocked_programs": sum(not row.usable_for_research for row in rows),
            "history_validation_improvement_requests": len(improvement_requests),
            "improvement_target_programs": len({_improvement_program_id(item) for item in improvement_requests}),
            "top_priority_programs": [_payload(item) for item in priorities[:10]],
        }


def default_always_on_orchestrator_paths(repo_root: Path) -> AlwaysOnOrchestratorPaths:
    return AlwaysOnOrchestratorPaths(
        status_file=repo_root / "var" / "research_orchestrator_status.json",
        runs_file=repo_root / "var" / "research_orchestrator_runs.json",
        idle_reasons_file=repo_root / "var" / "research_orchestrator_idle_reasons.json",
        guardrails_file=repo_root / "var" / "research_orchestrator_guardrails.json",
        history_validation_improvements_file=repo_root / "var" / "history_validation_improvements.json",
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


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _load_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_timestamp(values: tuple[str, ...]) -> datetime | None:
    parsed: list[datetime] = []
    for value in values:
        if not value:
            continue
        normalized = value.replace("Z", "+00:00")
        try:
            timestamp = datetime.fromisoformat(normalized)
        except ValueError:
            continue
        parsed.append(timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=UTC))
    return max(parsed) if parsed else None


def _improvement_program_id(item: dict[str, Any]) -> str:
    return str(item.get("research_program_id") or f"RP-{item.get('pair')}-{item.get('timeframe')}")


def _payload(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: _payload(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_payload(item) for item in value]
    if isinstance(value, list):
        return [_payload(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _payload(item) for key, item in value.items()}
    return value
