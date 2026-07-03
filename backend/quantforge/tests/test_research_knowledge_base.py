from pathlib import Path

from quantforge.research import (
    ExperimentResultKnowledge,
    HypothesisStatus,
    KnowledgeEngine,
    KnowledgeObjectType,
    KnowledgeOutcome,
    KnowledgeRepository,
    KnowledgeScoringEngine,
    KnowledgeStatisticsEngine,
    RecommendationLevel,
    build_demo_knowledge_engine,
)


def test_collects_experiment_feature_plugin_parameter_and_template_knowledge() -> None:
    engine = KnowledgeEngine()

    records = engine.collect_results(
        ExperimentResultKnowledge(
            experiment_id="exp_001",
            outcome=KnowledgeOutcome.SUCCESS,
            hypothesis_id="hyp_001",
            hypothesis_statement="Trend pullbacks work in London trending markets.",
            instrument="EUR_USD",
            timeframe="H1",
            regime="TRENDING",
            session="London",
            lessons=("Trend pullback works well.",),
            feature_importance={"trend_strength": 0.82},
            feature_stability={"trend_strength": 0.91},
            plugin_success={"ema_pullback": 0.78},
            parameter_scores={"ema_fast=20": {"score": 0.75, "stability": 0.88, "beats": "ema_fast=10"}},
            template_success={"trend_pullback": 0.8},
            regime_success={"TRENDING": 0.83},
        )
    )

    object_types = {record.object_type for record in records}
    assert KnowledgeObjectType.EXPERIMENT in object_types
    assert KnowledgeObjectType.FEATURE in object_types
    assert KnowledgeObjectType.PLUGIN in object_types
    assert KnowledgeObjectType.PARAMETER in object_types
    assert KnowledgeObjectType.TEMPLATE in object_types
    assert KnowledgeObjectType.REGIME in object_types
    assert KnowledgeObjectType.INSTRUMENT in object_types

    hypothesis = engine.repository.hypothesis("hyp_001")
    assert hypothesis is not None
    assert hypothesis.status == HypothesisStatus.SUPPORTED
    assert hypothesis.confidence == 1.0


def test_statistics_and_scoring_produce_high_recommendation_for_stable_success() -> None:
    engine = build_demo_knowledge_engine()
    stats = KnowledgeStatisticsEngine().summarize(engine.repository.records(KnowledgeObjectType.PLUGIN, "ema_pullback"))
    score = KnowledgeScoringEngine().score(stats)

    assert stats.success_rate == 1.0
    assert stats.average_metric == 0.825
    assert score.recommendation == RecommendationLevel.HIGH
    assert score.score > 0.75


def test_recommendation_engine_reports_best_features_plugins_regimes_and_unstable_parameters() -> None:
    engine = build_demo_knowledge_engine()
    report = engine.report()

    assert report.best_features[0].object_id == "trend_strength"
    assert report.best_plugins[0].object_id == "ema_pullback"
    assert report.best_regimes[0].object_id == "TRENDING"
    assert any(score.object_id == "rsi_threshold=30" for score in report.unstable_parameters)
    assert "ema_pullback" in report.next_experiments[0]


def test_dashboard_payload_is_json_ready() -> None:
    engine = build_demo_knowledge_engine()

    payload = engine.dashboard_payload()

    assert payload["best_features"]
    assert payload["best_plugins"]
    assert payload["unstable_parameters"]
    assert payload["best_regimes"]
    assert payload["next_experiments"]
    assert payload["hypotheses"]


def test_repository_persists_and_loads_json(tmp_path: Path) -> None:
    engine = build_demo_knowledge_engine()
    path = tmp_path / "knowledge.json"

    engine.repository.save_json(path)
    loaded = KnowledgeRepository.load_json(path)

    assert len(loaded.records()) == len(engine.repository.records())
    assert loaded.hypothesis("hyp_trend_pullback_london") is not None


def test_failed_hypothesis_is_rejected() -> None:
    engine = KnowledgeEngine()

    engine.collect_results(
        ExperimentResultKnowledge(
            experiment_id="exp_fail",
            outcome=KnowledgeOutcome.FAILURE,
            hypothesis_id="hyp_rsi_m1",
            hypothesis_statement="RSI < 30 works on USD_JPY M1.",
            plugin_success={"rsi_reversal": 0.18},
        )
    )

    hypothesis = engine.repository.hypothesis("hyp_rsi_m1")
    assert hypothesis is not None
    assert hypothesis.status == HypothesisStatus.REJECTED
