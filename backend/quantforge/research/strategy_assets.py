from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from quantforge.validation import (
    DeploymentDecision,
    StrategyAsset,
    StrategyPassport,
    ValidationGateResult,
    ValidationGateStatus,
    ValidationReport,
)


class ApprovedStrategyAssetStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    PAPER_ELIGIBLE = "PAPER_ELIGIBLE"
    PRODUCTION_ELIGIBLE = "PRODUCTION_ELIGIBLE"
    RETIRED = "RETIRED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class ApprovedStrategyAsset:
    strategy_asset_id: str
    strategy_id: str
    strategy_version: str
    strategy_name: str
    pair: str
    timeframe: str
    market_regime: str
    strategy_family: str
    template: str
    entry_plugin: str
    confirmation_plugins: tuple[str, ...]
    exit_plugin: str
    risk_model: str
    trade_management_model: str
    parameters: dict[str, Any]
    feature_versions: dict[str, str]
    plugin_versions: dict[str, str]
    optimization_report_id: str
    validation_report_id: str
    strategy_passport_id: str
    decision_trace_id: str
    confidence_score: float
    profit_factor: float
    max_drawdown: float
    validation_grade: str
    status: ApprovedStrategyAssetStatus
    created_at: str
    approved_at: str
    source_experiment_id: str
    source_workflow_id: str
    source_job_id: str = ""
    source_validation_id: str = ""
    source_publication_id: str = ""
    strategy_definition: dict[str, Any] = field(default_factory=dict)
    optimization_report: dict[str, Any] = field(default_factory=dict)
    validation_report: dict[str, Any] = field(default_factory=dict)
    strategy_passport: dict[str, Any] = field(default_factory=dict)
    decision_trace: tuple[str, ...] = ()

    @property
    def deployable(self) -> bool:
        return self.status in {
            ApprovedStrategyAssetStatus.APPROVED,
            ApprovedStrategyAssetStatus.PAPER_ELIGIBLE,
            ApprovedStrategyAssetStatus.PRODUCTION_ELIGIBLE,
        }


class StrategyAssetRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def list(self) -> tuple[ApprovedStrategyAsset, ...]:
        payload = self._load()
        return tuple(_asset_from_payload(item) for item in payload.get("assets", []))

    def get(self, strategy_asset_id: str) -> ApprovedStrategyAsset:
        for asset in self.list():
            if asset.strategy_asset_id == strategy_asset_id or asset.strategy_id == strategy_asset_id:
                return asset
        raise KeyError(strategy_asset_id)

    def upsert(self, asset: ApprovedStrategyAsset) -> None:
        payload = self._load()
        items = [item for item in payload.get("assets", []) if item.get("strategy_asset_id") != asset.strategy_asset_id]
        items.append(_asset_to_payload(asset))
        payload["assets"] = sorted(items, key=lambda item: str(item.get("approved_at", "")), reverse=True)
        self._save(payload)

    def upsert_many(self, assets: tuple[ApprovedStrategyAsset, ...]) -> None:
        payload = self._load()
        by_id = {str(item.get("strategy_asset_id")): item for item in payload.get("assets", [])}
        for asset in assets:
            by_id[asset.strategy_asset_id] = _asset_to_payload(asset)
        payload["assets"] = sorted(by_id.values(), key=lambda item: str(item.get("approved_at", "")), reverse=True)
        self._save(payload)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "assets": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


class ApprovedStrategyAssetStore:
    def __init__(self, repository: StrategyAssetRepository) -> None:
        self.repository = repository

    def publish(
        self,
        asset: StrategyAsset,
        *,
        source_experiment_id: str = "",
        source_workflow_id: str = "",
        source_job_id: str = "",
        source_publication_id: str = "",
        status: ApprovedStrategyAssetStatus = ApprovedStrategyAssetStatus.APPROVED,
    ) -> ApprovedStrategyAsset:
        record = approved_asset_from_strategy_asset(
            asset,
            source_experiment_id=source_experiment_id,
            source_workflow_id=source_workflow_id,
            source_job_id=source_job_id,
            source_publication_id=source_publication_id,
            status=status,
        )
        self.repository.upsert(record)
        return record


