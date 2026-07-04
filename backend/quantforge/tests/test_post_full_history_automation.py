from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from quantforge.research.full_history_scheduler import (
    FullHistoryResearchScheduler,
    FullHistorySchedulerConfig,
)
from quantforge.research.post_full_history_automation import (
    PostFullHistoryStage,
    automation_already_finished,
    full_history_plan_exhausted,
    run_post_full_history_automation,
)
from quantforge.tests.test_workstream1_pipeline import FakeCandleRepository


def test_full_history_plan_exhausted_requires_all_planned_jobs_finished(tmp_path) -> None:
    state_file = tmp_path / "full_history.json"
    scheduler = FullHistoryResearchScheduler(
        config=_config(),
        state_file=state_file,
        repository_factory=FakeCandleRepository,
    )
    planned = scheduler.plan()
    state_file.write_text(
        json.dumps(
            {
                "completed": [planned[0].job_id],
                "failed": [],
                "history": [],
                "running": {},
            }
        ),
        encoding="utf-8",
    )

    assert full_history_plan_exhausted(state_file, planned) is False

    state_file.write_text(
        json.dumps(
            {
                "completed": [planned[0].job_id],
                "failed": [planned[1].job_id, planned[2].job_id, planned[3].job_id],
                "history": [],
                "running": {},
            }
        ),
        encoding="utf-8",
    )

    assert full_history_plan_exhausted(state_file, planned) is True


def test_post_full_history_automation_runs_stages_once_and_records_state(tmp_path) -> None:
    repo_root = tmp_path
    script_dir = repo_root / "scripts"
    script_dir.mkdir()
    (script_dir / "stage_a.py").write_text("print('stage a complete')\n", encoding="utf-8")
    (script_dir / "stage_b.py").write_text("print('stage b complete')\n", encoding="utf-8")
    state_file = tmp_path / "post_pipeline.json"

    result = run_post_full_history_automation(
        repo_root=repo_root,
        state_file=state_file,
        python_exe=Path(sys.executable),
        stages=(
            PostFullHistoryStage("A", "scripts/stage_a.py", "Stage A"),
            PostFullHistoryStage("B", "scripts/stage_b.py", "Stage B"),
        ),
    )

    payload = json.loads(state_file.read_text(encoding="utf-8"))
    assert result.status == "COMPLETE"
    assert payload["status"] == "COMPLETE"
    assert [stage["stage_id"] for stage in payload["stages"]] == ["A", "B"]
    assert automation_already_finished(state_file) is True


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

