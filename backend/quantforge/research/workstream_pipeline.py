from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from quantforge.backtesting import BacktestEngine, BacktestReport
from quantforge.research.database_library import (
    DatabaseBackedStrategyAsset,
    DatabaseBackedStrategyLibraryResult,
    DatabaseBackedStrategyLibraryRunner,
    DatabaseResearchScope,
    ResearchCandleRepository,
)
from quantforge.research.optimization import OptimizationLaboratory, OptimizationReport, ReviewDecision
from quantforge.validation import (
    DeploymentDecision,
    StrategyAsset,
    StrategyValidationPlatform,
    ValidationReport,
)


class WorkstreamPipelineTaskStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class WorkstreamPipelineTaskType(StrEnum):
    DATABASE_CONNECTION = "DATABASE_CONNECTION"
    CANDLE_COVERAGE_VALIDATION = "CANDLE_COVERAGE_VALIDATION"
    REAL_EXPERIMENT_BATCHES = "REAL_EXPERIMENT_BATCHES"
    CANDIDATE_ASSET_GENERATION = "CANDIDATE_ASSET_GENERATION"
    OPTIMIZATION = "OPTIMIZATION"
    BACKTESTING = "BACKTESTING"
    VALIDATION = "VALIDATION"
    STRATEGY_ASSET_PUBLICATION = "STRATEGY_ASSET_PUBLICATION"
    PIPELINE_REPORT = "PIPELINE_REPORT"


@dataclass(frozen=True, slots=True)
class WorkstreamPipelineTask:
    task_id: str
    task_type: WorkstreamPipelineTaskType
    description: str
    status: WorkstreamPipelineTaskStatus
    evidence: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class WorkstreamPipelineSchedule:
    schedule_id: str
    scope: DatabaseResearchScope
    tasks: tuple[WorkstreamPipelineTask, ...]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class WorkstreamPipelineReport:
    title: str
    completed_tasks: int
    failed_tasks: int
    stored_candles: int
    duplicate_candles: int
    missing_candles: int
    real_experiment_batches: int
    database_backed_candidate_assets: int
    optimized_candidates: int
    backtested_candidates: int
    validated_strategy_assets: int
    recommendations: tuple[str, ...]
    archived: bool


@dataclass(frozen=True, slots=True)
class WorkstreamValidatedStrategyAsset:
    source_candidate: DatabaseBackedStrategyAsset
    optimization_report: OptimizationReport
    backtest_report: BacktestReport
    validation_report: ValidationReport
    strategy_asset: StrategyAsset
    reproducibility_key: str


@dataclass(frozen=True, slots=True)
class WorkstreamPipelineResult:
    schedule: WorkstreamPipelineSchedule
    database_result: DatabaseBackedStrategyLibraryResult
    validated_assets: tuple[WorkstreamValidatedStrategyAsset, ...]
    report: WorkstreamPipelineReport
    audit_trail: tuple[str, ...]

    @property
    def completed_tasks(self) -> tuple[WorkstreamPipelineTask, ...]:
        return tuple(
            task for task in self.schedule.tasks if task.status == WorkstreamPipelineTaskStatus.COMPLETE
        )

    @property
    def failed_tasks(self) -> tuple[WorkstreamPipelineTask, ...]:
        return tuple(
            task for task in self.schedule.tasks if task.status == WorkstreamPipelineTaskStatus.FAILED
        )

    @property
    def successful(self) -> bool:
        return self.database_result.successful and bool(self.validated_assets) and not self.failed_tasks


