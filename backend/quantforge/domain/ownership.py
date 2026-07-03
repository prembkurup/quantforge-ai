from quantforge.domain.model import (
    DataClassification,
    OwnershipRule,
    ServiceOwner,
    StorageClass,
)


OWNERSHIP_RULES: tuple[OwnershipRule, ...] = (
    OwnershipRule("Instrument", ServiceOwner.DATA, DataClassification.PERMANENT, StorageClass.WARM),
    OwnershipRule("Candle", ServiceOwner.DATA, DataClassification.PERMANENT, StorageClass.WARM),
    OwnershipRule("Spread", ServiceOwner.DATA, DataClassification.PERMANENT, StorageClass.HOT),
    OwnershipRule("ResearchRun", ServiceOwner.RESEARCH, DataClassification.ARCHIVE, StorageClass.COLD),
    OwnershipRule("BacktestRun", ServiceOwner.RESEARCH, DataClassification.ARCHIVE, StorageClass.COLD),
    OwnershipRule("StrategyVersion", ServiceOwner.STRATEGY, DataClassification.PERMANENT, StorageClass.WARM),
    OwnershipRule("LiveSignal", ServiceOwner.TRADING, DataClassification.CACHED, StorageClass.HOT),
    OwnershipRule("Order", ServiceOwner.TRADING, DataClassification.PERMANENT, StorageClass.HOT),
    OwnershipRule("Execution", ServiceOwner.TRADING, DataClassification.PERMANENT, StorageClass.HOT),
    OwnershipRule("Trade", ServiceOwner.TRADING, DataClassification.PERMANENT, StorageClass.WARM),
    OwnershipRule("RiskRule", ServiceOwner.RISK, DataClassification.PERMANENT, StorageClass.HOT),
    OwnershipRule("AuditLog", ServiceOwner.API, DataClassification.PERMANENT, StorageClass.ARCHIVE),
)


def owner_for(entity_type: str) -> ServiceOwner | None:
    for rule in OWNERSHIP_RULES:
        if rule.entity_type == entity_type:
            return rule.owner
    return None

