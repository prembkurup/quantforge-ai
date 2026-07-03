from typing import Any


class StrategyRankingEngine:
    """Ranks validated strategies with configurable metric weights."""

    def score(self, metrics: dict[str, float], weights: dict[str, float]) -> float:
        return sum(float(metrics.get(metric, 0)) * weight for metric, weight in weights.items())

    def rank(self, candidates: list[dict[str, Any]], weights: dict[str, float]) -> list[dict[str, Any]]:
        return sorted(
            candidates,
            key=lambda candidate: self.score(candidate.get("metrics", {}), weights),
            reverse=True,
        )

