"""補償（取消）の順序と冪等フラグ。"""

from __future__ import annotations

from typing import Any

from household_restock.status_labels import STATUS_CANCELLED

# ASL ステート名（実行履歴で確認する順序）
COMPENSATION_STATE_ORDER: tuple[str, ...] = (
    "CancelOrder",
    "CancelRestockRequest",
    "ReleaseLock",
)

ORDER_CANCEL_CONDITION = (
    "attribute_not_exists(orderCancelled) OR orderCancelled = :false"
)
RESTOCK_CANCEL_CONDITION = (
    "attribute_not_exists(restockCancelled) OR restockCancelled = :false"
)


def can_cancel_order(*, order_cancelled: bool) -> bool:
    return not order_cancelled


def can_cancel_restock(*, restock_cancelled: bool) -> bool:
    return not restock_cancelled


def status_after_compensation() -> str:
    return STATUS_CANCELLED


def apply_order_cancel(flags: dict[str, Any]) -> bool:
    """注文取消を 1 回だけ適用。適用したら True。"""
    if flags.get("orderCancelled"):
        return False
    flags["orderCancelled"] = True
    return True


def apply_restock_cancel(flags: dict[str, Any]) -> bool:
    """補充リクエスト取消を 1 回だけ適用。適用したら True。"""
    if flags.get("restockCancelled"):
        return False
    flags["restockCancelled"] = True
    return True
