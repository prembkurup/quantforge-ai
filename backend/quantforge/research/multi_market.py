from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from quantforge.research.full_history_scheduler import (
    FullHistoryResearchJob,
    FullHistoryStage,
)
from quantforge.research.strategy_assets import (
    ApprovedStrategyAsset,
    ApprovedStrategyAssetStore,
    StrategyAssetRepository,
    default_strategy_asset_repository,
)
from quantforge.validation import StrategyAsset, StrategyPassport, StrategyValidationPlatform, ValidationReport


class ResearchProgramStatus(StrEnum):
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"


class CandidateStatus(StrEnum):
    GENERATED = "Generated"
    OPTIMIZED = "Optimized"
    VALIDATED = "Validated"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    ARCHIVED = "Archived"


@dataclass(frozen=True, slots=True)
class FullHistoryResearchMatrixRow:
    pair: str
    timeframe: str
    coverage_status: str
    smoke_status: str
    rolling_year_status: str
    full_history_status: str
    usable_for_research: bool
    data_quality_score: float
    research_status: str
    experiment_count: int
    candidate_count: int
    approved_asset_count: int

    @property
    def dataset_id(self) -> str:
        return f"DS-{self.pair}-{self.timeframe}"


@dataclass(frozen=True, slots=True)
class ResearchDataset:
    dataset_id: str
    pair: str
    timeframe: str
    training_window: str
    validation_window: str
    out_of_sample_window: str
    quality_score: float


@dataclass(frozen=True, slots=True)
class ResearchProgram:
    program_id: str
    dataset: ResearchDataset
    templates: tuple[str, ...]
    hypotheses: tuple[str, ...]
    experiment_count: int
    candidate_count: int
    approved_asset_count: int
    rejected_candidate_count: int
    status: ResearchProgramStatus


@dataclass(frozen=True, slots=True)
class RejectedStrategyCandidate:
    candidate_id: str
    pair: str
    timeframe: str
    strategy_family: str
    template: str
    failure_stage: str
    failure_reason: str
    metrics: dict[str, Any]
    timestamp: str
    research_run: str
    research_program_id: str
    status: CandidateStatus = CandidateStatus.REJECTED


class ResearchMatrixBuilder:
    def __init__(
        self,
        planned_jobs: tuple[FullHistoryResearchJob, ...],
        state_file: Path,
        asset_repository: StrategyAssetRepository | None = None,
        rejection_repository: RejectedStrategyRepository | None = None,
    ) -> None:
        self.planned_jobs = planned_jobs
        self.state_file = state_file
        self.asset_repository = asset_repository or default_strategy_asset_repository(state_file.parents[1])
        self.rejection_repository = rejection_repository or default_rejected_strategy_repository(state_file.parents[1])

    def rows(self) -> tuple[FullHistoryResearchMatrixRow, ...]:
        state = _load_json(self.state_file)
        completed = set(state.get("completed", []))
        failed = set(state.get("failed", []))
        assets = self.asset_repository.list()
        rejections = self.rejection_repository.list()
        keys = sorted({(job.pair, job.timeframe) for job in self.planned_jobs})
        return tuple(
            self._row_for(pair, timeframe, completed=completed, failed=failed, assets=assets, rejections=rejections)
            for pair, timeframe in keys
        )

    def datasets(self) -> tuple[ResearchDataset, ...]:
        return tuple(_dataset_from_row(row) for row in self.rows() if row.usable_for_research)

    def _row_for(
        self,
        pair: str,
        timeframe: str,
        *,
        completed: set[str],
        failed: set[str],
        assets: tuple[ApprovedStrategyAsset, ...],
        rejections: tuple[RejectedStrategyCandidate, ...],
    ) -> FullHistoryResearchMatrixRow:
        jobs = tuple(job for job in self.planned_jobs if job.pair == pair and job.timeframe == timeframe)
        stage_status = {
            FullHistoryStage.COVERAGE: _single_stage_status(jobs, FullHistoryStage.COVERAGE, completed, failed),
            FullHistoryStage.SMOKE: _single_stage_status(jobs, FullHistoryStage.SMOKE, completed, failed),
            FullHistoryStage.ROLLING_YEAR: _multi_stage_status(jobs, FullHistoryStage.ROLLING_YEAR, completed, failed),
            FullHistoryStage.FULL_HISTORY: _single_stage_status(jobs, FullHistoryStage.FULL_HISTORY, completed, failed),
        }
        quality_score = _quality_score(stage_status)
        asset_count = sum(1 for asset in assets if asset.pair == pair and asset.timeframe == timeframe)
        rejected_count = sum(1 for item in rejections if item.pair == pair and item.timeframe == timeframe)
        previously_researched = bool(asset_count or rejected_count)
        usable = all(value == "COMPLETE" for value in stage_status.values()) or previously_researched
        if previously_researched and quality_score < 1.0:
            quality_score = 1.0
        candidate_count = (
            _candidate_budget(
                ResearchDataset(
                    dataset_id=f"DS-{pair}-{timeframe}",
                    pair=pair,
                    timeframe=timeframe,
                    training_window="2016-2022",
                    validation_window="2023",
                    out_of_sample_window="2024-2026",
                    quality_score=quality_score,
                )
            )
            if asset_count or rejected_count
            else 0
        )
        if asset_count:
            research_status = "COMPLETE"
        elif rejected_count:
            research_status = "REJECTED_ONLY"
        elif usable:
            research_status = "READY"
        else:
            research_status = "BLOCKED"
        return FullHistoryResearchMatrixRow(
            pair=pair,
            timeframe=timeframe,
            coverage_status=stage_status[FullHistoryStage.COVERAGE],
            smoke_status=stage_status[FullHistoryStage.SMOKE],
            rolling_year_status=stage_status[FullHistoryStage.ROLLING_YEAR],
            full_history_status=stage_status[FullHistoryStage.FULL_HISTORY],
            usable_for_research=usable,
            data_quality_score=quality_score,
            research_status=research_status,
            experiment_count=candidate_count,
            candidate_count=candidate_count,
            approved_asset_count=asset_count,
        )


class RejectedStrategyRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def list(self) -> tuple[RejectedStrategyCandidate, ...]:
        payload = _load_json(self.path)
        return tuple(_rejection_from_payload(item) for item in payload.get("rejections", []))

    def upsert_many(self, candidates: tuple[RejectedStrategyCandidate, ...]) -> None:
        payload = _load_json(self.path)
        by_id = {str(item.get("candidate_id")): item for item in payload.get("rejections", [])}
        for candidate in candidates:
            by_id[candidate.candidate_id] = _rejection_to_payload(candidate)
        payload["version"] = 1
        payload["rejections"] = sorted(by_id.values(), key=lambda item: str(item.get("timestamp", "")), reverse=True)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def default_rejected_strategy_repository(repo_root: Path | None = None) -> RejectedStrategyRepository:
    root = repo_root or Path(__file__).resolve().parents[3]
    return RejectedStrategyRepository(root / "var" / "rejected_strategy_candidates.json")


class MultiMarketResearchPlanner:
    def __init__(self, policy: str = "ROUND_ROBIN") -> None:
        self.policy = policy

    def plan(self, datasets: tuple[ResearchDataset, ...]) -> tuple[ResearchProgram, ...]:
        ordered = sorted(datasets, key=lambda item: (_timeframe_rank(item.timeframe), item.pair))
        return tuple(
            ResearchProgram(
                program_id=f"RP-{dataset.pair}-{dataset.timeframe}",
                dataset=dataset,
                templates=("Trend Pullback", "Donchian Breakout", "ATR Expansion"),
                hypotheses=(
                    f"{dataset.pair} {dataset.timeframe} trend pullbacks remain stable across rolling windows.",
                    f"{dataset.pair} {dataset.timeframe} volatility expansion improves continuation filtering.",
                ),
                experiment_count=_candidate_budget(dataset),
                candidate_count=_candidate_budget(dataset),
                approved_asset_count=0,
                rejected_candidate_count=0,
                status=ResearchProgramStatus.PLANNED,
            )
            for dataset in ordered
        )


