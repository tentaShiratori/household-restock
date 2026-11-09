"""承認 decision の状態遷移（純関数。token は扱わない）。"""

from __future__ import annotations

from dataclasses import dataclass

STATUS_RECORDED = "RECORDED"
STATUS_AWAITING = "AWAITING_APPROVAL"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"
STATUS_TIMED_OUT = "TIMED_OUT"
STATUS_FAILED = "FAILED"

DECISION_APPROVE = "approve"
DECISION_REJECT = "reject"

TERMINAL = frozenset(
    {
        STATUS_APPROVED,
        STATUS_REJECTED,
        STATUS_TIMED_OUT,
        STATUS_FAILED,
    }
)


@dataclass(frozen=True)
class DecisionResult:
    accepted: bool
    reason: str
    new_status: str | None = None


def normalize_decision(raw: str) -> str | None:
    value = raw.strip().lower()
    if value in {DECISION_APPROVE, DECISION_REJECT}:
        return value
    return None


def apply_decision(*, current_status: str, decision: str) -> DecisionResult:
    """AWAITING_APPROVAL 以外、または不正 decision は拒否。"""
    normalized = normalize_decision(decision)
    if normalized is None:
        return DecisionResult(False, "invalid_decision")
    if current_status in TERMINAL:
        return DecisionResult(False, "already_terminal")
    if current_status != STATUS_AWAITING:
        return DecisionResult(False, "not_awaiting_approval")
    if normalized == DECISION_APPROVE:
        return DecisionResult(True, "approved", STATUS_APPROVED)
    return DecisionResult(True, "rejected", STATUS_REJECTED)


def status_after_timeout(current_status: str) -> DecisionResult:
    if current_status in TERMINAL:
        return DecisionResult(False, "already_terminal")
    if current_status not in {STATUS_RECORDED, STATUS_AWAITING}:
        return DecisionResult(False, "not_awaiting_approval")
    return DecisionResult(True, "timed_out", STATUS_TIMED_OUT)


def may_store_token(current_status: str) -> DecisionResult:
    """RECORDED または再入時の AWAITING から token 保存を許す。"""
    if current_status in TERMINAL:
        return DecisionResult(False, "already_terminal")
    if current_status in {STATUS_RECORDED, STATUS_AWAITING}:
        return DecisionResult(True, "store_token", STATUS_AWAITING)
    return DecisionResult(False, "not_awaiting_approval")
