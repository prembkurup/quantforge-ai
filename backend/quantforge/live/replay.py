from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from quantforge.live.engine import LiveEvent, LiveEventType


class ReplayMode(StrEnum):
    SINGLE_PAIR_SINGLE_TIMEFRAME = "SINGLE_PAIR_SINGLE_TIMEFRAME"
    MULTI_PAIR_SINGLE_TIMEFRAME = "MULTI_PAIR_SINGLE_TIMEFRAME"
    MULTI_PAIR_MULTI_TIMEFRAME = "MULTI_PAIR_MULTI_TIMEFRAME"
    FORWARD_LIVE_PAPER = "FORWARD_LIVE_PAPER"


class ReplayStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class CandleWindowRepository(Protocol):
    def load_window(
        self,
        pair_name: str,
        granularity: str,
        start: datetime,
        end: datetime,
        *,
        complete_only: bool = True,
        limit: int = 50_000,
    ) -> list[dict[str, Any]]:
        ...


@dataclass(frozen=True, slots=True)
class ReplayCursor:
    replay_id: str
    pair: str
    timeframe: str
    current_candle_time: str
    start_time: str
    end_time: str
    processed_events: int
    generated_signals: int
    paper_orders: int
    status: ReplayStatus
    last_error: str = ""
    replay_mode: str = ""
    replay_speed: str = "MAXIMUM"
    progress_percent: float = 0.0
    control: str = "IDLE"
    updated_at: str = ""


@dataclass(frozen=True, slots=True)
class ReplaySession:
    replay_id: str
    pairs: tuple[str, ...]
    timeframes: tuple[str, ...]
    start_time: datetime
    end_time: datetime
    mode: ReplayMode
    status: ReplayStatus = ReplayStatus.PENDING


class ReplayProgressStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, cursor: ReplayCursor) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(cursor)
        payload["status"] = cursor.status.value
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def load(self) -> ReplayCursor | None:
        if not self.path.exists():
            return None
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        pairs = tuple(str(payload.get("pair", "")).split(","))
        timeframes = tuple(str(payload.get("timeframe", "")).split(","))
        payload.setdefault("replay_mode", infer_replay_mode(tuple(item for item in pairs if item), tuple(item for item in timeframes if item)).value)
        payload.setdefault("replay_speed", "MAXIMUM")
        payload.setdefault("progress_percent", 0.0)
        if payload.get("status") == ReplayStatus.COMPLETE.value:
            payload["progress_percent"] = 100.0
        payload.setdefault("control", str(payload.get("status", "IDLE")))
        payload.setdefault("updated_at", "")
        return ReplayCursor(**{**payload, "status": ReplayStatus(str(payload["status"]))})


class ReplayEventFactory:
    def new_candle(self, row: dict[str, Any]) -> LiveEvent:
        close_price = float(row["close_price"])
        open_price = float(row.get("open_price") or close_price)
        trend_strength = min(0.99, max(0.0, abs(close_price - open_price) / max(abs(open_price), 0.00001) * 1000))
        return LiveEvent(
            LiveEventType.NEW_CANDLE,
            _coerce_datetime(row["time"]),
            {
                "instrument": str(row["pair_name"]),
                "timeframe": str(row["granularity"]),
                "open": open_price,
                "high": float(row.get("high_price") or close_price),
                "low": float(row.get("low_price") or close_price),
                "close": close_price,
                "volume": int(row.get("volume") or 0),
                "session": _session(_coerce_datetime(row["time"])),
                "trend_strength": max(0.72, round(trend_strength, 4)),
                "pullback_state": close_price >= open_price,
                "spread": 0.00012,
                "source": row.get("source", "candle_database"),
            },
        )


