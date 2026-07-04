from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from quantforge.research.database_library import DatabaseResearchScope, ResearchCandleRepository
from quantforge.research.workstream_pipeline import Workstream1PipelineRunner, WorkstreamPipelineResult

FULL_HISTORY_RESEARCH_PAIRS = (
    "AUD_CAD",
    "AUD_CHF",
    "AUD_JPY",
    "AUD_NZD",
    "AUD_USD",
    "CAD_CHF",
    "CAD_JPY",
    "CHF_JPY",
    "EUR_AUD",
    "EUR_CAD",
    "EUR_CHF",
    "EUR_GBP",
    "EUR_JPY",
    "EUR_NZD",
    "EUR_USD",
    "GBP_AUD",
    "GBP_CAD",
    "GBP_CHF",
    "GBP_JPY",
    "GBP_NZD",
    "GBP_USD",
    "NAS100_USD",
    "NZD_CAD",
    "NZD_CHF",
    "NZD_JPY",
    "NZD_USD",
    "SPX500_USD",
    "USD_CAD",
    "USD_CHF",
    "USD_JPY",
)
FULL_HISTORY_RESEARCH_TIMEFRAMES = ("M5", "M15", "H1", "H4")
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
        running = set(_running_jobs(state))
        executed: list[FullHistoryResearchJob] = []
        planned = self.plan()
        pending = [
            job
            for job in planned
            if job.job_id not in completed and job.job_id not in failed and job.job_id not in running
        ]

        for job in pending[: max(0, max_jobs)]:
            if dry_run:
                executed.append(job)
                continue
            result_job = self._run_job(job)
            executed.append(result_job)
            _record_job_result(self.state_file, result_job)
            state = _load_state(self.state_file)
            completed = set(state.get("completed", []))
            failed = set(state.get("failed", []))

        return FullHistoryRunResult(
            planned_jobs=len(planned),
            completed_jobs=len(completed),
            failed_jobs=len(failed),
            skipped_jobs=max(0, len(pending) - len(executed)),
            executed_jobs=tuple(executed),
            state_file=str(self.state_file),
        )

    def run_job(self, job_id: str, *, dry_run: bool = False) -> FullHistoryRunResult:
        planned = self.plan()
        jobs_by_id = {job.job_id: job for job in planned}
        job = jobs_by_id.get(job_id)
        if job is None:
            raise ValueError(f"Unknown full-history job id: {job_id}")

        state = _load_state(self.state_file)
        completed = set(state.get("completed", []))
        failed = set(state.get("failed", []))
        if job_id in completed or job_id in failed:
            return FullHistoryRunResult(
                planned_jobs=len(planned),
                completed_jobs=len(completed),
                failed_jobs=len(failed),
                skipped_jobs=0,
                executed_jobs=(),
                state_file=str(self.state_file),
            )

        if dry_run:
            executed = (job,)
        else:
            result_job = self._run_job(job)
            _record_job_result(self.state_file, result_job)
            executed = (result_job,)

        state = _load_state(self.state_file)
        completed = set(state.get("completed", []))
        failed = set(state.get("failed", []))
        running = set(_running_jobs(state))
        pending = [
            item
            for item in planned
            if item.job_id not in completed and item.job_id not in failed and item.job_id not in running
        ]
        return FullHistoryRunResult(
            planned_jobs=len(planned),
            completed_jobs=len(completed),
            failed_jobs=len(failed),
            skipped_jobs=len(pending),
            executed_jobs=executed,
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
        return {"completed": [], "failed": [], "history": [], "running": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def claim_pending_jobs(
    path: Path,
    planned: tuple[FullHistoryResearchJob, ...],
    *,
    limit: int,
    owner: str,
    stale_after_seconds: int,
) -> tuple[FullHistoryResearchJob, ...]:
    now = datetime.now(timezone.utc)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _state_lock(path):
        state = _load_state(path)
        running = _fresh_running_jobs(state, now=now, stale_after_seconds=stale_after_seconds)
        completed = set(state.get("completed", []))
        failed = set(state.get("failed", []))
        claimed: list[FullHistoryResearchJob] = []
        for job in planned:
            if len(claimed) >= max(0, limit):
                break
            if job.job_id in completed or job.job_id in failed or job.job_id in running:
                continue
            running[job.job_id] = {"owner": owner, "claimed_at": now.isoformat()}
            claimed.append(job)

        _write_state(
            path,
            completed=completed,
            failed=failed,
            history=list(state.get("history", [])),
            running=running,
        )
        return tuple(claimed)


def release_running_jobs(path: Path, job_ids: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _state_lock(path):
        state = _load_state(path)
        running = dict(state.get("running", {}))
        for job_id in job_ids:
            running.pop(job_id, None)
        _write_state(
            path,
            completed=set(state.get("completed", [])),
            failed=set(state.get("failed", [])),
            history=list(state.get("history", [])),
            running=running,
        )


def _record_job_result(path: Path, job: FullHistoryResearchJob) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _state_lock(path):
        state = _load_state(path)
        completed = set(state.get("completed", []))
        failed = set(state.get("failed", []))
        running = dict(state.get("running", {}))
        if job.status == FullHistoryJobStatus.COMPLETE:
            completed.add(job.job_id)
            failed.discard(job.job_id)
        elif job.status == FullHistoryJobStatus.FAILED:
            failed.add(job.job_id)
            completed.discard(job.job_id)
        running.pop(job.job_id, None)

        history = list(state.get("history", []))
        payload = asdict(job)
        payload["stage"] = job.stage.value
        payload["status"] = job.status.value
        payload["start"] = job.start.isoformat()
        payload["end"] = job.end.isoformat()
        payload["recorded_at"] = datetime.now(timezone.utc).isoformat()
        history.append(payload)
        _write_state(path, completed=completed, failed=failed, history=history, running=running)


def _write_state(
    path: Path,
    *,
    completed: set[str],
    failed: set[str],
    history: list[object],
    running: dict[str, object],
) -> None:
    path.write_text(
        json.dumps(
            {
                "completed": sorted(completed),
                "failed": sorted(failed),
                "history": history,
                "running": running,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _fresh_running_jobs(
    state: dict[str, object],
    *,
    now: datetime,
    stale_after_seconds: int,
) -> dict[str, object]:
    fresh: dict[str, object] = {}
    running = state.get("running", {})
    if not isinstance(running, dict):
        return fresh
    for job_id, payload in running.items():
        if not isinstance(payload, dict):
            continue
        claimed_at = payload.get("claimed_at")
        if not isinstance(claimed_at, str):
            continue
        try:
            claimed = datetime.fromisoformat(claimed_at)
        except ValueError:
            continue
        if claimed.tzinfo is None:
            claimed = claimed.replace(tzinfo=timezone.utc)
        if (now - claimed).total_seconds() <= stale_after_seconds:
            fresh[job_id] = payload
    return fresh


def _running_jobs(state: dict[str, object]) -> tuple[str, ...]:
    running = state.get("running", {})
    if not isinstance(running, dict):
        return ()
    return tuple(str(job_id) for job_id in running)


@contextmanager
def _state_lock(path: Path):
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _save_state(
    path: Path,
    completed: set[str],
    failed: set[str],
    job: FullHistoryResearchJob,
) -> None:
    """Backward-compatible wrapper for older call sites."""
    state = _load_state(path)
    history = list(state.get("history", []))
    payload = asdict(job)
    payload["stage"] = job.stage.value
    payload["status"] = job.status.value
    payload["start"] = job.start.isoformat()
    payload["end"] = job.end.isoformat()
    payload["recorded_at"] = datetime.now(timezone.utc).isoformat()
    history.append(payload)
    _write_state(
        path,
        completed=completed,
        failed=failed,
        history=history,
        running=dict(state.get("running", {})),
    )
