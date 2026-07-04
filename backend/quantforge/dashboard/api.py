from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from quantforge.config.settings import get_settings
from quantforge.dashboard.service import DashboardService


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="QuantForge AI Dashboard API",
        description="Read-only dashboard API for research, strategy library, portfolio, paper trading, operations, and knowledge evidence.",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.dashboard_allowed_origins,
        allow_credentials=False,
        allow_methods=("GET",),
        allow_headers=("*",),
    )
    service = DashboardService()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "environment": settings.environment,
            "mode": "read-only",
        }

    @app.get("/api/dashboard/overview")
    def overview() -> dict[str, Any]:
        return service.overview()

    @app.get("/api/dashboard/research/progress")
    def research_progress() -> dict[str, Any]:
        return service.research_progress()

    @app.get("/api/dashboard/research/programs")
    def research_programs() -> list[dict[str, Any]]:
        return service.research_programs()

    @app.get("/api/dashboard/research/rejections")
    def research_rejections() -> list[dict[str, Any]]:
        return service.research_rejections()

    @app.get("/api/pipeline/summary")
    def pipeline_summary() -> dict[str, Any]:
        return service.pipeline_summary()

    @app.get("/api/pipeline/current-task")
    def pipeline_current_task() -> dict[str, Any]:
        return service.pipeline_current_task()

    @app.get("/api/pipeline/tasks")
    def pipeline_tasks() -> list[dict[str, Any]]:
        return service.pipeline_tasks()

    @app.get("/api/pipeline/engines")
    def pipeline_engines() -> list[dict[str, Any]]:
        return service.engine_status()

    @app.get("/api/pipeline/workload")
    def pipeline_workload() -> list[dict[str, Any]]:
        return service.engine_workload()

    @app.get("/api/strategies")
    def strategies() -> list[dict[str, Any]]:
        return service.strategies()

    @app.get("/api/strategies/{strategy_id}")
    def strategy(strategy_id: str) -> dict[str, Any]:
        return _strategy_or_404(service.strategy, strategy_id)

    @app.get("/api/strategies/{strategy_id}/passport")
    def strategy_passport(strategy_id: str) -> dict[str, Any]:
        return _strategy_or_404(service.strategy_passport, strategy_id)

    @app.get("/api/strategies/{strategy_id}/validation")
    def strategy_validation(strategy_id: str) -> dict[str, Any]:
        return _strategy_or_404(service.strategy_validation, strategy_id)

    @app.get("/api/strategies/{strategy_id}/decision-trace")
    def strategy_decision_trace(strategy_id: str) -> dict[str, Any]:
        return _strategy_or_404(service.strategy_decision_trace, strategy_id)

    @app.get("/api/portfolio/readiness")
    def portfolio_readiness() -> dict[str, Any]:
        return service.portfolio_readiness()

    @app.get("/api/portfolio/correlation")
    def portfolio_correlation() -> dict[str, Any]:
        return service.portfolio_correlation()

    @app.get("/api/portfolio/coverage")
    def portfolio_coverage() -> dict[str, Any]:
        return service.portfolio_coverage()

    @app.get("/api/portfolio/risk")
    def portfolio_risk() -> dict[str, Any]:
        return service.portfolio_risk()

    @app.get("/api/paper/summary")
    def paper_summary() -> dict[str, Any]:
        return service.paper_summary()

    @app.get("/api/paper/trades/open")
    def paper_open_trades() -> list[dict[str, Any]]:
        return service.paper_open_trades()

    @app.get("/api/paper/trades/closed")
    def paper_closed_trades() -> list[dict[str, Any]]:
        return service.paper_closed_trades()

    @app.get("/api/paper/drift")
    def paper_drift() -> dict[str, Any]:
        return service.paper_drift()

    @app.get("/api/paper/promotion")
    def paper_promotion() -> dict[str, Any]:
        return service.paper_promotion()

    @app.get("/api/ops/health")
    def ops_health() -> dict[str, Any]:
        return service.ops_health()

    @app.get("/api/ops/services")
    def ops_services() -> list[dict[str, Any]]:
        return service.ops_services()

    @app.get("/api/ops/incidents")
    def ops_incidents() -> list[dict[str, Any]]:
        return service.ops_incidents()

    @app.get("/api/ops/latency")
    def ops_latency() -> dict[str, Any]:
        return service.ops_latency()

    @app.get("/api/ops/system")
    def ops_system() -> dict[str, Any]:
        return service.ops_system()

    @app.get("/api/knowledge/summary")
    def knowledge_summary() -> dict[str, Any]:
        return service.knowledge_summary()

    @app.get("/api/knowledge/features")
    def knowledge_features() -> list[dict[str, Any]]:
        return service.knowledge_features()

    @app.get("/api/knowledge/plugins")
    def knowledge_plugins() -> list[dict[str, Any]]:
        return service.knowledge_plugins()

    @app.get("/api/knowledge/templates")
    def knowledge_templates() -> list[dict[str, Any]]:
        return service.knowledge_templates()

    @app.get("/api/knowledge/hypotheses")
    def knowledge_hypotheses() -> list[dict[str, Any]]:
        return service.knowledge_hypotheses()

    return app


def _strategy_or_404(callback: Any, strategy_id: str) -> dict[str, Any]:
    try:
        return callback(strategy_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Strategy not found") from exc


app = create_app()
