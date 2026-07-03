from collections import Counter
from typing import Any


class ResearchAnalyticsEngine:
    """Summarizes outcomes across research experiments."""

    def summarize_templates(self, candidates: list[dict[str, Any]]) -> dict[str, int]:
        return dict(Counter(str(candidate.get("template_key", "unknown")) for candidate in candidates))