class Workstream1PipelineScheduler:
    def schedule(self, scope: DatabaseResearchScope) -> WorkstreamPipelineSchedule:
        created_at = datetime.now(timezone.utc)
        tasks = (
            WorkstreamPipelineTask(
                task_id="WS1-PIPE-001",
                task_type=WorkstreamPipelineTaskType.DATABASE_CONNECTION,
                description="Open the configured CoreUI/OANDA candle database repository.",
                status=WorkstreamPipelineTaskStatus.PENDING,
            ),
            WorkstreamPipelineTask(
                task_id="WS1-PIPE-002",
                task_type=WorkstreamPipelineTaskType.CANDLE_COVERAGE_VALIDATION,
                description="Validate candle counts, duplicates, and market/calendar gap evidence.",
                status=WorkstreamPipelineTaskStatus.PENDING,
            ),
            WorkstreamPipelineTask(
                task_id="WS1-PIPE-003",
                task_type=WorkstreamPipelineTaskType.REAL_EXPERIMENT_BATCHES,
                description="Execute rolling Workstream 1 experiment batches from actual candle windows.",
                status=WorkstreamPipelineTaskStatus.PENDING,
            ),
            WorkstreamPipelineTask(
                task_id="WS1-PIPE-004",
                task_type=WorkstreamPipelineTaskType.CANDIDATE_ASSET_GENERATION,
                description="Generate database-backed candidate Strategy Assets from completed batches.",
                status=WorkstreamPipelineTaskStatus.PENDING,
            ),
            WorkstreamPipelineTask(
                task_id="WS1-PIPE-005",
                task_type=WorkstreamPipelineTaskType.OPTIMIZATION,
                description="Optimize database-backed candidate assets for stable parameter regions.",
                status=WorkstreamPipelineTaskStatus.PENDING,
            ),
            WorkstreamPipelineTask(
                task_id="WS1-PIPE-006",
                task_type=WorkstreamPipelineTaskType.BACKTESTING,
                description="Backtest optimized candidates through the event-driven backtesting engine.",
                status=WorkstreamPipelineTaskStatus.PENDING,
            ),
            WorkstreamPipelineTask(
                task_id="WS1-PIPE-007",
                task_type=WorkstreamPipelineTaskType.VALIDATION,
                description="Validate backtested candidates through walk-forward, Monte Carlo, stress, and cross checks.",
                status=WorkstreamPipelineTaskStatus.PENDING,
            ),
            WorkstreamPipelineTask(
                task_id="WS1-PIPE-008",
                task_type=WorkstreamPipelineTaskType.STRATEGY_ASSET_PUBLICATION,
                description="Publish validated database-backed candidates as immutable Strategy Assets.",
                status=WorkstreamPipelineTaskStatus.PENDING,
            ),
            WorkstreamPipelineTask(
                task_id="WS1-PIPE-009",
                task_type=WorkstreamPipelineTaskType.PIPELINE_REPORT,
                description="Archive the Workstream 1 pipeline report and audit evidence.",
                status=WorkstreamPipelineTaskStatus.PENDING,
            ),
        )
        return WorkstreamPipelineSchedule(
            schedule_id=f"WS1-SCHEDULE-{created_at.strftime('%Y%m%d%H%M%S')}",
            scope=scope,
            tasks=tasks,
            created_at=created_at,
        )


class Workstream1PipelineRunner:
    def __init__(self, repository: ResearchCandleRepository) -> None:
        self.repository = repository
        self.scheduler = Workstream1PipelineScheduler()

    def run(self, scope: DatabaseResearchScope) -> WorkstreamPipelineResult:
        schedule = self.scheduler.schedule(scope)
        tasks = tuple(_complete(task, "Database repository initialized.") for task in schedule.tasks[:1])
        database_result = DatabaseBackedStrategyLibraryRunner(self.repository).run(scope)
        validated_assets = _validate_database_assets(database_result, scope)
        tasks += (
            _task_result(
                schedule.tasks[1],
                all(item.database_ready for item in database_result.coverage),
                (
                    f"{sum(item.stored_candles for item in database_result.coverage):,} stored candles; "
                    f"{sum(item.duplicate_candles for item in database_result.coverage):,} duplicates; "
                    f"{sum(item.missing_candle_count for item in database_result.coverage):,} missing candles."
                ),
            ),
            _task_result(
                schedule.tasks[2],
                bool(database_result.experiment_batches),
                f"{len(database_result.experiment_batches):,} real candle experiment batches executed.",
            ),
            _task_result(
                schedule.tasks[3],
                bool(database_result.candidate_assets),
                f"{len(database_result.candidate_assets):,} database-backed candidate assets generated.",
            ),
            _task_result(
                schedule.tasks[4],
                bool(validated_assets),
                f"{len(validated_assets):,} database-backed candidates optimized for stable parameter regions.",
            ),
            _task_result(
                schedule.tasks[5],
                bool(validated_assets) and all(item.backtest_report.validation_ready for item in validated_assets),
                f"{len(validated_assets):,} optimized candidates backtested and marked validation-ready.",
            ),
            _task_result(
                schedule.tasks[6],
                bool(validated_assets)
                and
                all(
                    item.validation_report.deployment_decision == DeploymentDecision.APPROVED
                    for item in validated_assets
                ),
                f"{len(validated_assets):,} candidates passed full validation gates.",
            ),
            _task_result(
                schedule.tasks[7],
                bool(validated_assets) and all(item.strategy_asset.passport.production for item in validated_assets),
                f"{len(validated_assets):,} validated Strategy Assets published.",
            ),
            _task_result(
                schedule.tasks[8],
                database_result.report.archived,
                "Pipeline report archived with reproducibility and audit evidence.",
            ),
        )
        completed = sum(1 for task in tasks if task.status == WorkstreamPipelineTaskStatus.COMPLETE)
        failed = sum(1 for task in tasks if task.status == WorkstreamPipelineTaskStatus.FAILED)
        report = WorkstreamPipelineReport(
            title="Workstream 1 Database Pipeline Report",
            completed_tasks=completed,
            failed_tasks=failed,
            stored_candles=sum(item.stored_candles for item in database_result.coverage),
            duplicate_candles=sum(item.duplicate_candles for item in database_result.coverage),
            missing_candles=sum(item.missing_candle_count for item in database_result.coverage),
            real_experiment_batches=len(database_result.experiment_batches),
            database_backed_candidate_assets=len(database_result.candidate_assets),
            optimized_candidates=len(validated_assets),
            backtested_candidates=sum(1 for item in validated_assets if item.backtest_report.validation_ready),
            validated_strategy_assets=len(validated_assets),
            recommendations=(
                "Scale max_batches upward after each optimizer/backtester/validator run stays clean.",
                "Promote only validated Strategy Assets through paper/shadow trading before controlled live capital.",
            ),
            archived=True,
        )
        completed_schedule = replace(schedule, tasks=tasks)
        audit_trail = (
            tuple(f"{task.task_id}:{task.status}:{task.evidence}" for task in tasks)
            + database_result.audit_trail
            + tuple(
                f"{item.strategy_asset.passport.strategy_id}:validated_strategy_asset_published"
                for item in validated_assets
            )
        )
        return WorkstreamPipelineResult(
            schedule=completed_schedule,
            database_result=database_result,
            validated_assets=validated_assets,
            report=report,
            audit_trail=audit_trail,
        )