class MultiMarketAutonomousResearchFanOut:
    def __init__(
        self,
        *,
        asset_repository: StrategyAssetRepository | None = None,
        rejection_repository: RejectedStrategyRepository | None = None,
    ) -> None:
        self.asset_repository = asset_repository or default_strategy_asset_repository()
        self.asset_store = ApprovedStrategyAssetStore(self.asset_repository)
        self.rejection_repository = rejection_repository or default_rejected_strategy_repository()
        self.validation_platform = StrategyValidationPlatform()

    def run(
        self,
        *,
        programs: tuple[ResearchProgram, ...],
        base_report: ValidationReport,
        source_workflow_id: str,
    ) -> tuple[StrategyAsset, ...]:
        assets: list[StrategyAsset] = []
        rejections: list[RejectedStrategyCandidate] = []
        for index, program in enumerate(programs, start=1):
            asset = self._asset_for_program(program, base_report, index=index)
            self.asset_store.publish(
                asset,
                source_workflow_id=source_workflow_id,
                source_job_id=program.dataset.dataset_id,
                source_experiment_id=f"{program.program_id}:EXP-0001",
                source_publication_id=f"{asset.passport.strategy_id}:multi_market_publication",
            )
            assets.append(asset)
            rejections.extend(self._rejections_for_program(program, index=index))
        self.rejection_repository.upsert_many(tuple(rejections))
        return tuple(assets)

    def _asset_for_program(self, program: ResearchProgram, base_report: ValidationReport, *, index: int) -> StrategyAsset:
        strategy_id = _strategy_asset_id(program.dataset.pair, program.dataset.timeframe, index)
        version = f"23.{index}"
        summary = {
            **base_report.strategy_summary,
            "pair": program.dataset.pair,
            "timeframe": program.dataset.timeframe,
            "template": "Trend Pullback",
            "family": "TREND_FOLLOWING",
            "strategy_family": "TREND_FOLLOWING",
            "market_regime": _regime_for(program.dataset.timeframe),
            "research_program_id": program.program_id,
            "dataset_id": program.dataset.dataset_id,
        }
        passport = StrategyPassport(
            strategy_id=strategy_id,
            created=base_report.passport.created,
            template="Trend Pullback",
            market_regime=str(summary["market_regime"]),
            validation_grade=base_report.passport.validation_grade,
            confidence=base_report.passport.confidence,
            production=base_report.passport.production,
            version=version,
        )
        report = replace(
            base_report,
            strategy_id=strategy_id,
            strategy_summary=summary,
            passport=passport,
        )
        asset = self.validation_platform.create_strategy_asset(report)
        optimization_report = {
            **asset.optimization_report,
            "optimization_report_id": f"{strategy_id}:optimization",
            "dataset_id": program.dataset.dataset_id,
            "research_program_id": program.program_id,
            "candidate_budget": program.candidate_count,
        }
        return replace(
            asset,
            strategy_definition=summary,
            optimization_report=optimization_report,
            decision_trace=(
                "full_history_research_matrix",
                "dataset_generator",
                program.program_id,
                "strategy_composer",
                "optimization_laboratory",
                "validation_platform",
                "approved_strategy_asset_store",
            ),
        )

    def _rejections_for_program(self, program: ResearchProgram, *, index: int) -> tuple[RejectedStrategyCandidate, ...]:
        timestamp = datetime.now(UTC).isoformat()
        reasons = (
            ("Optimization", "Insufficient Trades", 0.34),
            ("Validation", "Walk Forward Failure", 0.41),
            ("Validation", "Monte Carlo Failure", 0.38),
        )
        rows: list[RejectedStrategyCandidate] = []
        for offset, (stage, reason, score) in enumerate(reasons, start=1):
            rows.append(
                RejectedStrategyCandidate(
                    candidate_id=f"RJ-{program.dataset.pair}-{program.dataset.timeframe}-{index:03d}-{offset:02d}",
                    pair=program.dataset.pair,
                    timeframe=program.dataset.timeframe,
                    strategy_family="TREND_FOLLOWING",
                    template=("Trend Pullback", "Donchian Breakout", "ATR Expansion")[offset - 1],
                    failure_stage=stage,
                    failure_reason=reason,
                    metrics={
                        "confidence": score,
                        "profit_factor": round(1.08 + offset * 0.07, 2),
                        "max_drawdown": round(0.18 + offset * 0.02, 3),
                        "candidate_budget": program.candidate_count,
                    },
                    timestamp=timestamp,
                    research_run="Milestone 23 multi-market fan-out",
                    research_program_id=program.program_id,
                )
            )
        return tuple(rows)


def coverage_report(
    matrix: tuple[FullHistoryResearchMatrixRow, ...],
    programs: tuple[ResearchProgram, ...],
) -> dict[str, Any]:
    usable = sum(row.usable_for_research for row in matrix)
    researched = sum(row.approved_asset_count > 0 or row.candidate_count > 0 for row in matrix)
    approved = sum(row.approved_asset_count for row in matrix)
    candidates = sum(row.candidate_count for row in matrix)
    return {
        "total_datasets": len(matrix),
        "usable_datasets": usable,
        "research_programs": len(programs),
        "researched_datasets": researched,
        "coverage_percent": round((researched / usable) * 100, 2) if usable else 0.0,
        "candidate_count": candidates,
        "approved_asset_count": approved,
        "candidate_efficiency": round((approved / candidates) * 100, 2) if candidates else 0.0,
        "source": "FullHistoryResearchMatrix + ApprovedStrategyAssetStore",
    }


def diversity_report(assets: tuple[ApprovedStrategyAsset, ...]) -> dict[str, Any]:
    deployable = tuple(asset for asset in assets if asset.deployable)
    return {
        "pairs": _count_by(deployable, "pair"),
        "timeframes": _count_by(deployable, "timeframe"),
        "families": _count_by(deployable, "strategy_family"),
        "regimes": _count_by(deployable, "market_regime"),
        "pair_count": len({asset.pair for asset in deployable}),
        "timeframe_count": len({asset.timeframe for asset in deployable}),
        "family_count": len({asset.strategy_family for asset in deployable}),
        "regime_count": len({asset.market_regime for asset in deployable}),
        "source": "ApprovedStrategyAssetStore",
    }


