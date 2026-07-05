from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from quantforge.validation import StrategyAsset, StrategyValidationPlatform


class StrategyRegistryStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAPER = "paper"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class DeploymentAction(StrEnum):
    INSTALL = "install"
    UPGRADE = "upgrade"
    ROLLBACK = "rollback"
    DISABLE = "disable"
    PROMOTE = "promote"
    ARCHIVE = "archive"


class DeploymentEnvironment(StrEnum):
    PAPER = "paper"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class CatalogRecord:
    asset: StrategyAsset
    versions: tuple[str, ...]
    validation_ids: tuple[str, ...]
    deployment_ids: tuple[str, ...] = ()
    retirement_reason: str | None = None


@dataclass(frozen=True, slots=True)
class RegistryEntry:
    strategy_id: str
    version: str
    status: StrategyRegistryStatus
    environment: DeploymentEnvironment | None = None


@dataclass(frozen=True, slots=True)
class DeploymentRecord:
    deployment_id: str
    strategy_id: str
    version: str
    action: DeploymentAction
    environment: DeploymentEnvironment
    status: str


@dataclass(frozen=True, slots=True)
class PortfolioStrategy:
    strategy_id: str
    version: str
    allocation_percent: float
    schedule: "StrategySchedule"
    status: StrategyRegistryStatus


@dataclass(frozen=True, slots=True)
class ProductionPortfolio:
    portfolio_id: str
    strategies: tuple[PortfolioStrategy, ...]
    total_allocation: float
    exposure_by_theme: dict[str, float]


@dataclass(frozen=True, slots=True)
class StrategySchedule:
    sessions: tuple[str, ...]
    timeframes: tuple[str, ...]
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class LivePerformanceSnapshot:
    strategy_id: str
    research_profit_factor: float
    live_profit_factor: float
    trades: int
    drift_score: float
    drift_detected: bool


@dataclass(frozen=True, slots=True)
class ProductionDashboard:
    approved_assets: int
    installed_assets: int
    portfolio_id: str
    active_strategies: int
    paper_trading: int
    production: int
    retired: int
    drift_alerts: int


@dataclass(frozen=True, slots=True)
class DeploymentPipelineResult:
    approved: bool
    installed: bool
    portfolio: ProductionPortfolio
    capital_allocated: bool
    paper_trading: bool
    production: bool
    dashboard: ProductionDashboard
    live_learning_records: tuple[dict[str, Any], ...] = ()


class StrategyCatalog:
    def __init__(self) -> None:
        self._records: dict[str, CatalogRecord] = {}

    def publish(self, asset: StrategyAsset) -> CatalogRecord:
        record = CatalogRecord(
            asset=asset,
            versions=(asset.passport.version,),
            validation_ids=(asset.validation_report.strategy_id,),
        )
        self._records[asset.passport.strategy_id] = record
        return record

    def get(self, strategy_id: str) -> CatalogRecord:
        return self._records[strategy_id]

    def list_assets(self) -> tuple[CatalogRecord, ...]:
        return tuple(self._records.values())


class StrategyRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, RegistryEntry] = {}

    def set_status(
        self,
        strategy_id: str,
        version: str,
        status: StrategyRegistryStatus,
        environment: DeploymentEnvironment | None = None,
    ) -> RegistryEntry:
        entry = RegistryEntry(strategy_id, version, status, environment)
        self._entries[strategy_id] = entry
        return entry

    def get(self, strategy_id: str) -> RegistryEntry:
        return self._entries[strategy_id]

    def list_entries(self) -> tuple[RegistryEntry, ...]:
        return tuple(self._entries.values())


