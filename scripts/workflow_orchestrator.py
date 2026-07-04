from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

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
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    scheduler = FullHistoryResearchScheduler(
        config=FullHistorySchedulerConfig(
            pairs=FULL_HISTORY_RESEARCH_PAIRS,
            timeframes=FULL_HISTORY_RESEARCH_TIMEFRAMES,
            start=FULL_HISTORY_RESEARCH_START,
            end=today_start + timedelta(days=1),
        ),
        state_file=PROJECT_ROOT / "var" / "full_history_research_state.json",
        repository_factory=lambda: None,  # type: ignore[arg-type]
    )
    return scheduler.plan()


if __name__ == "__main__":
    main()
