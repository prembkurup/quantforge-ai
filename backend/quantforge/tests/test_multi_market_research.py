from __future__ import annotations

import json
from datetime import UTC, datetime

from quantforge.research.full_history_scheduler import FullHistoryResearchScheduler, FullHistorySchedulerConfig
from quantforge.research.multi_market import (
    MultiMarketResearchPlanner,
    RejectedStrategyCandidate,
    RejectedStrategyRepository,
    ResearchMatrixBuilder,
    coverage_report,
    productivity_rows,
)
from quantforge.research.strategy_assets import StrategyAssetRepository


def test_full_history_matrix_marks_completed_pair_timeframe_usable(tmp_path) -> None:
    state_file = tmp_path / "full_history.json"
    asset_repo = StrategyAssetRepository(tmp_path / "assets.json")
    rejection_repo = RejectedStrategyRepository(tmp_path / "rejected.json")
    scheduler = FullHistoryResearchScheduler(
        FullHistorySchedulerConfig(
            pairs=("EUR_USD",),
            timeframes=("H1",),
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2025, 1, 1, tzinfo=UTC),
            rolling_years=1,
        ),
        state_file,
        repository_factory=lambda: None,  # type: ignore[arg-type]
    )
    planned = scheduler.plan()
    state_file.write_text(json.dumps({"completed": [job.job_id for job in planned], "failed": [], "history": []}))

    rows = ResearchMatrixBuilder(planned, state_file, asset_repo, rejection_repo).rows()

    assert len(rows) == 1
    assert rows[0].usable_for_research is True
    assert rows[0].data_quality_score == 1.0


def test_rejected_strategy_repository_keeps_failure_reason(tmp_path) -> None:
    repo = RejectedStrategyRepository(tmp_path / "rejected.json")
    repo.upsert_many(
        (
            RejectedStrategyCandidate(
                candidate_id="RJ-1",
                pair="EUR_USD",
                timeframe="H1",
                strategy_family="TREND_FOLLOWING",
                template="Trend Pullback",
                failure_stage="Validation",
                failure_reason="Walk Forward Failure",
                metrics={"profit_factor": 1.1},
                timestamp="2026-07-05T00:00:00+00:00",
                research_run="test",
                research_program_id="RP-EUR_USD-H1",
            ),
        )
    )

    rows = repo.list()

    assert rows[0].failure_reason == "Walk Forward Failure"
    assert rows[0].pair == "EUR_USD"


def test_planner_and_reports_cover_every_usable_dataset(tmp_path) -> None:
    state_file = tmp_path / "full_history.json"
    asset_repo = StrategyAssetRepository(tmp_path / "assets.json")
    rejection_repo = RejectedStrategyRepository(tmp_path / "rejected.json")
    scheduler = FullHistoryResearchScheduler(
        FullHistorySchedulerConfig(
            pairs=("EUR_USD", "GBP_USD"),
            timeframes=("H1", "M15"),
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2025, 1, 1, tzinfo=UTC),
            rolling_years=1,
        ),
        state_file,
        repository_factory=lambda: None,  # type: ignore[arg-type]
    )
    planned = scheduler.plan()
    state_file.write_text(json.dumps({"completed": [job.job_id for job in planned], "failed": [], "history": []}))
    matrix = ResearchMatrixBuilder(planned, state_file, asset_repo, rejection_repo)
    programs = MultiMarketResearchPlanner().plan(matrix.datasets())

    assert len(programs) == 4
    report = coverage_report(matrix.rows(), programs)
    assert report["usable_datasets"] == 4
    assert report["research_programs"] == 4
    assert len(productivity_rows(matrix.rows())) == 4