class DeploymentManager:
    def __init__(self, registry: StrategyRegistry) -> None:
        self._registry = registry
        self._records: list[DeploymentRecord] = []

    def install(self, asset: StrategyAsset) -> DeploymentRecord:
        return self._record(asset, DeploymentAction.INSTALL, DeploymentEnvironment.PAPER, StrategyRegistryStatus.PAPER)

    def promote(self, asset: StrategyAsset) -> DeploymentRecord:
        return self._record(
            asset,
            DeploymentAction.PROMOTE,
            DeploymentEnvironment.PRODUCTION,
            StrategyRegistryStatus.PRODUCTION,
        )

    def rollback(self, asset: StrategyAsset) -> DeploymentRecord:
        return self._record(asset, DeploymentAction.ROLLBACK, DeploymentEnvironment.PAPER, StrategyRegistryStatus.PAPER)

    def disable(self, asset: StrategyAsset) -> DeploymentRecord:
        return self._record(asset, DeploymentAction.DISABLE, DeploymentEnvironment.PAPER, StrategyRegistryStatus.INACTIVE)

    def archive(self, asset: StrategyAsset) -> DeploymentRecord:
        return self._record(asset, DeploymentAction.ARCHIVE, DeploymentEnvironment.PAPER, StrategyRegistryStatus.RETIRED)

    def records(self) -> tuple[DeploymentRecord, ...]:
        return tuple(self._records)

    def _record(
        self,
        asset: StrategyAsset,
        action: DeploymentAction,
        environment: DeploymentEnvironment,
        status: StrategyRegistryStatus,
    ) -> DeploymentRecord:
        strategy_id = asset.passport.strategy_id
        version = asset.passport.version
        record = DeploymentRecord(
            deployment_id=f"deploy_{len(self._records) + 1:04d}",
            strategy_id=strategy_id,
            version=version,
            action=action,
            environment=environment,
            status="completed",
        )
        self._records.append(record)
        self._registry.set_status(strategy_id, version, status, environment)
        return record


class CapitalAllocator:
    def allocate(self, assets: tuple[StrategyAsset, ...]) -> dict[str, float]:
        theme_targets = {
            "Trend Pullback": 0.40,
            "Mean Reversion": 0.25,
            "Breakout": 0.20,
            "Scalping": 0.15,
        }
        allocations: dict[str, float] = {}
        for asset in assets:
            template = str(asset.strategy_definition.get("template", "Trend Pullback"))
            allocations[asset.passport.strategy_id] = theme_targets.get(template, 0.05)
        return allocations


class StrategyScheduler:
    def schedule(self, asset: StrategyAsset) -> StrategySchedule:
        template = str(asset.strategy_definition.get("template", "Trend Pullback"))
        if template == "Trend Pullback":
            return StrategySchedule(sessions=("London", "NewYork"), timeframes=("H1", "H4"))
        return StrategySchedule(sessions=("London",), timeframes=("H1",))


class PortfolioManager:
    def __init__(self, allocator: CapitalAllocator | None = None, scheduler: StrategyScheduler | None = None) -> None:
        self._allocator = allocator or CapitalAllocator()
        self._scheduler = scheduler or StrategyScheduler()

    def build(self, assets: tuple[StrategyAsset, ...], registry: StrategyRegistry) -> ProductionPortfolio:
        allocations = self._allocator.allocate(assets)
        strategies = tuple(
            PortfolioStrategy(
                strategy_id=asset.passport.strategy_id,
                version=asset.passport.version,
                allocation_percent=allocations[asset.passport.strategy_id],
                schedule=self._scheduler.schedule(asset),
                status=registry.get(asset.passport.strategy_id).status,
            )
            for asset in assets
        )
        return ProductionPortfolio(
            portfolio_id="QF-PORT-0001",
            strategies=strategies,
            total_allocation=round(sum(strategy.allocation_percent for strategy in strategies), 4),
            exposure_by_theme={"trend": 0.40, "mean_reversion": 0.25, "breakout": 0.20, "scalping": 0.15},
        )


class DriftDetector:
    def detect(self, research_profit_factor: float, live_profit_factor: float) -> tuple[float, bool]:
        drift_score = round(max(0.0, research_profit_factor - live_profit_factor) / max(research_profit_factor, 0.01), 4)
        return drift_score, drift_score >= 0.30


class LivePerformanceMonitor:
    def __init__(self, drift_detector: DriftDetector | None = None) -> None:
        self._drift_detector = drift_detector or DriftDetector()

    def snapshot(
        self,
        asset: StrategyAsset,
        live_profit_factor: float = 2.05,
        trades: int = 64,
    ) -> LivePerformanceSnapshot:
        research_profit_factor = float(asset.validation_report.walk_forward.windows[0]["profit_factor"])
        drift_score, drift_detected = self._drift_detector.detect(research_profit_factor, live_profit_factor)
        return LivePerformanceSnapshot(
            strategy_id=asset.passport.strategy_id,
            research_profit_factor=research_profit_factor,
            live_profit_factor=live_profit_factor,
            trades=trades,
            drift_score=drift_score,
            drift_detected=drift_detected,
        )


