from dataclasses import dataclass, field
from typing import Any

from quantforge.domain import PluginCategory


@dataclass(frozen=True, slots=True)
class PluginRegistryEntry:
    """Common registry record for any plugin type."""

    plugin_key: str
    name: str
    version: str
    plugin_type: PluginCategory
    status: str = "discovered"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PluginTypeConfig:
    """Type-specific metadata/config attached to a registry entry."""

    plugin_key: str
    config_schema: dict[str, Any] = field(default_factory=dict)
    runtime_config: dict[str, Any] = field(default_factory=dict)