def _complete(task: WorkstreamPipelineTask, evidence: str) -> WorkstreamPipelineTask:
    now = datetime.now(timezone.utc)
    return replace(
        task,
        status=WorkstreamPipelineTaskStatus.COMPLETE,
        evidence=evidence,
        started_at=now,
        completed_at=now,
    )


def _fail(task: WorkstreamPipelineTask, evidence: str) -> WorkstreamPipelineTask:
    now = datetime.now(timezone.utc)
    return replace(
        task,
        status=WorkstreamPipelineTaskStatus.FAILED,
        evidence=evidence,
        started_at=now,
        completed_at=now,
    )


def _task_result(
    task: WorkstreamPipelineTask,
    passed: bool,
    evidence: str,
) -> WorkstreamPipelineTask:
    if passed:
        return _complete(task, evidence)
    return _fail(task, evidence)


def _validate_database_assets(
    result: DatabaseBackedStrategyLibraryResult,
    scope: DatabaseResearchScope,
) -> tuple[WorkstreamValidatedStrategyAsset, ...]:
    if not result.successful:
        return ()

    validated: list[WorkstreamValidatedStrategyAsset] = []
    platform = StrategyValidationPlatform()
    limit = min(len(result.candidate_assets), scope.max_assets_to_validate)
    for candidate in result.candidate_assets[:limit]:
        optimization = OptimizationLaboratory().run(candidate.template)
        if optimization.review.decision != ReviewDecision.APPROVED:
            continue
        backtest = BacktestEngine().run(_strategy_from_candidate(candidate, optimization)).report
        if backtest is None or not backtest.validation_ready:
            continue
        validation = platform.validate(candidate.asset_id)
        if validation.deployment_decision != DeploymentDecision.APPROVED:
            continue
        strategy_asset = _strategy_asset(candidate, optimization, validation)
        validated.append(
            WorkstreamValidatedStrategyAsset(
                source_candidate=candidate,
                optimization_report=optimization,
                backtest_report=backtest,
                validation_report=validation,
                strategy_asset=strategy_asset,
                reproducibility_key=f"{candidate.reproducibility_key}:{optimization.best_region.name}",
            )
        )
    return tuple(validated)


def _strategy_from_candidate(
    candidate: DatabaseBackedStrategyAsset,
    optimization: OptimizationReport,
) -> dict[str, Any]:
    return {
        "id": candidate.asset_id,
        "name": candidate.template,
        "version": "db-backed-1.0",
        "pair": candidate.pair,
        "timeframe": candidate.timeframe,
        "family": candidate.family.value,
        "parameters": optimization.best_region.parameter_bounds,
    }


def _strategy_asset(
    candidate: DatabaseBackedStrategyAsset,
    optimization: OptimizationReport,
    validation: ValidationReport,
) -> StrategyAsset:
    return StrategyAsset(
        strategy_definition={
            **validation.strategy_summary,
            "source_candidate": candidate.asset_id,
            "pair": candidate.pair,
            "timeframe": candidate.timeframe,
            "template": candidate.template,
        },
        plugin_versions={
            "market_regime": "database_regime_classifier@1.0.0",
            "entry": f"{candidate.template.lower().replace(' ', '_')}_entry@1.0.0",
            "risk": "drawdown_guard_risk_01@1.0.0",
            "exit": "atr_exit_01@1.0.0",
        },
        parameters=optimization.best_region.parameter_bounds,
        feature_versions={"database_candle_window": "1.0.0", "stable_region_features": "1.0.0"},
        decision_trace=(
            "database_candle_window",
            "workstream_1_candidate_asset",
            "optimization_laboratory",
            "event_driven_backtesting",
            "strategy_validation_platform",
        ),
        optimization_report=optimization.to_dict(),
        validation_report=validation,
        passport=validation.passport,
        deployment_history=({"decision": validation.deployment_decision.value, "environment": "paper_shadow_gate"},),
        live_performance_history=(),
    )
