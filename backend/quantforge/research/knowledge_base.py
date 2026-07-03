from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class KnowledgeObjectType(StrEnum):
    EXPERIMENT = "experiment"
    FEATURE = "feature"
    PLUGIN = "plugin"
    PARAMETER = "parameter"
    TEMPLATE = "template"
    REGIME = "regime"
    INSTRUMENT = "instrument"


class KnowledgeOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    NEUTRAL = "neutral"
    RISK_WARNING = "risk_warning"


class RecommendationLevel(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    IGNORE = "IGNORE"


class HypothesisStatus(StrEnum):
    PROPOSED = "proposed"
    SUPPORTED = "supported"
    REJECTED = "rejected"
    MIXED = "mixed"


@dataclass(frozen=True, slots=True)
class KnowledgeRecord:
    """One evidence item learned from an experiment or validation result."""

    object_type: KnowledgeObjectType
    object_id: str
    outcome: KnowledgeOutcome
    experiment_id: str
    hypothesis_id: str | None = None
    instrument: str | None = None
    timeframe: str | None = None
    regime: str | None = None
    session: str | None = None
    metric_name: str = "success_rate"
    metric_value: float | None = None
    stability: float | None = None
    importance: float | None = None
    sample_size: int = 1
    lessons: tuple[str, ...] = ()
    context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: str = "1.0.0"

    def key(self) -> tuple[KnowledgeObjectType, str]:
        return self.object_type, self.object_id


@dataclass(frozen=True, slots=True)
class Hypothesis:
    hypothesis_id: str
    statement: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    experiment_ids: tuple[str, ...] = ()
    supported_count: int = 0
    rejected_count: int = 0
    confidence: float = 0.0
    status: HypothesisStatus = HypothesisStatus.PROPOSED


@dataclass(frozen=True, slots=True)
class KnowledgeStatistics:
    object_type: KnowledgeObjectType
    object_id: str
    evidence_count: int
    success_count: int
    failure_count: int
    success_rate: float
    average_metric: float | None
    average_importance: float | None
    stability: float
    instruments: tuple[str, ...] = ()
    timeframes: tuple[str, ...] = ()
    regimes: tuple[str, ...] = ()
    sessions: tuple[str, ...] = ()
    lessons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class KnowledgeScore:
    object_type: KnowledgeObjectType
    object_id: str
    success_rate: float
    stability: float
    evidence_count: int
    score: float
    recommendation: RecommendationLevel


@dataclass(frozen=True, slots=True)
class ExperimentResultKnowledge:
    """Structured payload collected after an experiment finishes."""

    experiment_id: str
    outcome: KnowledgeOutcome
    lessons: tuple[str, ...] = ()
    hypothesis_id: str | None = None
    hypothesis_statement: str | None = None
    instrument: str | None = None
    timeframe: str | None = None
    regime: str | None = None
    session: str | None = None
    feature_importance: dict[str, float] = field(default_factory=dict)
    feature_stability: dict[str, float] = field(default_factory=dict)
    plugin_success: dict[str, float] = field(default_factory=dict)
    parameter_scores: dict[str, dict[str, Any]] = field(default_factory=dict)
    template_success: dict[str, float] = field(default_factory=dict)
    regime_success: dict[str, float] = field(default_factory=dict)


class KnowledgeRepository:
    """Repository for research knowledge records and hypotheses.

    V1 is intentionally lightweight and can persist to JSON for local reports. A
    PostgreSQL implementation can use the same domain objects later.
    """

    def __init__(self) -> None:
        self._records: list[KnowledgeRecord] = []
        self._hypotheses: dict[str, Hypothesis] = {}

    def add_record(self, record: KnowledgeRecord) -> KnowledgeRecord:
        self._records.append(record)
        return record

    def upsert_hypothesis(self, hypothesis: Hypothesis) -> Hypothesis:
        self._hypotheses[hypothesis.hypothesis_id] = hypothesis
        return hypothesis

    def records(
        self,
        object_type: KnowledgeObjectType | None = None,
        object_id: str | None = None,
    ) -> tuple[KnowledgeRecord, ...]:
        records = self._records
        if object_type is not None:
            records = [record for record in records if record.object_type == object_type]
        if object_id is not None:
            records = [record for record in records if record.object_id == object_id]
        return tuple(records)

    def hypotheses(self) -> tuple[Hypothesis, ...]:
        return tuple(self._hypotheses.values())

    def hypothesis(self, hypothesis_id: str) -> Hypothesis | None:
        return self._hypotheses.get(hypothesis_id)

    def save_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "records": [_serialize_dataclass(record) for record in self._records],
            "hypotheses": [_serialize_dataclass(hypothesis) for hypothesis in self._hypotheses.values()],
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load_json(cls, path: Path) -> KnowledgeRepository:
        repository = cls()
        if not path.exists():
            return repository
        payload = json.loads(path.read_text(encoding="utf-8"))
        for raw_record in payload.get("records", []):
            repository.add_record(_knowledge_record_from_json(raw_record))
        for raw_hypothesis in payload.get("hypotheses", []):
            hypothesis = _hypothesis_from_json(raw_hypothesis)
            repository.upsert_hypothesis(hypothesis)
        return repository


class KnowledgeStatisticsEngine:
    def summarize(self, records: tuple[KnowledgeRecord, ...]) -> KnowledgeStatistics:
        if not records:
            raise ValueError("Cannot summarize empty knowledge record set.")

        first = records[0]
        success_count = sum(record.outcome == KnowledgeOutcome.SUCCESS for record in records)
        failure_count = sum(record.outcome == KnowledgeOutcome.FAILURE for record in records)
        metric_values = [record.metric_value for record in records if record.metric_value is not None]
        importance_values = [record.importance for record in records if record.importance is not None]
        stability_values = [record.stability for record in records if record.stability is not None]
        sample_size = max(sum(record.sample_size for record in records), len(records))

        return KnowledgeStatistics(
            object_type=first.object_type,
            object_id=first.object_id,
            evidence_count=sample_size,
            success_count=success_count,
            failure_count=failure_count,
            success_rate=round(success_count / len(records), 4),
            average_metric=_average(metric_values),
            average_importance=_average(importance_values),
            stability=round(_average(stability_values) if stability_values else self._outcome_stability(records), 4),
            instruments=_unique(record.instrument for record in records),
            timeframes=_unique(record.timeframe for record in records),
            regimes=_unique(record.regime for record in records),
            sessions=_unique(record.session for record in records),
            lessons=_unique(lesson for record in records for lesson in record.lessons),
        )

    def summarize_repository(
        self,
        repository: KnowledgeRepository,
        object_type: KnowledgeObjectType | None = None,
    ) -> tuple[KnowledgeStatistics, ...]:
        grouped: dict[tuple[KnowledgeObjectType, str], list[KnowledgeRecord]] = {}
        for record in repository.records(object_type=object_type):
            grouped.setdefault(record.key(), []).append(record)
        return tuple(self.summarize(tuple(records)) for records in grouped.values())

    def _outcome_stability(self, records: tuple[KnowledgeRecord, ...]) -> float:
        if len(records) <= 1:
            return 0.5
        success_rate = sum(record.outcome == KnowledgeOutcome.SUCCESS for record in records) / len(records)
        return 1.0 - min(success_rate, 1.0 - success_rate) * 2.0


class KnowledgeScoringEngine:
    def score(self, statistics: KnowledgeStatistics) -> KnowledgeScore:
        evidence_factor = min(statistics.evidence_count / 30.0, 1.0)
        metric_factor = statistics.average_metric if statistics.average_metric is not None else statistics.success_rate
        raw_score = (statistics.success_rate * 0.45) + (statistics.stability * 0.30) + (metric_factor * 0.15) + (evidence_factor * 0.10)
        score = round(max(0.0, min(raw_score, 1.0)), 4)

        if statistics.success_rate < 0.35 and statistics.evidence_count >= 5:
            recommendation = RecommendationLevel.IGNORE
        elif score >= 0.75:
            recommendation = RecommendationLevel.HIGH
        elif score >= 0.55:
            recommendation = RecommendationLevel.MEDIUM
        else:
            recommendation = RecommendationLevel.LOW

        return KnowledgeScore(
            object_type=statistics.object_type,
            object_id=statistics.object_id,
            success_rate=statistics.success_rate,
            stability=statistics.stability,
            evidence_count=statistics.evidence_count,
            score=score,
            recommendation=recommendation,
        )

    def score_repository(
        self,
        repository: KnowledgeRepository,
        object_type: KnowledgeObjectType | None = None,
    ) -> tuple[KnowledgeScore, ...]:
        statistics_engine = KnowledgeStatisticsEngine()
        scores = [
            self.score(statistics)
            for statistics in statistics_engine.summarize_repository(repository, object_type=object_type)
        ]
        return tuple(sorted(scores, key=lambda score: score.score, reverse=True))


class RecommendationEngine:
    def __init__(self, scoring_engine: KnowledgeScoringEngine | None = None) -> None:
        self._scoring_engine = scoring_engine or KnowledgeScoringEngine()

    def best_features(self, repository: KnowledgeRepository, limit: int = 5) -> tuple[KnowledgeScore, ...]:
        return self._top(repository, KnowledgeObjectType.FEATURE, limit)

    def best_plugins(self, repository: KnowledgeRepository, limit: int = 5) -> tuple[KnowledgeScore, ...]:
        return self._top(repository, KnowledgeObjectType.PLUGIN, limit)

    def unstable_parameters(self, repository: KnowledgeRepository, limit: int = 5) -> tuple[KnowledgeScore, ...]:
        scores = self._scoring_engine.score_repository(repository, KnowledgeObjectType.PARAMETER)
        unstable = [score for score in scores if score.stability < 0.6 or score.recommendation == RecommendationLevel.IGNORE]
        return tuple(sorted(unstable, key=lambda score: (score.stability, -score.evidence_count))[:limit])

    def best_regimes(self, repository: KnowledgeRepository, limit: int = 5) -> tuple[KnowledgeScore, ...]:
        return self._top(repository, KnowledgeObjectType.REGIME, limit)

    def recommend_next_experiments(self, repository: KnowledgeRepository, limit: int = 5) -> tuple[str, ...]:
        best_features = self.best_features(repository, limit=3)
        best_plugins = self.best_plugins(repository, limit=3)
        best_regimes = self.best_regimes(repository, limit=3)
        ignored_plugins = [
            score.object_id
            for score in self._scoring_engine.score_repository(repository, KnowledgeObjectType.PLUGIN)
            if score.recommendation == RecommendationLevel.IGNORE
        ]

        recommendations: list[str] = []
        for regime in best_regimes:
            for plugin in best_plugins:
                if plugin.object_id in ignored_plugins:
                    continue
                feature_hint = best_features[0].object_id if best_features else "top_feature_set"
                recommendations.append(
                    f"Test {plugin.object_id} with {feature_hint} during {regime.object_id} regime."
                )
                if len(recommendations) >= limit:
                    return tuple(recommendations)

        if not recommendations:
            recommendations.append("Collect more experiment evidence before generating knowledge-guided strategies.")
        return tuple(recommendations[:limit])

    def _top(
        self,
        repository: KnowledgeRepository,
        object_type: KnowledgeObjectType,
        limit: int,
    ) -> tuple[KnowledgeScore, ...]:
        scores = self._scoring_engine.score_repository(repository, object_type)
        recommended = [
            score
            for score in scores
            if score.recommendation in {RecommendationLevel.HIGH, RecommendationLevel.MEDIUM}
        ]
        return tuple(recommended[:limit])


class KnowledgeEngine:
    """Collects experiment results and updates research knowledge."""

    def __init__(self, repository: KnowledgeRepository | None = None) -> None:
        self.repository = repository or KnowledgeRepository()
        self.statistics = KnowledgeStatisticsEngine()
        self.scoring = KnowledgeScoringEngine()
        self.recommendations = RecommendationEngine(self.scoring)

    def collect_results(self, result: ExperimentResultKnowledge) -> tuple[KnowledgeRecord, ...]:
        records: list[KnowledgeRecord] = [
            self._record(
                result,
                KnowledgeObjectType.EXPERIMENT,
                result.experiment_id,
                metric_value=1.0 if result.outcome == KnowledgeOutcome.SUCCESS else 0.0,
            )
        ]

        for feature, importance in result.feature_importance.items():
            records.append(
                self._record(
                    result,
                    KnowledgeObjectType.FEATURE,
                    feature,
                    metric_value=importance,
                    importance=importance,
                    stability=result.feature_stability.get(feature),
                )
            )
        for plugin, success_rate in result.plugin_success.items():
            records.append(self._record(result, KnowledgeObjectType.PLUGIN, plugin, metric_value=success_rate))
        for parameter, payload in result.parameter_scores.items():
            records.append(
                self._record(
                    result,
                    KnowledgeObjectType.PARAMETER,
                    parameter,
                    metric_value=float(payload.get("score", 0.0)),
                    stability=payload.get("stability"),
                    context={key: value for key, value in payload.items() if key not in {"score", "stability"}},
                )
            )
        for template, success_rate in result.template_success.items():
            records.append(self._record(result, KnowledgeObjectType.TEMPLATE, template, metric_value=success_rate))
        for regime, success_rate in result.regime_success.items():
            records.append(self._record(result, KnowledgeObjectType.REGIME, regime, metric_value=success_rate))
        if result.instrument:
            records.append(self._record(result, KnowledgeObjectType.INSTRUMENT, result.instrument))

        for record in records:
            self.repository.add_record(record)
        self._update_hypothesis(result)
        return tuple(records)

    def dashboard_payload(self) -> dict[str, Any]:
        return {
            "best_features": [_score_payload(score) for score in self.recommendations.best_features(self.repository)],
            "best_plugins": [_score_payload(score) for score in self.recommendations.best_plugins(self.repository)],
            "unstable_parameters": [
                _score_payload(score) for score in self.recommendations.unstable_parameters(self.repository)
            ],
            "best_regimes": [_score_payload(score) for score in self.recommendations.best_regimes(self.repository)],
            "next_experiments": list(self.recommendations.recommend_next_experiments(self.repository)),
            "hypotheses": [_serialize_dataclass(hypothesis) for hypothesis in self.repository.hypotheses()],
        }

    def report(self) -> KnowledgeReport:
        return KnowledgeReport(
            best_features=self.recommendations.best_features(self.repository),
            best_plugins=self.recommendations.best_plugins(self.repository),
            unstable_parameters=self.recommendations.unstable_parameters(self.repository),
            best_regimes=self.recommendations.best_regimes(self.repository),
            next_experiments=self.recommendations.recommend_next_experiments(self.repository),
        )

    def _record(
        self,
        result: ExperimentResultKnowledge,
        object_type: KnowledgeObjectType,
        object_id: str,
        metric_value: float | None = None,
        stability: float | None = None,
        importance: float | None = None,
        context: dict[str, Any] | None = None,
    ) -> KnowledgeRecord:
        return KnowledgeRecord(
            object_type=object_type,
            object_id=object_id,
            outcome=result.outcome,
            experiment_id=result.experiment_id,
            hypothesis_id=result.hypothesis_id,
            instrument=result.instrument,
            timeframe=result.timeframe,
            regime=result.regime,
            session=result.session,
            metric_value=metric_value,
            stability=stability,
            importance=importance,
            lessons=result.lessons,
            context=context or {},
        )

    def _update_hypothesis(self, result: ExperimentResultKnowledge) -> None:
        if not result.hypothesis_id:
            return

        existing = self.repository.hypothesis(result.hypothesis_id)
        statement = result.hypothesis_statement or (existing.statement if existing else result.hypothesis_id)
        experiment_ids = tuple(dict.fromkeys((existing.experiment_ids if existing else ()) + (result.experiment_id,)))
        supported = (existing.supported_count if existing else 0) + int(result.outcome == KnowledgeOutcome.SUCCESS)
        rejected = (existing.rejected_count if existing else 0) + int(result.outcome == KnowledgeOutcome.FAILURE)
        total = max(supported + rejected, 1)
        confidence = round(abs(supported - rejected) / total, 4)
        if supported and rejected:
            status = HypothesisStatus.MIXED
        elif supported:
            status = HypothesisStatus.SUPPORTED
        elif rejected:
            status = HypothesisStatus.REJECTED
        else:
            status = HypothesisStatus.PROPOSED

        self.repository.upsert_hypothesis(
            Hypothesis(
                hypothesis_id=result.hypothesis_id,
                statement=statement,
                experiment_ids=experiment_ids,
                supported_count=supported,
                rejected_count=rejected,
                confidence=confidence,
                status=status,
            )
        )


@dataclass(frozen=True, slots=True)
class KnowledgeReport:
    best_features: tuple[KnowledgeScore, ...]
    best_plugins: tuple[KnowledgeScore, ...]
    unstable_parameters: tuple[KnowledgeScore, ...]
    best_regimes: tuple[KnowledgeScore, ...]
    next_experiments: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "best_features": [_score_payload(score) for score in self.best_features],
            "best_plugins": [_score_payload(score) for score in self.best_plugins],
            "unstable_parameters": [_score_payload(score) for score in self.unstable_parameters],
            "best_regimes": [_score_payload(score) for score in self.best_regimes],
            "next_experiments": list(self.next_experiments),
        }


