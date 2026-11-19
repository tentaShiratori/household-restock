"""在庫加算の冪等条件（ASL TransactWrite と memory で共有）。"""

from __future__ import annotations

from household_restock.status_labels import STATUS_ARRIVAL_CONFIRMED, STATUS_COMPLETED

# Claim + ADD を 1 トランザクションにする条件（RESTOCK 側）
STOCK_CLAIM_CONDITION = "attribute_not_exists(stockApplied) AND #s = :arrived"

DEFAULT_RESTOCK_QTY = 10
OUTCOME_ARRIVED = "arrived"
OUTCOME_NOT_ARRIVED = "not_arrived"


def normalize_delivery_outcome(raw: object) -> str:
    if isinstance(raw, str) and raw.strip() == OUTCOME_NOT_ARRIVED:
        return OUTCOME_NOT_ARRIVED
    return OUTCOME_ARRIVED


def normalize_restock_qty(raw: object) -> int:
    """加算量。正の整数以外は既定値。"""
    if isinstance(raw, bool):
        return DEFAULT_RESTOCK_QTY
    if isinstance(raw, int):
        value = raw
    elif isinstance(raw, str):
        try:
            value = int(raw.strip())
        except ValueError:
            return DEFAULT_RESTOCK_QTY
    else:
        return DEFAULT_RESTOCK_QTY
    if value < 1:
        return DEFAULT_RESTOCK_QTY
    return value


def can_claim_stock_apply(*, status: str, stock_applied: bool) -> bool:
    """到着確認済みかつ未加算のときだけ claim できる。"""
    return status == STATUS_ARRIVAL_CONFIRMED and not stock_applied


def apply_stock(*, current_stock: int, restock_qty: int) -> int:
    """在庫へ加算したあとの値。"""
    return int(current_stock) + normalize_restock_qty(restock_qty)


def status_after_successful_apply() -> str:
    return STATUS_COMPLETED
