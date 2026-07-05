from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from quantforge.research import (
    FullHistoryJobStatus,
    FullHistoryResearchScheduler,
    FullHistoryRetryDecision,
    FullHistorySchedulerConfig,
    FullHistoryStage,
    claim_pending_jobs,
    classify_full_history_failure,
    release_running_jobs,
)
from quantforge.research.full_history_scheduler import _window_candles_for_job
from quantforge.tests.test_workstream1_pipeline import FakeCandleRepository


def test_full_history_scheduler_plans_staged_jobs() -> None:
    scheduler = FullHistoryResearchScheduler(
        config=_config(),
        state_file=_unused_state_path(),
        repository_factory=FakeCandleRepository,
    )

    jobs = scheduler.plan()

    assert tuple(job.stage for job in jobs) == (
        FullHistoryStage.COVERAGE,
        FullHistoryStage.SMOKE,
        FullHistoryStage.ROLLING_YEAR,
        FullHistoryStage.FULL_HISTORY,
    )
    assert all(job.status == FullHistoryJobStatus.PENDING for job in jobs)
    assert jobs[1].max_batches == 2
    assert jobs[-1].max_batches == 5


def test_full_history_scheduler_runs_limited_jobs_and_saves_state(tmp_path) -> None:
    state_file = tmp_path / "full_history_state.json"
    scheduler = FullHistoryResearchScheduler(
        config=_config(),
        state_file=state_file,
        repository_factory=FakeCandleRepository,
    )

    result = scheduler.run_pending(max_jobs=1)

    assert result.planned_jobs == 4
    assert result.completed_jobs == 1
    assert result.failed_jobs == 0
    assert result.skipped_jobs == 3
    assert result.executed_jobs[0].status == FullHistoryJobStatus.COMPLETE
    assert state_file.exists()

    second_result = scheduler.run_pending(max_jobs=1, dry_run=True)

    assert second_result.completed_jobs == 1
    assert second_result.executed_jobs[0].stage == FullHistoryStage.SMOKE


def test_full_history_scheduler_claims_distinct_parallel_jobs(tmp_path) -> None:
    state_file = tmp_path / "full_history_state.json"
    scheduler = FullHistoryResearchScheduler(
        config=_config(),
        state_file=state_file,
        repository_factory=FakeCandleRepository,
    )
    planned = scheduler.plan()

    first_claim = claim_pending_jobs(
        state_file,
        planned,
        limit=3,
        owner="worker-a",
        stale_after_seconds=3600,
    )
    second_claim = claim_pending_jobs(
        state_file,
        planned,
        limit=3,
        owner="worker-b",
        stale_after_seconds=3600,
    )

    assert len(first_claim) == 3
    assert len(second_claim) == 1
    assert {job.job_id for job in first_claim}.isdisjoint(job.job_id for job in second_claim)

    release_running_jobs(state_file, tuple(job.job_id for job in first_claim))
    released_claim = claim_pending_jobs(
        state_file,
        planned,
        limit=1,
        owner="worker-c",
        stale_after_seconds=3600,
    )

    assert released_claim[0].job_id == first_claim[0].job_id


def test_full_history_scheduler_runs_specific_claimed_job(tmp_path) -> None:
    state_file = tmp_path / "full_history_state.json"
    scheduler = FullHistoryResearchScheduler(
        config=_config(),
        state_file=state_file,
        repository_factory=FakeCandleRepository,
    )
    claimed = claim_pending_jobs(
        state_file,
        scheduler.plan(),
        limit=1,
        owner="worker-a",
        stale_after_seconds=3600,
    )

    result = scheduler.run_job(claimed[0].job_id)

    assert result.completed_jobs == 1
    assert result.failed_jobs == 0
    assert result.executed_jobs[0].job_id == claimed[0].job_id
    assert result.executed_jobs[0].status == FullHistoryJobStatus.COMPLETE


