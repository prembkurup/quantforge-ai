import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["QUANTFORGE_DEMO_MODE"] = "1"

from quantforge.dashboard import service as dashboard_service
from quantforge.dashboard.api import create_app
from quantforge.dashboard.service import DashboardService
from quantforge.research.strategy_assets import ApprovedStrategyAssetStatus, ApprovedStrategyAssetStore, StrategyAssetRepository
from quantforge.strategies.production import ProductionStrategyManagementPlatform


client = TestClient(create_app())


def test_dashboard_overview_returns_core_kpis() -> None:
    response = client.get("/api/dashboard/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["platform_status"] == "HEALTHY"
    assert payload["research_status"] == "COMPLETE"
    assert payload["portfolio_readiness"] == "READY_FOR_PORTFOLIO_CONSTRUCTION"
    assert payload["live_trading_status"] in {"DISABLED", "ENABLED", "BLOCKED_BY_POLICY"}
    assert payload["experiments"] == 750_000
    assert payload["candidate_strategies"] == 7_500_000
    assert payload["validated_assets"] == 1_000
    assert payload["production_strategies"] == 75


def test_dashboard_health_endpoint_is_read_only() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["mode"] == "read-only"


def test_strategy_library_is_readable_and_traceable() -> None:
    strategies = client.get("/api/strategies").json()
    first = strategies[0]

    assert len(strategies) == 75
    assert first["status"] == "PRODUCTION_GRADE"

    detail = client.get(f"/api/strategies/{first['strategy_id']}").json()
    assert detail["passport"]["strategy_id"] == first["strategy_id"]
    assert detail["validation_report"]["grade"] == "A"
    assert detail["decision_trace"]["complete"] is True
    trace = client.get(f"/api/strategies/{first['strategy_id']}/trace").json()
    assert trace["strategy_asset_id"] == first["strategy_id"]
    assert trace["trace_steps"]
    assert "approval_gate" in trace


def test_indicators_are_listed_for_dashboard_reference() -> None:
    indicators = client.get("/api/indicators").json()

    names = {indicator["indicator"] for indicator in indicators}
    assert "EMA" in names
    assert "ATR" in names
    assert "BOS" in names
    assert all(indicator["status"] == "ACTIVE" for indicator in indicators)


def test_pipeline_page_data_shows_tasks_engines_and_current_work() -> None:
    summary = client.get("/api/pipeline/summary").json()
    current = client.get("/api/pipeline/current-task").json()
    tasks = client.get("/api/pipeline/tasks").json()
    engines = client.get("/api/pipeline/engines").json()
    workload = client.get("/api/pipeline/workload").json()

    assert summary["pipeline_status"] in {"RUNNING", "COMPLETE", "COMPLETE_WITH_WARNINGS"}
    if summary["pipeline_status"] == "RUNNING":
        assert summary["running_tasks"] >= 1
        assert current["status"] == "RUNNING"
        assert any(task["status"] == "RUNNING" for task in tasks)
    else:
        assert summary["queue_depth"] == 0
        assert current["status"] in {"COMPLETE", "COMPLETE_WITH_WARNINGS"}
        assert all(task["status"] != "QUEUED" for task in tasks)
    assert current["progress"] > 0
    assert any(engine["engine"] == "Live Trading Engine" for engine in engines)
    live_engine = next(engine for engine in engines if engine["engine"] == "Live Trading Engine")
    assert live_engine["status"] in {"DISABLED", "ENABLED", "BLOCKED"}
    assert len(workload) == len(engines)


def test_intraday_daily_endpoint_exposes_version_2_dashboard_status() -> None:
    response = client.get("/api/intraday/daily")

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_session"] in {
        "Asian",
        "London Open",
        "London",
        "London-New York Overlap",
        "New York",
        "Late New York",
        "No Trading",
    }
    assert payload["trading_status"] in {
        "ACTIVE",
        "PAUSED (Risk Limit)",
        "FINISHED (End Of Day)",
        "NO TRADING",
    }
    assert "remaining_daily_risk" in payload
    assert payload["metrics"]["performance"]["daily_expectancy"] != 0
    assert payload["daily_report"]["report_id"].startswith("INTRADAY-DAILY-")
    assert payload["learning_loop"]["future_campaigns"]
    assert "certification" in payload
    assert "risk_decision" in payload
    assert "trade_journal" in payload
    assert 0 <= payload["market_readiness"]["score"] <= 100
    assert payload["market_readiness"]["decision"] in {"EXCELLENT", "NORMAL", "SELECTIVE", "NO_NEW_TRADES"}
    assert "session_quality" in payload["market_readiness"]["factors"]


