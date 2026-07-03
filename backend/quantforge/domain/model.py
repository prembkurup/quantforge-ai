from dataclasses import dataclass
from enum import StrEnum


class DomainName(StrEnum):
    MARKET_DATA = "market_data"
    INSTRUMENT = "instrument"
    PLUGIN = "plugin"
    RESEARCH = "research"
    STRATEGY = "strategy"
    BACKTESTING = "backtesting"
    VALIDATION = "validation"
    LIVE_TRADING = "live_trading"
    RISK_MANAGEMENT = "risk_management"
    REPORTING = "reporting"
    ADMINISTRATION = "administration"
    INFRASTRUCTURE = "infrastructure"


class PluginCategory(StrEnum):
    INDICATOR = "indicator"
    FEATURE = "feature"
    MARKET_REGIME = "market_regime"
    ENTRY_MODEL = "entry_model"
    CONFIRMATION = "confirmation"
    EXIT_MODEL = "exit_model"
    RISK_MODEL = "risk_model"
    POSITION_SIZING = "position_sizing"
    TRADE_MANAGEMENT = "trade_management"
    VALIDATION = "validation"
    RANKING = "ranking"


class StrategyLifecycleStatus(StrEnum):
    DRAFT = "draft"
    GENERATED = "generated"
    OPTIMIZED = "optimized"
    BACKTESTED = "backtested"
    VALIDATED = "validated"
    PAPER_TRADING = "paper_trading"
    APPROVED = "approved"
    PRODUCTION = "production"
    RETIRED = "retired"
    ARCHIVED = "archived"


class ValidationStatus(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


class DataClassification(StrEnum):
    PERMANENT = "permanent"
    CACHED = "cached"
    TEMPORARY = "temporary"
    ARCHIVE = "archive"


class StorageClass(StrEnum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    ARCHIVE = "archive"


class ServiceOwner(StrEnum):
    DATA = "data_service"
    RESEARCH = "research_service"
    STRATEGY = "strategy_service"
    TRADING = "trading_service"
    RISK = "risk_service"
    REPORTING = "reporting_service"
    API = "api_service"


@dataclass(frozen=True, slots=True)
class EntityRef:
    domain: DomainName
    entity_type: str
    entity_id: str


@dataclass(frozen=True, slots=True)
class OwnershipRule:
    entity_type: str
    owner: ServiceOwner
    classification: DataClassification
    storage_class: StorageClass
