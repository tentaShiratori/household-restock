"""日用品自動補充の共有ロジック（v0.1.0: 判定とキー）。"""

from __future__ import annotations

from household_restock.evaluate import (
    EvaluationDecision,
    evaluate_item_update,
    stock_at_or_below_threshold,
)
from household_restock.keys import (
    ENTITY_ITEM,
    ENTITY_RESTOCK,
    META_SK,
    item_pk,
    restock_sk,
)

__all__ = [
    "ENTITY_ITEM",
    "ENTITY_RESTOCK",
    "EvaluationDecision",
    "META_SK",
    "__version__",
    "evaluate_item_update",
    "item_pk",
    "package_name",
    "restock_sk",
    "stock_at_or_below_threshold",
]

__version__ = "0.1.0"


def package_name() -> str:
    """配布名を返す。"""
    return "household-restock"
