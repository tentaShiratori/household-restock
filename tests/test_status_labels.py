"""状態ラベル。"""

from __future__ import annotations

from household_restock.status_labels import (
    STATUS_ORDER_FAILED,
    STATUS_ORDERING,
    STATUS_SHIPPING_WAIT,
    label_for_status,
)


def test_order_flow_labels() -> None:
    assert label_for_status(STATUS_ORDERING) == "注文中"
    assert label_for_status(STATUS_SHIPPING_WAIT) == "配送待ち"
    assert label_for_status(STATUS_ORDER_FAILED) == "失敗"
    assert label_for_status("AWAITING_APPROVAL") == "承認待ち"
