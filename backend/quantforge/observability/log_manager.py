from __future__ import annotations

import socket
import sys
import traceback
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, TextIO
from uuid import uuid4

from sqlalchemy import text

from quantforge.database.session import get_engine


LOG_SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS infrastructure;

CREATE TABLE IF NOT EXISTS infrastructure.process_log (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    process_name VARCHAR(160) NOT NULL,
    script_path TEXT,
    category VARCHAR(80) NOT NULL,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    host_name VARCHAR(160) NOT NULL,
    pid INTEGER NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_process_log_created
    ON infrastructure.process_log (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_process_log_process_created
    ON infrastructure.process_log (process_name, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_process_log_category_created
    ON infrastructure.process_log (category, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_process_log_level_created
    ON infrastructure.process_log (level, created_at DESC);
"""


@dataclass(frozen=True)
class ProcessLogQuery:
    page: int = 1
    page_size: int = 30
    category: str | None = None
    process: str | None = None
    level: str | None = None


def ensure_log_schema() -> None:
    with get_engine().begin() as connection:
        for statement in LOG_SCHEMA_SQL.strip().split(";"):
            sql = statement.strip()
            if sql:
                connection.execute(text(sql))


def log_event(
    process_name: str,
    category: str,
    level: str,
    message: str,
    *,
    run_id: str | None = None,
    script_path: str | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    try:
        ensure_log_schema()
        with get_engine().begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO infrastructure.process_log (
                        run_id,
                        process_name,
                        script_path,
                        category,
                        level,
                        message,
                        host_name,
                        pid,
                        metadata_json
                    )
                    VALUES (
                        :run_id,
                        :process_name,
                        :script_path,
                        :category,
                        :level,
                        :message,
                        :host_name,
                        :pid,
                        CAST(:metadata_json AS jsonb)
                    )
                    """
                ),
                {
                    "run_id": run_id or str(uuid4()),
                    "process_name": process_name,
                    "script_path": script_path,
                    "category": category,
                    "level": level.upper(),
                    "message": message[:4000],
                    "host_name": socket.gethostname(),
                    "pid": _pid(),
                    "metadata_json": _json_object(metadata),
                },
            )
    except Exception:
        return


def get_process_logs(query: ProcessLogQuery) -> dict[str, object]:
    ensure_log_schema()
    page = max(1, query.page)
    page_size = max(1, min(100, query.page_size))
    offset = (page - 1) * page_size
    where, params = _where_clause(query)
    params.update({"limit": page_size, "offset": offset})

    with get_engine().begin() as connection:
        total = connection.execute(
            text(f"SELECT COUNT(*) FROM infrastructure.process_log {where}"),
            params,
        ).scalar_one()
        rows = (
            connection.execute(
                text(
                    f"""
                    SELECT
                        id,
                        run_id::text AS run_id,
                        process_name,
                        script_path,
                        category,
                        level,
                        message,
                        host_name,
                        pid,
                        metadata_json::text AS metadata_json,
                        created_at
                    FROM infrastructure.process_log
                    {where}
                    ORDER BY created_at DESC, id DESC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                params,
            )
            .mappings()
            .all()
        )

        categories = connection.execute(
            text("SELECT DISTINCT category FROM infrastructure.process_log ORDER BY category")
        ).scalars().all()
        processes = connection.execute(
            text("SELECT DISTINCT process_name FROM infrastructure.process_log ORDER BY process_name")
        ).scalars().all()

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, (int(total) + page_size - 1) // page_size),
        "categories": list(categories),
        "processes": list(processes),
        "rows": [_serialize_row(row) for row in rows],
    }


def run_script(callback: Callable[[], None], script_path: str | Path) -> None:
    process_name = Path(script_path).stem
    with script_logging(process_name, _infer_category(process_name), script_path):
        callback()


@contextmanager
def script_logging(process_name: str, category: str, script_path: str | Path) -> Iterator[None]:
    run_id = str(uuid4())
    script = str(script_path)
    log_event(process_name, category, "INFO", "Process started", run_id=run_id, script_path=script)
    stdout = _DatabaseTee(sys.stdout, process_name, category, "INFO", run_id, script)
    stderr = _DatabaseTee(sys.stderr, process_name, category, "ERROR", run_id, script)
    original_stdout, original_stderr = sys.stdout, sys.stderr
    started = datetime.now(timezone.utc)
    try:
        sys.stdout = stdout
        sys.stderr = stderr
        yield
    except Exception as exc:
        stderr.flush()
        log_event(
            process_name,
            category,
            "ERROR",
            "".join(traceback.format_exception_only(type(exc), exc)).strip(),
            run_id=run_id,
            script_path=script,
        )
        raise
    finally:
        stdout.flush()
        stderr.flush()
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        log_event(
            process_name,
            category,
            "INFO",
            "Process finished",
            run_id=run_id,
            script_path=script,
            metadata={"elapsed_seconds": elapsed},
        )


class _DatabaseTee:
    def __init__(
        self,
        wrapped: TextIO,
        process_name: str,
        category: str,
        level: str,
        run_id: str,
        script_path: str,
    ) -> None:
        self._wrapped = wrapped
        self._process_name = process_name
        self._category = category
        self._level = level
        self._run_id = run_id
        self._script_path = script_path
        self._buffer = ""

    def write(self, value: str) -> int:
        self._wrapped.write(value)
        self._buffer += value
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._write_line(line)
        return len(value)

    def flush(self) -> None:
        self._wrapped.flush()
        if self._buffer.strip():
            self._write_line(self._buffer)
        self._buffer = ""

    def isatty(self) -> bool:
        return self._wrapped.isatty()

    @property
    def encoding(self) -> str | None:
        return self._wrapped.encoding

    def _write_line(self, line: str) -> None:
        message = line.strip()
        if not message:
            return
        log_event(
            self._process_name,
            self._category,
            self._level,
            message,
            run_id=self._run_id,
            script_path=self._script_path,
        )


def _where_clause(query: ProcessLogQuery) -> tuple[str, dict[str, object]]:
    filters = []
    params: dict[str, object] = {}
    if query.category:
        filters.append("category = :category")
        params["category"] = query.category
    if query.process:
        filters.append("process_name = :process")
        params["process"] = query.process
    if query.level:
        filters.append("level = :level")
        params["level"] = query.level.upper()
    if not filters:
        return "", params
    return "WHERE " + " AND ".join(filters), params


def _infer_category(process_name: str) -> str:
    if "dashboard" in process_name:
        return "dashboard"
    if any(token in process_name for token in ("research", "strategy", "optimize", "backtest", "pipeline")):
        return "research"
    if any(token in process_name for token in ("validate", "certify", "acceptance", "readiness")):
        return "validation"
    if any(token in process_name for token in ("live", "shadow", "deploy")):
        return "trading"
    if any(token in process_name for token in ("database", "coreui", "oanda", "ingest", "feature", "regime")):
        return "data"
    if "monday" in process_name:
        return "integration"
    if any(token in process_name for token in ("operations", "check")):
        return "operations"
    return "utility"


def _serialize_row(row: object) -> dict[str, object]:
    mapping = dict(row)
    created_at = mapping.get("created_at")
    if isinstance(created_at, datetime):
        mapping["created_at"] = created_at.isoformat()
    return mapping


def _json_object(metadata: dict[str, object] | None) -> str:
    import json

    return json.dumps(metadata or {}, default=str)


def _pid() -> int:
    import os

    return os.getpid()
