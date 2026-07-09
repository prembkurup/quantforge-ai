from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from quantforge.config.settings import get_settings  # noqa: E402


@dataclass(frozen=True, slots=True)
class ManagedService:
    name: str
    command: tuple[str, ...]
    log_file: Path
    restart: bool = True
    cwd: Path = PROJECT_ROOT


@dataclass(slots=True)
class RunningService:
    spec: ManagedService
    process: subprocess.Popen[str]
    started_at: str
    restarts: int = 0


@dataclass(frozen=True, slots=True)
class RecurringJob:
    name: str
    command: tuple[str, ...]
    log_file: Path
    interval_seconds: int
    timeout_seconds: int = 600
    next_run_at: float = 0.0
    cwd: Path = PROJECT_ROOT


class SupervisorLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, message: str = "") -> None:
        line = message if message else ""
        print(line)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run QuantForge AI as a local 24/7 process supervisor.")
    parser.add_argument("--no-frontend", action="store_true", help="Do not start the Vite dashboard frontend.")
    parser.add_argument("--no-trading", action="store_true", help="Do not run the paper/practice-safe trading loop.")
    parser.add_argument("--trading-interval-seconds", type=int, default=60)
    parser.add_argument("--operations-interval-seconds", type=int, default=3600)
    parser.add_argument("--status-file", default="var/quantforge_247_status.json")
    parser.add_argument("--supervisor-log-file", default="var/log/quantforge-247-supervisor.log")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    _ensure_runtime_dirs()
    _write_pid()
    _validate_practice_connection()

    python = _python_exe()
    npm = _npm_command()
    env = _process_env()

    services = _services(python, npm, include_frontend=not args.no_frontend)
    jobs = _jobs(
        python,
        trading_enabled=not args.no_trading,
        trading_interval_seconds=max(args.trading_interval_seconds, 30),
        operations_interval_seconds=max(args.operations_interval_seconds, 300),
    )
    status_file = PROJECT_ROOT / args.status_file
    supervisor_log = SupervisorLog(PROJECT_ROOT / args.supervisor_log_file)

    running: dict[str, RunningService] = {}
    _install_shutdown_handlers(running, supervisor_log)

    supervisor_log.write("")
    supervisor_log.write("QuantForge AI 24/7 Supervisor")
    supervisor_log.write(f"Started At: {_now()}")
    supervisor_log.write(f"Practice URL: {get_settings().oanda_api_url}")
    supervisor_log.write(f"Trading Loop: {'ON' if not args.no_trading else 'OFF'}")
    supervisor_log.write(f"Supervisor Log: {supervisor_log.path}")
    supervisor_log.write()
    sys.stdout.flush()

    for service in services:
        running[service.name] = _start_service(service, env, supervisor_log)

    job_schedule = {job.name: time.time() for job in jobs}
    while True:
        for name, item in list(running.items()):
            if item.process.poll() is None:
                continue
            exit_code = item.process.returncode
            if not item.spec.restart:
                continue
            supervisor_log.write(f"[{_now()}] {name} exited with {exit_code}; restarting")
            sys.stdout.flush()
            running[name] = _start_service(item.spec, env, supervisor_log, restarts=item.restarts + 1)

        for job in jobs:
            next_run = job_schedule.get(job.name, 0.0)
            if time.time() < next_run:
                continue
            exit_code = _run_job(job, env)
            supervisor_log.write(f"[{_now()}] recurring job {job.name} finished with {exit_code}")
            sys.stdout.flush()
            job_schedule[job.name] = time.time() + job.interval_seconds

        _write_status(status_file, running, jobs, job_schedule, supervisor_log.path)
        time.sleep(10)