def test_intraday_decision_intelligence_endpoint_exposes_milestone_24_layers() -> None:
    response = client.get("/api/intraday/decision-intelligence")

    assert response.status_code == 200
    payload = response.json()
    assert 0 <= payload["opportunity_score"]["score"] <= 100
    assert payload["market_quality"]["rating"] in {"Poor", "Fair", "Good", "Excellent"}
    assert payload["eligibility"]["status"] in {"Eligible", "Not Eligible"}
    assert payload["trade_decision"]["decision"] in {"BUY", "SELL", "EXIT", "HOLD", "NO TRADE"}
    assert payload["trade_decision"]["decision_trace"]["reason_codes"]
    assert payload["daily_trading_plan"]["preferred_sessions"]
    assert payload["dynamic_daily_risk_budget"]["policy"] in {"Normal Risk", "Reduced Risk", "Minimal Risk", "No New Trades"}
    assert payload["intraday_trading_status"]["status"] in {"ACTIVE", "WAITING", "PAUSED", "NO TRADING", "FINISHED"}
    assert payload["dashboard"]["current_session"]
    assert payload["decision_timeline"]
    assert payload["daily_trading_journal"]["journal_id"].startswith("DECISION-JOURNAL-")
    assert payload["decision_quality_metrics"]["trades_avoided"] >= 0


def test_strategy_lifecycle_endpoint_exposes_milestone_28_payload() -> None:
    response = client.get("/api/strategy-lifecycle")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "StrategyLifecycleEngine"
    assert payload["strategy_count"] >= 1
    assert payload["strategies"]
    assert all("health_score" in strategy for strategy in payload["strategies"])
    assert payload["root_causes"]
    assert payload["reports"]["daily_strategy_health"]["report_id"].startswith("DAILY-STRATEGY-HEALTH-")
    assert payload["reports"]["weekly_lifecycle"]["report_id"].startswith("WEEKLY-LIFECYCLE-")
    assert payload["reports"]["monthly_strategy_evolution"]["report_id"].startswith("MONTHLY-STRATEGY-EVOLUTION-")
    assert payload["reports"]["research_recommendation"]["goals"]
    assert payload["reports"]["portfolio_impact"]["portfolio_impacts"]
    assert payload["acceptance_criteria"]["every_strategy_has_health_score"] is True
    assert payload["acceptance_criteria"]["degradations_have_root_cause"] is True
    assert "runtime_status" in payload
    assert "job_registered" in payload["runtime_status"]
    assert "research_requests_total" in payload["runtime_status"]


def test_pipeline_snapshot_combines_page_payload_for_fast_loading() -> None:
    snapshot = client.get("/api/pipeline/snapshot").json()

    assert snapshot["summary"]["pipeline_status"] in {"RUNNING", "COMPLETE", "COMPLETE_WITH_WARNINGS"}
    assert snapshot["current_task"]["status"] in {"RUNNING", "COMPLETE", "COMPLETE_WITH_WARNINGS"}
    assert snapshot["tasks"]
    assert snapshot["engines"]
    assert len(snapshot["workload"]) == len(snapshot["engines"])
    assert snapshot["full_history"]["planned_jobs"] >= 1
    assert snapshot["full_history"]["jobs"]
    assert snapshot["workflow"]["run"]["live_trading_status"] in {
        "BLOCKED_BY_POLICY",
        "WAITING_APPROVAL",
        "APPROVED_NOT_STARTED",
    }


def test_workflow_api_exposes_state_machine() -> None:
    response = client.get("/api/workflow/current")

    assert response.status_code == 200
    payload = response.json()
    workflow_id = payload["run"]["workflow_id"]
    assert payload["run"]["current_stage"]
    assert payload["run"]["next_action"]
    assert payload["run"]["live_trading_status"] in {
        "BLOCKED_BY_POLICY",
        "WAITING_APPROVAL",
        "APPROVED_NOT_STARTED",
    }
    assert payload["stages"]
    assert payload["tasks"]
    assert payload["approvals"]

    assert client.get("/api/workflow/runs").json()[0]["workflow_id"] == workflow_id
    assert client.get(f"/api/workflow/runs/{workflow_id}/stages").json()
    assert client.get(f"/api/workflow/runs/{workflow_id}/tasks").json()
    assert client.get(f"/api/workflow/runs/{workflow_id}/events").json()
    assert client.get(f"/api/workflow/runs/{workflow_id}/approvals").json()
    assert client.get("/api/workflow/approvals").json()
    assert client.get("/api/workflow/approvals/audit").status_code == 200
    assert client.post("/api/workflow/tasks/example/retry").status_code == 403


