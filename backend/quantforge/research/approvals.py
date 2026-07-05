from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from uuid import uuid4


class ApprovalType(StrEnum):
    PAPER_PORTFOLIO_APPROVAL = "PAPER_PORTFOLIO_APPROVAL"
    PRODUCTION_CERTIFICATION_APPROVAL = "PRODUCTION_CERTIFICATION_APPROVAL"
    LIVE_TRADING_APPROVAL = "LIVE_TRADING_APPROVAL"
    CAPITAL_SCALING_APPROVAL = "CAPITAL_SCALING_APPROVAL"


class ApprovalStatus(StrEnum):
    WAITING = "WAITING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    NOT_REQUIRED = "NOT_REQUIRED"


@dataclass(frozen=True, slots=True)
class ApprovalRecord:
    approval_id: str
    workflow_id: str
    approval_type: str
    stage: str
    requested_at: str
    requested_by: str
    status: str
    reason: str
    approved_by: str = ""
    approved_at: str = ""
    rejected_by: str = ""
    rejected_at: str = ""
    trace_id: str = ""


@dataclass(frozen=True, slots=True)
class ApprovalAuditRecord:
    approval_id: str
    workflow_id: str
    approval_type: str
    user: str
    action: str
    reason: str
    timestamp: str
    previous_status: str
    new_status: str
    trace_id: str


class ApprovalRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> ApprovalRecord | None:
        if not self.path.exists():
            return None
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not payload:
            return None
        return ApprovalRecord(**payload)

    def save(self, approval: ApprovalRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(approval), indent=2, sort_keys=True), encoding="utf-8")

    def find(self, approval_id: str) -> ApprovalRecord | None:
        approval = self.load()
        if approval and approval.approval_id == approval_id:
            return approval
        return None


class ApprovalAuditLog:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, record: ApprovalAuditRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")

    def list(self, *, limit: int = 200) -> list[dict[str, str]]:
        if not self.path.exists():
            return []
        rows = [
            json.loads(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return rows[-limit:]


class ApprovalPolicy:
    def validate_action(self, approval: ApprovalRecord, action: str) -> None:
        if approval.status != ApprovalStatus.WAITING.value:
            raise ValueError(f"Approval {approval.approval_id} is {approval.status}; only WAITING approvals can be {action}.")


class ApprovalService:
    def __init__(
        self,
        repository: ApprovalRepository,
        audit_log: ApprovalAuditLog,
        policy: ApprovalPolicy | None = None,
    ) -> None:
        self.repository = repository
        self.audit_log = audit_log
        self.policy = policy or ApprovalPolicy()

    def list(self) -> list[dict[str, str]]:
        approval = self.repository.load()
        return [asdict(approval)] if approval else []

    def audit_records(self, *, limit: int = 200) -> list[dict[str, str]]:
        return self.audit_log.list(limit=limit)

    def approve(self, approval_id: str, *, user: str, reason: str) -> ApprovalRecord:
        return self._transition(
            approval_id,
            user=user,
            reason=reason,
            action="APPROVE",
            new_status=ApprovalStatus.APPROVED,
        )

    def reject(self, approval_id: str, *, user: str, reason: str) -> ApprovalRecord:
        return self._transition(
            approval_id,
            user=user,
            reason=reason,
            action="REJECT",
            new_status=ApprovalStatus.REJECTED,
        )

    def _transition(
        self,
        approval_id: str,
        *,
        user: str,
        reason: str,
        action: str,
        new_status: ApprovalStatus,
    ) -> ApprovalRecord:
        approval = self.repository.find(approval_id)
        if approval is None:
            raise KeyError(approval_id)
        self.policy.validate_action(approval, action.lower())
        timestamp = _now()
        updated = replace(
            approval,
            status=new_status.value,
            approved_by=user if new_status == ApprovalStatus.APPROVED else approval.approved_by,
            approved_at=timestamp if new_status == ApprovalStatus.APPROVED else approval.approved_at,
            rejected_by=user if new_status == ApprovalStatus.REJECTED else approval.rejected_by,
            rejected_at=timestamp if new_status == ApprovalStatus.REJECTED else approval.rejected_at,
            reason=reason or approval.reason,
            trace_id=approval.trace_id or str(uuid4()),
        )
        self.repository.save(updated)
        self.audit_log.append(
            ApprovalAuditRecord(
                approval_id=approval.approval_id,
                workflow_id=approval.workflow_id,
                approval_type=approval.approval_type,
                user=user,
                action=action,
                reason=reason,
                timestamp=timestamp,
                previous_status=approval.status,
                new_status=updated.status,
                trace_id=updated.trace_id,
            )
        )
        return updated


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
