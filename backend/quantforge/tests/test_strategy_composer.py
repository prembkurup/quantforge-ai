from quantforge.domain import PluginCategory
from quantforge.strategies import (
    ConstraintBasedStrategyComposer,
    ConstraintBuilder,
    ConstraintOperator,
    DependencyEngine,
    DiversityFilter,
    StrategyComponent,
    StrategyCompositionRequest,
    StrategyGraphBuilder,
)


def test_constraint_builder_converts_research_goal_to_rules() -> None:
    constraints = ConstraintBuilder().build(
        StrategyCompositionRequest(
            research_goal="Trend Pullback",
            instrument="EUR_USD",
            session="London",
            max_drawdown=0.10,
            minimum_profit_factor=2.0,
            minimum_trades=500,
        )
    )

    by_key = {constraint.key: constraint for constraint in constraints}

    assert by_key["strategy_style"].value == "trend_pullback"
    assert by_key["max_drawdown"].operator == ConstraintOperator.LESS_THAN
    assert by_key["profit_factor"].value == 2.0
    assert by_key["trades"].value == 500


def test_strategy_graph_builder_orders_components_as_research_graph() -> None:
    components = (
        _component("regime", PluginCategory.MARKET_REGIME),
        _component("entry", PluginCategory.ENTRY_MODEL),
        _component("confirmation", PluginCategory.CONFIRMATION),
        _component("risk", PluginCategory.RISK_MODEL),
        _component("management", PluginCategory.TRADE_MANAGEMENT),
        _component("exit", PluginCategory.EXIT_MODEL),
    )

    graph = StrategyGraphBuilder().build(components)

    assert [node.category for node in graph.nodes] == [
        PluginCategory.MARKET_REGIME,
        PluginCategory.ENTRY_MODEL,
        PluginCategory.CONFIRMATION,
        PluginCategory.RISK_MODEL,
        PluginCategory.TRADE_MANAGEMENT,
        PluginCategory.EXIT_MODEL,
    ]
    assert graph.edges[-1].target == PluginCategory.EXIT_MODEL.value


def test_dependency_engine_rejects_missing_features_and_calculations() -> None:
    reasons = DependencyEngine().validate(
        (
            StrategyComponent(
                plugin_key="ema_pullback",
                name="EMA Pullback",
                category=PluginCategory.ENTRY_MODEL,
                family="ema_pullback",
                compatible_regimes=("TRENDING",),
                required_features=("trend_strength",),
                required_calculations=("ema",),
            ),
        ),
        available_features=(),
        available_calculations=(),
    )

    assert any("missing features" in reason for reason in reasons)
    assert any("missing calculations" in reason for reason in reasons)


def test_composer_filters_invalid_and_duplicate_candidates_before_optimization() -> None:
    result = ConstraintBasedStrategyComposer().compose(StrategyCompositionRequest(research_goal="Trend Pullback"))

    assert result.generated_count == 2840
    assert result.rejected_count == 2120
    assert result.valid_count == 720
    assert result.unique_count == 168
    assert len(result.ready_for_optimization) == 168
    assert result.ready_for_optimization[0].graph.nodes
    assert result.ready_for_optimization[0].trace.events
    assert result.decision_trace.events[-1].stage == "diversity_filter"


def test_diversity_filter_rejects_near_duplicate_signatures() -> None:
    result = ConstraintBasedStrategyComposer().compose(StrategyCompositionRequest(research_goal="Trend Pullback"))
    first_two = result.ready_for_optimization[:2]
    duplicated = first_two + first_two

    unique = DiversityFilter().filter(duplicated)

    assert len(unique) == 2


def _component(plugin_key: str, category: PluginCategory) -> StrategyComponent:
    return StrategyComponent(
        plugin_key=plugin_key,
        name=plugin_key,
        category=category,
        family=plugin_key,
        compatible_regimes=("TRENDING",),
    )