def build_demo_knowledge_engine() -> KnowledgeEngine:
    engine = KnowledgeEngine()
    engine.collect_results(
        ExperimentResultKnowledge(
            experiment_id="exp_eurusd_h1_trend_pullback_001",
            outcome=KnowledgeOutcome.SUCCESS,
            hypothesis_id="hyp_trend_pullback_london",
            hypothesis_statement="Trend pullbacks outperform breakouts during London sessions on major pairs.",
            instrument="EUR_USD",
            timeframe="H1",
            regime="TRENDING",
            session="London",
            lessons=("Trend pullback works well in trending London conditions.",),
            feature_importance={"trend_strength": 0.86, "pullback_state": 0.78},
            feature_stability={"trend_strength": 0.91, "pullback_state": 0.84},
            plugin_success={"ema_pullback": 0.82, "asian_breakout": 0.22},
            parameter_scores={
                "ema_fast=20": {"score": 0.79, "stability": 0.88, "beats": "ema_fast=10"},
                "rsi_threshold=30": {"score": 0.24, "stability": 0.42},
            },
            template_success={"trend_pullback": 0.81, "breakout": 0.31},
            regime_success={"TRENDING": 0.84, "RANGING": 0.29},
        )
    )
    engine.collect_results(
        ExperimentResultKnowledge(
            experiment_id="exp_usdjpy_m1_rsi_001",
            outcome=KnowledgeOutcome.FAILURE,
            hypothesis_id="hyp_rsi_m1_reversal",
            hypothesis_statement="RSI oversold reversal works on USD_JPY M1.",
            instrument="USD_JPY",
            timeframe="M1",
            regime="RANGING",
            session="Asian",
            lessons=("RSI < 30 fails on USD_JPY M1 in Asian session.",),
            feature_importance={"rsi_oversold": 0.18},
            feature_stability={"rsi_oversold": 0.33},
            plugin_success={"rsi_reversal": 0.21, "asian_breakout": 0.18},
            parameter_scores={"rsi_threshold=30": {"score": 0.18, "stability": 0.35}},
            template_success={"mean_reversion": 0.24, "breakout": 0.19},
            regime_success={"RANGING": 0.32},
        )
    )
    engine.collect_results(
        ExperimentResultKnowledge(
            experiment_id="exp_eurusd_h1_trend_pullback_002",
            outcome=KnowledgeOutcome.SUCCESS,
            hypothesis_id="hyp_trend_pullback_london",
            hypothesis_statement="Trend pullbacks outperform breakouts during London sessions on major pairs.",
            instrument="EUR_USD",
            timeframe="H1",
            regime="TRENDING",
            session="London",
            lessons=("EMA pullback remained stable in repeated trending tests.",),
            feature_importance={"trend_strength": 0.84, "pullback_state": 0.76},
            feature_stability={"trend_strength": 0.9, "pullback_state": 0.83},
            plugin_success={"ema_pullback": 0.83},
            parameter_scores={"ema_fast=20": {"score": 0.8, "stability": 0.9, "beats": "ema_fast=10"}},
            template_success={"trend_pullback": 0.82},
            regime_success={"TRENDING": 0.85},
        )
    )
    return engine


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _unique(values: Any) -> tuple[str, ...]:
    return tuple(sorted({str(value) for value in values if value is not None and str(value)}))