class HistoricalCandleReplayStream:
    def __init__(self, repository: CandleWindowRepository, event_factory: ReplayEventFactory | None = None) -> None:
        self.repository = repository
        self.event_factory = event_factory or ReplayEventFactory()

    def events(
        self,
        session: ReplaySession,
        *,
        progress_store: ReplayProgressStore | None = None,
        replay_speed: str = "MAXIMUM",
    ) -> tuple[LiveEvent, ...]:
        events: list[LiveEvent] = []
        for pair in session.pairs:
            for timeframe in session.timeframes:
                rows = self.repository.load_window(
                    pair,
                    timeframe,
                    session.start_time,
                    session.end_time,
                    complete_only=True,
                    limit=250_000,
                )
                events.extend(self.event_factory.new_candle(row) for row in rows)
        ordered = tuple(sorted(events, key=lambda event: event.timestamp))
        if progress_store is None:
            return ordered

        published: list[LiveEvent] = []
        previous_timestamp: datetime | None = None
        for event in ordered:
            while _control_status(progress_store) == ReplayStatus.PAUSED:
                progress_store.save(
                    replay_cursor(
                        session,
                        current_candle_time=event.timestamp.isoformat(),
                        processed_events=len(published),
                        status=ReplayStatus.PAUSED,
                        replay_speed=replay_speed,
                        control="PAUSED",
                    )
                )
                time.sleep(0.25)
            if _control_status(progress_store) == ReplayStatus.STOPPED:
                progress_store.save(
                    replay_cursor(
                        session,
                        current_candle_time=event.timestamp.isoformat(),
                        processed_events=len(published),
                        status=ReplayStatus.STOPPED,
                        replay_speed=replay_speed,
                        control="STOPPED",
                    )
                )
                break
            _sleep_for_replay_speed(previous_timestamp, event.timestamp, replay_speed)
            published.append(event)
            previous_timestamp = event.timestamp
            progress_store.save(
                replay_cursor(
                    session,
                    current_candle_time=event.timestamp.isoformat(),
                    processed_events=len(published),
                    status=ReplayStatus.RUNNING,
                    replay_speed=replay_speed,
                    control="PUBLISHING",
                )
            )
        return tuple(published)


def replay_cursor(
    session: ReplaySession,
    *,
    current_candle_time: str = "",
    processed_events: int = 0,
    generated_signals: int = 0,
    paper_orders: int = 0,
    status: ReplayStatus = ReplayStatus.RUNNING,
    last_error: str = "",
    replay_speed: str = "MAXIMUM",
    control: str = "",
) -> ReplayCursor:
    pair = ",".join(session.pairs)
    timeframe = ",".join(session.timeframes)
    progress_percent = 0.0
    if current_candle_time:
        try:
            start = session.start_time.timestamp()
            end = session.end_time.timestamp()
            current = _coerce_datetime(current_candle_time).timestamp()
            if end > start:
                progress_percent = round(max(0.0, min(100.0, ((current - start) / (end - start)) * 100.0)), 2)
        except (TypeError, ValueError):
            progress_percent = 0.0
    if status == ReplayStatus.COMPLETE:
        progress_percent = 100.0

    return ReplayCursor(
        replay_id=session.replay_id,
        pair=pair,
        timeframe=timeframe,
        current_candle_time=current_candle_time,
        start_time=session.start_time.isoformat(),
        end_time=session.end_time.isoformat(),
        processed_events=processed_events,
        generated_signals=generated_signals,
        paper_orders=paper_orders,
        status=status,
        last_error=last_error,
        replay_mode=session.mode.value,
        replay_speed=replay_speed,
        progress_percent=progress_percent,
        control=control or status.value,
        updated_at=datetime.now(UTC).isoformat(),
    )


def infer_replay_mode(pairs: tuple[str, ...], timeframes: tuple[str, ...]) -> ReplayMode:
    if len(pairs) == 1 and len(timeframes) == 1:
        return ReplayMode.SINGLE_PAIR_SINGLE_TIMEFRAME
    if len(pairs) > 1 and len(timeframes) == 1:
        return ReplayMode.MULTI_PAIR_SINGLE_TIMEFRAME
    return ReplayMode.MULTI_PAIR_MULTI_TIMEFRAME


def completed_session(session: ReplaySession) -> ReplaySession:
    return replace(session, status=ReplayStatus.COMPLETE)


def _control_status(progress_store: ReplayProgressStore) -> ReplayStatus:
    cursor = progress_store.load()
    if cursor is None:
        return ReplayStatus.RUNNING
    return cursor.status


def _sleep_for_replay_speed(previous_timestamp: datetime | None, timestamp: datetime, replay_speed: str) -> None:
    if previous_timestamp is None:
        return
    normalized = replay_speed.strip().upper()
    if normalized == "MAXIMUM":
        return
    multipliers = {
        "REAL_TIME": 1.0,
        "2X": 2.0,
        "5X": 5.0,
        "10X": 10.0,
        "100X": 100.0,
    }
    multiplier = multipliers.get(normalized, 100.0)
    delay = max(0.0, (timestamp - previous_timestamp).total_seconds() / multiplier)
    if delay:
        time.sleep(min(delay, 1.0))


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        timestamp = value
    else:
        timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC)


def _session(value: datetime) -> str:
    hour = value.hour
    if 7 <= hour < 16:
        return "London"
    if 16 <= hour < 22:
        return "NewYork"
    return "Asian"