def test_architecture_orphan_report_classifies_all_audit_findings() -> None:
    response = client.get("/api/architecture/orphans")

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) >= 13
    assert {row["classification"] for row in rows} >= {"WIRE_NOW", "KEEP_FOR_FUTURE", "MOVE_TO_LEGACY"}
    assert all(row["module"].startswith("quantforge.") for row in rows)


def test_admin_settings_api_exposes_help_defaults_and_updates_values() -> None:
    response = client.get("/api/admin/settings")

    assert response.status_code == 200
    payload = response.json()
    settings = [
        setting
        for group in payload["groups"]
        for setting in group["settings"]
    ]
    h4_smoke = next(setting for setting in settings if setting["setting_id"] == "full_history.h4_smoke_window_candles")
    live_enabled = next(setting for setting in settings if setting["setting_id"] == "risk.live_trading_enabled")
    assert h4_smoke["default"] == 120
    assert "Default:" in h4_smoke["help"]
    assert h4_smoke["editable"] is True
    assert live_enabled["kind"] == "boolean"
    assert live_enabled["editable"] is True

    update = client.post("/api/admin/settings", json={"values": {"full_history.h4_smoke_window_candles": 120}})

    assert update.status_code == 200
    updated_settings = [
        setting
        for group in update.json()["groups"]
        for setting in group["settings"]
    ]
    updated_h4_smoke = next(setting for setting in updated_settings if setting["setting_id"] == "full_history.h4_smoke_window_candles")
    assert updated_h4_smoke["value"] == 120
    assert updated_h4_smoke["default"] == 120

    readonly = client.post("/api/admin/settings", json={"values": {"dashboard.api_port": 9000}})
    assert readonly.status_code == 400


def test_full_history_research_lists_configured_pairs_timeframes_and_jobs() -> None:
    response = client.get("/api/full-history/research")

    assert response.status_code == 200
    payload = response.json()
    symbols = {row["symbol"] for row in payload["pairs"]}
    timeframes = {row["timeframe"] for row in payload["timeframes"]}
    assert {"AUD_CAD", "EUR_USD", "GBP_USD", "USD_JPY", "NAS100_USD", "SPX500_USD"} <= symbols
    assert {"M5", "M15", "H1", "H4"} <= timeframes
    assert payload["pair_count"] == 30
    assert payload["timeframe_count"] == 4
    assert payload["pair_timeframe_count"] == 120
    assert payload["scheduler"]["jobs"]
    assert payload["coverage"]


def test_multi_market_research_api_exposes_matrix_programs_and_productivity() -> None:
    matrix = client.get("/api/research/matrix")
    programs = client.get("/api/research/programs")
    coverage = client.get("/api/research/coverage")
    diversity = client.get("/api/research/diversity")
    productivity = client.get("/api/research/productivity")
    rejected = client.get("/api/research/rejected")

    assert matrix.status_code == 200
    assert len(matrix.json()) == 120
    assert programs.status_code == 200
    assert coverage.json()["total_datasets"] == 120
    assert "pair_count" in diversity.json()
    assert productivity.json()
    assert rejected.status_code == 200


def test_research_orchestrator_api_exposes_status_runs_and_idle_reasons() -> None:
    status = client.get("/api/research/orchestrator/status")
    runs = client.get("/api/research/orchestrator/runs")
    idle_reason = client.get("/api/research/orchestrator/idle-reason")
    idle_reasons = client.get("/api/research/orchestrator/idle-reasons")
    guardrails = client.get("/api/research/orchestrator/guardrails")

    assert status.status_code == 200
    assert status.json()["state"] in {"STOPPED", "IDLE", "WAITING_FOR_SCHEDULE", "ERROR"}
    assert "next_run_at" in status.json()
    assert "idle_reason" in status.json()
    assert idle_reason.status_code == 200
    assert runs.status_code == 200
    assert idle_reasons.status_code == 200
    assert guardrails.status_code == 200


def test_research_orchestrator_manual_control_endpoints() -> None:
    stopped = client.post("/api/research/orchestrator/stop")
    started = client.post("/api/research/orchestrator/start")
    wake = client.post("/api/research/orchestrator/wake")

    assert stopped.status_code == 200
    assert stopped.json()["enabled"] is False
    assert started.status_code == 200
    assert started.json()["enabled"] is True
    assert wake.status_code == 200
    assert wake.json()["trigger"] == "manual_wake"


