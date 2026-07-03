from typing import Any, Callable


class OptimizationEngine:
    """Searches candidate parameters using a caller-provided objective."""

    def maximize(
        self,
        candidates: list[dict[str, Any]],
        objective: Callable[[dict[str, Any]], float],
    ) -> dict[str, Any] | None:
        if not candidates:
            return None
        return max(candidates, key=objective)

