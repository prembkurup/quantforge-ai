from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from quantforge.research.full_history_scheduler import FullHistoryResearchJob
from quantforge.research.strategy_assets import default_strategy_asset_repository


@dataclass(frozen=True, slots=True)
class PostFullHistoryStage:
    stage_id: str
    script: str
    description: str


@dataclass(frozen=True, slots=True)
class PostFullHistoryStageResult:
    stage_id: str
    script: str
    description: str
    status: str
    started_at: str
    completed_at: str
    return_code: int
    output_tail: str


@dataclass(frozen=True, slots=True)
class PostFullHistoryAutomationResult:
    status: str
    started_at: str
    completed_at: str
    stages: tuple[PostFullHistoryStageResult, ...]


POST_FULL_HISTORY_STAGES = (
    PostFullHistoryStage(
        "AUTONOMOUS_RESEARCH",
        "scripts/autonomous_research.py",
        "Run autonomous research, strategy publication, reports, and knowledge update.",
    ),
    PostFullHistoryStage(
        "DEPLOY_PAPER_PORTFOLIO",
        "scripts/deploy_strategy.py",
        "Build portfolio allocation and install approved strategy for paper trading.",
    ),
    PostFullHistoryStage(
        "SHADOW_TRADING_REVIEW",
        "scripts/shadow_trading.py",
        "Refresh shadow/paper trading signals, drift, audit, and promotion review.",
    ),
    PostFullHistoryStage(
        "PRODUCTION_READINESS",
        "scripts/production_readiness.py",
        "Run operations, recovery, state sync, backup, latency, and capital-protection checks.",
    ),
    PostFullHistoryStage(
        "PRODUCTION_CERTIFICATION",
        "scripts/certify_production.py",
        "Run production certification and leave live trading blocked unless explicitly authorized.",
    ),
)


def full_history_plan_exhausted(
    state_file: Path,
    planned: tuple[FullHistoryResearchJob, ...],
) -> bool:
    if not state_file.exists() or not planned:
        return False

    state = _load_json(state_file)
    completed = set(state.get("completed", []))
    failed = set(state.get("failed", []))
    if failed:
        return False
    running = state.get("running", {})
    if isinstance(running, dict) and running:
        return False

    planned_ids = {job.job_id for job in planned}
    return planned_ids <= completed


def automation_already_finished(
    state_file: Path,
    planned: tuple[FullHistoryResearchJob, ...] = (),
) -> bool:
    if not state_file.exists():
        return False
    state = _load_json(state_file)
    if state.get("status") not in {"COMPLETE", "FAILED"}:
        return False
    if not planned:
        return True
    return state.get("full_history_plan_hash") == full_history_plan_hash(planned)


def run_post_full_history_automation(
    *,
    repo_root: Path,
    state_file: Path,
    python_exe: Path,
    planned: tuple[FullHistoryResearchJob, ...] = (),
    stages: tuple[PostFullHistoryStage, ...] = POST_FULL_HISTORY_STAGES,
) -> PostFullHistoryAutomationResult:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    started_at = _now()
    plan_hash = full_history_plan_hash(planned) if planned else ""
    _write_json(
        state_file,
        {
            "full_history_plan_hash": plan_hash,
            "full_history_planned_jobs": len(planned),
            "status": "RUNNING",
            "started_at": started_at,
            "completed_at": "",
            "stages": [],
        },
    )

    results: list[PostFullHistoryStageResult] = []
    status = "COMPLETE"
    for stage in stages:
        result = _run_stage(repo_root=repo_root, python_exe=python_exe, stage=stage)
        results.append(result)
        if result.status != "COMPLETE":
            status = "FAILED"
            break
        _write_json(
            state_file,
            {
                "status": "RUNNING",
                "started_at": started_at,
                "completed_at": "",
                "full_history_plan_hash": plan_hash,
                "full_history_planned_jobs": len(planned),
                "stages": [asdict(item) for item in results],
            },
        )

    completed_at = _now()
    payload = {
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "full_history_plan_hash": plan_hash,
        "full_history_planned_jobs": len(planned),
        "stages": [asdict(item) for item in results],
    }
    _write_json(state_file, payload)
    return PostFullHistoryAutomationResult(
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        stages=tuple(results),
    )


def _run_stage(
    *,
    repo_root: Path,
    python_exe: Path,
    stage: PostFullHistoryStage,
) -> PostFullHistoryStageResult:
    started_at = _now()
    script = repo_root / stage.script
    env = dict(os.environ)
    backend_path = str(repo_root / "backend")
    env["PYTHONPATH"] = (
        backend_path
        if not env.get("PYTHONPATH")
        else backend_path + os.pathsep + str(env["PYTHONPATH"])
    )
    command = [str(python_exe), str(script)]
    if stage.stage_id == "DEPLOY_PAPER_PORTFOLIO":
        latest = _latest_approved_strategy_asset_id(repo_root)
        command.extend(["--strategy-asset-id", latest])
    process = subprocess.run(
        command,
        cwd=repo_root,
        env=env,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
        text=True,
        timeout=1800,
        check=False,
    )
    completed_at = _now()
    return PostFullHistoryStageResult(
        stage_id=stage.stage_id,
        script=stage.script,
        description=stage.description,
        status="COMPLETE" if process.returncode == 0 else "FAILED",
        started_at=started_at,
        completed_at=completed_at,
        return_code=process.returncode,
        output_tail=_tail(process.stdout),
    )


def full_history_plan_hash(planned: tuple[FullHistoryResearchJob, ...]) -> str:
    job_ids = "\n".join(job.job_id for job in planned)
    return hashlib.sha256(job_ids.encode("utf-8")).hexdigest()


def _latest_approved_strategy_asset_id(repo_root: Path) -> str:
    assets = default_strategy_asset_repository(repo_root).list()
    if not assets:
        raise RuntimeError("No persisted approved Strategy Assets are available for deployment.")
    return assets[0].strategy_asset_id


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _tail(value: str, *, lines: int = 40) -> str:
    return "\n".join(value.splitlines()[-lines:])