class RetirementManager:
    def __init__(self, registry: StrategyRegistry) -> None:
        self._registry = registry

    def evaluate(self, asset: StrategyAsset, snapshot: LivePerformanceSnapshot) -> bool:
        if snapshot.drift_detected or snapshot.live_profit_factor < 1.25:
            self._registry.set_status(
                asset.passport.strategy_id,
                asset.passport.version,
                StrategyRegistryStatus.RETIRED,
                DeploymentEnvironment.PRODUCTION,
            )
            return True
        return False


class LiveLearningLoop:
    def update(self, asset: StrategyAsset, snapshot: LivePerformanceSnapshot) -> tuple[dict[str, Any], ...]:
        return (
            {"target": "knowledge_base", "strategy_id": asset.passport.strategy_id, "live_profit_factor": snapshot.live_profit_factor},
            {"target": "research_analytics", "strategy_id": asset.passport.strategy_id, "drift_score": snapshot.drift_score},
            {"target": "strategy_passport", "strategy_id": asset.passport.strategy_id, "trades": snapshot.trades},
        )


class ProductionStrategyManagementPlatform:
    def __init__(self) -> None:
        self.catalog = StrategyCatalog()
        self.registry = StrategyRegistry()
        self.deployment = DeploymentManager(self.registry)
        self.portfolio = PortfolioManager()
        self.performance = LivePerformanceMonitor()
        self.retirement = RetirementManager(self.registry)
        self.learning = LiveLearningLoop()

    def deploy(self, asset: StrategyAsset | None = None) -> DeploymentPipelineResult:
        if asset is None:
            raise ValueError("A real approved Strategy Asset is required. Use deploy_demo() only for explicit demo mode.")
        _require_deployable_asset(asset)
        self.catalog.publish(asset)
        self.registry.set_status(asset.passport.strategy_id, asset.passport.version, StrategyRegistryStatus.ACTIVE)
        install = self.deployment.install(asset)
        portfolio = self.portfolio.build((asset,), self.registry)
        paper_trading = install.environment == DeploymentEnvironment.PAPER
        production_record = self.deployment.promote(asset)
        snapshot = self.performance.snapshot(asset)
        retired = self.retirement.evaluate(asset, snapshot)
        learning_records = self.learning.update(asset, snapshot)
        dashboard = self.dashboard()
        return DeploymentPipelineResult(
            approved=asset.validation_report.deployment_decision.value == "APPROVED",
            installed=install.status == "completed",
            portfolio=portfolio,
            capital_allocated=portfolio.total_allocation > 0.0,
            paper_trading=paper_trading,
            production=production_record.environment == DeploymentEnvironment.PRODUCTION and not retired,
            dashboard=dashboard,
            live_learning_records=learning_records,
        )

    def deploy_demo(self) -> DeploymentPipelineResult:
        return self.deploy(self._demo_asset())

    def dashboard(self) -> ProductionDashboard:
        entries = self.registry.list_entries()
        return ProductionDashboard(
            approved_assets=len(self.catalog.list_assets()),
            installed_assets=len(self.deployment.records()),
            portfolio_id="QF-PORT-0001",
            active_strategies=sum(entry.status in {StrategyRegistryStatus.PAPER, StrategyRegistryStatus.PRODUCTION} for entry in entries),
            paper_trading=sum(entry.status == StrategyRegistryStatus.PAPER for entry in entries),
            production=sum(entry.status == StrategyRegistryStatus.PRODUCTION for entry in entries),
            retired=sum(entry.status == StrategyRegistryStatus.RETIRED for entry in entries),
            drift_alerts=0,
        )

    def _demo_asset(self) -> StrategyAsset:
        platform = StrategyValidationPlatform()
        report = platform.validate("QF-2026-00431")
        return platform.create_strategy_asset(report)


def _require_deployable_asset(asset: StrategyAsset) -> None:
    if asset.validation_report.deployment_decision.value not in {"APPROVED", "PAPER_TRADE"}:
        raise ValueError("Strategy Asset is not approved for deployment.")
    if not asset.validation_report.to_dict():
        raise ValueError("Strategy Asset is missing validation report.")
    if not asset.passport.strategy_id or not asset.passport.version:
        raise ValueError("Strategy Asset is missing Strategy Passport.")
    if not asset.decision_trace:
        raise ValueError("Strategy Asset is missing decision trace.")