def test_fine_tuning_status_is_separate_from_research_status() -> None:
    response = client.get("/api/fine-tuning/status")

    assert response.status_code == 200
    assert response.json()["state"] in {
        "DISABLED",
        "MANUAL",
        "GATED",
        "WAITING_FOR_NEW_ASSETS",
        "TRAINING",
        "EVALUATING",
        "READY_TO_PROMOTE",
        "BLOCKED",
        "ERROR",
    }


def test_history_validation_api_exposes_queue_results_and_improvements() -> None:
    run = client.post("/api/history-validation/run-next")
    status = client.get("/api/history-validation/status")
    balance = client.get("/api/history-validation/balance-sheet")
    queue = client.get("/api/history-validation/queue")
    running = client.get("/api/history-validation/running")
    results = client.get("/api/history-validation/results")
    improvements = client.get("/api/history-validation/improvements")
    spreads = client.get("/api/history-validation/spreads")

    assert run.status_code == 200
    assert status.status_code == 200
    assert status.json()["progress"]["total"] >= 1
    assert balance.status_code == 200
    assert balance.json()["paper_balance"] == 100_000.0
    assert queue.status_code == 200
    assert running.status_code == 200
    assert results.status_code == 200
    assert improvements.status_code == 200
    assert spreads.status_code == 200
    assert any(row["pair"] == "EUR_USD" for row in spreads.json())
    if results.json():
        detail = client.get(f"/api/history-validation/results/{results.json()[0]['validation_id']}")
        assert detail.status_code == 200


def test_portfolio_ops_knowledge_and_paper_endpoints_are_read_only() -> None:
    assert client.get("/api/portfolio/readiness").json()["portfolio_readiness"] == "READY_FOR_PAPER_TRADING"
    portfolio_intelligence = client.get("/api/portfolio/intelligence")
    assert portfolio_intelligence.status_code == 200
    payload = portfolio_intelligence.json()
    assert payload["health"]["status"] == "READY"
    assert payload["allocation"]["approved"] is True
    assert payload["daily_review"]["review_id"].startswith("PORT-REVIEW-")
    assert payload["acceptance"]["accepted"] is True
    assert client.get("/api/ops/health").json()["platform_status"] == "HEALTHY"
    assert client.get("/api/knowledge/summary").json()["knowledge_records"] == 795_000
    assert client.get("/api/paper/summary").json()["promotion_readiness"] == "PROMOTE"
    assert client.get("/api/paper/replay").json()["source"] == "ReplayProgressStore"
    assert client.post("/api/dashboard/overview").status_code == 405
    assert client.post("/api/portfolio/intelligence").status_code == 405


def test_paper_position_chart_uses_source_candle_time_as_utc_trade_time() -> None:
    response = client.get(
        "/api/paper/positions/chart",
        params={
            "pair": "EUR_USD",
            "timeframe": "H1",
            "opened_at": "2026-07-07T03:46:55+00:00",
            "source_candle_time": "2026-07-07 03:30:00",
        },
    )

    assert response.status_code == 200
    trade = response.json()["trade"]
    assert trade["opened_at"] == "2026-07-07T03:30:00+00:00"
    assert trade["source_candle_time"] == "2026-07-07T03:30:00+00:00"


