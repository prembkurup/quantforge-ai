from __future__ import annotations

import json
from datetime import datetime, timezone

from quantforge.research.full_history_scheduler import FullHistoryResearchScheduler, FullHistorySchedulerConfig
from quantforge.research.workflow_orchestration import (
    WorkflowOrchestrator,
    WorkflowStatus,
    default_workflow_paths,
)
from quantforge.tests.test_workstream1_pipeline import FakeCandleRepository


def test_workflow_orchestrator_tracks_full_history_blockers_and_live_gate(tmp_path) -> None:
    scheduler = FullHistoryResearchScheduler(
        config=_config(),
        state_file=tmp_path / "var" / "full_history_research_state.json",
        repository_factory=FakeCandleRepository,
    )
    planned = scheduler.plan()
    paths = default_workflow_paths(tmp_path)
    paths.full_history_state_file.parent.mkdir(parents=True)
    paths.full_history_state_file.write_text(
        json.dumps(
            {
                "completed": [planned[0].job_id],
                "failed": [],
                "history": [{"job_id": planned[0].job_id, "recorded_at": "2026-01-01T00:00:00+00:00"}],
                "running": {planned[1].job_id: {"claimed_at": "2026-01-01T00:01:00+00:00"}},
            }
        ),
        encoding="utf-8",
    )

    snapshot = WorkflowOrchestrator(paths).current(planned)

    assert snapshot["run"]["current_stage"] == "FULL_HISTORY_RUNNING"
    assert snapshot["run"]["live_trading_status"] == "BLOCKED_BY_POLICY"
    assert snapshot["live_gate"]["reason"] == "Live trading blocked by policy"
    assert any(task["status"] == WorkflowStatus.RUNNING.value for task in snapshot["tasks"])
    assert any(task["waiting_reason"] for task in snapshot["tasks"] if task["status"] == WorkflowStatus.BLOCKED.value)
    assert paths.state_file.exists()
    assert paths.events_file.exists()


def test_workflow_orchestrator_marks_failed_jobs_retryable(tmp_path) -> None:
    scheduler = FullHistoryResearchScheduler(
        config=_config(),
        state_file=tmp_path / "var" / "full_history_research_state.json",
        repository_factory=FakeCandleRepository,
    )
    planned = scheduler.plan()
    paths = default_workflow_paths(tmp_path)
    failed_job = planned[0]
    paths.full_history_state_file.parent.mkdir(parents=True)
    paths.full_history_state_file.write_text(
        json.dumps(
            {
                "completed": [],
                "failed": [failed_job.job_id],
                "history": [
                    {
                        "job_id": failed_job.job_id,
                        "evidence": "Network timeout while reading candles",
                        "recorded_at": "2026-01-01T00:00:00+00:00",
                    }
                ],
                "running": {},
            }
        ),
        encoding="utf-8",
    )

    snapshot = WorkflowOrchestrator(paths).current(planned)
    task = next(item for item in snapshot["tasks"] if item["task_id"] == failed_job.job_id)

    assert task["status"] == WorkflowStatus.FAILED_RETRYABLE.value
    assert task["max_retries"] == 3
    assert task["retry_delay_seconds"] == 300


def test_workflow_orchestrator_marks_research_quality_failure_permanent(tmp_path) -> None:
    scheduler = FullHistoryResearchScheduler(
        config=_config(),
        state_file=tmp_path / "var" / "full_history_research_state.json",
        repository_factory=FakeCandleRepository,
    )
    planned = scheduler.plan()
    paths = default_workflow_paths(tmp_path)
    failed_job = planned[1]
    paths.full_history_state_file.parent.mkdir(parents=True)
    paths.full_history_state_file.write_text(
        json.dumps(
            {
                "completed": [],
                "failed": [failed_job.job_id],
                "history": [
                    {
                        "job_id": failed_job.job_id,
                        "evidence": "tasks=2/9; candles=137; duplicates=0; successful=NO",
                        "recorded_at": "2026-01-01T00:00:00+00:00",
                    }
                ],
                "running": {},
            }
        ),
        encoding="utf-8",
    )

    snapshot = WorkflowOrchestrator(paths).current(planned)
    task = next(item for item in snapshot["tasks"] if item["task_id"] == failed_job.job_id)

    assert task["status"] == WorkflowStatus.FAILED_PERMANENT.value
    assert task["waiting_reason"] == "Blocked by permanent failure."
    assert snapshot["run"]["retryable_tasks"] == 0


def _config() -> FullHistorySchedulerConfig:
    return FullHistorySchedulerConfig(
        pairs=("EUR_USD",),
        timeframes=("H1",),
        start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end=datetime(2026, 2, 1, tzinfo=timezone.utc),
        smoke_days=7,
        rolling_years=1,
    )
