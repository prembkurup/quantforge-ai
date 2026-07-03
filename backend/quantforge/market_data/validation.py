from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class MissingCandleGap:
    previous_time: datetime
    next_time: datetime
    missing_count: int


def detect_missing_candle_gaps(
    candle_times: list[datetime],
    timeframe_seconds: int,
) -> list[MissingCandleGap]:
    """Return gaps where consecutive candle times skip one or more expected slots."""
    if timeframe_seconds <= 0:
        raise ValueError("timeframe_seconds must be greater than zero.")

    ordered_times = sorted(set(candle_times))
    gaps: list[MissingCandleGap] = []
    for previous_time, next_time in zip(ordered_times, ordered_times[1:]):
        elapsed_seconds = int((next_time - previous_time).total_seconds())
        if elapsed_seconds > timeframe_seconds:
            missing_count = (elapsed_seconds // timeframe_seconds) - 1
            gaps.append(
                MissingCandleGap(
                    previous_time=previous_time,
                    next_time=next_time,
                    missing_count=missing_count,
                )
            )
    return gaps
