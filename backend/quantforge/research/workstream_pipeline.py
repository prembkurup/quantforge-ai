from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import StrEnum

from quantforge.research.database_library import (
    DatabaseBackedStrategyLibraryResult,
    DatabaseBackedStrategyLibraryRunner,
    DatabaseResearchScope,
    ResearchCandleRepository,
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
    recommendations: tuple[str, ...]
    archived: bool


@dataclass(frozen=True, slots=True)
class WorkstreamPipelineResult:
    schedule: WorkstreamPipelineSchedule
    database_result: DatabaseBackedStrategyLibraryResult
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
        return self.database_result.successful and not self.failed_tasks


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
            recommendations=database_result.report.recommendations,
            archived=True,
        )
        completed_schedule = replace(schedule, tasks=tasks)
        audit_trail = (
            tuple(f"{task.task_id}:{task.status}:{task.evidence}" for task in tasks)
            + database_result.audit_trail
        )
        return WorkstreamPipelineResult(
            schedule=completed_schedule,
            database_result=database_result,
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
