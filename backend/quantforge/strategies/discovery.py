from importlib import import_module
from typing import Iterable

from quantforge.strategies.plugin import StrategyPlugin


def discover_plugins(module_paths: Iterable[str]) -> list[StrategyPlugin]:
    """Load strategy plugins from module paths.

    Each module may expose either `PLUGIN` for one plugin or `PLUGINS` for many.
    """

    plugins: list[StrategyPlugin] = []
    for module_path in module_paths:
        module = import_module(module_path)
        if hasattr(module, "PLUGIN"):
            plugins.append(module.PLUGIN)
        if hasattr(module, "PLUGINS"):
            plugins.extend(module.PLUGINS)
    return plugins

