from __future__ import annotations

from dataclasses import replace

from quantforge.research.history_validation import (
    DEFAULT_PAIR_SPREAD_PIPS,
    HistoricalValidationConfig,
    HistoricalValidationEngine,
    default_historical_validation_paths,
)
from quantforge.research.strategy_assets import ApprovedStrategyAssetStore, StrategyAssetRepository
from quantforge.validation import StrategyValidationPlatform


def test_history_validation_seeds_queue_from_approved_assets(tmp_path) -> None:
    engine = _engine(tmp_path, asset_count=2)

    queue = engine.ensure_queue()

    assert len(queue) == 2
    assert queue[0]["validation_id"].startswith("hv_")
    assert queue[0]["status"] == "Queued"
    assert queue[0]["dataset_id"]


def test_history_validation_runs_one_batch_and_persists_result(tmp_path) -> None:
    engine = _engine(tmp_path, asset_count=2, config=HistoricalValidationConfig(batch_size=1))

    status = engine.run_next_batch()
    results = engine.results()

    assert status["progress"]["completed"] == 1
    assert len(results) == 1
    assert results[0]["historical_period"] == "last_10_years"
    assert results[0]["trades"] >= 100
    assert results[0]["spread_pips"] == DEFAULT_PAIR_SPREAD_PIPS[results[0]["pair"]]
    assert results[0]["slippage_pips"] == 0.2
    assert results[0]["execution_cost"] == results[0]["trades"] * results[0]["execution_cost_per_trade"]
    assert results[0]["net_profit"] == round(results[0]["gross_profit"] - results[0]["execution_cost"], 2)
    assert results[0]["result"] in {"PASS", "FAIL"}


def test_history_validation_creates_improvement_request_for_failed_result(tmp_path) -> None:
    engine = _engine(
        tmp_path,
        asset_count=1,
        config=HistoricalValidationConfig(batch_size=1, min_profit_factor=99.0),
    )

    engine.run_next_batch()
    improvements = engine.improvements()

    assert improvements
    assert improvements[0]["status"] == "REQUESTED"
    assert improvements[0]["reason_code"] in {
        "LOW_PROFIT_FACTOR",
        "LOW_WIN_RATE",
        "EXCESSIVE_DRAWDOWN",
        "INSUFFICIENT_TRADES",
        "STRATEGY_DEGRADATION",
    }


def test_history_validation_status_reports_dashboard_summary(tmp_path) -> None:
    engine = _engine(tmp_path, asset_count=3, config=HistoricalValidationConfig(batch_size=1))

    engine.run_next_batch()
    status = engine.status()

    assert status["progress"]["total"] == 3
    assert status["completed_validations"] == 1
    assert "estimated_remaining_minutes" in status
    assert "recent_results" in status
    assert status["balance_sheet"]["paper_balance"] == 100_000.0


def test_history_validation_balance_sheet_matches_paper_summary_shape(tmp_path) -> None:
    engine = _engine(tmp_path, asset_count=2, config=HistoricalValidationConfig(batch_size=1))

    engine.run_next_batch()
    sheet = engine.balance_sheet()

    assert sheet["paper_balance"] == 100_000.0
    assert sheet["paper_equity"] == 100_000.0 + sheet["historical_pl"]
    assert sheet["spread_slippage_cost"] > 0
    assert sheet["spread_model"] == "PAIR_SPECIFIC"
    assert sheet["spread_pips"] == DEFAULT_PAIR_SPREAD_PIPS[engine.results()[0]["pair"]]
    assert sheet["slippage_pips"] == 0.2
    assert sheet["closed_validations"] == 1
    assert sheet["promotion_readiness"] in {"PROMOTE", "HOLD", "NEEDS_RESEARCH"}
    assert "drawdown" in sheet
    assert "expected_vs_actual_deviation" in sheet


def test_history_validation_uses_pair_specific_spread(tmp_path) -> None:
    engine = _engine(
        tmp_path,
        asset_count=2,
        config=HistoricalValidationConfig(batch_size=2, pair_spreads={"EUR_USD": 0.7, "GBP_USD": 1.4}),
    )

    engine.run_next_batch()
    results = {item["pair"]: item for item in engine.results()}

    assert results["EUR_USD"]["spread_pips"] == 0.7
    assert results["GBP_USD"]["spread_pips"] == 1.4
    assert results["GBP_USD"]["execution_cost_per_trade"] > results["EUR_USD"]["execution_cost_per_trade"]


def test_history_validation_exposes_pair_spread_profile(tmp_path) -> None:
    engine = _engine(tmp_path, asset_count=1, config=HistoricalValidationConfig(pair_spreads={"EUR_USD": 0.7}))

    profile = engine.spread_profile()

    eur_usd = next(row for row in profile if row["pair"] == "EUR_USD")
    gbp_jpy = next(row for row in profile if row["pair"] == "GBP_JPY")
    assert eur_usd["spread_pips"] == 0.7
    assert gbp_jpy["spread_pips"] == 2.0


def _engine(tmp_path, *, asset_count: int, config: HistoricalValidationConfig | None = None) -> HistoricalValidationEngine:
    repository = StrategyAssetRepository(tmp_path / "approved_strategy_assets.json")
    validation = StrategyValidationPlatform()
    store = ApprovedStrategyAssetStore(repository)
    pairs = ("EUR_USD", "GBP_USD", "AUD_USD")
    timeframes = ("M5", "M15", "H1")
    for index in range(asset_count):
        asset = validation.create_strategy_asset(validation.validate(f"QF-HV-{index:04d}"))
        asset = replace(
            asset,
            strategy_definition={
                **asset.strategy_definition,
                "pair": pairs[index % len(pairs)],
                "timeframe": timeframes[index % len(timeframes)],
                "research_program_id": f"RP-{pairs[index % len(pairs)]}-{timeframes[index % len(timeframes)]}",
                "dataset_id": f"DS-{pairs[index % len(pairs)]}-{timeframes[index % len(timeframes)]}",
            },
        )
        store.publish(asset, source_job_id=asset.strategy_definition["dataset_id"])
    return HistoricalValidationEngine(
        asset_repository=repository,
        paths=default_historical_validation_paths(tmp_path),
        config=config or HistoricalValidationConfig(batch_size=1),
    )
