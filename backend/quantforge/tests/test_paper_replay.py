import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import auto_replay_paper_trading as auto_replay
from quantforge.live import (
    HistoricalCandleReplayStream,
    PaperTradingReplayRunner,
    ReplayProgressStore,
    ReplaySession,
    ReplayStatus,
    infer_replay_mode,
)
from quantforge.research.strategy_assets import (
    ApprovedStrategyAssetStore,
    StrategyAssetLoader,
    StrategyAssetRepository,
)
from quantforge.validation import StrategyValidationPlatform
from quantforge.live.replay import _coerce_datetime, replay_cursor


class FakeCandleRepository:
    def __init__(self, count: int = 500) -> None:
        self.count = count

    def load_window(self, pair_name, granularity, start, end, *, complete_only=True, limit=50_000):
        rows = []
        for index in range(self.count):
            open_price = 1.10 + index * 0.00001
            rows.append(
                {
                    "time": start + timedelta(hours=index),
                    "pair_name": pair_name,
                    "granularity": granularity,
                    "volume": 100 + index,
                    "open_price": open_price,
                    "high_price": open_price + 0.0002,
                    "low_price": open_price - 0.0001,
                    "close_price": open_price + 0.0001,
                    "is_complete": True,
                    "source": "fake",
                }
            )
        return rows


def test_historical_candle_replay_stream_emits_new_candle_events() -> None:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    session = ReplaySession(
        replay_id="test-replay",
        pairs=("EUR_USD",),
        timeframes=("H1",),
        start_time=start,
        end_time=start + timedelta(days=30),
        mode=infer_replay_mode(("EUR_USD",), ("H1",)),
    )

    events = HistoricalCandleReplayStream(FakeCandleRepository(300)).events(session)

    assert len(events) == 300
    assert events[0].payload["instrument"] == "EUR_USD"
    assert events[0].payload["timeframe"] == "H1"
    assert all(event.event_type.value == "new_candle" for event in events)


def test_replay_treats_naive_candle_times_as_utc() -> None:
    assert _coerce_datetime("2026-07-07 03:30:00").isoformat() == "2026-07-07T03:30:00+00:00"


def test_paper_trading_replay_runner_processes_real_style_candle_events(tmp_path: Path) -> None:
    repository = StrategyAssetRepository(tmp_path / "approved_strategy_assets.json")
    validation = StrategyValidationPlatform()
    asset = validation.create_strategy_asset(validation.validate("QF-REPLAY-0001"))
    ApprovedStrategyAssetStore(repository).publish(
        asset,
        source_workflow_id="workflow-replay",
        source_experiment_id="experiment-replay",
    )
    progress = ReplayProgressStore(tmp_path / "paper_replay_progress.json")
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    session = ReplaySession(
        replay_id="test-replay-runner",
        pairs=("EUR_USD",),
        timeframes=("H1",),
        start_time=start,
        end_time=start + timedelta(days=365),
        mode=infer_replay_mode(("EUR_USD",), ("H1",)),
    )

    result = PaperTradingReplayRunner(
        HistoricalCandleReplayStream(FakeCandleRepository(500)),
        progress,
        strategy_asset_loader=StrategyAssetLoader(repository),
        report_path=tmp_path / "paper_replay_report.json",
        improvement_requests_path=tmp_path / "history_validation_improvements.json",
    ).run(session, strategy_asset_id="QF-REPLAY-0001")

    assert result.live_market_received is True
    assert result.replay_cursor is not None
    assert result.replay_cursor.processed_events == 500
    assert result.signals_generated == 500
    assert len(result.paper_orders) == 500
    assert progress.load().status.value == "COMPLETE"
    assert progress.load().replay_mode == "SINGLE_PAIR_SINGLE_TIMEFRAME"
    assert progress.load().progress_percent == 100.0
    assert (tmp_path / "paper_replay_report.json").exists()


def test_replay_progress_store_loads_legacy_cursor_payload(tmp_path: Path) -> None:
    path = tmp_path / "paper_replay_progress.json"
    path.write_text(
        """
        {
          "current_candle_time": "",
          "end_time": "2024-01-02T00:00:00+00:00",
          "generated_signals": 0,
          "last_error": "",
          "pair": "EUR_USD",
          "paper_orders": 0,
          "processed_events": 0,
          "replay_id": "legacy",
          "start_time": "2024-01-01T00:00:00+00:00",
          "status": "RUNNING",
          "timeframe": "H1"
        }
        """,
        encoding="utf-8",
    )

    cursor = ReplayProgressStore(path).load()

    assert cursor is not None
    assert cursor.status == ReplayStatus.RUNNING
    assert cursor.replay_speed == "MAXIMUM"
    assert cursor.control == "RUNNING"


def test_historical_replay_stream_honors_stop_control(tmp_path: Path) -> None:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    session = ReplaySession(
        replay_id="test-replay-stop",
        pairs=("EUR_USD",),
        timeframes=("H1",),
        start_time=start,
        end_time=start + timedelta(days=1),
        mode=infer_replay_mode(("EUR_USD",), ("H1",)),
    )
    progress = ReplayProgressStore(tmp_path / "paper_replay_progress.json")
    progress.save(replay_cursor(session, status=ReplayStatus.STOPPED, control="STOP_REQUESTED"))

    events = HistoricalCandleReplayStream(FakeCandleRepository(10)).events(
        session,
        progress_store=progress,
        replay_speed="MAXIMUM",
    )

    assert events == ()
    assert progress.load().status == ReplayStatus.STOPPED


def test_auto_replay_campaign_requeues_running_jobs_after_restart(tmp_path: Path, monkeypatch) -> None:
    state_file = tmp_path / "paper_replay_campaign_status.json"
    monkeypatch.setattr(auto_replay, "STATE_FILE", state_file)
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 2, tzinfo=timezone.utc)
    jobs = auto_replay._build_jobs("AUTO-TEST", ("EUR_USD",), ("H1",), start, end)
    jobs[0]["status"] = ReplayStatus.RUNNING.value
    state_file.write_text(
        json.dumps(
            {
                "campaign_id": "AUTO-TEST",
                "jobs": {jobs[0]["job_id"]: jobs[0]},
                "pairs": ["EUR_USD"],
                "timeframes": ["H1"],
            }
        ),
        encoding="utf-8",
    )

    resumed = auto_replay._load_state("AUTO-TEST", ("EUR_USD",), ("H1",), start, end, 6, jobs)
    job = next(iter(resumed["jobs"].values()))

    assert job["status"] == ReplayStatus.PENDING.value
    assert resumed["running_jobs"] == 0
    assert resumed["pending_jobs"] == 1
