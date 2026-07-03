from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RiskDecision:
    approved: bool
    reason: str
    metadata: dict[str, Any] | None = None


class RiskEngine:
    """Runs risk checks before live execution."""

    def evaluate(self, signal: dict[str, Any], account_state: dict[str, Any], rules: list[dict[str, Any]]) -> RiskDecision:
        for rule in rules:
            if rule.get("enabled") is False:
                continue
            max_units = rule.get("max_units")
            if max_units is not None and abs(float(signal.get("units", 0))) > float(max_units):
                return RiskDecision(False, f"Blocked by max_units rule: {max_units}", {"rule": rule})
        return RiskDecision(True, "Approved")

