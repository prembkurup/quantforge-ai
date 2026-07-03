from dataclasses import dataclass
from typing import Any

from quantforge.domain import ValidationStatus


@dataclass(frozen=True, slots=True)
class ValidationResult:
    status: ValidationStatus
    metrics: dict[str, Any]
    reason: str | None = None


class ValidationEngine:
    """Promotion gates before a strategy can trade live."""

    def evaluate(self, backtest_metrics: dict[str, Any], thresholds: dict[str, float]) -> ValidationResult:
        failures = [
            key for key, minimum in thresholds.items()
            if float(backtest_metrics.get(key, 0)) < minimum
        ]
        if failures:
            return ValidationResult(
                status=ValidationStatus.FAILED,
                metrics=backtest_metrics,
                reason=f"Failed thresholds: {', '.join(failures)}",
            )
        return ValidationResult(status=ValidationStatus.PASSED, metrics=backtest_metrics)

