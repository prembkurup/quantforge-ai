from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import text

from quantforge.admin import AdminSettingsStore
from quantforge.admin.settings import admin_setting_value
from quantforge.config.settings import get_settings
from quantforge.infrastructure.operations import AutonomousOperationsManager
from quantforge.live.shadow import ShadowTradingPlatform
from quantforge.market_data.coreui_repository import CoreUiCandleRepository, get_coreui_history_engine
from quantforge.research.approvals import ApprovalAuditLog, ApprovalRepository, ApprovalService
from quantforge.research.families import ResearchProgramFamily
from quantforge.research.full_history_scheduler import (
    FULL_HISTORY_RESEARCH_PAIRS,
    FULL_HISTORY_RESEARCH_START,
    FULL_HISTORY_RESEARCH_TIMEFRAMES,
    FullHistoryResearchScheduler,
    FullHistorySchedulerConfig,
)
from quantforge.research.full_history_summary import (
    BackgroundSummaryRefresher,
    FullHistoryResearchSummaryRepository,
    FullHistorySummaryCache,
)
from quantforge.research.history_validation import (
    HistoricalValidationEngine,
    default_historical_validation_paths,
    historical_validation_config_from_env,
)
from quantforge.research.library import InstitutionalStrategyLibraryBuilder, StrategyLibraryAsset
from quantforge.research.multi_market import (
    MultiMarketResearchPlanner,
    ResearchMatrixBuilder,
    coverage_report,
    default_rejected_strategy_repository,
    diversity_report,
    productivity_rows,
)
from quantforge.research.orchestrator import (
    AlwaysOnAutonomousResearchOrchestrator,
    AlwaysOnResearchThresholds,
    default_always_on_orchestrator_paths,
)
from quantforge.research.strategy_assets import StrategyAssetRepository, StrategyLibraryLoader, strategy_asset_from_approved
from quantforge.research.workflow_orchestration import WorkflowOrchestrator, default_workflow_paths
from quantforge.live import (
    DailyLearningLoop,
    DailyMarketReadinessEvaluator,
    DailyOperationsDashboardBuilder,
    DailyReportGenerator,
    DailyRiskController,
    DailyRiskState,
    DailyDecisionJournalGenerator,
    DailyTradingPlanGenerator,
    DecisionIntelligenceStatusEngine,
    DecisionQualityMetricsCalculator,
    DecisionTimelineBuilder,
    DynamicDailyRiskBudgetEngine,
    IntradayCertificationEngine,
    IntradayMetricsCalculator,
    IntradayTradeDecision,
    IntradayTradeDecisionEngine,
    MarketReadinessDecision,
    MarketReadinessInputs,
    MarketQualityEngine,
    MarketQualityInputs,
    NewsEventFilter,
    NewsEventType,
    ScheduledNewsEvent,
    SessionEngine,
    SessionPortfolioManager,
    TradeEligibilityEngine,
    TradeEligibilityRequest,
    TradeJournalStore,
    default_intraday_profile,
    default_trade_journal_path,
    PortfolioIntelligenceEngine,
    PerformanceLearningEngine,
    demo_portfolio_strategy_inputs,
    demo_portfolio_decision_inputs,
    demo_trade_performance_inputs,
    intraday_profile_from_strategy_definition,
    ReplayProgressStore,
)
from quantforge.live.paper_scanner import PaperPositionStore, default_paper_positions_file


