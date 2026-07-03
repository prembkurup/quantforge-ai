from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from quantforge.core.types import Granularity


class ExperimentStatus(str, Enum):
    DRAFT = "draft"
    CONFIGURED = "configured"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    VALIDATED = "validated"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    FAILED = "failed"


class ExperimentPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class ExperimentRunMode(str, Enum):
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


@dataclass(frozen=True, slots=True)
class ExperimentDataset:
    dataset_key: str
    instrument: str
    granularity: Granularity
    start: datetime
    end: datetime
    source_uri: str | None = None
    quality_report: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExperimentFeatureSet:
    feature_set_key: str
    feature_keys: tuple[str, ...]
    feature_vector_uri: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ParameterSearchPlan:
    optimizer: str
    objective: str
    search_space: dict[str, Any]
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExperimentSchedule:
    run_mode: ExperimentRunMode = ExperimentRunMode.IMMEDIATE
    priority: ExperimentPriority = ExperimentPriority.NORMAL
    scheduled_at: datetime | None = None
    max_parallel_workers: int = 1


@dataclass(frozen=True, slots=True)
class ExperimentDefinition:
    experiment_key: str
    name: str
    objective: str
    dataset: ExperimentDataset
    feature_set: ExperimentFeatureSet
    strategy_template_key: str
    parameter_search: ParameterSearchPlan
    hypothesis: str | None = None
    description: str | None = None
    market_regime: str | None = None
    success_criteria: dict[str, Any] = field(default_factory=dict)
    plugin_versions: dict[str, str] = field(default_factory=dict)
    validation_rules: dict[str, Any] = field(default_factory=dict)
    ranking_config: dict[str, Any] = field(default_factory=dict)
    optimization_config: dict[str, Any] = field(default_factory=dict)
    random_seed: int | None = None
    software_version: str | None = None
    schedule: ExperimentSchedule = field(default_factory=ExperimentSchedule)
    status: ExperimentStatus = ExperimentStatus.DRAFT


@dataclass(frozen=True, slots=True)
class ExperimentLineage:
    experiment_key: str
    dataset_key: str
    feature_set_key: str
    strategy_template_key: str
    parameter_search_key: str | None = None
    validation_result_keys: tuple[str, ...] = ()
    analytics_key: str | None = None
    published_strategy_version: str | None = None


@dataclass(frozen=True, slots=True)
class ExperimentResultSummary:
    experiment_key: str
    strategies_generated: int
    strategies_rejected: int
    validation_summary: dict[str, Any]
    best_strategy_key: str | None = None
    ranking_distribution: dict[str, Any] = field(default_factory=dict)
    feature_importance: dict[str, float] = field(default_factory=dict)
    parameter_importance: dict[str, float] = field(default_factory=dict)
    execution_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class ExperimentResourceUsage:
    experiment_key: str
    cpu_seconds: float | None = None
    peak_memory_mb: float | None = None
    queue_seconds: float | None = None
    worker_id: str | None = None
    estimated_completion_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ExperimentComparisonSpec:
    baseline_experiment_key: str
    candidate_experiment_keys: tuple[str, ...]
    metrics: tuple[str, ...] = (
        "net_profit",
        "profit_factor",
        "sharpe_ratio",
        "drawdown",
        "robustness",
        "trade_count",
        "execution_time",
    )


@dataclass(frozen=True, slots=True)
class ExperimentPublicationApproval:
    experiment_key: str
    strategy_version_key: str
    approved_by: str
    approval_reason: str
    promotion_metrics: dict[str, Any] = field(default_factory=dict)


class ExperimentService:
    """Coordinates experiment definitions and management metadata."""

    def create_lineage(self, definition: ExperimentDefinition) -> ExperimentLineage:
        return ExperimentLineage(
            experiment_key=definition.experiment_key,
            dataset_key=definition.dataset.dataset_key,
            feature_set_key=definition.feature_set.feature_set_key,
            strategy_template_key=definition.strategy_template_key,
        )

    def can_publish(
        self,
        definition: ExperimentDefinition,
        result: ExperimentResultSummary,
    ) -> bool:
        return (
            definition.status in {ExperimentStatus.VALIDATED, ExperimentStatus.COMPLETED}
            and result.best_strategy_key is not None
            and bool(result.validation_summary.get("passed"))
        )
