from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
from datetime import date, datetime, time as datetime_time, timedelta, timezone
from pathlib import Path

from quantforge.research.full_history_scheduler import (
    FULL_HISTORY_RESEARCH_PAIRS,
    FULL_HISTORY_RESEARCH_START,
    FULL_HISTORY_RESEARCH_TIMEFRAMES,
    FullHistoryResearchScheduler,
    FullHistorySchedulerConfig,
    claim_pending_jobs,
    release_running_jobs,
)
from quantforge.research.post_full_history_automation import (
    automation_already_finished,
    full_history_plan_exhausted,
    run_post_full_history_automation,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the full-history scheduler continuously, one job at a time."
    )
    parser.add_argument("--max-jobs", type=int, default=1)
    parser.add_argument("--sleep-seconds", type=int, default=30)
    parser.add_argument("--error-sleep-seconds", type=int, default=300)
    parser.add_argument("--idle-sleep-seconds", type=int, default=900)
    parser.add_argument("--running-stale-seconds", type=int, default=21600)
    parser.add_argument("--state-file", default="var/full_history_research_state.json")
    parser.add_argument("--post-pipeline-state-file", default="var/post_full_history_pipeline_state.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    lock_socket = _single_instance_lock()
    if lock_socket is None:
        print("Another full-history worker is already running; exiting.")
        return

    repo_root = Path(__file__).resolve().parents[1]
    scheduler_script = repo_root / "scripts" / "full_history_research_scheduler.py"
    state_file = repo_root / args.state_file
    post_pipeline_state_file = repo_root / args.post_pipeline_state_file
    python_exe = repo_root / ".venv" / "Scripts" / "python.exe"
    if not python_exe.exists():
        python_exe = Path(sys.executable)
    scheduler = FullHistoryResearchScheduler(
        config=_scheduler_config(),
        state_file=state_file,
        repository_factory=lambda: None,
    )

    print("Full History Research 24/7 Worker")
    print(f"Started At: {_now()}")
    print(f"Scheduler: {scheduler_script}")
    print(f"Max Jobs Per Loop: {args.max_jobs}")
    print(f"State File: {args.state_file}")
    print()
    sys.stdout.flush()

    while True:
        owner = f"{socket.gethostname()}:{_now()}"
        jobs = claim_pending_jobs(
            state_file,
            scheduler.plan(),
            limit=args.max_jobs,
            owner=owner,
            stale_after_seconds=args.running_stale_seconds,
        )
        if not jobs:
            _run_post_pipeline_if_ready(
                scheduler=scheduler,
                full_history_state_file=state_file,
                post_pipeline_state_file=post_pipeline_state_file,
                repo_root=repo_root,
                python_exe=python_exe,
            )
            print(
                f"[{_now()}] No pending full-history jobs detected; "
                f"sleeping {args.idle_sleep_seconds}s"
            )
            sys.stdout.flush()
            time.sleep(args.idle_sleep_seconds)
            continue

        print(f"[{_now()}] Starting {len(jobs)} parallel full-history scheduler job(s)")
        sys.stdout.flush()
        processes: list[tuple[str, subprocess.Popen[str]]] = []
        for job in jobs:
            command = [
                str(python_exe),
                str(scheduler_script),
                "--job-id",
                job.job_id,
                "--state-file",
                args.state_file,
            ]
            processes.append(
                (
                    job.job_id,
                    subprocess.Popen(
                        command,
                        cwd=repo_root,
                        stderr=subprocess.STDOUT,
                        stdout=subprocess.PIPE,
                        text=True,
                    ),
                )
            )

        failures: list[str] = []
        for job_id, process in processes:
            stdout, _ = process.communicate()
            print(stdout, end="" if stdout.endswith("\n") else "\n")
            if process.returncode != 0:
                failures.append(job_id)

        if failures:
            release_running_jobs(state_file, tuple(failures))
            print(
                f"[{_now()}] {len(failures)} scheduler job(s) failed at process level; "
                f"sleeping {args.error_sleep_seconds}s"
            )
            sys.stdout.flush()
            time.sleep(args.error_sleep_seconds)
            continue

        print(
            f"[{_now()}] Parallel scheduler loop complete; "
            f"executed {len(jobs)} job(s); sleeping {args.sleep_seconds}s"
        )
        sys.stdout.flush()
        time.sleep(args.sleep_seconds)


def _run_post_pipeline_if_ready(
    *,
    scheduler: FullHistoryResearchScheduler,
    full_history_state_file: Path,
    post_pipeline_state_file: Path,
    repo_root: Path,
    python_exe: Path,
) -> None:
    planned = scheduler.plan()
    if not full_history_plan_exhausted(full_history_state_file, planned):
        return
    if automation_already_finished(post_pipeline_state_file, planned):
        return

    print(f"[{_now()}] Full-history plan exhausted; starting post-full-history automation")
    sys.stdout.flush()
    result = run_post_full_history_automation(
        repo_root=repo_root,
        state_file=post_pipeline_state_file,
        python_exe=python_exe,
        planned=planned,
    )
    print(f"[{_now()}] Post-full-history automation finished with status {result.status}")
    for stage in result.stages:
        print(f"- {stage.stage_id} {stage.status}")
    sys.stdout.flush()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _scheduler_config() -> FullHistorySchedulerConfig:
    return FullHistorySchedulerConfig(
        pairs=FULL_HISTORY_RESEARCH_PAIRS,
        timeframes=FULL_HISTORY_RESEARCH_TIMEFRAMES,
        start=FULL_HISTORY_RESEARCH_START,
        end=datetime.combine(date.today(), datetime_time.min, tzinfo=timezone.utc)
        + timedelta(days=1),
    )


def _single_instance_lock() -> socket.socket | None:
    lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock_socket.bind(("127.0.0.1", 48271))
        lock_socket.listen(1)
    except OSError:
        lock_socket.close()
        return None
    return lock_socket


if __name__ == "__main__":
    main()
