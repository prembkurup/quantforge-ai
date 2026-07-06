from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from quantforge.config.settings import get_settings


SettingKind = Literal["boolean", "integer", "number", "text", "select", "multi_select", "password", "path"]


@dataclass(frozen=True, slots=True)
class AdminSettingDefinition:
    setting_id: str
    group: str
    label: str
    kind: SettingKind
    default: Any
    description: str
    editable: bool = True
    restart_required: bool = False
    options: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None
    source: str = "admin_settings"


class AdminSettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def current(self) -> dict[str, Any]:
        stored = self._load()
        values = stored.get("values", {}) if isinstance(stored.get("values"), dict) else {}
        settings = get_settings()
        groups: dict[str, list[dict[str, Any]]] = {}
        for definition in _definitions(settings):
            value = _source_value(definition, settings, values)
            groups.setdefault(definition.group, []).append(
                {
                    **asdict(definition),
                    "value": _masked_value(definition, value),
                    "default": _masked_value(definition, definition.default),
                    "is_default": value == definition.default,
                    "help": f"{definition.description} Default: {_display_default(definition)}.",
                }
            )
        return {
            "groups": [
                {"group": group, "settings": items}
                for group, items in groups.items()
            ],
            "values": values,
            "updated_at": stored.get("updated_at", ""),
            "source": str(self.path),
        }

    def update(self, values: dict[str, Any]) -> dict[str, Any]:
        definitions = {definition.setting_id: definition for definition in _definitions(get_settings())}
        stored = self._load()
        current = stored.get("values", {}) if isinstance(stored.get("values"), dict) else {}
        merged = dict(current)
        for setting_id, raw_value in values.items():
            definition = definitions.get(setting_id)
            if definition is None:
                raise ValueError(f"Unknown admin setting: {setting_id}")
            if not definition.editable:
                raise ValueError(f"Admin setting is read-only: {setting_id}")
            merged[setting_id] = _coerce(definition, raw_value)
        payload = {
            "values": merged,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return self.current()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"values": {}, "updated_at": ""}
        return json.loads(self.path.read_text(encoding="utf-8"))


