from __future__ import annotations

from datetime import datetime, timezone

from quantforge.research import (
    FullHistoryJobStatus,
    FullHistoryResearchScheduler,
    FullHistorySchedulerConfig,
    FullHistoryStage,
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