class StrategyAssetPersistenceService:
    def __init__(self, store: ApprovedStrategyAssetStore) -> None:
        self.store = store

    def persist_many(
        self,
        assets: tuple[StrategyAsset, ...],
        *,
        source_workflow_id: str = "",
        source_experiment_ids: tuple[str, ...] = (),
    ) -> tuple[ApprovedStrategyAsset, ...]:
        records = tuple(
            self.store.publish(
                asset,
                source_workflow_id=source_workflow_id,
                source_experiment_id=source_experiment_ids[index] if index < len(source_experiment_ids) else "",
            )
            for index, asset in enumerate(assets)
        )
        return records


class StrategyAssetLoader:
    def __init__(self, repository: StrategyAssetRepository) -> None:
        self.repository = repository

    def load_strategy_asset(self, strategy_asset_id: str) -> StrategyAsset:
        return strategy_asset_from_approved(self.repository.get(strategy_asset_id))


class StrategyLibraryLoader:
    def __init__(self, repository: StrategyAssetRepository) -> None:
        self.repository = repository

    def load(self):
        from quantforge.research.library import (
            InstitutionalStrategyLibraryResult,
            StrategyLibraryDashboard,
            StrategyLibraryReport,
            StrategyLibraryStatus,
            StrategyLibraryTargets,
        )

        records = tuple(asset for asset in self.repository.list() if asset.deployable)
        assets = tuple(_library_asset_from_record(record) for record in records)
        production_grade = tuple(
            asset for asset in assets if asset.status in {"APPROVED", "PAPER_ELIGIBLE", "PRODUCTION_ELIGIBLE"}
        )
        targets = StrategyLibraryTargets(
            planned_experiments=0,
            planned_validated_strategy_assets=len(assets),
            planned_production_grade_strategies=len(production_grade),
        )
        kpis = _kpis(assets, production_grade)
        dashboard = StrategyLibraryDashboard(
            status=StrategyLibraryStatus.COMPLETE if assets else StrategyLibraryStatus.BLOCKED,
            experiments_progress="Persisted asset store",
            validated_assets=len(assets),
            production_grade_strategies=len(production_grade),
            families=tuple(sorted({asset.family.value for asset in assets})),
            top_templates=tuple(asset.template for asset in production_grade[:10]),
            feature_importance={},
            portfolio_readiness="READY_FOR_PORTFOLIO_CONSTRUCTION" if production_grade else "WAITING_FOR_APPROVED_ASSETS",
        )
        report = StrategyLibraryReport(
            title="Approved Strategy Asset Store",
            library_summary=f"{len(assets)} persisted approved Strategy Assets loaded.",
            research_statistics={
                "experiments": 0,
                "candidates": 0,
                "optimized": 0,
                "validated_assets": len(assets),
                "production_grade": len(production_grade),
            },
            production_grade_summary=f"{len(production_grade)} Strategy Assets are deployable.",
            lessons_learned=("Strategy Library is repository-backed; demo assets require explicit demo mode.",),
            archived=True,
        )
        return InstitutionalStrategyLibraryResult(
            targets=targets,
            programs=(),
            validated_assets=assets,
            production_grade_strategies=production_grade,
            kpis=kpis,
            dashboard=dashboard,
            report=report,
            audit_trail=("approved_strategy_asset_store_loaded",),
            reproducibility_key=f"persisted:{len(assets)}",
        )


def default_strategy_asset_repository(repo_root: Path | None = None) -> StrategyAssetRepository:
    root = repo_root or Path(__file__).resolve().parents[3]
    return StrategyAssetRepository(root / "var" / "approved_strategy_assets.json")


