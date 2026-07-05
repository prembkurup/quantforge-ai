from __future__ import annotations

import json

import pytest

from quantforge.research.approvals import (
    ApprovalAuditLog,
    ApprovalRecord,
    ApprovalRepository,
    ApprovalService,
    ApprovalStatus,
    ApprovalType,
)
from quantforge.research.workflow_orchestration import WorkflowApprovalGate


def test_approval_gate_persists_waiting_live_trading_approval(tmp_path) -> None:
    approval_file = tmp_path / "workflow_live_approval.json"

    approval = WorkflowApprovalGate(approval_file).approval("WF-123", certification_complete=True)

    assert approval.status == ApprovalStatus.WAITING.value
    assert approval.approval_type == ApprovalType.LIVE_TRADING_APPROVAL.value
    assert approval_file.exists()
    stored = json.loads(approval_file.read_text(encoding="utf-8"))
    assert stored["approval_id"] == "APPROVAL-WF-123"
    assert stored["reason"] == "Manual approval required before live trading."


def test_approval_service_approves_waiting_record_and_writes_audit(tmp_path) -> None:
    repository = ApprovalRepository(tmp_path / "approval.json")
    audit_log = ApprovalAuditLog(tmp_path / "approval_audit.jsonl")
    repository.save(
        ApprovalRecord(
            approval_id="APPROVAL-WF-123",
            workflow_id="WF-123",
            approval_type=ApprovalType.LIVE_TRADING_APPROVAL.value,
            stage="MANUAL_APPROVAL",
            requested_at="2026-07-05T12:00:00+00:00",
            requested_by="workflow_orchestrator",
            status=ApprovalStatus.WAITING.value,
            reason="Manual approval required before live trading.",
            trace_id="trace-123",
        )
    )

    approved = ApprovalService(repository, audit_log).approve(
        "APPROVAL-WF-123",
        user="Prem",
        reason="Approved controlled launch gate.",
    )

    assert approved.status == ApprovalStatus.APPROVED.value
    assert approved.approved_by == "Prem"
    assert repository.load().status == ApprovalStatus.APPROVED.value  # type: ignore[union-attr]
    audit = audit_log.list()
    assert audit[-1]["action"] == "APPROVE"
    assert audit[-1]["previous_status"] == ApprovalStatus.WAITING.value
    assert audit[-1]["new_status"] == ApprovalStatus.APPROVED.value


def test_approval_service_rejects_non_waiting_reapproval(tmp_path) -> None:
    repository = ApprovalRepository(tmp_path / "approval.json")
    audit_log = ApprovalAuditLog(tmp_path / "approval_audit.jsonl")
    repository.save(
        ApprovalRecord(
            approval_id="APPROVAL-WF-123",
            workflow_id="WF-123",
            approval_type=ApprovalType.LIVE_TRADING_APPROVAL.value,
            stage="MANUAL_APPROVAL",
            requested_at="2026-07-05T12:00:00+00:00",
            requested_by="workflow_orchestrator",
            status=ApprovalStatus.APPROVED.value,
            reason="Already approved.",
        )
    )

    with pytest.raises(ValueError, match="only WAITING approvals"):
        ApprovalService(repository, audit_log).reject(
            "APPROVAL-WF-123",
            user="Prem",
            reason="Cannot reject after approval.",
        )
