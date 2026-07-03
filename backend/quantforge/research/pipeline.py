from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ResearchStage(StrEnum):
    EXPERIMENT_DEFINITION = "experiment_definition"
    DATASET_SELECTION = "dataset_selection"
    DATA_PREPARATION = "data_preparation"
    CALCULATION = "calculation"
    FEATURE_ENGINEERING = "feature_engineering"
    FEATURE_STORE = "feature_store"
    MARKET_REGIME_DETECTION = "market_regime_detection"
    KNOWLEDGE_BASE_LOOKUP = "knowledge_base_lookup"
    RESEARCH_ORCHESTRATION = "research_orchestration"
    STRATEGY_TEMPLATE_SELECTION = "strategy_template_selection"
    STRATEGY_FACTORY = "strategy_factory"
    PARAMETER_GENERATION = "parameter_generation"
    OPTIMIZATION = "optimization"
    BACKTESTING = "backtesting"
    VALIDATION = "validation"
    RANKING = "ranking"
    RESEARCH_ANALYTICS = "research_analytics"
    STRATEGY_PUBLISHING = "strategy_publishing"


RESEARCH_PIPELINE: tuple[ResearchStage, ...] = (
    ResearchStage.EXPERIMENT_DEFINITION,
    ResearchStage.DATASET_SELECTION,
    ResearchStage.DATA_PREPARATION,
    ResearchStage.CALCULATION,
    ResearchStage.FEATURE_ENGINEERING,
    ResearchStage.FEATURE_STORE,
    ResearchStage.MARKET_REGIME_DETECTION,
    ResearchStage.KNOWLEDGE_BASE_LOOKUP,
    ResearchStage.RESEARCH_ORCHESTRATION,
    ResearchStage.STRATEGY_TEMPLATE_SELECTION,
    ResearchStage.STRATEGY_FACTORY,
    ResearchStage.PARAMETER_GENERATION,
    ResearchStage.OPTIMIZATION,
    ResearchStage.BACKTESTING,
    ResearchStage.VALIDATION,
    ResearchStage.RANKING,
    ResearchStage.RESEARCH_ANALYTICS,
    ResearchStage.STRATEGY_PUBLISHING,
)


@dataclass(frozen=True, slots=True)
class ResearchStageResult:
    stage: ResearchStage
    status: str
    metrics: dict[str, Any] = field(default_factory=dict)
    artifact_uri: str | None = None
