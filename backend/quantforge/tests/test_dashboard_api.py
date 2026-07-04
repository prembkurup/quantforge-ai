from fastapi.testclient import TestClient

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


def test_portfolio_ops_knowledge_and_paper_endpoints_are_read_only() -> None:
    assert client.get("/api/portfolio/readiness").json()["portfolio_readiness"] == "READY_FOR_PAPER_TRADING"
    assert client.get("/api/ops/health").json()["platform_status"] == "HEALTHY"
    assert client.get("/api/knowledge/summary").json()["knowledge_records"] == 795_000
    assert client.get("/api/paper/summary").json()["promotion_readiness"] == "PROMOTE"
    assert client.post("/api/dashboard/overview").status_code == 405
