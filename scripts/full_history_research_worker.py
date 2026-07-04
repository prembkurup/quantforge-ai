from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the full-history scheduler continuously, one job at a time."
    )
    parser.add_argument("--max-jobs", type=int, default=1)
    parser.add_argument("--sleep-seconds", type=int, default=30)
    parser.add_argument("--error-sleep-seconds", type=int, default=300)
    parser.add_argument("--idle-sleep-seconds", type=int, default=900)
    parser.add_argument("--state-file", default="var/full_history_research_state.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    lock_socket = _single_instance_lock()
    if lock_socket is None:
        print("Another full-history worker is already running; exiting.")
        return

    repo_root = Path(__file__).resolve().parents[1]
    scheduler_script = repo_root / "scripts" / "full_history_research_scheduler.py"
    python_exe = repo_root / ".venv" / "Scripts" / "python.exe"
    if not python_exe.exists():
        python_exe = Path(sys.executable)

    print("Full History Research 24/7 Worker")
    print(f"Started At: {_now()}")
    print(f"Scheduler: {scheduler_script}")
    print(f"Max Jobs Per Loop: {args.max_jobs}")
    print(f"State File: {args.state_file}")
    print()
    sys.stdout.flush()

    while True:
        command = [
            str(python_exe),
            str(scheduler_script),
            "--max-jobs",
            str(args.max_jobs),
            "--state-file",
            args.state_file,
        ]
        print(f"[{_now()}] Starting one full-history scheduler loop")
        sys.stdout.flush()
        completed = subprocess.run(
            command,
            cwd=repo_root,
            check=False,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
            text=True,
        )
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
        if completed.returncode != 0:
            print(
                f"[{_now()}] Scheduler loop failed with exit code {completed.returncode}; "
                f"sleeping {args.error_sleep_seconds}s"
            )
            sys.stdout.flush()
            time.sleep(args.error_sleep_seconds)
            continue

        if "Executed This Run: 0" in completed.stdout:
            print(
                f"[{_now()}] No pending full-history jobs detected; "
                f"sleeping {args.idle_sleep_seconds}s"
            )
            sys.stdout.flush()
            time.sleep(args.idle_sleep_seconds)
            continue

        print(f"[{_now()}] Scheduler loop complete; sleeping {args.sleep_seconds}s")
        sys.stdout.flush()
        time.sleep(args.sleep_seconds)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
