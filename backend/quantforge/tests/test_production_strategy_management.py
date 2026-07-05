import pytest

from quantforge.strategies import (
    CapitalAllocator,
    DriftDetector,
    ProductionStrategyManagementPlatform,
    StrategyCatalog,
    StrategyRegistry,
    StrategyRegistryStatus,
)
from quantforge.validation import StrategyValidationPlatform


def test_strategy_catalog_stores_strategy_asset_versions_and_validation() -> None:
    validation = StrategyValidationPlatform()
    asset = validation.create_strategy_asset(validation.validate("QF-2026-00431"))
    catalog = StrategyCatalog()

    record = catalog.publish(asset)

    assert record.asset.passport.strategy_id == "QF-2026-00431"
    assert record.versions == ("3.2",)
    assert record.validation_ids == ("QF-2026-00431",)
    assert catalog.get("QF-2026-00431") == record


def test_registry_tracks_active_paper_production_and_retired_status() -> None:
    registry = StrategyRegistry()

    registry.set_status("QF-2026-00431", "3.2", StrategyRegistryStatus.ACTIVE)
    registry.set_status("QF-2026-00431", "3.2", StrategyRegistryStatus.PRODUCTION)

    assert registry.get("QF-2026-00431").status == StrategyRegistryStatus.PRODUCTION


def test_capital_allocator_uses_portfolio_theme_targets() -> None:
    validation = StrategyValidationPlatform()
    asset = validation.create_strategy_asset(validation.validate("QF-2026-00431"))

    allocation = CapitalAllocator().allocate((asset,))

    assert allocation["QF-2026-00431"] == 0.40


def test_drift_detector_flags_live_underperformance() -> None:
    score, detected = DriftDetector().detect(research_profit_factor=2.1, live_profit_factor=1.1)

    assert score > 0.30
    assert detected is True


def test_production_platform_deploys_asset_from_catalog_to_production() -> None:
    validation = StrategyValidationPlatform()
    asset = validation.create_strategy_asset(validation.validate("QF-2026-00431"))

    result = ProductionStrategyManagementPlatform().deploy(asset)

    assert result.approved is True
    assert result.installed is True
    assert result.portfolio.portfolio_id == "QF-PORT-0001"
    assert result.portfolio.total_allocation == 0.40
    assert result.capital_allocated is True
    assert result.paper_trading is True
    assert result.production is True
    assert result.dashboard.production == 1
    assert result.live_learning_records[0]["target"] == "knowledge_base"


def test_production_platform_blocks_silent_demo_fallback() -> None:
    with pytest.raises(ValueError, match="real approved Strategy Asset"):
        ProductionStrategyManagementPlatform().deploy()


def test_production_platform_demo_requires_explicit_method() -> None:
    result = ProductionStrategyManagementPlatform().deploy_demo()

    assert result.approved is True
    assert result.production is True