def admin_setting_values(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    values = payload.get("values", {})
    return values if isinstance(values, dict) else {}


def admin_setting_value(path: Path, setting_id: str, default: Any) -> Any:
    return admin_setting_values(path).get(setting_id, default)


def _definitions(settings: Any) -> tuple[AdminSettingDefinition, ...]:
    return (
        AdminSettingDefinition("runtime.environment", "Runtime", "Environment", "text", settings.environment, "Runtime environment loaded from QUANTFORGE_ENVIRONMENT.", editable=False, source="environment"),
        AdminSettingDefinition("runtime.candle_source", "Runtime", "Candle source", "select", settings.candle_source, "Market-data source used by research scripts.", options=("coreui", "oanda", "csv"), restart_required=True),
        AdminSettingDefinition("runtime.parquet_cache_dir", "Runtime", "Parquet cache directory", "path", settings.parquet_cache_dir, "Directory for local parquet/cache artifacts.", restart_required=True),
        AdminSettingDefinition("dashboard.refresh_seconds", "Dashboard", "Dashboard refresh seconds", "integer", 30, "How often dashboard pages poll read-only APIs.", minimum=5, maximum=300),
        AdminSettingDefinition("dashboard.table_page_size", "Dashboard", "Table page size", "integer", 30, "Default number of rows shown in paginated dashboard tables.", minimum=10, maximum=200),
        AdminSettingDefinition("dashboard.api_host", "Dashboard", "API host", "text", settings.dashboard_api_host, "Host used by the dashboard API server.", editable=False, source="environment"),
        AdminSettingDefinition("dashboard.api_port", "Dashboard", "API port", "integer", settings.dashboard_api_port, "Port used by the dashboard API server.", editable=False, source="environment"),
        AdminSettingDefinition("dashboard.cors_origins", "Dashboard", "Allowed dashboard origins", "text", settings.dashboard_cors_origins, "Comma-separated browser origins allowed to call the dashboard API.", editable=False, source="environment"),
        AdminSettingDefinition("full_history.max_parallel_jobs", "Full History Research", "Max parallel jobs", "integer", 3, "Number of full-history jobs the worker can claim per loop.", minimum=1, maximum=12, restart_required=True),
        AdminSettingDefinition("full_history.sleep_seconds", "Full History Research", "Loop sleep seconds", "integer", 30, "Delay between active worker loops.", minimum=5, maximum=600, restart_required=True),
        AdminSettingDefinition("full_history.idle_sleep_seconds", "Full History Research", "Idle sleep seconds", "integer", 900, "Delay when no pending full-history jobs exist.", minimum=30, maximum=3600, restart_required=True),
        AdminSettingDefinition("full_history.error_sleep_seconds", "Full History Research", "Error sleep seconds", "integer", 300, "Delay after process-level scheduler failures.", minimum=30, maximum=3600, restart_required=True),
        AdminSettingDefinition("full_history.running_stale_seconds", "Full History Research", "Running stale seconds", "integer", 21600, "How long a claimed job can remain running before another worker can reclaim it.", minimum=300, maximum=86400, restart_required=True),
        AdminSettingDefinition("full_history.window_candles", "Full History Research", "Research window candles", "integer", 300, "Default candle count required for rolling/full-history research windows.", minimum=50, maximum=2000, restart_required=True),
        AdminSettingDefinition("full_history.h4_smoke_window_candles", "Full History Research", "H4 smoke window candles", "integer", 120, "Candle count used for quick H4 smoke checks.", minimum=50, maximum=300, restart_required=True),
        AdminSettingDefinition("full_history.smoke_days", "Full History Research", "Smoke days", "integer", 31, "Calendar days included in smoke-stage research checks.", minimum=7, maximum=120, restart_required=True),
        AdminSettingDefinition("full_history.smoke_max_batches", "Full History Research", "Smoke max batches", "integer", 2, "Maximum experiment batches produced by each smoke job.", minimum=1, maximum=20, restart_required=True),
        AdminSettingDefinition("full_history.rolling_max_batches", "Full History Research", "Rolling max batches", "integer", 25, "Maximum batches per rolling-year job.", minimum=1, maximum=200, restart_required=True),
        AdminSettingDefinition("full_history.full_history_max_batches", "Full History Research", "Full-history max batches", "integer", 100, "Maximum batches per full-history job.", minimum=1, maximum=500, restart_required=True),
        AdminSettingDefinition("workflow.max_retries", "Workflow", "Max retries", "integer", 3, "Maximum retry attempts before a retryable task becomes permanent failure.", minimum=0, maximum=10, restart_required=True),
        AdminSettingDefinition("workflow.retry_delay_seconds", "Workflow", "Retry delay seconds", "integer", 300, "Minimum delay before a retryable full-history job can be reclaimed.", minimum=0, maximum=3600, restart_required=True),
        AdminSettingDefinition("workflow.manual_live_approval_required", "Workflow", "Manual live approval required", "boolean", True, "Keep live trading blocked until a human approval gate is explicitly satisfied."),
        AdminSettingDefinition("workflow.auto_post_pipeline", "Workflow", "Auto-run post full-history pipeline", "boolean", True, "Allow the worker to run downstream automation after full-history research completes."),
        AdminSettingDefinition("workflow.live_trading_blocked_by_policy", "Workflow", "Live trading blocked by policy", "boolean", True, "Safety switch that prevents live execution by default."),
        AdminSettingDefinition("market_data.coreui_database_url", "Market Data", "CoreUI database URL", "password", settings.coreui_history_database_url or "", "Database URL used for CoreUI/OANDA candle history.", editable=False, source="environment"),
        AdminSettingDefinition("market_data.coreui_candle_table", "Market Data", "CoreUI candle table", "text", settings.coreui_candle_table, "Database table containing candle rows.", editable=False, source="environment"),
        AdminSettingDefinition("oanda.api_url", "Integrations", "OANDA API URL", "text", settings.oanda_api_url, "Base URL used for OANDA candle ingestion.", editable=False, source="environment"),
        AdminSettingDefinition("oanda.account_id", "Integrations", "OANDA account ID", "password", settings.oanda_account_id or "", "OANDA account identifier.", editable=False, source="environment"),
        AdminSettingDefinition("oanda.api_token", "Integrations", "OANDA API token", "password", settings.oanda_api_token or "", "OANDA API token used for authenticated requests.", editable=False, source="environment"),
        AdminSettingDefinition("monday.api_url", "Integrations", "Monday API URL", "text", settings.monday_api_url, "Base URL for Monday.com GraphQL API.", editable=False, source="environment"),
        AdminSettingDefinition("monday.board_id", "Integrations", "Monday board ID", "text", settings.monday_board_id or "", "Default Monday.com board for roadmap sync.", editable=False, source="environment"),
        AdminSettingDefinition("monday.api_token", "Integrations", "Monday API token", "password", settings.monday_api_token or "", "Monday.com API token.", editable=False, source="environment"),
        AdminSettingDefinition("risk.paper_trading_enabled", "Risk / Safety", "Paper trading enabled", "boolean", True, "Allow paper/shadow trading workflows to operate."),
        AdminSettingDefinition("risk.live_trading_enabled", "Risk / Safety", "Live trading enabled", "boolean", False, "Master switch for controlled live trading execution."),
        AdminSettingDefinition("risk.production_certification_required", "Risk / Safety", "Production certification required", "boolean", True, "Require production certification before live approval can be requested."),
        AdminSettingDefinition("risk.capital_protection_enabled", "Risk / Safety", "Capital protection enabled", "boolean", True, "Keep operational capital-protection checks enabled."),
    )


def _source_value(definition: AdminSettingDefinition, settings: Any, values: dict[str, Any]) -> Any:
    if definition.editable:
        return values.get(definition.setting_id, definition.default)
    return definition.default


def _coerce(definition: AdminSettingDefinition, raw_value: Any) -> Any:
    if definition.kind == "boolean":
        value = bool(raw_value)
    elif definition.kind == "integer":
        value = int(raw_value)
    elif definition.kind == "number":
        value = float(raw_value)
    elif definition.kind == "multi_select":
        value = [str(item) for item in raw_value]
    else:
        value = str(raw_value)
    if definition.options and definition.kind == "select" and value not in definition.options:
        raise ValueError(f"{definition.setting_id} must be one of: {', '.join(definition.options)}")
    if isinstance(value, int | float):
        if definition.minimum is not None and value < definition.minimum:
            raise ValueError(f"{definition.setting_id} must be >= {definition.minimum}")
        if definition.maximum is not None and value > definition.maximum:
            raise ValueError(f"{definition.setting_id} must be <= {definition.maximum}")
    return value


def _masked_value(definition: AdminSettingDefinition, value: Any) -> Any:
    if definition.kind == "password" and value:
        return "********"
    return value


def _display_default(definition: AdminSettingDefinition) -> str:
    value = _masked_value(definition, definition.default)
    if value == "":
        return "empty"
    return str(value)