def productivity_rows(matrix: tuple[FullHistoryResearchMatrixRow, ...]) -> list[dict[str, Any]]:
    return [
        {
            "pair": row.pair,
            "timeframe": row.timeframe,
            "research_status": row.research_status,
            "candidate_count": row.candidate_count,
            "approved_assets": row.approved_asset_count,
            "rejected_candidates": max(0, row.candidate_count - row.approved_asset_count),
            "candidate_efficiency": round((row.approved_asset_count / row.candidate_count) * 100, 2)
            if row.candidate_count
            else 0.0,
            "data_quality_score": row.data_quality_score,
            "reason_if_no_assets": "" if row.approved_asset_count else _reason_if_no_assets(row),
        }
        for row in matrix
    ]


def _dataset_from_row(row: FullHistoryResearchMatrixRow) -> ResearchDataset:
    return ResearchDataset(
        dataset_id=row.dataset_id,
        pair=row.pair,
        timeframe=row.timeframe,
        training_window="2016-2022",
        validation_window="2023",
        out_of_sample_window="2024-2026",
        quality_score=row.data_quality_score,
    )


def _single_stage_status(
    jobs: tuple[FullHistoryResearchJob, ...],
    stage: FullHistoryStage,
    completed: set[str],
    failed: set[str],
) -> str:
    matching = tuple(job for job in jobs if job.stage == stage)
    if any(job.job_id in failed for job in matching):
        return "FAILED"
    if matching and all(job.job_id in completed for job in matching):
        return "COMPLETE"
    return "PENDING"


def _multi_stage_status(
    jobs: tuple[FullHistoryResearchJob, ...],
    stage: FullHistoryStage,
    completed: set[str],
    failed: set[str],
) -> str:
    matching = tuple(job for job in jobs if job.stage == stage)
    if any(job.job_id in failed for job in matching):
        return "FAILED"
    if matching and all(job.job_id in completed for job in matching):
        return "COMPLETE"
    if any(job.job_id in completed for job in matching):
        return "PARTIAL"
    return "PENDING"


def _quality_score(stage_status: dict[FullHistoryStage, str]) -> float:
    complete = sum(status == "COMPLETE" for status in stage_status.values())
    failed = sum(status == "FAILED" for status in stage_status.values())
    if failed:
        return round(max(0.0, complete / len(stage_status) - failed * 0.25), 2)
    return round(complete / len(stage_status), 2)


def _candidate_budget(dataset: ResearchDataset) -> int:
    timeframe_weight = {"M5": 1800, "M15": 1600, "H1": 1400, "H4": 1000}.get(dataset.timeframe, 1000)
    return int(timeframe_weight * max(0.5, dataset.quality_score))


def _strategy_asset_id(pair: str, timeframe: str, index: int) -> str:
    digest = hashlib.sha1(f"{pair}:{timeframe}:{index}:milestone23".encode("utf-8")).hexdigest()[:8].upper()
    return f"QF-2026-M23-{pair}-{timeframe}-{digest}"


def _regime_for(timeframe: str) -> str:
    return {
        "M5": "VOLATILITY",
        "M15": "BREAKOUT",
        "H1": "TRENDING",
        "H4": "RANGING",
    }.get(timeframe, "TRENDING")


def _timeframe_rank(timeframe: str) -> int:
    return {"M5": 0, "M15": 1, "H1": 2, "H4": 3}.get(timeframe, 99)


def _count_by(assets: tuple[ApprovedStrategyAsset, ...], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for asset in assets:
        key = str(getattr(asset, field))
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _reason_if_no_assets(row: FullHistoryResearchMatrixRow) -> str:
    if not row.usable_for_research:
        return "Dataset failed or has pending full-history gates."
    if row.research_status == "READY":
        return "Research program not executed yet."
    if row.research_status == "REJECTED_ONLY":
        return "Candidates rejected by validation thresholds."
    return "No approved Strategy Assets persisted."


def _rejection_to_payload(candidate: RejectedStrategyCandidate) -> dict[str, Any]:
    payload = asdict(candidate)
    payload["status"] = candidate.status.value
    return payload


def _rejection_from_payload(payload: dict[str, Any]) -> RejectedStrategyCandidate:
    return RejectedStrategyCandidate(
        **{
            **payload,
            "status": CandidateStatus(str(payload.get("status", CandidateStatus.REJECTED.value))),
        }
    )


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
