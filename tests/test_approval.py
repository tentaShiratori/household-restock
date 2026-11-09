"""承認状態遷移の単体テスト。"""

from __future__ import annotations

from household_restock.approval import (
    STATUS_APPROVED,
    STATUS_AWAITING,
    STATUS_RECORDED,
    STATUS_REJECTED,
    STATUS_TIMED_OUT,
    apply_decision,
    may_store_token,
    status_after_timeout,
)


def test_approve_and_reject_from_awaiting() -> None:
    ok = apply_decision(current_status=STATUS_AWAITING, decision="approve")
    assert ok.accepted is True
    assert ok.new_status == STATUS_APPROVED
    ng = apply_decision(current_status=STATUS_AWAITING, decision="REJECT")
    assert ng.accepted is True
    assert ng.new_status == STATUS_REJECTED


def test_reject_invalid_and_terminal() -> None:
    bad = apply_decision(current_status=STATUS_AWAITING, decision="maybe")
    assert bad.accepted is False
    assert (
        apply_decision(current_status=STATUS_APPROVED, decision="approve").reason
        == "already_terminal"
    )
    assert (
        apply_decision(current_status=STATUS_RECORDED, decision="approve").reason
        == "not_awaiting_approval"
    )


def test_timeout_and_store_token() -> None:
    timed = status_after_timeout(STATUS_AWAITING)
    assert timed.accepted is True
    assert timed.new_status == STATUS_TIMED_OUT
    assert status_after_timeout(STATUS_REJECTED).accepted is False
    assert may_store_token(STATUS_RECORDED).new_status == STATUS_AWAITING
    assert may_store_token(STATUS_TIMED_OUT).accepted is False