def approved_asset_from_strategy_asset(
    asset: StrategyAsset,
    *,
    source_experiment_id: str = "",
    source_workflow_id: str = "",
    source_job_id: str = "",
    source_publication_id: str = "",
    status: ApprovedStrategyAssetStatus = ApprovedStrategyAssetStatus.APPROVED,
) -> ApprovedStrategyAsset:
    summary = dict(asset.strategy_definition)
    validation_payload = asset.validation_report.to_dict()
    passport_payload = validation_payload["passport"]
    now = datetime.now(UTC).isoformat()
    template = str(summary.get("template") or asset.passport.template)
    pair = str(summary.get("pair") or summary.get("instrument") or "UNKNOWN")
    timeframe = str(summary.get("timeframe") or "UNKNOWN")
    plugin_versions = dict(asset.plugin_versions)
    return ApprovedStrategyAsset(
        strategy_asset_id=asset.passport.strategy_id,
        strategy_id=asset.passport.strategy_id,
        strategy_version=asset.passport.version,
        strategy_name=f"{template} {timeframe}".strip(),
        pair=pair,
        timeframe=timeframe,
        market_regime=str(summary.get("market_regime") or asset.passport.market_regime).upper(),
        strategy_family=str(summary.get("family") or summary.get("strategy_family") or "TREND_FOLLOWING"),
        template=template,
        entry_plugin=plugin_versions.get("entry", ""),
        confirmation_plugins=tuple(
            item
            for key, item in plugin_versions.items()
            if key.startswith("confirmation") or key == "confirmation"
        ),
        exit_plugin=plugin_versions.get("exit", ""),
        risk_model=plugin_versions.get("risk", ""),
        trade_management_model=str(summary.get("trade_management_model") or "default"),
        parameters=dict(asset.parameters),
        feature_versions=dict(asset.feature_versions),
        plugin_versions=plugin_versions,
        optimization_report_id=f"{asset.passport.strategy_id}:optimization",
        validation_report_id=asset.validation_report.strategy_id,
        strategy_passport_id=f"{asset.passport.strategy_id}:passport",
        decision_trace_id=f"{asset.passport.strategy_id}:decision_trace",
        confidence_score=asset.validation_report.confidence,
        profit_factor=float(asset.validation_report.walk_forward.windows[0].get("profit_factor", 0.0))
        if asset.validation_report.walk_forward.windows
        else 0.0,
        max_drawdown=float(asset.validation_report.walk_forward.windows[0].get("max_drawdown", 0.0))
        if asset.validation_report.walk_forward.windows
        else 0.0,
        validation_grade=asset.validation_report.deployment_grade,
        status=status,
        created_at=passport_payload.get("created", now),
        approved_at=now,
        source_experiment_id=source_experiment_id,
        source_workflow_id=source_workflow_id,
        source_job_id=source_job_id,
        source_validation_id=asset.validation_report.strategy_id,
        source_publication_id=source_publication_id or f"{asset.passport.strategy_id}:publication",
        strategy_definition=summary,
        optimization_report=dict(asset.optimization_report),
        validation_report=validation_payload,
        strategy_passport=passport_payload,
        decision_trace=tuple(asset.decision_trace),
    )


def strategy_asset_from_approved(record: ApprovedStrategyAsset) -> StrategyAsset:
    validation = _validation_report_from_payload(record.validation_report)
    passport = validation.passport
    return StrategyAsset(
        strategy_definition=dict(record.strategy_definition),
        plugin_versions=dict(record.plugin_versions),
        parameters=dict(record.parameters),
        feature_versions=dict(record.feature_versions),
        decision_trace=tuple(record.decision_trace),
        optimization_report=dict(record.optimization_report),
        validation_report=validation,
        passport=passport,
    )


def _validation_report_from_payload(payload: dict[str, Any]) -> ValidationReport:
    passport_payload = payload["passport"]
    passport = StrategyPassport(
        strategy_id=str(passport_payload["strategy_id"]),
        created=date.fromisoformat(str(passport_payload["created"])),
        template=str(passport_payload["template"]),
        market_regime=str(passport_payload["market_regime"]),
        validation_grade=str(passport_payload["validation_grade"]),
        confidence=float(passport_payload["confidence"]),
        production=bool(passport_payload["production"]),
        version=str(passport_payload["version"]),
    )
    return ValidationReport(
        strategy_id=str(payload["strategy_id"]),
        strategy_summary=dict(payload["strategy_summary"]),
        walk_forward=_gate_from_payload(payload["walk_forward"]),
        out_of_sample=_gate_from_payload(payload["out_of_sample"]),
        monte_carlo=_gate_from_payload(payload["monte_carlo"]),
        cross_pair=_gate_from_payload(payload["cross_pair"]),
        cross_timeframe=_gate_from_payload(payload["cross_timeframe"]),
        parameter_stability=_gate_from_payload(payload["parameter_stability"]),
        stress_test=_gate_from_payload(payload["stress_test"]),
        confidence=float(payload["confidence"]),
        deployment_grade=str(payload["deployment_grade"]),
        deployment_decision=DeploymentDecision(str(payload["deployment_decision"])),
        recommendation=str(payload["recommendation"]),
        passport=passport,
    )


