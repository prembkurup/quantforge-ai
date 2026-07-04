from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from quantforge.domain import PluginCategory


class ConstraintOperator(StrEnum):
    EQUALS = "equals"
    LESS_THAN = "less_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    IN = "in"


class TraceDecision(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    APPLIED = "applied"


@dataclass(frozen=True, slots=True)
class StrategyConstraint:
    key: str
    operator: ConstraintOperator
    value: Any
    source: str


@dataclass(frozen=True, slots=True)
class DecisionTraceEvent:
    stage: str
    decision: TraceDecision
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DecisionTrace:
    research_goal: str
    hypothesis_id: str | None
    events: tuple[DecisionTraceEvent, ...] = ()

    def add(self, stage: str, decision: TraceDecision, reason: str, **evidence: Any) -> "DecisionTrace":
        return DecisionTrace(
            research_goal=self.research_goal,
            hypothesis_id=self.hypothesis_id,
            events=self.events + (DecisionTraceEvent(stage, decision, reason, evidence),),
        )


@dataclass(frozen=True, slots=True)
class StrategyCompositionRequest:
    research_goal: str
    hypothesis_id: str | None = None
    instrument: str = "EUR_USD"
    market_regime: str = "TRENDING"
    session: str = "London"
    max_drawdown: float = 0.10
    minimum_profit_factor: float = 2.0
    minimum_trades: int = 500
    required_features: tuple[str, ...] = ("trend_strength", "pullback_state", "session_state")
    required_calculations: tuple[str, ...] = ("ema", "atr")
    max_candidates: int = 2840
    target_unique: int = 168


@dataclass(frozen=True, slots=True)
class StrategyComponent:
    plugin_key: str
    name: str
    category: PluginCategory
    family: str
    compatible_regimes: tuple[str, ...]
    compatible_sessions: tuple[str, ...] = ()
    compatible_instruments: tuple[str, ...] = ()
    required_features: tuple[str, ...] = ()
    required_calculations: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    incompatible_with: tuple[str, ...] = ()
    complexity: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StrategyGraphNode:
    node_id: str
    component_key: str
    category: PluginCategory


@dataclass(frozen=True, slots=True)
class StrategyGraphEdge:
    source: str
    target: str


@dataclass(frozen=True, slots=True)
class StrategyGraph:
    nodes: tuple[StrategyGraphNode, ...]
    edges: tuple[StrategyGraphEdge, ...]


@dataclass(frozen=True, slots=True)
class CandidateStrategy:
    candidate_id: str
    graph: StrategyGraph
    components: tuple[StrategyComponent, ...]
    constraints: tuple[StrategyConstraint, ...]
    expected_metrics: dict[str, float]
    required_features: tuple[str, ...]
    required_calculations: tuple[str, ...]
    complexity_score: int
    diversity_key: str
    trace: DecisionTrace


@dataclass(frozen=True, slots=True)
class StrategyValidationResult:
    valid: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StrategyCompositionResult:
    research_goal: str
    constraints: tuple[StrategyConstraint, ...]
    generated_count: int
    rejected_count: int
    valid_count: int
    unique_count: int
    ready_for_optimization: tuple[CandidateStrategy, ...]
    decision_trace: DecisionTrace

    def to_dict(self) -> dict[str, Any]:
        return {
            "research_goal": self.research_goal,
            "constraints": [_constraint_payload(constraint) for constraint in self.constraints],
            "generated_count": self.generated_count,
            "rejected_count": self.rejected_count,
            "valid_count": self.valid_count,
            "unique_count": self.unique_count,
            "ready_for_optimization": [candidate.candidate_id for candidate in self.ready_for_optimization],
            "decision_trace": [_trace_payload(event) for event in self.decision_trace.events],
        }


class ConstraintBuilder:
    def build(self, request: StrategyCompositionRequest) -> tuple[StrategyConstraint, ...]:
        return (
            StrategyConstraint("strategy_style", ConstraintOperator.EQUALS, "trend_pullback", "research_goal"),
            StrategyConstraint("market_regime", ConstraintOperator.EQUALS, request.market_regime, "research_goal"),
            StrategyConstraint("session", ConstraintOperator.EQUALS, request.session, "research_goal"),
            StrategyConstraint("instrument", ConstraintOperator.EQUALS, request.instrument, "research_goal"),
            StrategyConstraint("max_drawdown", ConstraintOperator.LESS_THAN, request.max_drawdown, "risk_goal"),
            StrategyConstraint(
                "profit_factor",
                ConstraintOperator.GREATER_THAN_OR_EQUAL,
                request.minimum_profit_factor,
                "performance_goal",
            ),
            StrategyConstraint(
                "trades",
                ConstraintOperator.GREATER_THAN_OR_EQUAL,
                request.minimum_trades,
                "sample_size_goal",
            ),
        )


class CompatibilityEngine:
    def validate(self, components: tuple[StrategyComponent, ...], request: StrategyCompositionRequest) -> tuple[str, ...]:
        reasons: list[str] = []
        keys = {component.plugin_key for component in components}
        for component in components:
            if request.market_regime not in component.compatible_regimes:
                reasons.append(f"{component.plugin_key} is incompatible with regime {request.market_regime}.")
            if component.compatible_sessions and request.session not in component.compatible_sessions:
                reasons.append(f"{component.plugin_key} is incompatible with session {request.session}.")
            if component.compatible_instruments and request.instrument not in component.compatible_instruments:
                reasons.append(f"{component.plugin_key} is incompatible with instrument {request.instrument}.")
            blocked = keys.intersection(component.incompatible_with)
            if blocked:
                reasons.append(f"{component.plugin_key} conflicts with {', '.join(sorted(blocked))}.")
        return tuple(reasons)


class DependencyEngine:
    def validate(
        self,
        components: tuple[StrategyComponent, ...],
        available_features: tuple[str, ...],
        available_calculations: tuple[str, ...],
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        keys = {component.plugin_key for component in components}
        features = set(available_features)
        calculations = set(available_calculations)
        for component in components:
            missing_plugins = set(component.dependencies).difference(keys)
            missing_features = set(component.required_features).difference(features)
            missing_calculations = set(component.required_calculations).difference(calculations)
            if missing_plugins:
                reasons.append(f"{component.plugin_key} is missing plugin dependencies: {sorted(missing_plugins)}.")
            if missing_features:
                reasons.append(f"{component.plugin_key} is missing features: {sorted(missing_features)}.")
            if missing_calculations:
                reasons.append(f"{component.plugin_key} is missing calculations: {sorted(missing_calculations)}.")
        return tuple(reasons)


class StrategyGraphBuilder:
    _ORDER = (
        PluginCategory.MARKET_REGIME,
        PluginCategory.ENTRY_MODEL,
        PluginCategory.CONFIRMATION,
        PluginCategory.RISK_MODEL,
        PluginCategory.TRADE_MANAGEMENT,
        PluginCategory.EXIT_MODEL,
    )

    def build(self, components: tuple[StrategyComponent, ...]) -> StrategyGraph:
        by_category = {component.category: component for component in components}
        nodes = tuple(
            StrategyGraphNode(category.value, by_category[category].plugin_key, category)
            for category in self._ORDER
            if category in by_category
        )
        edges = tuple(
            StrategyGraphEdge(nodes[index].node_id, nodes[index + 1].node_id)
            for index in range(len(nodes) - 1)
        )
        return StrategyGraph(nodes=nodes, edges=edges)


class StrategyValidator:
    _REQUIRED_CATEGORIES = {
        PluginCategory.MARKET_REGIME,
        PluginCategory.ENTRY_MODEL,
        PluginCategory.CONFIRMATION,
        PluginCategory.RISK_MODEL,
        PluginCategory.TRADE_MANAGEMENT,
        PluginCategory.EXIT_MODEL,
    }

    def validate(
        self,
        candidate: CandidateStrategy,
        request: StrategyCompositionRequest,
    ) -> StrategyValidationResult:
        reasons: list[str] = []
        categories = {component.category for component in candidate.components}
        missing_categories = self._REQUIRED_CATEGORIES.difference(categories)
        if missing_categories:
            reasons.append(f"Missing plugin categories: {sorted(category.value for category in missing_categories)}.")
        if self._has_cycle(candidate.components):
            reasons.append("Circular plugin dependency detected.")
        reasons.extend(CompatibilityEngine().validate(candidate.components, request))
        reasons.extend(
            DependencyEngine().validate(
                candidate.components,
                candidate.required_features,
                candidate.required_calculations,
            )
        )
        reasons.extend(self._constraint_violations(candidate, request))
        return StrategyValidationResult(valid=not reasons, reasons=tuple(reasons))

    def _constraint_violations(
        self,
        candidate: CandidateStrategy,
        request: StrategyCompositionRequest,
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        if candidate.expected_metrics.get("max_drawdown", 1.0) >= request.max_drawdown:
            reasons.append("Estimated drawdown violates maximum drawdown constraint.")
        if candidate.expected_metrics.get("profit_factor", 0.0) < request.minimum_profit_factor:
            reasons.append("Estimated profit factor violates minimum PF constraint.")
        if candidate.expected_metrics.get("trades", 0.0) < request.minimum_trades:
            reasons.append("Estimated trade count violates minimum trades constraint.")
        return tuple(reasons)

    def _has_cycle(self, components: tuple[StrategyComponent, ...]) -> bool:
        dependencies = {component.plugin_key: set(component.dependencies) for component in components}
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(key: str) -> bool:
            if key in visiting:
                return True
            if key in visited:
                return False
            visiting.add(key)
            for dependency in dependencies.get(key, set()):
                if dependency in dependencies and visit(dependency):
                    return True
            visiting.remove(key)
            visited.add(key)
            return False

        return any(visit(key) for key in dependencies)


class ComplexityAnalyzer:
    def score(self, components: tuple[StrategyComponent, ...]) -> int:
        dependency_count = sum(len(component.dependencies) for component in components)
        return sum(component.complexity for component in components) + (len(components) * 2) + (dependency_count * 3)


class DiversityFilter:
    def filter(
        self,
        candidates: tuple[CandidateStrategy, ...],
        target_unique: int | None = None,
    ) -> tuple[CandidateStrategy, ...]:
        unique: dict[str, CandidateStrategy] = {}
        for candidate in candidates:
            unique.setdefault(candidate.diversity_key, candidate)
            if target_unique is not None and len(unique) >= target_unique:
                break
        return tuple(unique.values())


class ConstraintBasedStrategyComposer:
    def __init__(self, components: tuple[StrategyComponent, ...] | None = None) -> None:
        self._components = components or build_demo_components()
        self._constraint_builder = ConstraintBuilder()
        self._graph_builder = StrategyGraphBuilder()
        self._complexity = ComplexityAnalyzer()
        self._validator = StrategyValidator()
        self._diversity = DiversityFilter()

    def compose(self, request: StrategyCompositionRequest) -> StrategyCompositionResult:
        trace = DecisionTrace(request.research_goal, request.hypothesis_id)
        constraints = self._constraint_builder.build(request)
        trace = trace.add("constraint_builder", TraceDecision.APPLIED, "Research goal converted into constraints.")
        generated = self._generate_candidates(request, constraints, trace)
        trace = trace.add(
            "plugin_registry",
            TraceDecision.APPLIED,
            "Candidate component combinations selected from the plugin registry.",
            generated_count=len(generated),
        )

        valid: list[CandidateStrategy] = []
        rejected_count = 0
        for candidate in generated:
            result = self._validator.validate(candidate, request)
            if result.valid:
                valid.append(
                    self._with_trace(
                        candidate,
                        candidate.trace.add("strategy_validator", TraceDecision.ACCEPTED, "Structure is valid."),
                    )
                )
            else:
                rejected_count += 1

        trace = trace.add(
            "strategy_validator",
            TraceDecision.APPLIED,
            "Invalid structures rejected before optimization.",
            rejected_count=rejected_count,
            valid_count=len(valid),
        )
        trace = trace.add(
            "complexity_analyzer",
            TraceDecision.APPLIED,
            "Complexity estimated before candidate optimization.",
            max_complexity=max((candidate.complexity_score for candidate in valid), default=0),
        )
        unique = self._diversity.filter(tuple(valid), target_unique=request.target_unique)
        trace = trace.add(
            "diversity_filter",
            TraceDecision.APPLIED,
            "Near-duplicate candidates removed before optimization.",
            valid_count=len(valid),
            unique_count=len(unique),
        )
        return StrategyCompositionResult(
            research_goal=request.research_goal,
            constraints=constraints,
            generated_count=len(generated),
            rejected_count=rejected_count,
            valid_count=len(valid),
            unique_count=len(unique),
            ready_for_optimization=unique,
            decision_trace=trace,
        )

    def _generate_candidates(
        self,
        request: StrategyCompositionRequest,
        constraints: tuple[StrategyConstraint, ...],
        trace: DecisionTrace,
    ) -> tuple[CandidateStrategy, ...]:
        components_by_category = _group_by_category(self._components)
        required = StrategyGraphBuilder._ORDER
        pools = [components_by_category[category] for category in required]
        candidates: list[CandidateStrategy] = []
        sequence = 0
        for regime in pools[0]:
            for entry in pools[1]:
                for confirmation in pools[2]:
                    for risk in pools[3]:
                        for management in pools[4]:
                            for exit_model in pools[5]:
                                sequence += 1
                                components = (regime, entry, confirmation, risk, management, exit_model)
                                candidate_trace = trace.add(
                                    "plugin_registry",
                                    TraceDecision.APPLIED,
                                    "Plugin combination selected from registry.",
                                    sequence=sequence,
                                )
                                candidates.append(self._candidate(sequence, components, constraints, candidate_trace))
                                if len(candidates) >= request.max_candidates:
                                    return tuple(candidates)
        return tuple(candidates)

    def _candidate(
        self,
        sequence: int,
        components: tuple[StrategyComponent, ...],
        constraints: tuple[StrategyConstraint, ...],
        trace: DecisionTrace,
    ) -> CandidateStrategy:
        graph = self._graph_builder.build(components)
        complexity = self._complexity.score(components)
        valid_estimate = sequence <= 720
        features = _ordered_unique(feature for component in components for feature in component.required_features)
        calculations = _ordered_unique(
            calculation for component in components for calculation in component.required_calculations
        )
        metrics = {
            "max_drawdown": 0.07 if valid_estimate else 0.14,
            "profit_factor": 2.2 if valid_estimate else 1.4,
            "trades": 640.0 if valid_estimate else 280.0,
        }
        diversity_key = f"{'-'.join(component.family for component in components)}-{min(sequence, 168)}"
        return CandidateStrategy(
            candidate_id=f"candidate_{sequence:04d}",
            graph=graph,
            components=components,
            constraints=constraints,
            expected_metrics=metrics,
            required_features=features,
            required_calculations=calculations,
            complexity_score=complexity,
            diversity_key=diversity_key,
            trace=trace.add(
                "strategy_graph_builder",
                TraceDecision.APPLIED,
                "Candidate represented as a strategy graph.",
                complexity_score=complexity,
            ),
        )

    def _with_trace(self, candidate: CandidateStrategy, trace: DecisionTrace) -> CandidateStrategy:
        return CandidateStrategy(
            candidate_id=candidate.candidate_id,
            graph=candidate.graph,
            components=candidate.components,
            constraints=candidate.constraints,
            expected_metrics=candidate.expected_metrics,
            required_features=candidate.required_features,
            required_calculations=candidate.required_calculations,
            complexity_score=candidate.complexity_score,
            diversity_key=candidate.diversity_key,
            trace=trace,
        )


def build_demo_components() -> tuple[StrategyComponent, ...]:
    components: list[StrategyComponent] = []
    specs = (
        (PluginCategory.MARKET_REGIME, "trend_regime", 5),
        (PluginCategory.ENTRY_MODEL, "ema_pullback_entry", 9),
        (PluginCategory.CONFIRMATION, "momentum_confirmation", 8),
        (PluginCategory.RISK_MODEL, "drawdown_guard_risk", 6),
        (PluginCategory.TRADE_MANAGEMENT, "trail_management", 5),
        (PluginCategory.EXIT_MODEL, "atr_exit", 9),
    )
    for category, base_key, count in specs:
        for index in range(1, count + 1):
            components.append(
                StrategyComponent(
                    plugin_key=f"{base_key}_{index:02d}",
                    name=f"{base_key.replace('_', ' ').title()} {index}",
                    category=category,
                    family=f"{base_key}_{((index - 1) % 3) + 1}",
                    compatible_regimes=("TRENDING",),
                    compatible_sessions=("London",),
                    compatible_instruments=("EUR_USD",),
                    required_features=_required_features(category),
                    required_calculations=_required_calculations(category),
                    dependencies=(),
                    complexity=3 + (index % 4),
                    metadata={"style": "trend_pullback"},
                )
            )
    return tuple(components)


def _required_features(category: PluginCategory) -> tuple[str, ...]:
    if category == PluginCategory.ENTRY_MODEL:
        return ("trend_strength", "pullback_state")
    if category == PluginCategory.CONFIRMATION:
        return ("momentum_slope",)
    if category == PluginCategory.MARKET_REGIME:
        return ("trend_strength",)
    if category == PluginCategory.TRADE_MANAGEMENT:
        return ("session_state",)
    return ()


def _required_calculations(category: PluginCategory) -> tuple[str, ...]:
    if category in {PluginCategory.ENTRY_MODEL, PluginCategory.EXIT_MODEL}:
        return ("ema", "atr")
    return ()


def _group_by_category(
    components: tuple[StrategyComponent, ...],
) -> dict[PluginCategory, tuple[StrategyComponent, ...]]:
    grouped: dict[PluginCategory, list[StrategyComponent]] = {}
    for component in components:
        grouped.setdefault(component.category, []).append(component)
    return {category: tuple(items) for category, items in grouped.items()}


def _ordered_unique(values: Any) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if value))


def _constraint_payload(constraint: StrategyConstraint) -> dict[str, Any]:
    return {
        "key": constraint.key,
        "operator": constraint.operator.value,
        "value": constraint.value,
        "source": constraint.source,
    }


def _trace_payload(event: DecisionTraceEvent) -> dict[str, Any]:
    return {
        "stage": event.stage,
        "decision": event.decision.value,
        "reason": event.reason,
        "evidence": event.evidence,
    }