def _services(python: Path, npm: str, *, include_frontend: bool) -> tuple[ManagedService, ...]:
    services = [
        ManagedService(
            name="dashboard-api",
            command=(str(python), str(PROJECT_ROOT / "scripts" / "serve_dashboard_api.py")),
            log_file=PROJECT_ROOT / "var" / "log" / "dashboard-api.log",
        ),
        ManagedService(
            name="full-history-worker",
            command=(str(python), str(PROJECT_ROOT / "scripts" / "full_history_research_worker.py")),
            log_file=PROJECT_ROOT / "var" / "log" / "full-history-research-worker.log",
        ),
        ManagedService(
            name="historical-validation-worker",
            command=(str(python), str(PROJECT_ROOT / "scripts" / "historical_validation_worker.py")),
            log_file=PROJECT_ROOT / "var" / "log" / "historical-validation-worker.log",
        ),
        ManagedService(
            name="research-orchestrator",
            command=(str(python), str(PROJECT_ROOT / "scripts" / "always_on_research_orchestrator.py")),
            log_file=PROJECT_ROOT / "var" / "log" / "always-on-research-orchestrator.log",
        ),
    ]
    if include_frontend:
        services.insert(
            1,
            ManagedService(
                name="dashboard-frontend",
                command=(npm, "run", "dev"),
                log_file=PROJECT_ROOT / "var" / "log" / "dashboard-frontend.log",
                cwd=PROJECT_ROOT / "frontend",
            ),
        )
    return tuple(services)


def _jobs(
    python: Path,
    *,
    trading_enabled: bool,
    trading_interval_seconds: int,
    operations_interval_seconds: int,
) -> tuple[RecurringJob, ...]:
    jobs = [
        RecurringJob(
            name="intraday-start",
            command=(str(python), str(PROJECT_ROOT / "scripts" / "intraday_daily_scheduler.py"), "--mode", "start"),
            log_file=PROJECT_ROOT / "var" / "log" / "intraday-start.log",
            interval_seconds=operations_interval_seconds,
        ),
        RecurringJob(
            name="intraday-end",
            command=(str(python), str(PROJECT_ROOT / "scripts" / "intraday_daily_scheduler.py"), "--mode", "end"),
            log_file=PROJECT_ROOT / "var" / "log" / "intraday-end.log",
            interval_seconds=operations_interval_seconds,
        ),
        RecurringJob(
            name="portfolio-intelligence",
            command=(str(python), str(PROJECT_ROOT / "scripts" / "portfolio_intelligence.py")),
            log_file=PROJECT_ROOT / "var" / "log" / "portfolio-intelligence.log",
            interval_seconds=operations_interval_seconds,
        ),
        RecurringJob(
            name="performance-learning",
            command=(str(python), str(PROJECT_ROOT / "scripts" / "performance_learning.py")),
            log_file=PROJECT_ROOT / "var" / "log" / "performance-learning.log",
            interval_seconds=operations_interval_seconds,
        ),
        RecurringJob(
            name="strategy-lifecycle",
            command=(str(python), str(PROJECT_ROOT / "scripts" / "strategy_lifecycle.py")),
            log_file=PROJECT_ROOT / "var" / "log" / "strategy-lifecycle.log",
            interval_seconds=operations_interval_seconds,
        ),
    ]
    if trading_enabled:
        jobs.insert(
            0,
            RecurringJob(
                name="paper-practice-trading",
                command=(str(python), str(PROJECT_ROOT / "scripts" / "live_trading.py"), "--mode", "paper-scanner", "--once"),
                log_file=PROJECT_ROOT / "var" / "log" / "paper-practice-trading.log",
                interval_seconds=trading_interval_seconds,
            ),
        )
        jobs.insert(
            1,
            RecurringJob(
                name="replay-paper-trading",
                command=(
                    str(python),
                    str(PROJECT_ROOT / "scripts" / "auto_replay_paper_trading.py"),
                    "--timeframes",
                    os.getenv("QUANTFORGE_REPLAY_TIMEFRAMES", "M5,M15"),
                    "--max-workers",
                    os.getenv("QUANTFORGE_REPLAY_MAX_WORKERS", "3"),
                    "--max-jobs-per-run",
                    os.getenv("QUANTFORGE_REPLAY_MAX_JOBS_PER_RUN", "12"),
                    "--executor",
                    os.getenv("QUANTFORGE_REPLAY_EXECUTOR", "process"),
                ),
                log_file=PROJECT_ROOT / "var" / "log" / "replay-paper-trading.log",
                interval_seconds=max(trading_interval_seconds, 300),
                timeout_seconds=86400,
            ),
        )
    return tuple(jobs)