def _gate_from_payload(payload: dict[str, Any]) -> ValidationGateResult:
    return ValidationGateResult(
        name=str(payload["name"]),
        status=ValidationGateStatus(str(payload["status"])),
        score=float(payload["score"]),
        details=dict(payload.get("details", {})),
        windows=tuple(dict(item) for item in payload.get("windows", [])),
        reasons=tuple(str(item) for item in payload.get("reasons", [])),
    )


def _asset_to_payload(asset: ApprovedStrategyAsset) -> dict[str, Any]:
    payload = asdict(asset)
    payload["status"] = asset.status.value
    payload["confirmation_plugins"] = list(asset.confirmation_plugins)
    payload["decision_trace"] = list(asset.decision_trace)
    return payload


def _asset_from_payload(payload: dict[str, Any]) -> ApprovedStrategyAsset:
    return ApprovedStrategyAsset(
        **{
            **payload,
            "status": ApprovedStrategyAssetStatus(str(payload["status"])),
            "confirmation_plugins": tuple(payload.get("confirmation_plugins", [])),
            "decision_trace": tuple(payload.get("decision_trace", [])),
        }
    )


def _library_asset_from_record(record: ApprovedStrategyAsset):
    from quantforge.research.library import StrategyLibraryAsset

    return StrategyLibraryAsset(
        asset_id=record.strategy_asset_id,
        family=_family(record.strategy_family),
        template=record.template,
        timeframe=record.timeframe,
        instruments=(record.pair,),
        validation_grade=record.validation_grade,
        confidence=record.confidence_score,
        profit_factor=record.profit_factor,
        max_drawdown=record.max_drawdown,
        walk_forward=str(record.validation_report.get("walk_forward", {}).get("status", "PASS")),
        monte_carlo=str(record.validation_report.get("monte_carlo", {}).get("status", "PASS")),
        cross_pair=str(record.validation_report.get("cross_pair", {}).get("status", "PASS")),
        cross_timeframe=str(record.validation_report.get("cross_timeframe", {}).get("status", "PASS")),
        stress_test=str(record.validation_report.get("stress_test", {}).get("status", "PASS")),
        decision_trace_complete=bool(record.decision_trace),
        strategy_passport_present=bool(record.strategy_passport),
        reproducibility_key=f"{record.source_workflow_id}:{record.source_experiment_id}:{record.strategy_asset_id}",
        production_grade=record.deployable,
        status=record.status.value,
        source_workflow_id=record.source_workflow_id,
        source_job_id=record.source_job_id,
        source_experiment_id=record.source_experiment_id,
        source_validation_id=record.source_validation_id,
        source_publication_id=record.source_publication_id,
        approved_at=record.approved_at,
        strategy_version=record.strategy_version,
        demo_mode=False,
    )


def _family(value: str):
    from quantforge.research.campaign import ResearchProgramFamily

    normalized = value.upper()
    if normalized in ResearchProgramFamily.__members__:
        return ResearchProgramFamily[normalized]
    for family in ResearchProgramFamily:
        if family.value.upper() == normalized:
            return family
    return ResearchProgramFamily.TREND_FOLLOWING


def _kpis(
    assets: tuple[Any, ...],
    production_grade: tuple[Any, ...],
):
    from quantforge.research.library import StrategyLibraryKPIReport

    return StrategyLibraryKPIReport(
        experiments_executed=0,
        candidate_strategies=0,
        optimized_strategies=0,
        validated_strategy_assets=len(assets),
        production_grade_strategies=len(production_grade),
        validation_pass_rate=1.0 if assets else 0.0,
        research_throughput_per_hour=0,
        knowledge_records_written=0,
        average_confidence=round(sum(asset.confidence for asset in assets) / len(assets), 3) if assets else 0.0,
        average_profit_factor=round(sum(asset.profit_factor for asset in assets) / len(assets), 2) if assets else 0.0,
        max_observed_drawdown=max((asset.max_drawdown for asset in assets), default=0.0),
    )