class DashboardService:
    """Read-only DTO provider for the QuantForge dashboard MVP."""

    def __init__(self) -> None:
        self._demo_mode = os.getenv("QUANTFORGE_DEMO_MODE", "").lower() in {"1", "true", "yes"}
        self._strategy_asset_repository = StrategyAssetRepository(_approved_strategy_assets_file())
        self._library = (
            InstitutionalStrategyLibraryBuilder().build()
            if self._demo_mode
            else StrategyLibraryLoader(self._strategy_asset_repository).load()
        )
        self._operations = AutonomousOperationsManager().run_validation()
        self._paper = ShadowTradingPlatform().run()
        self._timestamp = datetime.now(UTC).isoformat()

    def overview(self) -> dict[str, Any]:
        kpis = self._library.kpis
        live = _live_trading_admin_state()
        return {
            "platform_status": "HEALTHY",
            "research_status": self._library.dashboard.status.value,
            "architecture_freeze": "VERSION_1_STABLE",
            "portfolio_readiness": self._library.dashboard.portfolio_readiness,
            "paper_trading_status": "READY_FOR_WORKSTREAM_2",
            "live_trading_status": live["status"],
            "experiments": kpis.experiments_executed,
            "candidate_strategies": kpis.candidate_strategies,
            "optimized_strategies": kpis.optimized_strategies,
            "validated_assets": kpis.validated_strategy_assets,
            "production_strategies": kpis.production_grade_strategies,
            "knowledge_records": kpis.knowledge_records_written,
            "average_confidence": round(kpis.average_confidence * 100, 1),
            "average_profit_factor": kpis.average_profit_factor,
            "max_drawdown": round(kpis.max_observed_drawdown * 100, 1),
            "decision_banner": "READY_FOR_PORTFOLIO_CONSTRUCTION",
            "critical_alerts": 0,
            "source": "Demo Strategy Library + Operations Validation"
            if self._demo_mode
            else "ApprovedStrategyAssetStore + Operations Validation",
            "timestamp": self._timestamp,
        }

    def research_progress(self) -> dict[str, Any]:
        kpis = self._library.kpis
        return {
            "charts": {
                "experiments_over_time": _series(kpis.experiments_executed, 6),
                "candidates_over_time": _series(kpis.candidate_strategies, 6),
                "validation_pass_fail": {"pass": kpis.validated_strategy_assets, "fail": 124},
                "knowledge_growth": _series(kpis.knowledge_records_written, 6),
                "average_confidence_trend": [88.5, 89.9, 90.8, 91.6, 92.1, 92.7],
                "profit_factor_distribution": [1.8, 2.0, 2.1, 2.21, 2.35],
                "drawdown_distribution": [5.8, 7.2, 8.5, 9.1, 9.8],
            },
            "source": "InstitutionalStrategyLibraryBuilder" if self._demo_mode else "ApprovedStrategyAssetStore",
            "demo_mode": self._demo_mode,
            "timestamp": self._timestamp,
        }

    def research_programs(self) -> list[dict[str, Any]]:
        by_family = _assets_by_family(self._library.production_grade_strategies)
        rows: list[dict[str, Any]] = []
        for program in self._library.programs:
            assets = by_family.get(program.family, ())
            rows.append(
                {
                    "program": program.family.value,
                    "experiments": program.experiment_allocation,
                    "candidates": program.experiment_allocation * 10,
                    "validated_assets": program.validated_asset_target,
                    "production_strategies": len(assets),
                    "average_confidence": _avg([asset.confidence for asset in assets], default=0.927),
                    "average_pf": _avg([asset.profit_factor for asset in assets], default=2.21),
                    "status": "COMPLETE",
                    "source": program.program_id,
                    "timestamp": self._timestamp,
                }
            )
        return rows

    def research_rejections(self) -> list[dict[str, Any]]:
        rejected = self.research_rejected()
        if rejected:
            counts: dict[str, int] = {}
            for item in rejected:
                reason = str(item["failure_reason"])
                counts[reason] = counts.get(reason, 0) + 1
            return [
                {"reason": reason, "count": count, "severity": "high" if "Failure" in reason else "medium"}
                for reason, count in sorted(counts.items(), key=lambda row: row[1], reverse=True)
            ]
        return [
            {"reason": "Parameter instability", "count": 18_240, "severity": "medium"},
            {"reason": "Drawdown above limit", "count": 12_760, "severity": "high"},
            {"reason": "Low cross-pair robustness", "count": 9_410, "severity": "medium"},
            {"reason": "Decision trace incomplete", "count": 1_128, "severity": "high"},
        ]

    def research_matrix(self) -> list[dict[str, Any]]:
        return [asdict(row) for row in self._research_matrix_rows()]

    def research_program_fanout(self) -> list[dict[str, Any]]:
        programs = MultiMarketResearchPlanner().plan(
            tuple(row_to_dataset for row_to_dataset in self._research_matrix_builder().datasets())
        )
        assets = self._strategy_asset_repository.list()
        rejected = default_rejected_strategy_repository(_repo_root()).list()
        rows: list[dict[str, Any]] = []
        for program in programs:
            approved = sum(
                1
                for asset in assets
                if asset.pair == program.dataset.pair and asset.timeframe == program.dataset.timeframe
            )
            rejected_count = sum(
                1
                for item in rejected
                if item.pair == program.dataset.pair and item.timeframe == program.dataset.timeframe
            )
            rows.append(
                {
                    "program_id": program.program_id,
                    "dataset_id": program.dataset.dataset_id,
                    "pair": program.dataset.pair,
                    "timeframe": program.dataset.timeframe,
                    "status": "COMPLETE" if approved else program.status.value,
                    "experiment_count": program.experiment_count,
                    "candidate_count": program.candidate_count,
                    "approved_asset_count": approved,
                    "rejected_candidate_count": rejected_count,
                    "quality_score": program.dataset.quality_score,
                }
            )
        return rows

    def research_program_detail(self, program_id: str) -> dict[str, Any]:
        for program in self.research_program_fanout():
            if program["program_id"] == program_id:
                return {
                    **program,
                    "templates": ("Trend Pullback", "Donchian Breakout", "ATR Expansion"),
                    "hypotheses": (
                        f"{program['pair']} {program['timeframe']} trend pullbacks remain stable across rolling windows.",
                        f"{program['pair']} {program['timeframe']} volatility expansion improves continuation filtering.",
                    ),
                    "source": "ResearchMatrixBuilder",
                    "timestamp": self._timestamp,
                }
        raise KeyError(program_id)

    def research_rejected(self) -> list[dict[str, Any]]:
        return [asdict(item) for item in default_rejected_strategy_repository(_repo_root()).list()]

    def research_coverage(self) -> dict[str, Any]:
        rows = self._research_matrix_rows()
        programs = MultiMarketResearchPlanner().plan(self._research_matrix_builder().datasets())
        return {**coverage_report(rows, programs), "timestamp": self._timestamp}

    def research_diversity(self) -> dict[str, Any]:
        return {**diversity_report(self._strategy_asset_repository.list()), "timestamp": self._timestamp}

    def research_productivity(self) -> list[dict[str, Any]]:
        return productivity_rows(self._research_matrix_rows())

    def research_orchestrator_status(self) -> dict[str, Any]:
        return self._always_on_research_orchestrator().current_status()

    def research_orchestrator_runs(self) -> list[dict[str, Any]]:
        return self._always_on_research_orchestrator().runs()

    def research_orchestrator_idle_reasons(self) -> list[dict[str, Any]]:
        return self._always_on_research_orchestrator().idle_reasons()

    def research_orchestrator_idle_reason(self) -> dict[str, Any]:
        return self._always_on_research_orchestrator().latest_idle_reason()

    def research_orchestrator_guardrails(self) -> list[dict[str, Any]]:
        return self._always_on_research_orchestrator().guardrails()

    def wake_research_orchestrator(self) -> dict[str, Any]:
        record = self._always_on_research_orchestrator().run_once(trigger="manual_wake")
        payload = asdict(record)
        payload["state"] = record.state.value
        return payload

    def stop_research_orchestrator(self) -> dict[str, Any]:
        return self._always_on_research_orchestrator().stop()

    def start_research_orchestrator(self) -> dict[str, Any]:
        return self._always_on_research_orchestrator().start()

    def fine_tuning_status(self) -> dict[str, Any]:
        return self._always_on_research_orchestrator().fine_tuning_status()

    def history_validation_status(self) -> dict[str, Any]:
        return self._history_validation_engine().status()

    def history_validation_balance_sheet(self) -> dict[str, Any]:
        return self._history_validation_engine().balance_sheet()

    def history_validation_queue(self) -> list[dict[str, Any]]:
        return self._history_validation_engine().queue()

    def history_validation_running(self) -> list[dict[str, Any]]:
        return self._history_validation_engine().running()

    def history_validation_results(self) -> list[dict[str, Any]]:
        return self._history_validation_engine().results()

    def history_validation_result(self, validation_id: str) -> dict[str, Any]:
        return self._history_validation_engine().result(validation_id)

    def history_validation_improvements(self) -> list[dict[str, Any]]:
        return self._history_validation_engine().improvements()

    def history_validation_spreads(self) -> list[dict[str, Any]]:
        return self._history_validation_engine().spread_profile()

    def run_history_validation_batch(self) -> dict[str, Any]:
        return self._history_validation_engine().run_next_batch()

    def pipeline_summary(self) -> dict[str, Any]:
        tasks = self.pipeline_tasks()
        full_history = self.full_history_scheduler_status()
        engines = self.engine_status(full_history)
        return self._pipeline_summary_from(tasks, engines, full_history)

    def pipeline_snapshot(self) -> dict[str, Any]:
        full_history = self.full_history_scheduler_status()
        tasks = self.pipeline_tasks()
        engines = self.engine_status(full_history)
        workflow = self.workflow_current()
        return {
            "summary": self._pipeline_summary_from(tasks, engines, full_history),
            "current_task": self.pipeline_current_task(),
            "tasks": tasks,
            "engines": engines,
            "workload": self._engine_workload_from(engines),
            "full_history": full_history,
            "workflow": workflow,
            "timestamp": self._timestamp,
        }

    def _pipeline_summary_from(
        self,
        tasks: list[dict[str, Any]],
        engines: list[dict[str, Any]],
        full_history: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        full_history = full_history or self.full_history_scheduler_status()
        pipeline_done = _full_history_pipeline_done(full_history)
        failed = full_history["failed_jobs"]
        return {
            "pipeline_status": (
                "COMPLETE_WITH_WARNINGS" if pipeline_done and failed else "COMPLETE" if pipeline_done else "RUNNING"
            ),
            "current_task": (
                "Full-history research complete; review failed short-window jobs"
                if pipeline_done and failed
                else "Full-history research complete"
                if pipeline_done
                else "Full-history research scheduler"
            ),
            "active_engines": sum(1 for engine in engines if engine["status"] == "RUNNING"),
            "healthy_engines": sum(1 for engine in engines if engine["health"] == "HEALTHY"),
            "total_engines": len(engines),
            "running_tasks": sum(1 for task in tasks if task["status"] == "RUNNING"),
            "queued_tasks": sum(1 for task in tasks if task["status"] == "QUEUED"),
            "completed_tasks": sum(1 for task in tasks if task["status"] == "COMPLETE"),
            "blocked_tasks": sum(1 for task in tasks if task["status"] == "BLOCKED"),
            "overall_progress": full_history["progress_percent"],
            "queue_depth": 0 if pipeline_done else 2,
            "full_history_completed_jobs": full_history["completed_jobs"],
            "full_history_failed_jobs": full_history["failed_jobs"],
            "full_history_planned_jobs": full_history["planned_jobs"],
            "source": "Workstream 1 Pipeline + Full History Research Scheduler",
            "timestamp": self._timestamp,
        }

    def pipeline_current_task(self) -> dict[str, Any]:
        full_history = self.full_history_scheduler_status()
        completed = full_history["completed_jobs"]
        planned = full_history["planned_jobs"]
        failed = full_history["failed_jobs"]
        pending = full_history["pending_jobs"]
        status = full_history["status"]
        latest_job = full_history["latest_job"]
        timestamp = datetime.now(UTC).isoformat()
        pipeline_done = _full_history_pipeline_done(full_history)
        return {
            "task_id": "FH-SCHEDULER",
            "task": (
                "Review full-history research completion"
                if pipeline_done and failed
                else "Run full-history research scheduler"
            ),
            "status": "COMPLETE_WITH_WARNINGS" if pipeline_done and failed else status,
            "engine": "Research Orchestrator",
            "stage": (
                "Full-history complete; worker idle watcher"
                if pipeline_done
                else "24/7 worker, 6 parallel scheduler jobs"
            ),
            "progress": full_history["progress_percent"],
            "started_at": full_history["latest_recorded_at"] or timestamp,
            "eta": "done; worker watching for new jobs" if pipeline_done else "continuous 24/7 worker",
            "input": f"{planned} planned jobs; {pending} pending",
            "output": "Full-history research job state and validated strategy assets",
            "last_event": f"{completed}/{planned} complete; {failed} failed; latest: {latest_job}",
            "timestamp": timestamp,
        }

    def pipeline_tasks(self) -> list[dict[str, Any]]:
        full_history = self.full_history_scheduler_status()
        pipeline_done = _full_history_pipeline_done(full_history)
        validation_status = "COMPLETE" if pipeline_done else "RUNNING"
        validation_progress = 100 if pipeline_done else 72
        validation_eta = "done" if pipeline_done else "18 min"
        validation_workload = (
            "Validated assets produced across full-history jobs"
            if pipeline_done
            else "29 selected candidates"
        )
        downstream_status = "COMPLETE" if pipeline_done else "QUEUED"
        downstream_progress = 100 if pipeline_done else 0
        portfolio_eta = "ready" if pipeline_done else "after validation"
        paper_eta = "ready" if pipeline_done else "after portfolio update"
        return [
            {
                "task_id": "FH-SCHEDULER",
                "task": "Run full-history research scheduler",
                "engine": "Research Orchestrator",
                "status": "RUNNING" if full_history["pending_jobs"] > 0 else "COMPLETE",
                "progress": full_history["progress_percent"],
                "workload": (
                    f"{full_history['completed_jobs']}/{full_history['planned_jobs']} jobs complete; "
                    f"{full_history['pending_jobs']} pending"
                ),
                "eta": "done; worker watching" if pipeline_done else "continuous 24/7 worker",
                "last_update": full_history["latest_recorded_at"] or self._timestamp,
            },
            {
                "task_id": "WF1-DB-INGEST-001",
                "task": "Read CoreUI/OANDA candle database windows",
                "engine": "Market Data Engine",
                "status": "COMPLETE",
                "progress": 100,
                "workload": "6216 H1 candles",
                "eta": "done",
                "last_update": self._timestamp,
            },
            {
                "task_id": "WF1-FEATURE-002",
                "task": "Generate standardized FeatureVectors",
                "engine": "Feature Engine",
                "status": "COMPLETE",
                "progress": 100,
                "workload": "300-candle lookback windows",
                "eta": "done",
                "last_update": self._timestamp,
            },
            {
                "task_id": "WF1-COMPOSE-003",
                "task": "Compose candidate strategies",
                "engine": "Strategy Composer",
                "status": "COMPLETE",
                "progress": 100,
                "workload": "7,500,000 candidates screened",
                "eta": "done",
                "last_update": self._timestamp,
            },
            {
                "task_id": "WF1-DB-VALIDATE-004",
                "task": "Validate database-backed Strategy Assets",
                "engine": "Strategy Validation Engine",
                "status": validation_status,
                "progress": validation_progress,
                "workload": validation_workload,
                "eta": validation_eta,
                "last_update": full_history["latest_recorded_at"] or self._timestamp,
            },
            {
                "task_id": "WF1-PORTFOLIO-005",
                "task": "Update portfolio construction readiness",
                "engine": "Portfolio Engine",
                "status": downstream_status,
                "progress": downstream_progress,
                "workload": "validated asset set",
                "eta": portfolio_eta,
                "last_update": full_history["latest_recorded_at"] or self._timestamp,
            },
            {
                "task_id": "WF1-PAPER-006",
                "task": "Refresh paper trading drift review",
                "engine": "Shadow Trading Engine",
                "status": downstream_status,
                "progress": downstream_progress,
                "workload": "paper portfolio and open trades",
                "eta": paper_eta,
                "last_update": full_history["latest_recorded_at"] or self._timestamp,
            },
        ]

    def full_history_scheduler_status(self) -> dict[str, Any]:
        state_file = _full_history_state_file()
        planned_jobs = _planned_full_history_jobs(state_file)
        if not state_file.exists():
            return {
                "status": "PENDING",
                "planned_jobs": len(planned_jobs),
                "completed_jobs": 0,
                "failed_jobs": 0,
                "pending_jobs": len(planned_jobs),
                "progress_percent": 0,
                "latest_job": "No scheduler state yet",
                "latest_recorded_at": "",
                "state_file": str(state_file),
                "jobs": _full_history_job_rows(planned_jobs, {}, set(), set()),
            }
        state = json.loads(state_file.read_text(encoding="utf-8"))
        completed_ids = set(state.get("completed", []))
        failed_ids = set(state.get("failed", []))
        history = list(state.get("history", []))
        history_by_id = {str(item.get("job_id", "")): item for item in history}
        latest = history[-1] if history else {}
        completed = sum(1 for job in planned_jobs if job.job_id in completed_ids)
        failed = sum(1 for job in planned_jobs if job.job_id in failed_ids)
        pending = max(0, len(planned_jobs) - completed - failed)
        progress = round(((completed + failed) / len(planned_jobs)) * 100) if planned_jobs else 0
        return {
            "status": "RUNNING" if pending else "COMPLETE",
            "planned_jobs": len(planned_jobs),
            "completed_jobs": completed,
            "failed_jobs": failed,
            "pending_jobs": pending,
            "progress_percent": progress,
            "latest_job": latest.get("job_id", "No completed job yet"),
            "latest_recorded_at": latest.get("recorded_at", ""),
            "state_file": str(state_file),
            "jobs": _full_history_job_rows(planned_jobs, history_by_id, completed_ids, failed_ids),
        }

    def full_history_research(self) -> dict[str, Any]:
        status = self.full_history_scheduler_status()
        cached = _full_history_summary_cache().get()
        if cached:
            cached["scheduler"] = status
            cached["timestamp"] = self._timestamp
            return cached
        return _full_history_research_cache_miss(status, self._timestamp)

    def refresh_full_history_research_summary(self) -> dict[str, Any]:
        return BackgroundSummaryRefresher(
            _full_history_summary_cache(),
            lambda: _build_full_history_research_summary(self.full_history_scheduler_status(), self._timestamp),
        ).refresh()

    def workflow_current(self) -> dict[str, Any]:
        orchestrator = WorkflowOrchestrator(_workflow_paths())
        return orchestrator.current(_planned_full_history_jobs(_full_history_state_file()))

    def workflow_runs(self) -> list[dict[str, Any]]:
        return [self.workflow_current()["run"]]

    def workflow_run(self, workflow_id: str) -> dict[str, Any]:
        current = self.workflow_current()
        if current["run"]["workflow_id"] != workflow_id:
            raise KeyError(workflow_id)
        return current

    def workflow_stages(self, workflow_id: str) -> list[dict[str, Any]]:
        return self.workflow_run(workflow_id)["stages"]

    def workflow_tasks(self, workflow_id: str) -> list[dict[str, Any]]:
        return self.workflow_run(workflow_id)["tasks"]

    def workflow_events(self, workflow_id: str) -> list[dict[str, Any]]:
        return self.workflow_run(workflow_id)["events"]

    def workflow_approvals(self, workflow_id: str) -> list[dict[str, Any]]:
        return self.workflow_run(workflow_id)["approvals"]

    def workflow_current_approvals(self) -> list[dict[str, Any]]:
        return self.workflow_current()["approvals"]

    def workflow_approval_audit(self) -> list[dict[str, str]]:
        return _approval_service().audit_records()

    def architecture_orphans(self) -> list[dict[str, Any]]:
        return _orphan_module_report()

    def approve_workflow_approval(self, approval_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.workflow_current()
        user = str(payload.get("user") or payload.get("approved_by") or "dashboard_user")
        reason = str(payload.get("reason") or "Manual approval recorded from dashboard.")
        return asdict(_approval_service().approve(approval_id, user=user, reason=reason))

    def reject_workflow_approval(self, approval_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.workflow_current()
        user = str(payload.get("user") or payload.get("rejected_by") or "dashboard_user")
        reason = str(payload.get("reason") or "Manual approval rejected from dashboard.")
        return asdict(_approval_service().reject(approval_id, user=user, reason=reason))

    def admin_settings(self) -> dict[str, Any]:
        return AdminSettingsStore(_admin_settings_file()).current()

    def update_admin_settings(self, values: dict[str, Any]) -> dict[str, Any]:
        return AdminSettingsStore(_admin_settings_file()).update(values)

    def engine_status(self, full_history: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        full_history = full_history or self.full_history_scheduler_status()
        pipeline_done = _full_history_pipeline_done(full_history)
        live = _live_trading_admin_state()
        if pipeline_done:
            return [
                _engine("Market Data Engine", "IDLE", "HEALTHY", 0, 0, "Full-history candle windows complete"),
                _engine("Calculation Engine", "IDLE", "HEALTHY", 0, 0, "Feature calculations complete"),
                _engine("Feature Engine", "IDLE", "HEALTHY", 0, 0, "FeatureVector batches complete"),
                _engine("Market Regime Engine", "IDLE", "HEALTHY", 0, 0, "Regime snapshots available"),
                _engine("Research Orchestrator", "IDLE", "HEALTHY", 0, 0, "Worker watching for new scheduler jobs"),
                _engine("Strategy Composer", "IDLE", "HEALTHY", 0, 0, "Candidate composition complete"),
                _engine("Optimization Engine", "IDLE", "HEALTHY", 0, 0, "Optimization gates complete"),
                _engine("Backtesting Engine", "IDLE", "HEALTHY", 0, 0, "Backtesting batches complete"),
                _engine("Strategy Validation Engine", "IDLE", "HEALTHY", 0, 0, "Validation batches complete"),
                _engine("Portfolio Engine", "IDLE", "HEALTHY", 0, 0, "Portfolio readiness available"),
                _engine("Shadow Trading Engine", "IDLE", "HEALTHY", 0, 0, "Paper trading review available"),
                _engine("Live Trading Engine", live["engine_status"], live["health"], 0, 0, live["message"]),
                _engine("Operations Manager", "RUNNING", "HEALTHY", 18, 0, "Monitoring services and workload"),
            ]
        return [
            _engine("Market Data Engine", "RUNNING", "HEALTHY", 22, 0, "CoreUI candle source connected"),
            _engine("Calculation Engine", "IDLE", "HEALTHY", 0, 0, "Ready for next feature batch"),
            _engine("Feature Engine", "IDLE", "HEALTHY", 0, 0, "Latest FeatureVector batch complete"),
            _engine("Market Regime Engine", "IDLE", "HEALTHY", 0, 0, "Latest regime snapshot available"),
            _engine("Research Orchestrator", "RUNNING", "HEALTHY", 44, 2, "Scheduling next validation gate"),
            _engine("Strategy Composer", "IDLE", "HEALTHY", 0, 0, "Candidate composition complete"),
            _engine("Optimization Engine", "IDLE", "HEALTHY", 0, 0, "Stable parameter regions ready"),
            _engine("Backtesting Engine", "RUNNING", "HEALTHY", 63, 1, "Event replay for validation batch"),
            _engine("Strategy Validation Engine", "RUNNING", "HEALTHY", 72, 1, "Walk-forward and robustness gates active"),
            _engine("Portfolio Engine", "QUEUED", "HEALTHY", 0, 1, "Waiting for validation output"),
            _engine("Shadow Trading Engine", "QUEUED", "HEALTHY", 0, 1, "Waiting for portfolio update"),
            _engine("Live Trading Engine", live["engine_status"], live["health"], 0, 0, live["message"]),
            _engine("Operations Manager", "RUNNING", "HEALTHY", 18, 0, "Monitoring services and workload"),
        ]

    def engine_workload(self) -> list[dict[str, Any]]:
        return self._engine_workload_from(self.engine_status())

    def intraday_daily(self) -> dict[str, Any]:
        approved_assets = tuple(asset for asset in self._strategy_asset_repository.list() if asset.deployable)
        certified_profiles: dict[str, Any] = {}
        certification_rows: list[dict[str, Any]] = []
        for asset in approved_assets:
            strategy_asset = strategy_asset_from_approved(asset)
            profile = intraday_profile_from_strategy_definition(strategy_asset.strategy_definition) or default_intraday_profile()
            certification = IntradayCertificationEngine().certify(
                strategy_asset,
                profile,
                {
                    "overnight_positions": 0,
                    "late_closes": 0,
                    "maximum_daily_drawdown": asset.max_drawdown,
                    "average_trade_duration_minutes": min(profile.maximum_trade_duration_minutes, 60),
                },
            )
            certification_rows.append(
                {
                    "strategy_asset_id": asset.strategy_asset_id,
                    "pair": asset.pair,
                    "session": profile.preferred_session.value,
                    "status": certification.status,
                    "certified": certification.certified,
                }
            )
            if certification.certified:
                certified_profiles[asset.strategy_asset_id] = profile
        if certified_profiles:
            profile = next(iter(certified_profiles.values()))
        else:
            profile = default_intraday_profile()
            certified_profiles = {"QF-INTRADAY-DEMO": profile}
        timestamp = datetime.now(UTC)
        portfolios = SessionPortfolioManager().build(certified_profiles)
        paper = self.paper_summary()
        open_trades = self.paper_open_trades()
        exposure = float(self._paper.paper_portfolio.exposure)
        daily_drawdown = float(paper.get("paper_drawdown", 0.0))
        realized_loss = abs(min(float(paper.get("daily_pl", 0.0)), 0.0)) / max(float(self._paper.paper_portfolio.balance), 1.0)
        risk_state = DailyRiskState(
            realized_daily_loss=round(realized_loss, 4),
            current_daily_drawdown=daily_drawdown,
            trades_today=len(open_trades),
            daily_exposure=exposure,
            strategy_allocation=max(self._paper.paper_portfolio.portfolio.values(), default=0.0),
            currency_exposure=exposure,
        )
        risk_decision = DailyRiskController().evaluate_new_trade(profile.daily_risk_profile, risk_state)
        current_session = SessionEngine().current_session(timestamp)
        readiness_inputs = MarketReadinessInputs(
            market_regime="TRENDING",
            volatility=0.006,
            spread=0.00012,
            session=current_session,
            available_strategies=len(certified_profiles),
            portfolio_exposure=exposure,
        )
        market_readiness = DailyMarketReadinessEvaluator().evaluate(readiness_inputs)
        snapshot = DailyOperationsDashboardBuilder().snapshot(
            profile,
            risk_state,
            portfolios,
            timestamp,
            todays_pl=float(paper.get("daily_pl", 0.0)),
            open_positions=len(open_trades),
            risk_paused=not risk_decision.approved or market_readiness.decision == MarketReadinessDecision.NO_NEW_TRADES,
        )
        metrics = IntradayMetricsCalculator().calculate(
            (
                {"profit": 420.50, "trades": 4, "average_trade_duration_minutes": 64, "drawdown": 0.006, "trading_hours": 5.5},
                {"profit": 185.25, "trades": 3, "average_trade_duration_minutes": 58, "drawdown": 0.004, "trading_hours": 4.0},
                {"profit": -95.10, "trades": 2, "average_trade_duration_minutes": 72, "drawdown": 0.012, "trading_hours": 3.5},
            ),
            daily_signals=(9, 7, 5),
            daily_executions=(4, 3, 2),
            daily_exposure=(0.18, 0.14, 0.11),
            daily_slippage=(0.2, 0.1, 0.3),
        )
        report = DailyReportGenerator().generate(snapshot, metrics)
        learning = DailyLearningLoop().update_priorities(report)
        journal_entries = list(TradeJournalStore(default_trade_journal_path()).list())[-20:]
        return {
            "current_session": snapshot.current_session.value,
            "todays_pl": snapshot.todays_pl,
            "todays_trades": snapshot.todays_trades,
            "open_positions": snapshot.open_positions,
            "remaining_daily_risk": snapshot.remaining_daily_risk,
            "daily_drawdown": snapshot.daily_drawdown,
            "session_portfolio": snapshot.session_portfolio,
            "active_strategies": list(snapshot.active_strategies),
            "trading_status": snapshot.trading_status.value,
            "market_readiness": {
                "score": market_readiness.score,
                "band": market_readiness.band.value,
                "decision": market_readiness.decision.value,
                "factors": market_readiness.factors,
                "reasons": list(market_readiness.reasons),
                "inputs": {
                    "market_regime": readiness_inputs.market_regime,
                    "volatility": readiness_inputs.volatility,
                    "spread": readiness_inputs.spread,
                    "session": readiness_inputs.session.value,
                    "available_strategies": readiness_inputs.available_strategies,
                    "portfolio_exposure": readiness_inputs.portfolio_exposure,
                },
            },
            "metrics": {
                "performance": {
                    "average_daily_profit": metrics.performance.average_daily_profit,
                    "winning_days": metrics.performance.winning_days,
                    "losing_days": metrics.performance.losing_days,
                    "average_trades_per_day": metrics.performance.average_trades_per_day,
                    "average_trade_duration_minutes": metrics.performance.average_trade_duration_minutes,
                    "profit_per_trading_hour": metrics.performance.profit_per_trading_hour,
                    "daily_expectancy": metrics.performance.daily_expectancy,
                },
                "risk": {
                    "maximum_daily_drawdown": metrics.risk.maximum_daily_drawdown,
                    "average_daily_drawdown": metrics.risk.average_daily_drawdown,
                    "daily_risk_utilization": metrics.risk.daily_risk_utilization,
                },
                "operational": {
                    "average_daily_signals": metrics.operational.average_daily_signals,
                    "average_daily_executions": metrics.operational.average_daily_executions,
                    "average_daily_exposure": metrics.operational.average_daily_exposure,
                    "average_daily_slippage": metrics.operational.average_daily_slippage,
                },
            },
            "daily_report": {
                "report_id": report.report_id,
                "trading_day": report.trading_day,
                "knowledge_updates": list(report.knowledge_updates),
                "improvement_recommendations": list(report.improvement_recommendations),
            },
            "learning_loop": {
                "knowledge_updates": list(learning["knowledge_updates"]),
                "research_priorities": list(learning["research_priorities"]),
                "future_campaigns": list(learning["future_campaigns"]),
            },
            "certification": certification_rows,
            "risk_decision": {
                "approved": risk_decision.approved,
                "reasons": list(risk_decision.reasons),
                "checks": risk_decision.metadata.get("checks", {}),
            },
            "trade_journal": journal_entries,
            "timestamp": snapshot.timestamp.isoformat(),
        }

    def intraday_decision_intelligence(self) -> dict[str, Any]:
        daily = self.intraday_daily()
        profile = default_intraday_profile()
        timestamp = datetime.now(UTC)
        session = SessionEngine().current_session(timestamp)
        readiness_inputs = MarketReadinessInputs(
            market_regime=daily["market_readiness"]["inputs"]["market_regime"],
            volatility=float(daily["market_readiness"]["inputs"]["volatility"]),
            spread=float(daily["market_readiness"]["inputs"]["spread"]),
            session=session,
            available_strategies=len(daily.get("active_strategies", [])),
            portfolio_exposure=float(daily["market_readiness"]["inputs"]["portfolio_exposure"]),
        )
        opportunity_score = DailyMarketReadinessEvaluator().evaluate(readiness_inputs)
        market_quality = MarketQualityEngine().evaluate(
            MarketQualityInputs(
                spread=readiness_inputs.spread,
                liquidity=0.82,
                volatility=readiness_inputs.volatility,
                price_stability=0.84,
                session=session,
                market_structure="CLEAN_TREND",
            )
        )
        news_state = NewsEventFilter().evaluate(
            (
                ScheduledNewsEvent(
                    NewsEventType.CENTRAL_BANK_SPEECH,
                    timestamp + timedelta(minutes=120),
                    "medium",
                    "EUR_USD",
                ),
            ),
            timestamp,
        )
        risk_state = DailyRiskState(
            realized_daily_loss=max(profile.daily_risk_profile.max_daily_loss - float(daily["remaining_daily_risk"]), 0.0),
            current_daily_drawdown=float(daily["daily_drawdown"]),
            trades_today=int(daily["todays_trades"]),
            daily_exposure=readiness_inputs.portfolio_exposure,
            strategy_allocation=readiness_inputs.portfolio_exposure,
            currency_exposure=readiness_inputs.portfolio_exposure,
        )
        eligibility = TradeEligibilityEngine().evaluate(
            TradeEligibilityRequest(
                strategy_active=bool(daily.get("active_strategies")),
                session_allowed=session in profile.allowed_sessions,
                opportunity_score=opportunity_score,
                market_quality=market_quality,
                portfolio_exposure=readiness_inputs.portfolio_exposure,
                daily_risk_remaining=float(daily["remaining_daily_risk"]),
                news_state=news_state,
                manual_trading_suspension=False,
                broker_healthy=True,
            )
        )
        active_strategies = daily.get("active_strategies") or ["QF-INTRADAY-DEMO"]
        decision = IntradayTradeDecisionEngine().decide(
            instrument="EUR_USD",
            strategy_asset_id=str(next(iter(active_strategies))),
            feature_vector_id=f"FV-{timestamp.strftime('%Y%m%d')}-INTRADAY",
            market_regime=readiness_inputs.market_regime,
            signal=IntradayTradeDecision.BUY,
            eligibility=eligibility,
            opportunity_score=opportunity_score,
            market_quality=market_quality,
            risk_state=risk_state,
            portfolio_state={
                "session_portfolio": daily["session_portfolio"],
                "portfolio_exposure": readiness_inputs.portfolio_exposure,
                "active_strategies": daily.get("active_strategies", []),
            },
            news_state=news_state,
            timestamp=timestamp,
        )
        risk_budget = DynamicDailyRiskBudgetEngine().allocate(profile.daily_risk_profile.max_daily_loss, opportunity_score)
        plan = DailyTradingPlanGenerator().generate(
            trading_day=timestamp.date().isoformat(),
            profile=profile,
            opportunity_score=opportunity_score,
            risk_budget=risk_budget,
        )
        status = DecisionIntelligenceStatusEngine().status(
            snapshot=DailyOperationsDashboardBuilder().snapshot(
                profile,
                risk_state,
                SessionPortfolioManager().build({"QF-INTRADAY-DEMO": profile}),
                timestamp,
                todays_pl=float(daily["todays_pl"]),
                open_positions=int(daily["open_positions"]),
                risk_paused=not eligibility.eligible,
            ),
            eligibility=eligibility,
            news_state=news_state,
        )
        timeline = DecisionTimelineBuilder().build(
            timestamp=timestamp,
            opportunity_score=opportunity_score,
            market_quality=market_quality,
            eligibility=eligibility,
            decision=decision,
            status=status,
        )
        journal = DailyDecisionJournalGenerator().generate(
            trading_day=timestamp.date().isoformat(),
            opportunity_score=opportunity_score,
            market_quality=market_quality,
            decision=decision,
            eligibility=eligibility,
            risk_budget=risk_budget,
        )
        avoided_eligibility = TradeEligibilityEngine().evaluate(
            TradeEligibilityRequest(
                strategy_active=True,
                session_allowed=True,
                opportunity_score=opportunity_score,
                market_quality=market_quality,
                portfolio_exposure=readiness_inputs.portfolio_exposure,
                daily_risk_remaining=0.0,
                news_state=news_state,
                manual_trading_suspension=False,
                broker_healthy=True,
            )
        )
        avoided_decision = IntradayTradeDecisionEngine().decide(
            instrument="EUR_USD",
            strategy_asset_id="QF-INTRADAY-DEMO",
            feature_vector_id=f"FV-{timestamp.strftime('%Y%m%d')}-AVOIDED",
            market_regime="NEWS_RISK",
            signal=IntradayTradeDecision.BUY,
            eligibility=avoided_eligibility,
            opportunity_score=opportunity_score,
            market_quality=market_quality,
            risk_state=risk_state,
            portfolio_state={"portfolio_exposure": readiness_inputs.portfolio_exposure},
            news_state=news_state,
            timestamp=timestamp,
        )
        quality_metrics = DecisionQualityMetricsCalculator().calculate((decision, avoided_decision))
        return {
            "opportunity_score": {
                "score": opportunity_score.score,
                "band": opportunity_score.band.value,
                "decision": opportunity_score.decision.value,
                "factors": opportunity_score.factors,
                "reasons": list(opportunity_score.reasons),
            },
            "market_quality": {
                "score": market_quality.score,
                "rating": market_quality.rating.value,
                "factors": market_quality.factors,
                "reasons": list(market_quality.reasons),
            },
            "news_filter": _news_state_payload(news_state),
            "eligibility": {
                "status": eligibility.status.value,
                "eligible": eligibility.eligible,
                "reasons": list(eligibility.reasons),
            },
            "trade_decision": _trade_decision_payload(decision),
            "daily_trading_plan": _daily_plan_payload(plan),
            "dynamic_daily_risk_budget": {
                "opportunity_decision": risk_budget.opportunity_decision.value,
                "budget": risk_budget.budget,
                "policy": risk_budget.policy,
            },
            "intraday_trading_status": {
                "status": status.status.value,
                "reasons": list(status.reasons),
            },
            "dashboard": {
                "current_session": session.value,
                "opportunity_score": opportunity_score.score,
                "market_quality": market_quality.rating.value,
                "trading_status": status.status.value,
                "todays_risk_usage": risk_state.realized_daily_loss,
                "todays_trades": risk_state.trades_today,
                "remaining_risk_budget": daily["remaining_daily_risk"],
                "current_portfolio": daily["session_portfolio"],
                "expected_market_regime": plan.expected_regimes[0],
                "next_high_impact_event": _news_state_payload(news_state)["next_event"],
            },
            "decision_timeline": [_timeline_event_payload(item) for item in timeline],
            "daily_trading_journal": _daily_decision_journal_payload(journal),
            "decision_quality_metrics": _decision_quality_metrics_payload(quality_metrics),
            "timestamp": timestamp.isoformat(),
        }

    def _engine_workload_from(self, engines: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "engine": engine["engine"],
                "status": engine["status"],
                "active_workload": engine["workload_percent"],
                "queue_depth": engine["queue_depth"],
                "capacity": 100,
                "last_update": self._timestamp,
            }
            for engine in engines
        ]

    def indicators(self) -> list[dict[str, Any]]:
        return [
            _indicator("EMA", "Indicator", "Trend direction, pullback zones, moving-average alignment", "Strategy Library, Feature Engine"),
            _indicator("SMA", "Indicator", "Baseline trend and mean reference", "Feature Engine"),
            _indicator("WMA", "Indicator", "Weighted trend smoothing", "Calculation Engine"),
            _indicator("HMA", "Indicator", "Low-lag trend smoothing", "Calculation Engine"),
            _indicator("SuperTrend", "Indicator", "Trend state and trailing stop context", "Strategy Composer"),
            _indicator("Ichimoku", "Indicator", "Cloud trend, support/resistance, and momentum context", "Strategy Composer"),
            _indicator("Donchian Channels", "Indicator", "Breakout range and channel boundaries", "Breakout templates"),
            _indicator("RSI", "Indicator", "Momentum exhaustion and pullback qualification", "Feature Engine"),
            _indicator("MACD", "Indicator", "Momentum direction and signal-line confirmation", "Strategy Library"),
            _indicator("Stochastic", "Indicator", "Range momentum and overbought/oversold context", "Mean reversion templates"),
            _indicator("CCI", "Indicator", "Cyclical deviation from mean price", "Research features"),
            _indicator("ROC", "Indicator", "Rate-of-change momentum", "Momentum templates"),
            _indicator("Momentum", "Indicator", "Directional impulse scoring", "Feature Engine"),
            _indicator("ATR", "Volatility", "Volatility sizing, stop distance, and exit model", "Backtesting, Risk, Portfolio"),
            _indicator("Bollinger Bands", "Volatility", "Volatility envelope and mean-reversion context", "Mean reversion templates"),
            _indicator("Keltner Channels", "Volatility", "ATR envelope and trend channel context", "Breakout templates"),
            _indicator("OBV", "Volume", "Volume pressure confirmation", "Research features"),
            _indicator("VWAP", "Session", "Session value reference and intraday mean", "Session features"),
            _indicator("MFI", "Volume", "Volume-weighted momentum", "Research features"),
            _indicator("Rolling Mean", "Statistical", "Moving statistical baseline", "Feature Engine"),
            _indicator("Rolling Median", "Statistical", "Robust central tendency", "Feature Engine"),
            _indicator("Rolling Standard Deviation", "Statistical", "Volatility and dispersion", "Feature Engine"),
            _indicator("Z-Score", "Statistical", "Standardized distance from baseline", "Strategy Composer"),
            _indicator("Variance", "Statistical", "Dispersion measurement", "Research features"),
            _indicator("Percentile", "Statistical", "Relative rank of recent values", "Optimization Laboratory"),
            _indicator("Skewness", "Statistical", "Return distribution asymmetry", "Validation reports"),
            _indicator("Kurtosis", "Statistical", "Tail-risk profile", "Validation reports"),
            _indicator("Simple Returns", "Statistical", "Basic return stream", "Backtesting"),
            _indicator("Log Returns", "Statistical", "Normalized return stream", "Backtesting"),
            _indicator("True Range", "Volatility", "Raw volatility component for ATR", "Calculation Engine"),
            _indicator("Close-to-Close Volatility", "Volatility", "Realized volatility estimate", "Portfolio Engine"),
            _indicator("Candle Body/Wick/Range", "Price Action", "Candle anatomy and rejection signals", "Price Action Calculator"),
            _indicator("Inside/Outside Bar", "Price Action", "Compression and expansion patterns", "Strategy Composer"),
            _indicator("Pin Bar", "Price Action", "Rejection and reversal signal", "Price Action templates"),
            _indicator("Engulfing", "Price Action", "Momentum reversal pattern", "Price Action templates"),
            _indicator("Swing High/Low", "Market Structure", "Local structure pivots", "Market Structure Calculator"),
            _indicator("HH/HL/LH/LL", "Market Structure", "Trend structure classification", "Market Regime Engine"),
            _indicator("BOS", "Market Structure", "Break of structure detection", "Strategy Composer"),
            _indicator("CHoCH", "Market Structure", "Change of character detection", "Strategy Composer"),
            _indicator("Support/Resistance Distance", "Market Structure", "Distance to nearby structure levels", "Risk and entry filters"),
            _indicator("Session Flags", "Session", "Asian, London, New York, overlap, weekend, holiday context", "Session Calculator"),
        ]

    def strategies(self) -> list[dict[str, Any]]:
        return [_strategy_row(asset) for asset in self._library.production_grade_strategies]

    def strategy(self, strategy_id: str) -> dict[str, Any]:
        asset = self._find_strategy(strategy_id)
        stored = self._find_approved_strategy(strategy_id)
        return {
            **_strategy_row(asset),
            "passport": self.strategy_passport(strategy_id),
            "decision_trace": self.strategy_decision_trace(strategy_id),
            "optimization_report": stored.optimization_report
            if stored
            else {
                "stable_regions": 7,
                "best_region": {"ema_fast": "18-26", "ema_slow": "60-90", "atr": "1.8-2.3"},
                "review": "APPROVED",
            },
            "validation_report": self.strategy_validation(strategy_id),
            "backtest_report": {
                "profit_factor": asset.profit_factor,
                "max_drawdown": round(asset.max_drawdown * 100, 1),
                "validation_ready": True,
            },
            "paper_trading_status": "READY",
            "deployment_status": "PAPER_SHADOW_GATE",
            "source_workflow_id": asset.source_workflow_id,
            "source_job_id": asset.source_job_id,
            "source_experiment_id": asset.source_experiment_id,
            "source_validation_id": asset.source_validation_id,
            "source_publication_id": asset.source_publication_id,
            "approved_at": asset.approved_at,
            "demo_mode": asset.demo_mode,
            "timestamp": self._timestamp,
        }

    def strategy_passport(self, strategy_id: str) -> dict[str, Any]:
        asset = self._find_strategy(strategy_id)
        return {
            "strategy_id": asset.asset_id,
            "template": asset.template,
            "family": asset.family.value,
            "validation_grade": asset.validation_grade,
            "confidence": round(asset.confidence * 100, 1),
            "production": asset.production_grade,
            "passport_present": asset.strategy_passport_present,
            "strategy_version": asset.strategy_version,
            "source_workflow_id": asset.source_workflow_id,
            "source_experiment_id": asset.source_experiment_id,
            "approved_at": asset.approved_at,
            "demo_mode": asset.demo_mode,
            "source": "Strategy Library",
            "timestamp": self._timestamp,
        }

    def strategy_validation(self, strategy_id: str) -> dict[str, Any]:
        asset = self._find_strategy(strategy_id)
        return {
            "strategy_id": asset.asset_id,
            "walk_forward": asset.walk_forward,
            "monte_carlo": asset.monte_carlo,
            "cross_pair": asset.cross_pair,
            "cross_timeframe": asset.cross_timeframe,
            "stress_test": asset.stress_test,
            "grade": asset.validation_grade,
            "confidence": round(asset.confidence * 100, 1),
            "source_validation_id": asset.source_validation_id,
            "demo_mode": asset.demo_mode,
            "timestamp": self._timestamp,
        }

    def strategy_decision_trace(self, strategy_id: str) -> dict[str, Any]:
        asset = self._find_strategy(strategy_id)
        return {
            "strategy_id": asset.asset_id,
            "complete": asset.decision_trace_complete,
            "events": (
                "research_goal_selected",
                "hypothesis_generated",
                "candidate_composed",
                "stable_region_optimized",
                "event_backtest_completed",
                "validation_gates_passed",
                "strategy_asset_published",
            ),
            "source_experiment_id": asset.source_experiment_id,
            "demo_mode": asset.demo_mode,
            "timestamp": self._timestamp,
        }

    def strategy_optimization(self, strategy_id: str) -> dict[str, Any]:
        asset = self._find_strategy(strategy_id)
        stored = self._find_approved_strategy(strategy_id)
        return {
            "strategy_id": asset.asset_id,
            "optimization_report": stored.optimization_report
            if stored
            else {
                "stable_regions": 7,
                "best_region": {"ema_fast": "18-26", "ema_slow": "60-90", "atr": "1.8-2.3"},
                "review": "APPROVED",
            },
            "demo_mode": asset.demo_mode,
            "timestamp": self._timestamp,
        }

    def strategy_trace(self, strategy_id: str) -> dict[str, Any]:
        asset = self._find_strategy(strategy_id)
        stored = self._find_approved_strategy(strategy_id)
        replay = self.paper_replay_status()
        approvals = self.workflow_current_approvals()
        approval = approvals[0] if approvals else {}
        return {
            "strategy_asset_id": asset.asset_id,
            "strategy_version": asset.strategy_version,
            "demo_mode": asset.demo_mode,
            "source": "ApprovedStrategyAssetStore" if stored else "Demo Strategy Library",
            "origin": {
                "source_workflow_id": asset.source_workflow_id,
                "source_job_id": asset.source_job_id,
                "source_experiment_id": asset.source_experiment_id,
                "source_validation_id": asset.source_validation_id,
                "source_publication_id": asset.source_publication_id,
                "approved_at": asset.approved_at,
            },
            "reports": {
                "optimization_report_id": stored.optimization_report_id if stored else "",
                "validation_report_id": stored.validation_report_id if stored else asset.source_validation_id,
                "strategy_passport_id": stored.strategy_passport_id if stored else asset.asset_id,
                "decision_trace_id": stored.decision_trace_id if stored else asset.source_experiment_id,
            },
            "paper_replay": {
                "replay_id": replay.get("replay_id", ""),
                "status": replay.get("status", ""),
                "pair": replay.get("pair", ""),
                "timeframe": replay.get("timeframe", ""),
                "processed_events": replay.get("processed_events", 0),
                "generated_signals": replay.get("generated_signals", 0),
                "paper_orders": replay.get("paper_orders", 0),
                "current_candle_time": replay.get("current_candle_time", ""),
            },
            "approval_gate": {
                "approval_id": approval.get("approval_id", ""),
                "approval_type": approval.get("approval_type", ""),
                "status": approval.get("status", ""),
                "reason": approval.get("reason", ""),
                "approved_at": approval.get("approved_at", ""),
                "rejected_at": approval.get("rejected_at", ""),
            },
            "trace_steps": [
                {"step": "Full-history research", "id": asset.source_job_id, "status": "COMPLETE"},
                {"step": "Autonomous research", "id": asset.source_experiment_id, "status": "COMPLETE"},
                {"step": "Validation platform", "id": asset.source_validation_id, "status": asset.validation_grade},
                {"step": "Approved Strategy Asset Store", "id": asset.asset_id, "status": asset.status},
                {"step": "Strategy Library", "id": asset.asset_id, "status": "VISIBLE"},
                {"step": "Paper replay", "id": str(replay.get("replay_id", "")), "status": str(replay.get("status", ""))},
                {"step": "Manual approval gate", "id": str(approval.get("approval_id", "")), "status": str(approval.get("status", ""))},
            ],
            "timestamp": self._timestamp,
        }

    def portfolio_readiness(self) -> dict[str, Any]:
        return {
            "portfolio_readiness": "READY_FOR_PAPER_TRADING",
            "production_strategies": self._library.kpis.production_grade_strategies,
            "selected_portfolio_strategies": 29,
            "average_correlation": 0.24,
            "expected_drawdown": 8.5,
            "expected_portfolio_pf": 2.18,
            "regime_coverage": 0.96,
            "pair_coverage": 0.91,
            "timeframe_coverage": 1.0,
            "source": "PortfolioConstructionEngine",
            "timestamp": self._timestamp,
        }

    def portfolio_correlation(self) -> dict[str, Any]:
        return {
            "labels": ("Trend", "Mean", "Breakout", "Momentum", "Volatility"),
            "matrix": (
                (1.0, 0.18, 0.22, 0.35, 0.12),
                (0.18, 1.0, 0.10, 0.16, 0.28),
                (0.22, 0.10, 1.0, 0.31, 0.24),
                (0.35, 0.16, 0.31, 1.0, 0.19),
                (0.12, 0.28, 0.24, 0.19, 1.0),
            ),
            "timestamp": self._timestamp,
        }

    def portfolio_coverage(self) -> dict[str, Any]:
        diversity = self.research_diversity()
        return {
            "regimes": {"trending": 0.96, "ranging": 0.82, "breakout": 0.88, "volatile": 0.91},
            "pairs": _ratio_map(diversity.get("pairs", {})),
            "timeframes": _ratio_map(diversity.get("timeframes", {})),
            "families": _ratio_map(diversity.get("families", {})) or {family.value: 0.20 for family in ResearchProgramFamily},
            "timestamp": self._timestamp,
        }

    def portfolio_risk(self) -> dict[str, Any]:
        return {
            "expected_drawdown_curve": [0.0, 1.1, 2.8, 3.5, 5.9, 8.5],
            "portfolio_equity_curve": [100000, 101240, 102180, 103560, 104020, 105410],
            "max_strategy_allocation": 0.05,
            "max_pair_exposure": 0.22,
            "timestamp": self._timestamp,
        }

    def portfolio_intelligence(self) -> dict[str, Any]:
        snapshot = PortfolioIntelligenceEngine().analyze(demo_portfolio_strategy_inputs())
        return {
            **snapshot.to_payload(),
            "source": "PortfolioIntelligenceEngine",
            "demo_mode": self._demo_mode,
        }

    def performance_learning(self) -> dict[str, Any]:
        snapshot = PerformanceLearningEngine().analyze(
            demo_trade_performance_inputs(),
            demo_portfolio_decision_inputs(),
        )
        return {
            **snapshot.to_payload(),
            "source": "PerformanceLearningEngine",
            "demo_mode": self._demo_mode,
        }

    def paper_summary(self) -> dict[str, Any]:
        starting_balance = 100_000.0
        positions = _paper_position_records()
        open_positions = [position for position in positions if position.get("status") == "OPEN"]
        closed_positions = [position for position in positions if position.get("status") == "CLOSED"]
        realized_pl = round(sum(_position_pl_value(position) for position in closed_positions), 2)
        floating_pl = round(sum(_position_pl_value(position) for position in open_positions), 2)
        balance = round(starting_balance + realized_pl, 2)
        equity = round(balance + floating_pl, 2)
        total_pl = round(realized_pl + floating_pl, 2)
        return {
            "paper_balance": balance,
            "paper_equity": equity,
            "open_trades": len(open_positions),
            "closed_trades": len(closed_positions),
            "daily_pl": total_pl,
            "total_pl": total_pl,
            "realized_pl": realized_pl,
            "floating_pl": floating_pl,
            "paper_drawdown": round(abs(min(total_pl, 0.0)) / starting_balance, 4),
            "expected_vs_actual_deviation": self._paper.prediction_analysis.deviation,
            "promotion_readiness": self._paper.monthly_review.decision.value,
            "timestamp": self._timestamp,
        }

    def paper_open_trades(self) -> list[dict[str, Any]]:
        return [
            {
                "order_id": order.order_id,
                "instrument": order.instrument,
                "action": order.action.value,
                "units": order.units,
                "expected_price": order.expected_price,
            }
            for order in self._paper.paper_orders
        ]

    def paper_closed_trades(self) -> list[dict[str, Any]]:
        return []

    def paper_drift(self) -> dict[str, Any]:
        return {
            "strategy_drift": self._paper.dashboard.strategy_drift,
            "execution_drift": self._paper.dashboard.execution_drift,
            "expected_vs_actual": self._paper.dashboard.expected_vs_actual,
            "metrics": [
                {"type": metric.drift_type.value, "score": metric.score, "status": metric.status}
                for metric in self._paper.drift_metrics
            ],
            "timestamp": self._timestamp,
        }

    def paper_promotion(self) -> dict[str, Any]:
        review = self._paper.monthly_review
        return {
            "decision": review.decision.value,
            "days_observed": review.days_observed,
            "duplicate_orders": review.duplicate_orders,
            "decision_trace_coverage": review.decision_trace_coverage,
            "expected_actual_within_threshold": review.expected_actual_within_threshold,
            "timestamp": self._timestamp,
        }

    def paper_replay_status(self) -> dict[str, Any]:
        cursor = ReplayProgressStore(_paper_replay_progress_file()).load()
        if cursor is None:
            return {
                "status": "NOT_STARTED",
                "replay_id": "",
                "pair": "",
                "timeframe": "",
                "current_candle_time": "",
                "start_time": "",
                "end_time": "",
                "processed_events": 0,
                "generated_signals": 0,
                "paper_orders": 0,
                "last_error": "",
                "source": "ReplayProgressStore",
                "timestamp": self._timestamp,
            }
        return {
            "status": cursor.status.value,
            "replay_id": cursor.replay_id,
            "pair": cursor.pair,
            "timeframe": cursor.timeframe,
            "current_candle_time": cursor.current_candle_time,
            "start_time": cursor.start_time,
            "end_time": cursor.end_time,
            "processed_events": cursor.processed_events,
            "generated_signals": cursor.generated_signals,
            "paper_orders": cursor.paper_orders,
            "last_error": cursor.last_error,
            "source": "ReplayProgressStore",
            "timestamp": self._timestamp,
        }

    def paper_practice_latest(self) -> dict[str, Any]:
        path = _paper_practice_result_file()
        if not path.exists():
            return {
                "status": "NOT_STARTED",
                "updated_at": "",
                "connected": False,
                "events_processed": 0,
                "signals_generated": 0,
                "orders_executed": 0,
                "orders_blocked": 0,
                "open_positions": 0,
                "pairs_scanned": 0,
                "timeframes_scanned": 0,
                "candles_checked": 0,
                "skip_reasons": {},
                "paper_scanner_pair_result": [],
                "open_paper_positions": [],
                "closed_paper_positions": [],
                "run_24_7_ready": False,
                "execution_path": "NO_RESULT_FILE",
                "latest_signal": {},
                "latest_execution": {},
                "open_position_details": [],
                "source": str(path.relative_to(_repo_root())),
                "timestamp": datetime.now(UTC).isoformat(),
            }
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["open_paper_positions"] = self._paper_position_rows("OPEN")
        payload["closed_paper_positions"] = self._paper_position_rows("CLOSED")
        return {
            "status": "RUNNING",
            **payload,
            "source": str(path.relative_to(_repo_root())),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def _paper_position_rows(self, status: str) -> list[dict[str, Any]]:
        store = PaperPositionStore(default_paper_positions_file())
        rows = store.list_open() if status == "OPEN" else store.list_closed(limit=200)
        strategy_names = _strategy_name_lookup(self._strategy_asset_repository)
        return [_paper_position_table_row(position, strategy_names, closed=status == "CLOSED") for position in rows]

    def paper_practice_history(self) -> list[dict[str, Any]]:
        path = _paper_practice_history_file()
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines()[-50:]:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.append(
                {
                    "updated_at": payload.get("updated_at", ""),
                    "connected": payload.get("connected", False),
                    "events_processed": payload.get("events_processed", 0),
                    "signals_generated": payload.get("signals_generated", 0),
                    "orders_executed": payload.get("orders_executed", 0),
                    "open_positions": payload.get("open_positions", 0),
                    "execution_path": payload.get("execution_path", ""),
                    "run_24_7_ready": payload.get("run_24_7_ready", False),
                }
            )
        rows.reverse()
        return rows

    def paper_position_chart(
        self,
        *,
        pair: str,
        timeframe: str,
        direction: str = "",
        open_price: str | float | None = None,
        stop_loss: str | float | None = None,
        take_profit: str | float | None = None,
        opened_at: str = "",
        source_candle_time: str = "",
        limit: int = 3000,
    ) -> dict[str, Any]:
        pair_name = _chart_pair_name(pair)
        candle_limit = max(1, min(int(limit or 3000), 3000))
        candles: list[dict[str, Any]] = []
        database_status = "available"
        error = ""
        try:
            with get_coreui_history_engine().connect() as connection:
                repository = CoreUiCandleRepository(connection, get_settings().coreui_candle_table)
                rows = repository.load_latest(pair_name, timeframe, limit=candle_limit)
            candles = [
                {
                    "time": _chart_time(row.get("time")),
                    "open": _safe_float(row.get("open_price")),
                    "high": _safe_float(row.get("high_price")),
                    "low": _safe_float(row.get("low_price")),
                    "close": _safe_float(row.get("close_price")),
                    "volume": int(row.get("volume") or 0),
                }
                for row in rows
                if _safe_float(row.get("open_price")) is not None
                and _safe_float(row.get("high_price")) is not None
                and _safe_float(row.get("low_price")) is not None
                and _safe_float(row.get("close_price")) is not None
            ]
        except Exception as exc:
            database_status = "unavailable"
            error = str(exc)

        return {
            "pair": pair_name,
            "display_pair": _display_pair(pair_name),
            "timeframe": timeframe,
            "limit": candle_limit,
            "candles": candles,
            "trade": {
                "direction": direction,
                "open_price": _safe_float(open_price),
                "stop_loss": _safe_float(stop_loss),
                "take_profit": _safe_float(take_profit),
                "opened_at": _chart_time(source_candle_time or opened_at),
                "source_candle_time": _chart_time(source_candle_time),
            },
            "database_status": database_status,
            "error": error,
            "source": "coreui.oanda_candles",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def ops_health(self) -> dict[str, Any]:
        return {
            "platform_status": "HEALTHY",
            "last_candle_update": "2026-07-02T19:40:00+08:00",
            "services_online": 10,
            "open_incidents": 0,
            "warnings": 0,
            "errors": 0,
            "queue_size": 2,
            "cpu_usage": 24.0,
            "ram_usage": 38.0,
            "disk_usage": 42.0,
            "source": "AutonomousOperationsManager",
            "timestamp": self._timestamp,
        }

    def ops_services(self) -> list[dict[str, Any]]:
        services = (
            "Market Data Collector",
            "PostgreSQL",
            "Redis",
            "OANDA Connection",
            "Calculation Engine",
            "Feature Engine",
            "Research Engine",
            "Live Trading Engine",
            "Shadow Trading Engine",
            "Operations Manager",
        )
        return [
            {
                "service": service,
                "status": "HEALTHY",
                "version": "1.0.0",
                "uptime": "5d 12h",
                "source": "SRE health checks",
                "timestamp": self._timestamp,
            }
            for service in services
        ]

    def ops_incidents(self) -> list[dict[str, Any]]:
        return [
            {
                "incident_id": incident.incident_id,
                "severity": incident.severity.value,
                "service": incident.service,
                "root_cause": incident.root_cause,
                "resolved": incident.resolved,
                "resolution_time_seconds": incident.resolution_time_seconds,
            }
            for incident in self._operations.incidents
        ]

    def ops_latency(self) -> dict[str, Any]:
        return {
            "database_latency_ms": 8.0,
            "oanda_latency_ms": 74.0,
            "event_processing_latency_ms": 12.0,
            "broker_sync_seconds": 4.2,
            "timestamp": self._timestamp,
        }

    def ops_system(self) -> dict[str, Any]:
        return {
            "uptime": _series(99.97, 6),
            "cpu": [18, 22, 24, 21, 23, 24],
            "ram": [31, 34, 36, 35, 37, 38],
            "database_latency": [7, 8, 7, 9, 8, 8],
            "incident_count": [0, 0, 1, 0, 0, 0],
            "timestamp": self._timestamp,
        }

    def knowledge_summary(self) -> dict[str, Any]:
        return {
            "knowledge_records": self._library.kpis.knowledge_records_written,
            "confirmed_hypotheses": 1240,
            "rejected_hypotheses": 317,
            "top_feature_family": "trend_strength",
            "top_strategy_template": "EMA Pullback",
            "top_regime": "TRENDING",
            "timestamp": self._timestamp,
        }

    def knowledge_features(self) -> list[dict[str, Any]]:
        return _ranked("feature", self._library.dashboard.feature_importance)

    def knowledge_plugins(self) -> list[dict[str, Any]]:
        return _ranked(
            "plugin",
            {
                "ema_pullback_entry": 0.94,
                "atr_exit": 0.91,
                "drawdown_guard": 0.90,
                "volatility_filter": 0.88,
            },
        )

    def knowledge_templates(self) -> list[dict[str, Any]]:
        counts: dict[str, float] = {}
        for asset in self._library.production_grade_strategies:
            counts[asset.template] = counts.get(asset.template, 0.0) + 1
        return _ranked("template", counts)

    def knowledge_hypotheses(self) -> list[dict[str, Any]]:
        return [
            {"hypothesis": "Trend pullbacks outperform during London trends.", "confidence": 0.94},
            {"hypothesis": "ATR expansion improves breakout filtering.", "confidence": 0.91},
            {"hypothesis": "Mean reversion weakens during high-volatility news windows.", "confidence": 0.88},
        ]

    def _research_matrix_builder(self) -> ResearchMatrixBuilder:
        state_file = _full_history_state_file()
        return ResearchMatrixBuilder(
            _planned_full_history_jobs(state_file),
            state_file,
            asset_repository=self._strategy_asset_repository,
            rejection_repository=default_rejected_strategy_repository(_repo_root()),
        )

    def _research_matrix_rows(self):
        return self._research_matrix_builder().rows()

    def _always_on_research_orchestrator(self) -> AlwaysOnAutonomousResearchOrchestrator:
        state_file = _full_history_state_file()
        return AlwaysOnAutonomousResearchOrchestrator(
            planned_jobs=_planned_full_history_jobs(state_file),
            full_history_state_file=state_file,
            paths=default_always_on_orchestrator_paths(_repo_root()),
            thresholds=_research_orchestrator_thresholds(),
        )

    def _history_validation_engine(self) -> HistoricalValidationEngine:
        return HistoricalValidationEngine(
            asset_repository=self._strategy_asset_repository,
            paths=default_historical_validation_paths(_repo_root()),
            config=historical_validation_config_from_env(),
        )

    def _find_strategy(self, strategy_id: str) -> StrategyLibraryAsset:
        for asset in self._library.production_grade_strategies:
            if asset.asset_id == strategy_id:
                return asset
        raise KeyError(strategy_id)

    def _find_approved_strategy(self, strategy_id: str):
        if self._demo_mode:
            return None
        try:
            return self._strategy_asset_repository.get(strategy_id)
        except KeyError:
            return None


def _full_history_state_file() -> Path:
    return _repo_root() / "var" / "full_history_research_state.json"


def _workflow_paths():
    return default_workflow_paths(_repo_root())


def _approval_service() -> ApprovalService:
    paths = _workflow_paths()
    audit_file = paths.approval_file.with_name("workflow_approval_audit.jsonl")
    return ApprovalService(ApprovalRepository(paths.approval_file), ApprovalAuditLog(audit_file))


def _admin_settings_file() -> Path:
    return _repo_root() / "var" / "admin_settings.json"


def _live_trading_admin_state() -> dict[str, str]:
    admin_file = _admin_settings_file()
    enabled = bool(admin_setting_value(admin_file, "risk.live_trading_enabled", False))
    blocked = bool(admin_setting_value(admin_file, "workflow.live_trading_blocked_by_policy", True))
    if enabled and not blocked:
        return {
            "status": "ENABLED",
            "engine_status": "ENABLED",
            "health": "WATCH",
            "message": "Live trading enabled from Admin; execution remains subject to broker credentials and risk checks",
        }
    if enabled and blocked:
        return {
            "status": "BLOCKED_BY_POLICY",
            "engine_status": "BLOCKED",
            "health": "SAFE",
            "message": "Live trading switch is enabled, but policy block is still active",
        }
    return {
        "status": "DISABLED",
        "engine_status": "DISABLED",
        "health": "SAFE",
        "message": "Live execution disabled from Admin",
    }


def _approved_strategy_assets_file() -> Path:
    return _repo_root() / "var" / "approved_strategy_assets.json"


def _paper_replay_progress_file() -> Path:
    return _repo_root() / "var" / "paper_replay_progress.json"


def _paper_practice_result_file() -> Path:
    return _repo_root() / "var" / "paper_practice_trading_result.json"


def _paper_practice_history_file() -> Path:
    return _repo_root() / "var" / "paper_practice_trading_history.jsonl"


def _paper_position_records() -> list[dict[str, Any]]:
    path = default_paper_positions_file()
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [position for position in payload.get("positions", []) if isinstance(position, dict)]


def _position_pl_value(position: dict[str, Any]) -> float:
    value = _safe_float(position.get("p_l_account_currency"))
    if value is not None:
        return value
    value = _safe_float(position.get("p_l"))
    if value is not None:
        return value
    value = _safe_float(position.get("floating_pl"))
    return value if value is not None else 0.0


def _strategy_name_lookup(repository: StrategyAssetRepository) -> dict[str, str]:
    names: dict[str, str] = {}
    for asset in repository.list():
        for key in (asset.strategy_asset_id, asset.strategy_id):
            if key:
                names[key] = asset.strategy_name
    return names


def _paper_position_table_row(
    position: dict[str, Any],
    strategy_names: dict[str, str],
    *,
    closed: bool,
) -> dict[str, Any]:
    strategy_asset_id = str(position.get("strategy_asset_id") or position.get("strategy_id") or "")
    row = {
        "pair": position.get("pair") or position.get("instrument") or "",
        "timeframe": position.get("timeframe", ""),
        "strategy": strategy_names.get(strategy_asset_id, strategy_asset_id),
        "strategy_asset_id": strategy_asset_id,
        "direction": position.get("direction", ""),
        "units": position.get("units", 0),
        "open_price": _display_price(position.get("entry_price") or position.get("open_price")),
        "close_price": _display_price(position.get("close_price") or position.get("current_price")),
        "take_profit": _display_price(position.get("take_profit")),
        "stop_loss": _display_price(position.get("stop_loss")),
        "p_l": _display_money(_position_pl_value(position)),
    }
    if closed:
        row.update(
            {
                "close_reason": position.get("close_reason", ""),
                "opened_at": position.get("entry_time") or position.get("opened_at") or "",
                "closed_at": position.get("closed_at", ""),
                "source_candle_time": position.get("source_candle_time", ""),
            }
        )
    else:
        row.update(
            {
                "status": position.get("status", ""),
                "opened_at": position.get("entry_time") or position.get("opened_at") or "",
                "entry_time": position.get("entry_time", ""),
                "source_candle_time": position.get("source_candle_time", ""),
            }
        )
    return row


def _display_price(value: Any) -> str:
    number = _safe_float(value)
    if number is None:
        return ""
    return f"{number:.5f}"


def _display_money(value: Any) -> str:
    number = _safe_float(value)
    if number is None:
        return "0.00"
    return f"{number:.2f}"


def _full_history_research_cache_file() -> Path:
    return _repo_root() / "var" / "full_history_research_summary.json"


def _full_history_summary_cache() -> FullHistorySummaryCache:
    return FullHistorySummaryCache(FullHistoryResearchSummaryRepository(_full_history_research_cache_file()))


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _full_history_config() -> FullHistorySchedulerConfig:
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    admin_file = _admin_settings_file()
    return FullHistorySchedulerConfig(
        pairs=FULL_HISTORY_RESEARCH_PAIRS,
        timeframes=FULL_HISTORY_RESEARCH_TIMEFRAMES,
        start=FULL_HISTORY_RESEARCH_START,
        end=today_start + timedelta(days=1),
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
    )


def _research_orchestrator_thresholds() -> AlwaysOnResearchThresholds:
    return AlwaysOnResearchThresholds(
        min_assets_per_program=_env_int("RESEARCH_ORCHESTRATOR_MIN_ASSETS_PER_PROGRAM", 1),
        stale_after_hours=_env_int("RESEARCH_ORCHESTRATOR_STALE_AFTER_HOURS", 6),
        force_rerun_after_hours=_env_int("RESEARCH_ORCHESTRATOR_FORCE_RERUN_AFTER_HOURS", 24),
        max_jobs_per_pass=_env_int("RESEARCH_ORCHESTRATOR_MAX_JOBS_PER_CYCLE", 12),
        schedule_seconds=_env_int("RESEARCH_ORCHESTRATOR_INTERVAL_SECONDS", 900),
        max_jobs_in_flight=_env_int("RESEARCH_ORCHESTRATOR_MAX_IN_FLIGHT", 24),
    )


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _build_full_history_research_summary(status: dict[str, Any], timestamp: str) -> dict[str, Any]:
    coverage_rows, database_status, error = _full_history_coverage_rows()
    return {
        **_full_history_research_base(status, timestamp),
        "coverage": coverage_rows,
        "database_status": database_status,
        "error": error,
        "source": "FullHistoryResearchScheduler + CoreUI/OANDA candle database + cached snapshot",
    }


def _full_history_research_cache_miss(status: dict[str, Any], timestamp: str) -> dict[str, Any]:
    return {
        **_full_history_research_base(status, timestamp),
        "coverage": _configured_coverage_rows(),
        "database_status": "CACHE_PENDING",
        "error": "",
        "source": "FullHistoryResearchScheduler + cached summary pending",
        "cache": {
            "status": "MISS",
            "generated_at": "",
            "source": "FullHistorySummaryCache",
        },
    }


def _full_history_research_base(status: dict[str, Any], timestamp: str) -> dict[str, Any]:
    return {
        "pair_count": len(FULL_HISTORY_RESEARCH_PAIRS),
        "timeframe_count": len(FULL_HISTORY_RESEARCH_TIMEFRAMES),
        "pair_timeframe_count": len(FULL_HISTORY_RESEARCH_PAIRS)
        * len(FULL_HISTORY_RESEARCH_TIMEFRAMES),
        "pairs": [
            {"pair": _display_pair(pair), "symbol": pair, "type": _instrument_type(pair)}
            for pair in FULL_HISTORY_RESEARCH_PAIRS
        ],
        "timeframes": [{"timeframe": timeframe} for timeframe in FULL_HISTORY_RESEARCH_TIMEFRAMES],
        "scheduler": status,
        "timestamp": timestamp,
    }


def _configured_coverage_rows() -> list[dict[str, Any]]:
    return [
        {
            "pair": pair,
            "timeframe": timeframe,
            "candles": 0,
            "first_candle": "",
            "last_candle": "",
            "years": 0.0,
            "scheduler_start": FULL_HISTORY_RESEARCH_START.date().isoformat(),
            "status": "CACHE_PENDING",
        }
        for pair in FULL_HISTORY_RESEARCH_PAIRS
        for timeframe in FULL_HISTORY_RESEARCH_TIMEFRAMES
    ]


def _orphan_module_report() -> list[dict[str, Any]]:
    return [
        _orphan("quantforge.core.config", "MOVE_TO_LEGACY", "Superseded by quantforge.config.settings.", "Document as legacy compatibility config."),
        _orphan("quantforge.data.repository", "MOVE_TO_LEGACY", "Market data reads now use quantforge.market_data.coreui_repository.", "Keep out of production workflow."),
        _orphan("quantforge.domain.ownership", "KEEP_FOR_FUTURE", "Domain ownership helpers are not required by current single-team workflow.", "Owner: architecture."),
        _orphan("quantforge.experiments", "KEEP_FOR_FUTURE", "Facade exports experiment primitives used by research concepts but not active entrypoints.", "Owner: research."),
        _orphan("quantforge.indicators.dynamic", "WIRE_NOW", "Dynamic indicator registry is aligned with Strategy Composer but not surfaced in production flow.", "Wire into indicator discovery after Milestone 22."),
        _orphan("quantforge.instruments.model", "WIRE_NOW", "Instrument model should be the canonical source for pair metadata.", "Wire into full-history and strategy asset metadata."),
        _orphan("quantforge.plugins.components", "WIRE_NOW", "Plugin components match the target entry/confirmation/exit architecture.", "Wire into Strategy Composer templates."),
        _orphan("quantforge.plugins.registry", "WIRE_NOW", "Plugin registry should back plugin_versions on persisted Strategy Assets.", "Wire into StrategyAssetPersistenceService."),
        _orphan("quantforge.reporting", "KEEP_FOR_FUTURE", "Reporting facade is harmless but not used by dashboard/API yet.", "Owner: reporting."),
        _orphan("quantforge.research.engine", "MOVE_TO_LEGACY", "Older research engine path replaced by autonomous/full-history pipeline.", "Move to legacy after confirming no external imports."),
        _orphan("quantforge.storage.parquet_cache", "KEEP_FOR_FUTURE", "Parquet cache may be useful for large replay summaries but is not needed by current JSON store.", "Owner: storage."),
        _orphan("quantforge.strategies.discovery", "WIRE_NOW", "Strategy discovery belongs before candidate composition in real research controls.", "Wire into new research-run controls."),
        _orphan("quantforge.strategies.lifecycle", "WIRE_NOW", "Lifecycle states should govern APPROVED/PAPER_ELIGIBLE/PRODUCTION_ELIGIBLE transitions.", "Wire into approval and deployment gates."),
    ]


def _orphan(module: str, classification: str, reason: str, action: str) -> dict[str, Any]:
    return {
        "module": module,
        "classification": classification,
        "reason": reason,
        "action_taken": action,
        "entrypoint_or_owner": _orphan_owner(classification),
    }


def _orphan_owner(classification: str) -> str:
    return {
        "WIRE_NOW": "Milestone 22 integration backlog",
        "KEEP_FOR_FUTURE": "Architecture owner review",
        "MOVE_TO_LEGACY": "Legacy cleanup",
        "DELETE": "Deletion review",
    }.get(classification, "Architecture review")


def _planned_full_history_jobs(state_file: Path) -> tuple[Any, ...]:
    scheduler = FullHistoryResearchScheduler(
        config=_full_history_config(),
        state_file=state_file,
        repository_factory=lambda: None,  # type: ignore[arg-type]
    )
    return scheduler.plan()


def _full_history_job_rows(
    planned_jobs: tuple[Any, ...],
    history_by_id: dict[str, Any],
    completed_ids: set[str],
    failed_ids: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for job in planned_jobs:
        history = history_by_id.get(job.job_id, {})
        if job.job_id in completed_ids:
            status = "COMPLETE"
        elif job.job_id in failed_ids:
            status = "FAILED"
        else:
            status = "PENDING"
        rows.append(
            {
                "job_id": job.job_id,
                "stage": job.stage.value,
                "pair": _display_pair(job.pair),
                "timeframe": job.timeframe,
                "status": status,
                "start": job.start.date().isoformat(),
                "end": job.end.date().isoformat(),
                "max_batches": job.max_batches,
                "evidence": history.get("evidence", ""),
                "recorded_at": history.get("recorded_at", ""),
            }
        )
    return rows


def _full_history_coverage_rows() -> tuple[list[dict[str, Any]], str, str]:
    rows_by_key: dict[tuple[str, str], Any] = {}
    try:
        settings = get_settings()
        pair_values = ", ".join(f"'{pair}'" for pair in FULL_HISTORY_RESEARCH_PAIRS)
        timeframe_values = ", ".join(f"'{timeframe}'" for timeframe in FULL_HISTORY_RESEARCH_TIMEFRAMES)
        sql = text(
            f"""
            SELECT pair_name, granularity, COUNT(*) AS candles, MIN(time) AS first_time, MAX(time) AS last_time
            FROM {settings.coreui_candle_table}
            WHERE complete = true
              AND pair_name IN ({pair_values})
              AND granularity IN ({timeframe_values})
            GROUP BY pair_name, granularity
            ORDER BY pair_name, granularity
            """
        )
        with get_coreui_history_engine().connect() as connection:
            for row in connection.execute(sql).mappings():
                rows_by_key[(str(row["pair_name"]), str(row["granularity"]))] = row
        database_status = "available"
        error = ""
    except Exception as exc:
        database_status = "unavailable"
        error = str(exc)

    rows: list[dict[str, Any]] = []
    for pair in FULL_HISTORY_RESEARCH_PAIRS:
        for timeframe in FULL_HISTORY_RESEARCH_TIMEFRAMES:
            item = rows_by_key.get((pair, timeframe), {})
            first_time = item.get("first_time")
            last_time = item.get("last_time")
            rows.append(
                {
                    "pair": _display_pair(pair),
                    "symbol": pair,
                    "timeframe": timeframe,
                    "candles": int(item.get("candles", 0) or 0),
                    "first_candle": _date_string(first_time),
                    "last_candle": _date_string(last_time),
                    "years": _years_between(first_time, last_time),
                    "scheduler_start": FULL_HISTORY_RESEARCH_START.date().isoformat(),
                    "status": "CONFIGURED" if item else "CONFIGURED_NO_DB_COUNT",
                }
            )
    return rows, database_status, error


def _display_pair(pair: str) -> str:
    return {"NAS100_USD": "NAS100", "SPX500_USD": "SPX500"}.get(pair, pair)


def _chart_pair_name(pair: str) -> str:
    value = pair.strip().upper().replace("/", "_")
    return {"NAS100": "NAS100_USD", "SPX500": "SPX500_USD"}.get(value, value)


def _instrument_type(pair: str) -> str:
    return "index" if pair in {"NAS100_USD", "SPX500_USD"} else "fx"


def _chart_time(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat()
    if not value:
        return ""
    text = str(value)
    try:
        timestamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC).isoformat()


def _safe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _date_string(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    return str(value)[:10] if value else ""


def _years_between(first_time: Any, last_time: Any) -> float:
    if not isinstance(first_time, datetime) or not isinstance(last_time, datetime):
        return 0.0
    return round((last_time - first_time).days / 365.25, 2)


def _strategy_row(asset: StrategyLibraryAsset) -> dict[str, Any]:
    pair = asset.instruments[0]
    return {
        "strategy_id": asset.asset_id,
        "strategy_name": f"{asset.template} {asset.timeframe}",
        "pair": pair,
        "timeframe": asset.timeframe,
        "regime": "TRENDING" if asset.family == ResearchProgramFamily.TREND_FOLLOWING else asset.family.value,
        "template": asset.template,
        "entry_plugin": f"{asset.template.lower().replace(' ', '_')}_entry",
        "exit_plugin": "atr_exit",
        "risk_model": "drawdown_guard",
        "confidence": round(asset.confidence * 100, 1),
        "profit_factor": asset.profit_factor,
        "max_drawdown": round(asset.max_drawdown * 100, 1),
        "validation_grade": asset.validation_grade,
        "status": asset.status if asset.status else "PRODUCTION_GRADE" if asset.production_grade else "VALIDATED",
        "source": "Demo Strategy Library" if asset.demo_mode else "ApprovedStrategyAssetStore",
        "demo_mode": asset.demo_mode,
        "source_workflow_id": asset.source_workflow_id,
        "source_job_id": asset.source_job_id,
        "source_experiment_id": asset.source_experiment_id,
        "source_validation_id": asset.source_validation_id,
        "source_publication_id": asset.source_publication_id,
        "approved_at": asset.approved_at,
        "strategy_version": asset.strategy_version,
    }


def _assets_by_family(
    assets: tuple[StrategyLibraryAsset, ...],
) -> dict[ResearchProgramFamily, tuple[StrategyLibraryAsset, ...]]:
    grouped: dict[ResearchProgramFamily, list[StrategyLibraryAsset]] = {}
    for asset in assets:
        grouped.setdefault(asset.family, []).append(asset)
    return {family: tuple(items) for family, items in grouped.items()}


def _series(total: float, points: int) -> list[float]:
    return [round(total * (index + 1) / points, 2) for index in range(points)]


def _avg(values: list[float], *, default: float) -> float:
    return round(sum(values) / len(values), 3) if values else default


def _ranked(kind: str, values: dict[str, float]) -> list[dict[str, Any]]:
    return [
        {kind: key, "score": round(value, 3), "rank": index}
        for index, (key, value) in enumerate(
            sorted(values.items(), key=lambda item: item[1], reverse=True),
            start=1,
        )
    ]


def _ratio_map(values: Any) -> dict[str, float]:
    if not isinstance(values, dict):
        return {}
    total = sum(int(value) for value in values.values()) or 1
    return {str(key): round(int(value) / total, 3) for key, value in values.items()}


def _engine(
    engine: str,
    status: str,
    health: str,
    workload_percent: int,
    queue_depth: int,
    current_activity: str,
) -> dict[str, Any]:
    return {
        "engine": engine,
        "status": status,
        "health": health,
        "workload_percent": workload_percent,
        "queue_depth": queue_depth,
        "current_activity": current_activity,
    }


def _full_history_pipeline_done(full_history: dict[str, Any]) -> bool:
    planned = int(full_history.get("planned_jobs") or 0)
    pending = int(full_history.get("pending_jobs") or 0)
    completed = int(full_history.get("completed_jobs") or 0)
    failed = int(full_history.get("failed_jobs") or 0)
    return planned > 0 and pending == 0 and completed + failed >= planned


def _indicator(name: str, category: str, purpose: str, used_by: str) -> dict[str, Any]:
    return {
        "indicator": name,
        "category": category,
        "purpose": purpose,
        "used_by": used_by,
        "status": "ACTIVE",
    }


def _news_state_payload(news_state: Any) -> dict[str, Any]:
    return {
        "paused": news_state.paused,
        "reason": news_state.reason,
        "minutes_to_event": news_state.minutes_to_event,
        "next_event": {
            "event_type": news_state.next_event.event_type.value,
            "event_time": news_state.next_event.event_time.isoformat(),
            "impact": news_state.next_event.impact,
            "instrument": news_state.next_event.instrument,
        }
        if news_state.next_event
        else None,
    }


def _trade_decision_payload(decision: Any) -> dict[str, Any]:
    trace = decision.decision_trace
    return {
        "decision": decision.decision.value,
        "confidence": decision.confidence,
        "reason": decision.reason,
        "supporting_evidence": decision.supporting_evidence,
        "decision_trace": {
            "timestamp": trace.timestamp.isoformat(),
            "instrument": trace.instrument,
            "strategy_asset_id": trace.strategy_asset_id,
            "feature_vector_id": trace.feature_vector_id,
            "market_regime": trace.market_regime,
            "opportunity_score": trace.opportunity_score,
            "market_quality": trace.market_quality,
            "risk_state": trace.risk_state,
            "portfolio_state": trace.portfolio_state,
            "news_state": trace.news_state,
            "final_decision": trace.final_decision.value,
            "decision_confidence": trace.decision_confidence,
            "reason_codes": list(trace.reason_codes),
        },
    }


def _daily_plan_payload(plan: Any) -> dict[str, Any]:
    return {
        "trading_day": plan.trading_day,
        "preferred_sessions": [session.value for session in plan.preferred_sessions],
        "preferred_strategy_families": list(plan.preferred_strategy_families),
        "daily_risk_budget": plan.daily_risk_budget,
        "capital_allocation": plan.capital_allocation,
        "expected_regimes": list(plan.expected_regimes),
        "maximum_trades": plan.maximum_trades,
        "trading_objectives": list(plan.trading_objectives),
    }


def _timeline_event_payload(event: Any) -> dict[str, Any]:
    return {
        "timestamp": event.timestamp.isoformat(),
        "stage": event.stage,
        "status": event.status,
        "reason": event.reason,
    }


def _daily_decision_journal_payload(journal: Any) -> dict[str, Any]:
    return {
        "journal_id": journal.journal_id,
        "trading_day": journal.trading_day,
        "market_summary": journal.market_summary,
        "trading_opportunities": list(journal.trading_opportunities),
        "trades_executed": list(journal.trades_executed),
        "trades_skipped": list(journal.trades_skipped),
        "risk_summary": journal.risk_summary,
        "strategy_performance": journal.strategy_performance,
        "knowledge_updates": list(journal.knowledge_updates),
        "recommendations": list(journal.recommendations),
    }


def _decision_quality_metrics_payload(metrics: Any) -> dict[str, Any]:
    return {
        "trading_days": metrics.trading_days,
        "opportunity_days": metrics.opportunity_days,
        "no_trade_days": metrics.no_trade_days,
        "trades_avoided": metrics.trades_avoided,
        "average_opportunity_score": metrics.average_opportunity_score,
        "average_market_quality": metrics.average_market_quality,
        "average_decision_confidence": metrics.average_decision_confidence,
        "trade_acceptance_rate": metrics.trade_acceptance_rate,
        "trade_rejection_reasons": metrics.trade_rejection_reasons,
    }
