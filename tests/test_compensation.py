"""補償順序と冪等フラグ。"""

from __future__ import annotations

from household_restock.compensation import (
    COMPENSATION_STATE_ORDER,
    ORDER_CANCEL_CONDITION,
    RESTOCK_CANCEL_CONDITION,
    apply_order_cancel,
    apply_restock_cancel,
    can_cancel_order,
    can_cancel_restock,
    status_after_compensation,
)


def test_compensation_order_is_order_then_restock_then_lock() -> None:
    assert COMPENSATION_STATE_ORDER == (
        "CancelOrder",
        "CancelRestockRequest",
        "ReleaseLock",
    )
    assert "orderCancelled" in ORDER_CANCEL_CONDITION
    assert "restockCancelled" in RESTOCK_CANCEL_CONDITION


def test_cancel_flags_are_idempotent() -> None:
    flags: dict[str, object] = {}
    assert can_cancel_order(order_cancelled=False)
    assert apply_order_cancel(flags) is True
    assert apply_order_cancel(flags) is False
    assert can_cancel_order(order_cancelled=True) is False

    assert apply_restock_cancel(flags) is True
    assert apply_restock_cancel(flags) is False
    assert can_cancel_restock(restock_cancelled=True) is False
    assert status_after_compensation() == "CANCELLED"