def _serialize_dataclass(value: Any) -> dict[str, Any]:
    payload = asdict(value)
    for key, item in payload.items():
        if isinstance(item, StrEnum):
            payload[key] = item.value
        elif isinstance(item, datetime):
            payload[key] = item.isoformat()
    return payload


def _knowledge_record_from_json(payload: dict[str, Any]) -> KnowledgeRecord:
    return KnowledgeRecord(
        object_type=KnowledgeObjectType(payload["object_type"]),
        object_id=payload["object_id"],
        outcome=KnowledgeOutcome(payload["outcome"]),
        experiment_id=payload["experiment_id"],
        hypothesis_id=payload.get("hypothesis_id"),
        instrument=payload.get("instrument"),
        timeframe=payload.get("timeframe"),
        regime=payload.get("regime"),
        session=payload.get("session"),
        metric_name=payload.get("metric_name", "success_rate"),
        metric_value=payload.get("metric_value"),
        stability=payload.get("stability"),
        importance=payload.get("importance"),
        sample_size=payload.get("sample_size", 1),
        lessons=tuple(payload.get("lessons", ())),
        context=payload.get("context", {}),
        created_at=datetime.fromisoformat(payload["created_at"]),
        version=payload.get("version", "1.0.0"),
    )


def _hypothesis_from_json(payload: dict[str, Any]) -> Hypothesis:
    return Hypothesis(
        hypothesis_id=payload["hypothesis_id"],
        statement=payload["statement"],
        created_at=datetime.fromisoformat(payload["created_at"]),
        experiment_ids=tuple(payload.get("experiment_ids", ())),
        supported_count=payload.get("supported_count", 0),
        rejected_count=payload.get("rejected_count", 0),
        confidence=payload.get("confidence", 0.0),
        status=HypothesisStatus(payload.get("status", HypothesisStatus.PROPOSED)),
    )


def _score_payload(score: KnowledgeScore) -> dict[str, Any]:
    return {
        "object_type": score.object_type.value,
        "object_id": score.object_id,
        "success_rate": score.success_rate,
        "stability": score.stability,
        "evidence_count": score.evidence_count,
        "score": score.score,
        "recommendation": score.recommendation.value,
    }
