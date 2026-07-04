from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from quantforge.research.database_library import DatabaseResearchScope, ResearchCandleRepository
from quantforge.research.workstream_pipeline import Workstream1PipelineRunner, WorkstreamPipelineResult

FULL_HISTORY_RESEARCH_PAIRS = ("EUR_USD", "GBP_USD", "USD_JPY", "NAS100_USD", "SPX500_USD")
FULL_HISTORY_RESEARCH_TIMEFRAMES = ("M15", "H1", "H4")
FULL_HISTORY_RESEARCH_START = datetime(2016, 1, 4, tzinfo=timezone.utc)


class FullHistoryStage(StrEnum):
    COVERAGE = "COVERAGE"
    SMOKE = "SMOKE"
    ROLLING_YEAR = "ROLLING_YEAR"
    FULL_HISTORY = "FULL_HISTORY"


class FullHistoryJobStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class FullHistoryRepositoryFactory(Protocol):
    def __call__(self) -> ResearchCandleRepository: ...


@dataclass(frozen=True, slots=True)
class FullHistorySchedulerConfig:
    pairs: tuple[str, ...]
    timeframes: tuple[str, ...]
    start: datetime
    end: datetime
    rolling_years: int = 1
    window_candles: int = 300
    stride_candles: int = 100
    smoke_days: int = 31
    smoke_max_batches: int = 2
    rolling_max_batches: int = 25
    full_history_max_batches: int = 100
    max_assets_to_validate: int = 10


@dataclass(frozen=True, slots=True)
class FullHistoryResearchJob:
    job_id: str
    stage: FullHistoryStage
    pair: str
    timeframe: str
    start: datetime
    end: datetime
    max_batches: int
    status: FullHistoryJobStatus = FullHistoryJobStatus.PENDING
    evidence: str = ""


@dataclass(frozen=True, slots=True)
class FullHistoryRunResult:
    planned_jobs: int
    completed_jobs: int
    failed_jobs: int
    skipped_jobs: int
    executed_jobs: tuple[FullHistoryResearchJob, ...]
    state_file: str


class FullHistoryResearchScheduler:
    def __init__(
        self,
        config: FullHistorySchedulerConfig,
        state_file: Path,
        repository_factory: FullHistoryRepositoryFactory,
    ) -> None:
        self.config = config
        self.state_file = state_file
        self.repository_factory = repository_factory

    def plan(self) -> tuple[FullHistoryResearchJob, ...]:
        jobs: list[FullHistoryResearchJob] = []
        for pair in self.config.pairs:
            for timeframe in self.config.timeframes:
                jobs.append(
                    _job(
                        FullHistoryStage.COVERAGE,
                        pair,
                        timeframe,
                        self.config.start,
                        self.config.end,
                        max_batches=0,
                    )
                )
                smoke_end = min(self.config.end, self.config.start + timedelta(days=self.config.smoke_days))
                jobs.append(
                    _job(
                        FullHistoryStage.SMOKE,
                        pair,
                        timeframe,
                        self.config.start,
                        smoke_end,
                        max_batches=self.config.smoke_max_batches,
                    )
                )
                for start, end in _rolling_windows(self.config.start, self.config.end, self.config.rolling_years):
                    jobs.append(
                        _job(
                            FullHistoryStage.ROLLING_YEAR,
                            pair,
                            timeframe,
                            start,
                            end,
                            max_batches=self.config.rolling_max_batches,
                        )
                    )
                jobs.append(
                    _job(
                        FullHistoryStage.FULL_HISTORY,
                        pair,
                        timeframe,
                        self.config.start,
                        self.config.end,
                        max_batches=self.config.full_history_max_batches,
                    )
                )
        return tuple(jobs)

    def run_pending(self, *, max_jobs: int, dry_run: bool = False) -> FullHistoryRunResult:
        state = _load_state(self.state_file)
        completed = set(state.get("completed", []))
        failed = set(state.get("failed", []))
        executed: list[FullHistoryResearchJob] = []
        planned = self.plan()
        pending = [job for job in planned if job.job_id not in completed and job.job_id not in failed]

        for job in pending[: max(0, max_jobs)]:
            if dry_run:
                executed.append(job)
                continue
            result_job = self._run_job(job)
            executed.append(result_job)
            if result_job.status == FullHistoryJobStatus.COMPLETE:
                completed.add(result_job.job_id)
            elif result_job.status == FullHistoryJobStatus.FAILED:
                failed.add(result_job.job_id)
            _save_state(self.state_file, completed, failed, result_job)

        return FullHistoryRunResult(
            planned_jobs=len(planned),
            completed_jobs=len(completed),
            failed_jobs=len(failed),
            skipped_jobs=max(0, len(pending) - len(executed)),
            executed_jobs=tuple(executed),
            state_file=str(self.state_file),
        )

    def _run_job(self, job: FullHistoryResearchJob) -> FullHistoryResearchJob:
        try:
            max_batches = job.max_batches if job.stage != FullHistoryStage.COVERAGE else 1
            scope = DatabaseResearchScope(
                pairs=(job.pair,),
                timeframes=(job.timeframe,),
                start=job.start,
                end=job.end,
                window_candles=self.config.window_candles,
                stride_candles=self.config.stride_candles,
                max_batches=max_batches,
                max_assets_to_validate=self.config.max_assets_to_validate,
            )
            result = Workstream1PipelineRunner(self.repository_factory()).run(scope)
            return _result_job(job, result)
        except Exception as exc:
            return _replace_job(
                job,
                FullHistoryJobStatus.FAILED,
                f"{type(exc).__name__}: {exc}",
            )


