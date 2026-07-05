from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True, slots=True)
class ResearchProgressSnapshot:
    payload: dict[str, Any]
    generated_at: str
    source: str

    def as_payload(self) -> dict[str, Any]:
        return {
            **self.payload,
            "cache": {
                "status": "HIT",
                "generated_at": self.generated_at,
                "source": self.source,
            },
        }


class FullHistoryResearchSummaryRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> ResearchProgressSnapshot | None:
        if not self.path.exists():
            return None
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return ResearchProgressSnapshot(
            payload=dict(payload.get("payload", {})),
            generated_at=str(payload.get("generated_at", "")),
            source=str(payload.get("source", "FullHistoryResearchSummaryRepository")),
        )

    def save(self, snapshot: ResearchProgressSnapshot) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {
                    "payload": snapshot.payload,
                    "generated_at": snapshot.generated_at,
                    "source": snapshot.source,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )


class FullHistorySummaryCache:
    def __init__(self, repository: FullHistoryResearchSummaryRepository) -> None:
        self.repository = repository

    def get(self) -> dict[str, Any] | None:
        snapshot = self.repository.load()
        return snapshot.as_payload() if snapshot else None

    def set(self, payload: dict[str, Any], *, source: str) -> ResearchProgressSnapshot:
        snapshot = ResearchProgressSnapshot(payload=payload, generated_at=_now(), source=source)
        self.repository.save(snapshot)
        return snapshot


class BackgroundSummaryRefresher:
    def __init__(self, cache: FullHistorySummaryCache, builder: Callable[[], dict[str, Any]]) -> None:
        self.cache = cache
        self.builder = builder

    def refresh(self) -> dict[str, Any]:
        snapshot = self.cache.set(
            self.builder(),
            source="BackgroundSummaryRefresher",
        )
        return snapshot.as_payload()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
