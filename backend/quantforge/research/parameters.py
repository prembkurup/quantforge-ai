from itertools import product
from typing import Any


class ParameterGenerator:
    """Generates valid parameter combinations before optimization."""

    def generate(self, search_space: dict[str, list[Any]]) -> list[dict[str, Any]]:
        keys = list(search_space)
        combinations = product(*(search_space[key] for key in keys))
        return [dict(zip(keys, values, strict=True)) for values in combinations]

