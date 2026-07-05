from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from quantforge.research.approvals import (
    ApprovalRecord,
    ApprovalRepository,
    ApprovalStatus,
    ApprovalType,
)
from quantforge.research.full_history_scheduler import (
    FULL_HISTORY_MAX_RETRIES,
    FULL_HISTORY_RETRY_DELAY_SECONDS,
    FullHistoryResearchJob,
    FullHistoryRetryDecision,
    classify_full_history_failure,
)


DEFAULT_MAX_RETRIES = FULL_HISTORY_MAX_RETRIES
DEFAULT_RETRY_DELAY_SECONDS = FULL_HISTORY_RETRY_DELAY_SECONDS


class WorkflowStatus(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_PERMANENT = "FAILED_PERMANENT"
    RETRYING = "RETRYING"
    BLOCKED = "BLOCKED"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


class WorkflowStage(StrEnum):
    PLAN_DETECTION = "PLAN_DETECTION"
    JOBS_CREATED = "JOBS_CREATED"
    FULL_HISTORY_RESEARCH = "FULL_HISTORY_RESEARCH"
    AUTONOMOUS_RESEARCH = "AUTONOMOUS_RESEARCH"
    STRATEGY_PUBLICATION = "STRATEGY_PUBLICATION"
    PAPER_PORTFOLIO_DEPLOYMENT = "PAPER_PORTFOLIO_DEPLOYMENT"
    SHADOW_TRADING_REVIEW = "SHADOW_TRADING_REVIEW"
    PRODUCTION_READINESS = "PRODUCTION_READINESS"
    PRODUCTION_CERTIFICATION = "PRODUCTION_CERTIFICATION"
    MANUAL_APPROVAL = "MANUAL_APPROVAL"
    LIVE_TRADING_GATE = "LIVE_TRADING_GATE"


class WorkflowEventType(StrEnum):
    WORKFLOW_CREATED = "WORKFLOW_CREATED"
    WORKFLOW_UPDATED = "WORKFLOW_UPDATED"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    TASK_RETRY_SCHEDULED = "TASK_RETRY_SCHEDULED"
    STAGE_COMPLETED = "STAGE_COMPLETED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    LIVE_TRADING_BLOCKED = "LIVE_TRADING_BLOCKED"


@dataclass(frozen=True, slots=True)
class WorkflowPaths:
    state_file: Path
    events_file: Path
    full_history_state_file: Path
    post_pipeline_state_file: Path
    approval_file: Path


@dataclass(frozen=True, slots=True)
class WorkflowApproval:
    approval_id: str
    workflow_id: str
    stage: str
    approval_type: str
    requested_at: str
    requested_by: str
    status: str
    approved_by: str = ""
    approved_at: str = ""
    rejected_by: str = ""
    rejected_at: str = ""
    reason: str = "Manual approval required before live trading."


class WorkflowStateRepository:
    def __init__(self, paths: WorkflowPaths) -> None:
        self.paths = paths

    def load_state(self) -> dict[str, Any]:
        return _load_json(self.paths.state_file)

    def load_events(self, *, limit: int = 200) -> list[dict[str, Any]]:
        if not self.paths.events_file.exists():
            return []
        rows = [
            json.loads(line)
            for line in self.paths.events_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return rows[-limit:]

    def save_state(self, snapshot: dict[str, Any]) -> None:
        self.paths.state_file.parent.mkdir(parents=True, exist_ok=True)
        previous = self.load_state()
        self.paths.state_file.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
        for event in _events_for_change(previous, snapshot):
            self.append_event(event)

    def append_event(self, event: dict[str, Any]) -> None:
        self.paths.events_file.parent.mkdir(parents=True, exist_ok=True)
        with self.paths.events_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")


class WorkflowRetryManager:
    def status_for_failure(self, error_message: str, attempt: int) -> str:
        if classify_full_history_failure(error_message, attempt) == FullHistoryRetryDecision.RETRYABLE:
            return WorkflowStatus.FAILED_RETRYABLE.value
        return WorkflowStatus.FAILED_PERMANENT.value


class WorkflowApprovalGate:
    def __init__(self, approval_file: Path) -> None:
        self.approval_file = approval_file
        self.repository = ApprovalRepository(approval_file)

    def approval(self, workflow_id: str, *, certification_complete: bool) -> WorkflowApproval:
        requested_at = _now() if certification_complete else ""
        status = ApprovalStatus.WAITING.value if certification_complete else ApprovalStatus.NOT_REQUIRED.value
        approval = WorkflowApproval(
            approval_id=f"APPROVAL-{workflow_id}",
            workflow_id=workflow_id,
            stage=WorkflowStage.MANUAL_APPROVAL.value,
            approval_type=ApprovalType.LIVE_TRADING_APPROVAL.value,
            requested_at=requested_at,
            requested_by="workflow_orchestrator",
            status=status,
        )
        stored = self.repository.load()
        if stored and stored.workflow_id == workflow_id:
            return _approval_record_to_workflow_approval(stored)
        if certification_complete:
            self.repository.save(
                ApprovalRecord(
                    approval_id=approval.approval_id,
                    workflow_id=approval.workflow_id,
                    approval_type=approval.approval_type,
                    stage=approval.stage,
                    requested_at=approval.requested_at,
                    requested_by=approval.requested_by,
                    status=approval.status,
                    reason=approval.reason,
                    trace_id=workflow_id,
                )
            )
        return approval

    def live_trading_status(self, approval: WorkflowApproval) -> str:
        if approval.status == ApprovalStatus.APPROVED.value:
            return "APPROVED_NOT_STARTED"
        if approval.status == ApprovalStatus.WAITING.value:
            return "WAITING_APPROVAL"
        return "BLOCKED_BY_POLICY"


class WorkflowDependencyResolver:
    def full_history_dependencies(self, job: FullHistoryResearchJob) -> list[str]:
        if job.stage.value == "COVERAGE":
            return []
        if job.stage.value == "SMOKE":
            return [_logical_task_id(job.pair, job.timeframe, "COVERAGE")]
        if job.stage.value == "ROLLING_YEAR":
            return [_logical_task_id(job.pair, job.timeframe, "SMOKE")]
        if job.stage.value == "FULL_HISTORY":
            return [_logical_task_id(job.pair, job.timeframe, "ROLLING_YEAR")]
        return []


class WorkflowPlanner:
    def __init__(self) -> None:
        self.retry_manager = WorkflowRetryManager()
        self.resolver = WorkflowDependencyResolver()

    def full_history_tasks(
        self,
        *,
        workflow_id: str,
        planned: tuple[FullHistoryResearchJob, ...],
        state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        history = [item for item in state.get("history", []) if isinstance(item, dict)]
        history_by_id = {str(item.get("job_id", "")): item for item in history}
        attempts_by_id: dict[str, int] = {}
        for item in history:
            job_id = str(item.get("job_id", ""))
            attempts_by_id[job_id] = attempts_by_id.get(job_id, 0) + 1
        completed = set(state.get("completed", []))
        failed = set(state.get("failed", []))
        running = set((state.get("running") or {}).keys())
        rows: list[dict[str, Any]] = []
        for job in planned:
            history_item = history_by_id.get(job.job_id, {})
            error = str(history_item.get("evidence", ""))
            attempt = max(1, attempts_by_id.get(job.job_id, 0))
            if job.job_id in completed:
                status = WorkflowStatus.COMPLETE.value
                waiting = ""
                next_action = "Task complete."
            elif job.job_id in failed:
                status = self.retry_manager.status_for_failure(error, attempt)
                waiting = "Waiting for retry policy." if status == WorkflowStatus.FAILED_RETRYABLE else "Blocked by permanent failure."
                next_action = "Retry task." if status == WorkflowStatus.FAILED_RETRYABLE else "Review permanent failure."
            elif job.job_id in running:
                status = WorkflowStatus.RUNNING.value
                waiting = ""
                next_action = "Continue full-history jobs."
            else:
                status = WorkflowStatus.PENDING.value
                waiting = "Waiting for dependency or worker claim."
                next_action = "Wait for scheduler claim."
            rows.append(
                {
                    "task_id": job.job_id,
                    "workflow_id": workflow_id,
                    "stage": WorkflowStage.FULL_HISTORY_RESEARCH.value,
                    "name": f"{job.pair} {job.timeframe} {job.stage.value}",
                    "task_type": job.stage.value,
                    "pair": job.pair,
                    "timeframe": job.timeframe,
                    "status": status,
                    "trigger": "full_history_research_worker.py",
                    "depends_on": self.resolver.full_history_dependencies(job),
                    "attempt": attempt,
                    "max_retries": DEFAULT_MAX_RETRIES,
                    "retry_delay_seconds": DEFAULT_RETRY_DELAY_SECONDS,
                    "started_at": str((state.get("running") or {}).get(job.job_id, {}).get("claimed_at", "")),
                    "finished_at": str(history_item.get("recorded_at", "")),
                    "error_message": error if "FAILED" in status else "",
                    "waiting_reason": waiting,
                    "next_action": next_action,
                    "output_path": str(history_item.get("output_path", "")),
                    "approval_required": False,
                }
            )
        return rows

    def post_pipeline_tasks(
        self,
        *,
        workflow_id: str,
        full_history_complete: bool,
        post_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        stage_map = {str(item.get("stage_id", "")): item for item in post_state.get("stages", []) if isinstance(item, dict)}
        definitions = (
            (
                "AUTONOMOUS_RESEARCH",
                "AUTONOMOUS_RESEARCH",
                WorkflowStage.AUTONOMOUS_RESEARCH.value,
                "autonomous_research.py",
                "FULL_HISTORY_RESEARCH",
            ),
            (
                "STRATEGY_PUBLICATION",
                "AUTONOMOUS_RESEARCH",
                WorkflowStage.STRATEGY_PUBLICATION.value,
                "autonomous_research.py",
                "AUTONOMOUS_RESEARCH",
            ),
            (
                "DEPLOY_PAPER_PORTFOLIO",
                "DEPLOY_PAPER_PORTFOLIO",
                WorkflowStage.PAPER_PORTFOLIO_DEPLOYMENT.value,
                "deploy_strategy.py",
                "STRATEGY_PUBLICATION",
            ),
            (
                "SHADOW_TRADING_REVIEW",
                "SHADOW_TRADING_REVIEW",
                WorkflowStage.SHADOW_TRADING_REVIEW.value,
                "shadow_trading.py",
                "DEPLOY_PAPER_PORTFOLIO",
            ),
            (
                "PRODUCTION_READINESS",
                "PRODUCTION_READINESS",
                WorkflowStage.PRODUCTION_READINESS.value,
                "production_readiness.py",
                "SHADOW_TRADING_REVIEW",
            ),
            (
                "PRODUCTION_CERTIFICATION",
                "PRODUCTION_CERTIFICATION",
                WorkflowStage.PRODUCTION_CERTIFICATION.value,
                "certify_production.py",
                "PRODUCTION_READINESS",
            ),
        )
        previous_complete = full_history_complete
        rows: list[dict[str, Any]] = []
        for task_id, source_stage_id, stage, script, dependency in definitions:
            source = stage_map.get(source_stage_id, {})
            source_status = str(source.get("status", ""))
            if not previous_complete:
                status = WorkflowStatus.BLOCKED.value
                waiting = _waiting_reason_for_dependency(dependency)
                next_action = "Wait for upstream stage."
            elif source_status == "COMPLETE":
                status = WorkflowStatus.COMPLETE.value
                waiting = ""
                next_action = "Task complete."
                previous_complete = True
            elif source_status == "FAILED":
                status = WorkflowStatus.FAILED_RETRYABLE.value
                waiting = "Waiting for retry policy."
                next_action = "Retry task."
                previous_complete = False
            elif previous_complete and post_state.get("status") == "RUNNING":
                status = WorkflowStatus.READY.value
                waiting = ""
                next_action = f"Run {script}."
                previous_complete = False
            elif previous_complete:
                status = WorkflowStatus.READY.value
                waiting = ""
                next_action = f"Run {script}."
                previous_complete = False
            rows.append(
                {
                    "task_id": task_id,
                    "workflow_id": workflow_id,
                    "stage": stage,
                    "name": task_id.replace("_", " ").title(),
                    "task_type": task_id,
                    "pair": "",
                    "timeframe": "",
                    "status": status,
                    "trigger": script,
                    "depends_on": [dependency],
                    "attempt": 1,
                    "max_retries": DEFAULT_MAX_RETRIES,
                    "retry_delay_seconds": DEFAULT_RETRY_DELAY_SECONDS,
                    "started_at": str(source.get("started_at", "")),
                    "finished_at": str(source.get("completed_at", "")),
                    "error_message": str(source.get("output_tail", "")) if "FAILED" in status else "",
                    "waiting_reason": waiting,
                    "next_action": next_action,
                    "output_path": "var/post_full_history_pipeline_state.json",
                    "approval_required": False,
                }
            )
        return rows


class WorkflowStateMachine:
    def current_stage(self, tasks: list[dict[str, Any]], approval: WorkflowApproval) -> str:
        if any(task["stage"] == WorkflowStage.FULL_HISTORY_RESEARCH.value and task["status"] == WorkflowStatus.RUNNING.value for task in tasks):
            return "FULL_HISTORY_RUNNING"
        if any(task["stage"] == WorkflowStage.FULL_HISTORY_RESEARCH.value and task["status"] in {WorkflowStatus.PENDING.value, WorkflowStatus.READY.value} for task in tasks):
            return "FULL_HISTORY_RUNNING"
        if any(task["stage"] == WorkflowStage.FULL_HISTORY_RESEARCH.value and "FAILED" in task["status"] for task in tasks):
            return "FULL_HISTORY_BLOCKED"
        for stage in (
            WorkflowStage.AUTONOMOUS_RESEARCH,
            WorkflowStage.PAPER_PORTFOLIO_DEPLOYMENT,
            WorkflowStage.SHADOW_TRADING_REVIEW,
            WorkflowStage.PRODUCTION_READINESS,
            WorkflowStage.PRODUCTION_CERTIFICATION,
        ):
            if any(task["stage"] == stage.value and task["status"] in {WorkflowStatus.READY.value, WorkflowStatus.RUNNING.value} for task in tasks):
                return stage.value + "_RUNNING"
        if approval.status == ApprovalStatus.WAITING.value:
            return "WAITING_FOR_MANUAL_APPROVAL"
        if approval.status == ApprovalStatus.APPROVED.value:
            return "LIVE_TRADING_GATE"
        return "LIVE_TRADING_BLOCKED"

    def run_status(self, tasks: list[dict[str, Any]], approval: WorkflowApproval) -> str:
        if any(task["status"] == WorkflowStatus.RUNNING.value for task in tasks):
            return WorkflowStatus.RUNNING.value
        if any(
            task["stage"] == WorkflowStage.FULL_HISTORY_RESEARCH.value
            and task["status"] in {WorkflowStatus.PENDING.value, WorkflowStatus.READY.value}
            for task in tasks
        ):
            return WorkflowStatus.RUNNING.value
        if approval.status == ApprovalStatus.WAITING.value:
            return WorkflowStatus.WAITING_APPROVAL.value
        if any(task["status"] in {WorkflowStatus.FAILED_PERMANENT.value, WorkflowStatus.BLOCKED.value} for task in tasks):
            return WorkflowStatus.BLOCKED.value
        return WorkflowStatus.COMPLETE.value


class WorkflowOrchestrator:
    def __init__(self, paths: WorkflowPaths) -> None:
        self.paths = paths
        self.repository = WorkflowStateRepository(paths)
        self.planner = WorkflowPlanner()
        self.state_machine = WorkflowStateMachine()
        self.approval_gate = WorkflowApprovalGate(paths.approval_file)

    def current(self, planned: tuple[FullHistoryResearchJob, ...]) -> dict[str, Any]:
        now = _now()
        plan_hash = full_history_plan_hash(planned)
        workflow_id = f"WF-FULL-HISTORY-{plan_hash[:12]}"
        full_state = _load_json(self.paths.full_history_state_file)
        post_state = _load_json(self.paths.post_pipeline_state_file)
        tasks = self.planner.full_history_tasks(workflow_id=workflow_id, planned=planned, state=full_state)
        full_history_complete = _all_full_history_finished(tasks)
        tasks += self.planner.post_pipeline_tasks(
            workflow_id=workflow_id,
            full_history_complete=full_history_complete,
            post_state=post_state,
        )
        certification_complete = any(
            task["task_id"] == "PRODUCTION_CERTIFICATION" and task["status"] == WorkflowStatus.COMPLETE.value
            for task in tasks
        )
        approval = self.approval_gate.approval(workflow_id, certification_complete=certification_complete)
        tasks += _approval_tasks(workflow_id, approval)
        current_stage = self.state_machine.current_stage(tasks, approval)
        status = self.state_machine.run_status(tasks, approval)
        run = _workflow_run(
            workflow_id=workflow_id,
            plan_hash=plan_hash,
            status=status,
            current_stage=current_stage,
            created_at=str(full_state.get("created_at", "")) or now,
            tasks=tasks,
            approval=approval,
        )
        stages = _workflow_stages(workflow_id, tasks, run)
        approvals = [asdict(approval)]
        events = self.repository.load_events()
        snapshot = {
            "run": run,
            "stages": stages,
            "tasks": tasks,
            "events": events,
            "approvals": approvals,
            "live_gate": {
                "status": run["live_trading_status"],
                "reason": _live_gate_reason(approval),
            },
            "source": "WorkflowOrchestrator + full-history/post-pipeline state",
            "timestamp": now,
        }
        self.repository.save_state(snapshot)
        snapshot["events"] = self.repository.load_events()
        return snapshot


def default_workflow_paths(repo_root: Path) -> WorkflowPaths:
    return WorkflowPaths(
        state_file=repo_root / "var" / "workflow_state.json",
        events_file=repo_root / "var" / "workflow_events.jsonl",
        full_history_state_file=repo_root / "var" / "full_history_research_state.json",
        post_pipeline_state_file=repo_root / "var" / "post_full_history_pipeline_state.json",
        approval_file=repo_root / "var" / "workflow_live_approval.json",
    )


def full_history_plan_hash(planned: tuple[FullHistoryResearchJob, ...]) -> str:
    job_ids = "\n".join(job.job_id for job in planned)
    return hashlib.sha256(job_ids.encode("utf-8")).hexdigest()


def _workflow_run(
    *,
    workflow_id: str,
    plan_hash: str,
    status: str,
    current_stage: str,
    created_at: str,
    tasks: list[dict[str, Any]],
    approval: WorkflowApproval,
) -> dict[str, Any]:
    completed = sum(1 for task in tasks if task["status"] == WorkflowStatus.COMPLETE.value)
    failed = sum(1 for task in tasks if "FAILED" in task["status"])
    running = sum(1 for task in tasks if task["status"] == WorkflowStatus.RUNNING.value)
    blocked = sum(1 for task in tasks if task["status"] in {WorkflowStatus.BLOCKED.value, WorkflowStatus.WAITING_APPROVAL.value})
    retryable = sum(1 for task in tasks if task["status"] == WorkflowStatus.FAILED_RETRYABLE.value)
    return {
        "workflow_id": workflow_id,
        "name": "Full History Research Plan",
        "plan_hash": plan_hash,
        "status": status,
        "current_stage": current_stage,
        "created_at": created_at,
        "started_at": created_at,
        "completed_at": "" if status != WorkflowStatus.COMPLETE.value else _now(),
        "total_tasks": len(tasks),
        "completed_tasks": completed,
        "failed_tasks": failed,
        "retryable_tasks": retryable,
        "running_tasks": running,
        "blocked_tasks": blocked,
        "next_action": _next_action(tasks, approval),
        "live_trading_status": _live_trading_status(approval),
    }


def _workflow_stages(workflow_id: str, tasks: list[dict[str, Any]], run: dict[str, Any]) -> list[dict[str, Any]]:
    stages: list[dict[str, Any]] = []
    for stage in WorkflowStage:
        stage_tasks = [task for task in tasks if task["stage"] == stage.value]
        if not stage_tasks:
            status = (
                WorkflowStatus.COMPLETE.value
                if stage in {WorkflowStage.PLAN_DETECTION, WorkflowStage.JOBS_CREATED}
                else WorkflowStatus.PENDING.value
            )
            progress = 100 if status == WorkflowStatus.COMPLETE.value else 0
            waiting = ""
        else:
            complete = sum(1 for task in stage_tasks if task["status"] == WorkflowStatus.COMPLETE.value)
            progress = round((complete / len(stage_tasks)) * 100)
            status = _stage_status(stage_tasks)
            waiting = next((str(task["waiting_reason"]) for task in stage_tasks if task["waiting_reason"]), "")
        stages.append(
            {
                "stage_id": stage.value,
                "workflow_id": workflow_id,
                "name": stage.value.replace("_", " ").title(),
                "status": status,
                "started_at": run["started_at"] if status in {WorkflowStatus.RUNNING.value, WorkflowStatus.COMPLETE.value} else "",
                "completed_at": run["completed_at"] if status == WorkflowStatus.COMPLETE.value else "",
                "progress_percent": progress,
                "waiting_reason": waiting,
                "blocker_summary": waiting,
            }
        )
    return stages


def _stage_status(tasks: list[dict[str, Any]]) -> str:
    statuses = {str(task["status"]) for task in tasks}
    if WorkflowStatus.RUNNING.value in statuses:
        return WorkflowStatus.RUNNING.value
    if WorkflowStatus.WAITING_APPROVAL.value in statuses:
        return WorkflowStatus.WAITING_APPROVAL.value
    if WorkflowStatus.BLOCKED.value in statuses:
        return WorkflowStatus.BLOCKED.value
    if any("FAILED" in status for status in statuses):
        return WorkflowStatus.FAILED.value
    if statuses == {WorkflowStatus.COMPLETE.value}:
        return WorkflowStatus.COMPLETE.value
    if WorkflowStatus.READY.value in statuses:
        return WorkflowStatus.READY.value
    return WorkflowStatus.PENDING.value


def _approval_tasks(workflow_id: str, approval: WorkflowApproval) -> list[dict[str, Any]]:
    if approval.status == ApprovalStatus.APPROVED.value:
        manual_status = WorkflowStatus.COMPLETE.value
        live_status = WorkflowStatus.READY.value
        manual_waiting = ""
        live_waiting = "Manual approval recorded; live trading has not been started."
    elif approval.status == ApprovalStatus.WAITING.value:
        manual_status = WorkflowStatus.WAITING_APPROVAL.value
        live_status = WorkflowStatus.BLOCKED.value
        manual_waiting = "Waiting for manual approval"
        live_waiting = "Manual approval required"
    elif approval.status == ApprovalStatus.REJECTED.value:
        manual_status = WorkflowStatus.BLOCKED.value
        live_status = WorkflowStatus.BLOCKED.value
        manual_waiting = "Manual approval was rejected"
        live_waiting = "Live trading blocked by rejected approval"
    else:
        manual_status = WorkflowStatus.BLOCKED.value
        live_status = WorkflowStatus.BLOCKED.value
        manual_waiting = "Waiting for production certification"
        live_waiting = "Live trading blocked by policy"
    return [
        _control_task(
            workflow_id,
            "MANUAL_APPROVAL_GATE",
            WorkflowStage.MANUAL_APPROVAL.value,
            manual_status,
            manual_waiting,
        ),
        _control_task(
            workflow_id,
            "LIVE_TRADING_GATE",
            WorkflowStage.LIVE_TRADING_GATE.value,
            live_status,
            live_waiting,
        ),
    ]


def _control_task(workflow_id: str, task_id: str, stage: str, status: str, waiting_reason: str) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "workflow_id": workflow_id,
        "stage": stage,
        "name": task_id.replace("_", " ").title(),
        "task_type": task_id,
        "pair": "",
        "timeframe": "",
        "status": status,
        "trigger": "WorkflowApprovalGate",
        "depends_on": ["PRODUCTION_CERTIFICATION"] if task_id == "MANUAL_APPROVAL_GATE" else ["MANUAL_APPROVAL_GATE"],
        "attempt": 1,
        "max_retries": 0,
        "retry_delay_seconds": 0,
        "started_at": "",
        "finished_at": "",
        "error_message": "",
        "waiting_reason": waiting_reason,
        "next_action": "Manual approval required." if task_id == "MANUAL_APPROVAL_GATE" else "Keep live trading blocked.",
        "output_path": "var/workflow_live_approval.json",
        "approval_required": True,
    }


def _logical_task_id(pair: str, timeframe: str, task_type: str) -> str:
    return f"{task_type}:{pair}:{timeframe}"


def _all_full_history_finished(tasks: list[dict[str, Any]]) -> bool:
    full_history_tasks = [task for task in tasks if task["stage"] == WorkflowStage.FULL_HISTORY_RESEARCH.value]
    return bool(full_history_tasks) and all(task["status"] == WorkflowStatus.COMPLETE.value for task in full_history_tasks)


def _waiting_reason_for_dependency(dependency: str) -> str:
    return {
        "FULL_HISTORY_RESEARCH": "Waiting for full-history jobs to complete",
        "AUTONOMOUS_RESEARCH": "Waiting for strategy assets",
        "STRATEGY_PUBLICATION": "Waiting for strategy assets",
        "DEPLOY_PAPER_PORTFOLIO": "Waiting for paper portfolio deployment",
        "SHADOW_TRADING_REVIEW": "Waiting for shadow review complete",
        "PRODUCTION_READINESS": "Waiting for production readiness",
        "PRODUCTION_CERTIFICATION": "Waiting for production certification",
    }.get(dependency, "Waiting for upstream dependency")


def _next_action(tasks: list[dict[str, Any]], approval: WorkflowApproval) -> str:
    if any(
        task["stage"] == WorkflowStage.FULL_HISTORY_RESEARCH.value
        and task["status"] in {WorkflowStatus.PENDING.value, WorkflowStatus.RUNNING.value}
        for task in tasks
    ):
        return "Continue full-history jobs"
    retryable = next((task for task in tasks if task["status"] == WorkflowStatus.FAILED_RETRYABLE.value), None)
    if retryable:
        return f"Retry {retryable['task_id']}"
    permanent = next((task for task in tasks if task["status"] == WorkflowStatus.FAILED_PERMANENT.value), None)
    if permanent:
        return f"Review permanent failure {permanent['task_id']}"
    ready = next((task for task in tasks if task["status"] == WorkflowStatus.READY.value), None)
    if ready:
        return str(ready["next_action"])
    if approval.status == ApprovalStatus.APPROVED.value:
        return "Live trading approved but not started"
    if approval.status == ApprovalStatus.WAITING.value:
        return "Manual approval required before live trading"
    if approval.status == ApprovalStatus.REJECTED.value:
        return "Live trading blocked by rejected manual approval"
    return "Live trading blocked by policy"


def _live_trading_status(approval: WorkflowApproval) -> str:
    if approval.status == ApprovalStatus.APPROVED.value:
        return "APPROVED_NOT_STARTED"
    if approval.status == ApprovalStatus.WAITING.value:
        return "WAITING_APPROVAL"
    return "BLOCKED_BY_POLICY"


def _live_gate_reason(approval: WorkflowApproval) -> str:
    if approval.status == ApprovalStatus.APPROVED.value:
        return "Manual approval recorded; live trading not started"
    if approval.status == ApprovalStatus.WAITING.value:
        return "Manual approval required"
    if approval.status == ApprovalStatus.REJECTED.value:
        return "Manual approval rejected"
    return "Live trading blocked by policy"


def _approval_record_to_workflow_approval(record: ApprovalRecord) -> WorkflowApproval:
    return WorkflowApproval(
        approval_id=record.approval_id,
        workflow_id=record.workflow_id,
        stage=record.stage,
        approval_type=record.approval_type,
        requested_at=record.requested_at,
        requested_by=record.requested_by,
        status=record.status,
        approved_by=record.approved_by,
        approved_at=record.approved_at,
        rejected_by=record.rejected_by,
        rejected_at=record.rejected_at,
        reason=record.reason,
    )


def _events_for_change(previous: dict[str, Any], snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    run = snapshot["run"]
    previous_run = previous.get("run", {}) if previous else {}
    events: list[dict[str, Any]] = []
    if not previous:
        events.append(_event(run, WorkflowEventType.WORKFLOW_CREATED, "", run["status"], "Workflow run created."))
        events.append(_event(run, WorkflowEventType.LIVE_TRADING_BLOCKED, "", run["live_trading_status"], "Live trading blocked by policy."))
    elif (
        previous_run.get("current_stage") != run["current_stage"]
        or previous_run.get("status") != run["status"]
        or previous_run.get("completed_tasks") != run["completed_tasks"]
        or previous_run.get("failed_tasks") != run["failed_tasks"]
        or previous_run.get("running_tasks") != run["running_tasks"]
    ):
        events.append(
            _event(
                run,
                WorkflowEventType.WORKFLOW_UPDATED,
                str(previous_run.get("status", "")),
                run["status"],
                f"Workflow moved to {run['current_stage']}.",
            )
        )
    return events


def _event(run: dict[str, Any], event_type: WorkflowEventType, old_status: str, new_status: str, message: str) -> dict[str, Any]:
    return {
        "event_id": str(uuid4()),
        "workflow_id": run["workflow_id"],
        "task_id": "",
        "stage": run["current_stage"],
        "event_type": event_type.value,
        "old_status": old_status,
        "new_status": new_status,
        "message": message,
        "timestamp": _now(),
        "trace_id": run["plan_hash"][:12],
        "metadata": {"next_action": run["next_action"]},
    }


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
