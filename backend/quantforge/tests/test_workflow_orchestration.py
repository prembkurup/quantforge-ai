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


def test_workflow_orchestrator_maps_autonomous_stage_to_strategy_publication(tmp_path) -> None:
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
                "completed": [job.job_id for job in planned],
                "failed": [],
                "history": [{"job_id": job.job_id, "recorded_at": "2026-01-01T00:00:00+00:00"} for job in planned],
                "running": {},
            }
        ),
        encoding="utf-8",
    )
    paths.post_pipeline_state_file.write_text(
        json.dumps(
            {
                "status": "COMPLETE",
                "stages": [
                    {"stage_id": "AUTONOMOUS_RESEARCH", "status": "COMPLETE"},
                    {"stage_id": "DEPLOY_PAPER_PORTFOLIO", "status": "COMPLETE"},
                    {"stage_id": "SHADOW_TRADING_REVIEW", "status": "COMPLETE"},
                    {"stage_id": "PRODUCTION_READINESS", "status": "COMPLETE"},
                    {"stage_id": "PRODUCTION_CERTIFICATION", "status": "COMPLETE"},
                ],
            }
        ),
        encoding="utf-8",
    )

    snapshot = WorkflowOrchestrator(paths).current(planned)
    strategy_publication = next(item for item in snapshot["tasks"] if item["task_id"] == "STRATEGY_PUBLICATION")

    assert strategy_publication["status"] == WorkflowStatus.COMPLETE.value
    assert snapshot["run"]["current_stage"] == "WAITING_FOR_MANUAL_APPROVAL"
    assert snapshot["run"]["next_action"] == "Manual approval required before live trading"


def test_workflow_orchestrator_honors_admin_live_trading_switch(tmp_path) -> None:
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
                "completed": [job.job_id for job in planned],
                "failed": [],
                "history": [{"job_id": job.job_id, "recorded_at": "2026-01-01T00:00:00+00:00"} for job in planned],
                "running": {},
            }
        ),
        encoding="utf-8",
    )
    paths.post_pipeline_state_file.write_text(
        json.dumps(
            {
                "status": "COMPLETE",
                "stages": [
                    {"stage_id": "AUTONOMOUS_RESEARCH", "status": "COMPLETE"},
                    {"stage_id": "DEPLOY_PAPER_PORTFOLIO", "status": "COMPLETE"},
                    {"stage_id": "SHADOW_TRADING_REVIEW", "status": "COMPLETE"},
                    {"stage_id": "PRODUCTION_READINESS", "status": "COMPLETE"},
                    {"stage_id": "PRODUCTION_CERTIFICATION", "status": "COMPLETE"},
                ],
            }
        ),
        encoding="utf-8",
    )
    paths.admin_settings_file.write_text(
        json.dumps(
            {
                "values": {
                    "risk.live_trading_enabled": True,
                    "workflow.live_trading_blocked_by_policy": False,
                }
            }
        ),
        encoding="utf-8",
    )

    snapshot = WorkflowOrchestrator(paths).current(planned)
    manual_gate = next(item for item in snapshot["tasks"] if item["task_id"] == "MANUAL_APPROVAL_GATE")
    live_gate = next(item for item in snapshot["tasks"] if item["task_id"] == "LIVE_TRADING_GATE")

    assert manual_gate["status"] == WorkflowStatus.COMPLETE.value
    assert live_gate["status"] == WorkflowStatus.READY.value
    assert snapshot["run"]["current_stage"] == "LIVE_TRADING_GATE"
    assert snapshot["run"]["live_trading_status"] == "APPROVED_NOT_STARTED"


def _config() -> FullHistorySchedulerConfig:
    return FullHistorySchedulerConfig(
        pairs=("EUR_USD",),
        timeframes=("H1",),
        start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end=datetime(2026, 2, 1, tzinfo=timezone.utc),
        smoke_days=7,
        rolling_years=1,
    )
