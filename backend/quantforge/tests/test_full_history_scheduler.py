from __future__ import annotations

from datetime import datetime, timezone

from quantforge.research import (
    FullHistoryJobStatus,
    FullHistoryResearchScheduler,
    FullHistorySchedulerConfig,
    FullHistoryStage,
    claim_pending_jobs,
    release_running_jobs,
)
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
