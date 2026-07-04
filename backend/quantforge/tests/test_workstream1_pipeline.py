from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from quantforge.research import (
    DatabaseResearchScope,
    Workstream1PipelineRunner,
    Workstream1PipelineScheduler,
    WorkstreamPipelineTaskStatus,
    WorkstreamPipelineTaskType,
)


class FakeCandleRepository:
    def __init__(self, *, duplicates: int = 0) -> None:
        self.duplicates = duplicates
        self.rows = [
            {
                "time": datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=index),
                "pair_name": "EUR_USD",
                "granularity": "H1",
                "open_price": Decimal("1.1000") + Decimal(index) * Decimal("0.0001"),
                "high_price": Decimal("1.1010") + Decimal(index) * Decimal("0.0001"),
                "low_price": Decimal("1.0990") + Decimal(index) * Decimal("0.0001"),
                "close_price": Decimal("1.1005") + Decimal(index) * Decimal("0.0001"),
                "volume": 100 + index,
                "is_complete": True,
            }
            for index in range(1_000)
        ]

    def count_window(self, pair_name: str, granularity: str, start: datetime, end: datetime, **_: object) -> int:
        return len(self._window(pair_name, granularity, start, end))

    def duplicate_count(self, pair_name: str, granularity: str, start: datetime, end: datetime, **_: object) -> int:
        return self.duplicates

    def load_window(
        self,
        pair_name: str,
        granularity: str,
        start: datetime,
        end: datetime,
        **kwargs: object,
    ) -> list[dict]:
        limit = int(kwargs.get("limit", 50_000))
        return self._window(pair_name, granularity, start, end)[:limit]

    def _window(self, pair_name: str, granularity: str, start: datetime, end: datetime) -> list[dict]:
        return [
            row
            for row in self.rows
            if row["pair_name"] == pair_name
            and row["granularity"] == granularity
            and start <= row["time"] < end
        ]


def test_scheduler_creates_complete_workstream_task_plan() -> None:
    scope = _scope()

    schedule = Workstream1PipelineScheduler().schedule(scope)

    assert len(schedule.tasks) == 9
    assert tuple(task.task_type for task in schedule.tasks) == (
        WorkstreamPipelineTaskType.DATABASE_CONNECTION,
        WorkstreamPipelineTaskType.CANDLE_COVERAGE_VALIDATION,
        WorkstreamPipelineTaskType.REAL_EXPERIMENT_BATCHES,
        WorkstreamPipelineTaskType.CANDIDATE_ASSET_GENERATION,
        WorkstreamPipelineTaskType.OPTIMIZATION,
        WorkstreamPipelineTaskType.BACKTESTING,
        WorkstreamPipelineTaskType.VALIDATION,
        WorkstreamPipelineTaskType.STRATEGY_ASSET_PUBLICATION,
        WorkstreamPipelineTaskType.PIPELINE_REPORT,
    )
    assert all(task.status == WorkstreamPipelineTaskStatus.PENDING for task in schedule.tasks)


def test_pipeline_runs_database_backed_workstream_to_completion() -> None:
    result = Workstream1PipelineRunner(FakeCandleRepository()).run(_scope())

    assert result.successful is True
    assert len(result.completed_tasks) == 9
    assert result.failed_tasks == ()
    assert result.report.completed_tasks == 9
    assert result.report.failed_tasks == 0
    assert result.report.stored_candles >= 700
    assert result.report.real_experiment_batches == 12
    assert result.report.database_backed_candidate_assets == 12
    assert result.report.optimized_candidates == 3
    assert result.report.backtested_candidates == 3
    assert result.report.validated_strategy_assets == 3
    assert len(result.validated_assets) == 3
    assert all(asset.strategy_asset.passport.production for asset in result.validated_assets)
    assert result.report.archived is True
    assert result.audit_trail


def test_pipeline_reports_failed_coverage_without_validated_assets() -> None:
    result = Workstream1PipelineRunner(FakeCandleRepository(duplicates=1)).run(_scope())

    assert result.successful is False
    assert len(result.failed_tasks) == 7
    assert result.report.failed_tasks == 7
    assert result.report.real_experiment_batches == 0
    assert result.report.database_backed_candidate_assets == 0
    assert result.report.validated_strategy_assets == 0
    assert result.validated_assets == ()
    assert result.schedule.tasks[1].status == WorkstreamPipelineTaskStatus.FAILED


def _scope() -> DatabaseResearchScope:
    return DatabaseResearchScope(
        pairs=("EUR_USD",),
        timeframes=("H1",),
        start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end=datetime(2026, 2, 1, tzinfo=timezone.utc),
        window_candles=100,
        stride_candles=50,
        max_batches=12,
        max_assets_to_validate=3,
    )