def _job(
    stage: FullHistoryStage,
    pair: str,
    timeframe: str,
    start: datetime,
    end: datetime,
    *,
    max_batches: int,
) -> FullHistoryResearchJob:
    return FullHistoryResearchJob(
        job_id=":".join(
            (
                stage.value,
                pair,
                timeframe,
                start.strftime("%Y%m%d"),
                end.strftime("%Y%m%d"),
                str(max_batches),
            )
        ),
        stage=stage,
        pair=pair,
        timeframe=timeframe,
        start=start,
        end=end,
        max_batches=max_batches,
    )


def _result_job(job: FullHistoryResearchJob, result: WorkstreamPipelineResult) -> FullHistoryResearchJob:
    status = FullHistoryJobStatus.COMPLETE if result.successful else FullHistoryJobStatus.FAILED
    evidence = (
        f"tasks={len(result.completed_tasks)}/{len(result.schedule.tasks)}; "
        f"candles={result.report.stored_candles}; "
        f"duplicates={result.report.duplicate_candles}; "
        f"batches={result.report.real_experiment_batches}; "
        f"validated_assets={result.report.validated_strategy_assets}; "
        f"successful={'YES' if result.successful else 'NO'}"
    )
    return _replace_job(job, status, evidence)


def _replace_job(
    job: FullHistoryResearchJob,
    status: FullHistoryJobStatus,
    evidence: str,
) -> FullHistoryResearchJob:
    return FullHistoryResearchJob(
        job_id=job.job_id,
        stage=job.stage,
        pair=job.pair,
        timeframe=job.timeframe,
        start=job.start,
        end=job.end,
        max_batches=job.max_batches,
        status=status,
        evidence=evidence,
    )


def _rolling_windows(start: datetime, end: datetime, years: int) -> tuple[tuple[datetime, datetime], ...]:
    windows: list[tuple[datetime, datetime]] = []
    cursor = start
    while cursor < end:
        try:
            next_end = cursor.replace(year=cursor.year + years)
        except ValueError:
            next_end = cursor + timedelta(days=365 * years)
        next_end = min(next_end, end)
        windows.append((cursor, next_end))
        cursor = next_end
    return tuple(windows)


def _load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"completed": [], "failed": [], "history": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(
    path: Path,
    completed: set[str],
    failed: set[str],
    job: FullHistoryResearchJob,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state = _load_state(path)
    history = list(state.get("history", []))
    payload = asdict(job)
    payload["stage"] = job.stage.value
    payload["status"] = job.status.value
    payload["start"] = job.start.isoformat()
    payload["end"] = job.end.isoformat()
    payload["recorded_at"] = datetime.now(timezone.utc).isoformat()
    history.append(payload)
    path.write_text(
        json.dumps(
            {
                "completed": sorted(completed),
                "failed": sorted(failed),
                "history": history,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
