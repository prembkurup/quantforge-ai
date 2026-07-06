from __future__ import annotations

import sys
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from quantforge.admin.settings import admin_setting_value  # noqa: E402
from quantforge.research.full_history_scheduler import (  # noqa: E402
    FULL_HISTORY_RESEARCH_PAIRS,
    FULL_HISTORY_RESEARCH_START,
    FULL_HISTORY_RESEARCH_TIMEFRAMES,
    FullHistoryResearchScheduler,
    FullHistorySchedulerConfig,
)
from quantforge.research.workflow_orchestration import (  # noqa: E402
    WorkflowOrchestrator,
    default_workflow_paths,
)


def main() -> None:
    snapshot = WorkflowOrchestrator(default_workflow_paths(PROJECT_ROOT)).current(_planned_jobs())
    run = snapshot["run"]
    print("Workflow: Full History Research Plan")
    print(f"Stage: {run['current_stage']}")
    print(f"Progress: {run['completed_tasks']} / {run['total_tasks']}")
    print(f"Running: {run['running_tasks']}")
    print(f"Failed: {run['failed_tasks']}")
    print(f"Retryable: {run['retryable_tasks']}")
    print(f"Blocked: {run['blocked_tasks']}")
    print(f"Next Action: {run['next_action']}")
    print(f"Live Trading: {run['live_trading_status']} - {snapshot['live_gate']['reason']}")


def _planned_jobs():
    admin_file = PROJECT_ROOT / "var" / "admin_settings.json"
    scheduler = FullHistoryResearchScheduler(
        config=FullHistorySchedulerConfig(
            pairs=FULL_HISTORY_RESEARCH_PAIRS,
            timeframes=FULL_HISTORY_RESEARCH_TIMEFRAMES,
            start=FULL_HISTORY_RESEARCH_START,
            end=datetime.combine(date.today(), time.min, tzinfo=UTC) + timedelta(days=1),
            window_candles=int(admin_setting_value(admin_file, "full_history.window_candles", 300)),
            smoke_window_candles_by_timeframe={
                "M5": 300,
                "M15": 300,
                "H1": 300,
                "H4": int(admin_setting_value(admin_file, "full_history.h4_smoke_window_candles", 120)),
            },
            smoke_days=int(admin_setting_value(admin_file, "full_history.smoke_days", 31)),
            smoke_max_batches=int(admin_setting_value(admin_file, "full_history.smoke_max_batches", 2)),
            rolling_max_batches=int(admin_setting_value(admin_file, "full_history.rolling_max_batches", 25)),
            full_history_max_batches=int(admin_setting_value(admin_file, "full_history.full_history_max_batches", 100)),
        ),
        state_file=PROJECT_ROOT / "var" / "full_history_research_state.json",
        repository_factory=lambda: None,  # type: ignore[arg-type]
    )
    return scheduler.plan()


if __name__ == "__main__":
    main()
