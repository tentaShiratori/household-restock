"""在庫加算の冪等条件。"""

from __future__ import annotations

from household_restock.stock_apply import (
    STOCK_CLAIM_CONDITION,
    apply_stock,
    can_claim_stock_apply,
    normalize_delivery_outcome,
    normalize_restock_qty,
    status_after_successful_apply,
)


def test_claim_only_once_on_arrival_confirmed() -> None:
    assert can_claim_stock_apply(status="ARRIVAL_CONFIRMED", stock_applied=False)
    assert not can_claim_stock_apply(status="ARRIVAL_CONFIRMED", stock_applied=True)
    assert not can_claim_stock_apply(status="SHIPPING_WAIT", stock_applied=False)
    assert STOCK_CLAIM_CONDITION.startswith("attribute_not_exists(stockApplied)")


def test_apply_stock_adds_qty() -> None:
    assert apply_stock(current_stock=2, restock_qty=10) == 12
    assert normalize_restock_qty(0) == 10
    assert status_after_successful_apply() == "COMPLETED"
    assert normalize_delivery_outcome("not_arrived") == "not_arrived"
    assert normalize_delivery_outcome("other") == "arrived"
