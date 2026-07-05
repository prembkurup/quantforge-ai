import os

from fastapi.testclient import TestClient

os.environ["QUANTFORGE_DEMO_MODE"] = "1"

from quantforge.dashboard.api import create_app


client = TestClient(create_app())


def test_dashboard_overview_returns_core_kpis() -> None:
    response = client.get("/api/dashboard/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["platform_status"] == "HEALTHY"
    assert payload["research_status"] == "COMPLETE"
    assert payload["portfolio_readiness"] == "READY_FOR_PORTFOLIO_CONSTRUCTION"
    assert payload["live_trading_status"] == "DISABLED"
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
    assert any(engine["status"] == "DISABLED" for engine in engines)
    assert len(workload) == len(engines)


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
    assert h4_smoke["default"] == 120
    assert "Default:" in h4_smoke["help"]
    assert h4_smoke["editable"] is True

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


def test_portfolio_ops_knowledge_and_paper_endpoints_are_read_only() -> None:
    assert client.get("/api/portfolio/readiness").json()["portfolio_readiness"] == "READY_FOR_PAPER_TRADING"
    assert client.get("/api/ops/health").json()["platform_status"] == "HEALTHY"
    assert client.get("/api/knowledge/summary").json()["knowledge_records"] == 795_000
    assert client.get("/api/paper/summary").json()["promotion_readiness"] == "PROMOTE"
    assert client.get("/api/paper/replay").json()["source"] == "ReplayProgressStore"
    assert client.post("/api/dashboard/overview").status_code == 405


def test_process_logs_endpoint_is_paginated_and_filterable() -> None:
    response = client.get("/api/logs?page=1&page_size=30")

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 1
    assert payload["page_size"] == 30
    assert "rows" in payload
    assert "categories" in payload
    assert "processes" in payload