def test_full_history_scheduler_reclaims_due_retryable_failed_job(tmp_path) -> None:
    state_file = tmp_path / "full_history_state.json"
    scheduler = FullHistoryResearchScheduler(
        config=_config(),
        state_file=state_file,
        repository_factory=FakeCandleRepository,
    )
    retryable_job = scheduler.plan()[0]
    state_file.write_text(
        json.dumps(
            {
                "completed": [],
                "failed": [retryable_job.job_id],
                "history": [
                    {
                        "job_id": retryable_job.job_id,
                        "stage": retryable_job.stage.value,
                        "status": FullHistoryJobStatus.FAILED.value,
                        "evidence": "Timeout while reading OANDA candles",
                        "recorded_at": (datetime.now(timezone.utc) - timedelta(minutes=6)).isoformat(),
                    }
                ],
                "running": {},
            }
        ),
        encoding="utf-8",
    )

    claimed = claim_pending_jobs(
        state_file,
        scheduler.plan(),
        limit=1,
        owner="worker-a",
        stale_after_seconds=3600,
    )
    state = json.loads(state_file.read_text(encoding="utf-8"))

    assert claimed[0].job_id == retryable_job.job_id
    assert retryable_job.job_id not in state["failed"]
    assert state["running"][retryable_job.job_id]["retry_attempt"] == 2


def test_full_history_scheduler_does_not_retry_research_quality_failure(tmp_path) -> None:
    state_file = tmp_path / "full_history_state.json"
    scheduler = FullHistoryResearchScheduler(
        config=_config(),
        state_file=state_file,
        repository_factory=FakeCandleRepository,
    )
    failed_job = scheduler.plan()[1]
    state_file.write_text(
        json.dumps(
            {
                "completed": [],
                "failed": [failed_job.job_id],
                "history": [
                    {
                        "job_id": failed_job.job_id,
                        "stage": failed_job.stage.value,
                        "status": FullHistoryJobStatus.FAILED.value,
                        "evidence": "tasks=2/9; candles=137; successful=NO",
                        "recorded_at": (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat(),
                    }
                ],
                "running": {},
            }
        ),
        encoding="utf-8",
    )

    claimed = claim_pending_jobs(
        state_file,
        scheduler.plan(),
        limit=4,
        owner="worker-a",
        stale_after_seconds=3600,
    )

    assert failed_job.job_id not in {job.job_id for job in claimed}
    assert classify_full_history_failure("tasks=2/9; successful=NO", 1) == FullHistoryRetryDecision.PERMANENT


def test_full_history_scheduler_uses_timeframe_aware_smoke_window_candles() -> None:
    scheduler = FullHistoryResearchScheduler(
        config=FullHistorySchedulerConfig(
            pairs=("EUR_USD",),
            timeframes=("H4",),
            start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end=datetime(2026, 4, 1, tzinfo=timezone.utc),
            window_candles=300,
        ),
        state_file=_unused_state_path(),
        repository_factory=FakeCandleRepository,
    )
    smoke_job = next(job for job in scheduler.plan() if job.stage == FullHistoryStage.SMOKE)
    full_history_job = next(job for job in scheduler.plan() if job.stage == FullHistoryStage.FULL_HISTORY)

    assert _window_candles_for_job(smoke_job, scheduler.config) == 120
    assert _window_candles_for_job(full_history_job, scheduler.config) == 300


def _config() -> FullHistorySchedulerConfig:
    return FullHistorySchedulerConfig(
        pairs=("EUR_USD",),
        timeframes=("H1",),
        start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end=datetime(2026, 2, 1, tzinfo=timezone.utc),
        window_candles=100,
        stride_candles=50,
        smoke_days=7,
        smoke_max_batches=2,
        rolling_max_batches=3,
        full_history_max_batches=5,
        max_assets_to_validate=1,
    )


def _unused_state_path():
    from pathlib import Path

    return Path("var/test-full-history-state-unused.json")