def _start_service(
    spec: ManagedService,
    env: dict[str, str],
    supervisor_log: SupervisorLog,
    *,
    restarts: int = 0,
) -> RunningService:
    spec.log_file.parent.mkdir(parents=True, exist_ok=True)
    handle = spec.log_file.open("a", encoding="utf-8")
    handle.write(f"\n[{_now()}] starting {spec.name}: {' '.join(spec.command)}\n")
    handle.flush()
    supervisor_log.write(f"[{_now()}] starting service {spec.name} pid=pending log={spec.log_file}")
    process = subprocess.Popen(
        spec.command,
        cwd=spec.cwd,
        env=env,
        stdout=handle,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    supervisor_log.write(f"[{_now()}] service {spec.name} started pid={process.pid}")
    return RunningService(spec=spec, process=process, started_at=_now(), restarts=restarts)


def _run_job(job: RecurringJob, env: dict[str, str]) -> int:
    job.log_file.parent.mkdir(parents=True, exist_ok=True)
    with job.log_file.open("a", encoding="utf-8") as handle:
        handle.write(f"\n[{_now()}] running {job.name}: {' '.join(job.command)}\n")
        handle.flush()
        try:
            process = subprocess.run(
                job.command,
                cwd=job.cwd,
                env=env,
                stdout=handle,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=job.timeout_seconds,
                check=False,
            )
            return process.returncode
        except subprocess.TimeoutExpired:
            handle.write(f"[{_now()}] {job.name} timed out after {job.timeout_seconds}s; it will resume on the next run.\n")
            handle.flush()
            return 124


def _validate_practice_connection() -> None:
    settings = get_settings()
    if "api-fxpractice.oanda.com" not in settings.oanda_api_url:
        raise SystemExit(
            "Refusing to start trading automation: QUANTFORGE_OANDA_API_URL is not the OANDA practice URL."
        )
    if not settings.oanda_account_id or not settings.oanda_api_token:
        raise SystemExit("Refusing to start trading automation: OANDA practice account credentials are missing.")


def _write_status(
    path: Path,
    running: dict[str, RunningService],
    jobs: tuple[RecurringJob, ...],
    schedule: dict[str, float],
    supervisor_log_file: Path,
) -> None:
    payload: dict[str, Any] = {
        "status": "RUNNING",
        "updated_at": _now(),
        "supervisor_pid": os.getpid(),
        "supervisor_log_file": str(supervisor_log_file.relative_to(PROJECT_ROOT)),
        "services": [
            {
                "name": item.spec.name,
                "pid": item.process.pid,
                "running": item.process.poll() is None,
                "started_at": item.started_at,
                "restarts": item.restarts,
                "log_file": str(item.spec.log_file.relative_to(PROJECT_ROOT)),
            }
            for item in running.values()
        ],
        "recurring_jobs": [
            {
                "name": job.name,
                "interval_seconds": job.interval_seconds,
                "timeout_seconds": job.timeout_seconds,
                "next_run_at": datetime.fromtimestamp(schedule.get(job.name, 0.0), UTC).isoformat(),
                "log_file": str(job.log_file.relative_to(PROJECT_ROOT)),
            }
            for job in jobs
        ],
        "safety": {
            "oanda_api_url": get_settings().oanda_api_url,
            "practice_only": True,
            "broker_order_execution": "disabled_by_current_live_trading_script; OANDA_PAPER path is used",
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _install_shutdown_handlers(running: dict[str, RunningService], supervisor_log: SupervisorLog) -> None:
    def shutdown(_: int, __: Any) -> None:
        supervisor_log.write(f"[{_now()}] shutdown requested; stopping {len(running)} service(s)")
        for item in running.values():
            if item.process.poll() is None:
                supervisor_log.write(f"[{_now()}] stopping service {item.spec.name} pid={item.process.pid}")
                item.process.terminate()
        supervisor_log.write(f"[{_now()}] supervisor stopped")
        raise SystemExit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)


def _write_pid() -> None:
    pid_file = PROJECT_ROOT / "var" / "quantforge_247.pid"
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()), encoding="utf-8")


def _ensure_runtime_dirs() -> None:
    (PROJECT_ROOT / "var" / "log").mkdir(parents=True, exist_ok=True)


def _process_env() -> dict[str, str]:
    env = os.environ.copy()
    backend = str(BACKEND_PATH)
    env["PYTHONPATH"] = backend + os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else backend
    env["QUANTFORGE_DASHBOARD_API_HOST"] = "0.0.0.0"
    return env


def _python_exe() -> Path:
    local_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    return local_python if local_python.exists() else Path(sys.executable)


def _npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


if __name__ == "__main__":
    main()