def test_paper_summary_uses_real_position_store_and_rows_include_strategy(monkeypatch, tmp_path: Path) -> None:
    positions_file = tmp_path / "paper_positions.json"
    assets_file = tmp_path / "approved_strategy_assets.json"
    repository = StrategyAssetRepository(assets_file)
    record = ApprovedStrategyAssetStore(repository).publish(
        ProductionStrategyManagementPlatform()._demo_asset(),
        status=ApprovedStrategyAssetStatus.APPROVED,
    )
    positions_file.write_text(
        f"""
        {{
          "positions": [
            {{
              "position_id": "closed",
              "status": "CLOSED",
              "pair": "EUR_USD",
              "timeframe": "H1",
              "strategy_asset_id": "{record.strategy_asset_id}",
              "direction": "BUY",
              "units": 10000,
              "entry_price": 1.1000,
              "close_price": 1.1020,
              "p_l": 20.0
            }},
            {{
              "position_id": "open",
              "status": "OPEN",
              "pair": "EUR_USD",
              "timeframe": "H1",
              "strategy_asset_id": "{record.strategy_asset_id}",
              "direction": "BUY",
              "units": 10000,
              "entry_price": 1.1000,
              "close_price": 1.1010,
              "floating_pl": 10.0
            }}
          ]
        }}
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(dashboard_service, "default_paper_positions_file", lambda: positions_file)
    monkeypatch.setattr(dashboard_service, "_approved_strategy_assets_file", lambda: assets_file)

    service = DashboardService()
    summary = service.paper_summary()
    rows = service._paper_position_rows("OPEN")
    open_trades = service.paper_open_trades()
    closed_trades = service.paper_closed_trades()

    assert summary["paper_balance"] == 100_020.0
    assert summary["paper_equity"] == 100_030.0
    assert summary["realized_pl"] == 20.0
    assert summary["floating_pl"] == 10.0
    assert rows[0]["strategy"] == record.strategy_name
    assert rows[0]["strategy_asset_id"] == record.strategy_asset_id
    assert open_trades[0]["position_id"] == "open"
    assert closed_trades[0]["position_id"] == "closed"


def test_paper_open_rows_calculate_missing_usd_index_pl(monkeypatch, tmp_path: Path) -> None:
    positions_file = tmp_path / "paper_positions.json"
    positions_file.write_text(
        """
        {
          "positions": [
            {
              "position_id": "nas-open",
              "status": "OPEN",
              "pair": "NAS100_USD",
              "timeframe": "H1",
              "strategy_asset_id": "QF-IDX",
              "direction": "BUY",
              "units": 10000,
              "entry_price": 28831.0,
              "close_price": 28841.0
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(dashboard_service, "default_paper_positions_file", lambda: positions_file)

    rows = DashboardService()._paper_position_rows("OPEN")

    assert rows[0]["p_l"] == "10.00"


def test_trade_investigation_endpoints_expose_milestone_27_report(monkeypatch, tmp_path: Path) -> None:
    positions_file = tmp_path / "paper_positions.json"
    positions_file.write_text(
        """
        {
          "positions": [
            {
              "position_id": "paper-test-1",
              "status": "CLOSED",
              "pair": "EUR_USD",
              "timeframe": "H1",
              "strategy_asset_id": "strategy_asset_001",
              "direction": "BUY",
              "units": 10000,
              "entry_price": 1.1000,
              "close_price": 1.1020,
              "stop_loss": 1.0980,
              "take_profit": 1.1040,
              "p_l": 20.0,
              "entry_time": "2026-07-07T03:30:00+00:00",
              "closed_at": "2026-07-07T06:30:00+00:00",
              "close_reason": "TAKE_PROFIT"
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(dashboard_service, "default_paper_positions_file", lambda: positions_file)

    response = client.get("/api/trades/paper-test-1")
    passport = client.get("/api/trades/paper-test-1/passport")
    risk = client.get("/api/trades/paper-test-1/risk")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trade_id"] == "paper-test-1"
    assert payload["sections"]["header"]["pair"] == "EUR_USD"
    assert payload["sections"]["strategy_selection"]["candidates"][0]["decision"] == "SELECTED"
    assert payload["sections"]["opportunity"]["total"] == 86
    assert payload["sections"]["summary"]["decision_transparency"] == "complete"
    assert passport.status_code == 200
    assert passport.json()["data"]["strategy_asset_id"] == "strategy_asset_001"
    assert risk.status_code == 200
    assert risk.json()["data"]["risk_approval"] == "PASS"


def test_performance_learning_endpoint_exposes_milestone_26_layers() -> None:
    response = client.get("/api/performance/learning")

    assert response.status_code == 200
    payload = response.json()
    assert payload["attribution"]["total_profit_loss"] == 1900.0
    assert payload["learning"]["knowledge_updates"]
    assert payload["research_priorities"]
    assert payload["strategy_evolution"]
    assert payload["portfolio_evolution"]
    assert payload["decision_quality"]["decision_accuracy"] >= 0
    assert payload["daily_report"]["report_id"].startswith("LEARNING-DAILY-")
    assert payload["weekly_review"]["review_id"].startswith("LEARNING-WEEK-")
    assert payload["monthly_review"]["review_id"].startswith("INTEL-MONTH-")
    assert client.post("/api/performance/learning").status_code == 405


def test_process_logs_endpoint_is_paginated_and_filterable() -> None:
    response = client.get("/api/logs?page=1&page_size=30")

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 1
    assert payload["page_size"] == 30
    assert "rows" in payload
    assert "categories" in payload
    assert "processes" in payload
