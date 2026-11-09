"""日用品自動補充の共有ロジック（v0.2.0: 判定・占有・承認遷移）。"""

from __future__ import annotations

from household_restock.approval import (
    DECISION_APPROVE,
    DECISION_REJECT,
    DecisionResult,
    apply_decision,
    status_after_timeout,
)
from household_restock.evaluate import (
    EvaluationDecision,
    evaluate_item_update,
    stock_at_or_below_threshold,
)
from household_restock.keys import (
    ENTITY_ITEM,
    ENTITY_LOCK,
    ENTITY_RESTOCK,
    LOCK_SK,
    META_SK,
    item_pk,
    restock_sk,
)
from household_restock.occupancy import build_occupancy_put, release_condition

__all__ = [
    "DECISION_APPROVE",
    "DECISION_REJECT",
    "DecisionResult",
    "ENTITY_ITEM",
    "ENTITY_LOCK",
    "ENTITY_RESTOCK",
    "EvaluationDecision",
    "LOCK_SK",
    "META_SK",
    "__version__",
    "apply_decision",
    "build_occupancy_put",
    "evaluate_item_update",
    "item_pk",
    "package_name",
    "release_condition",
    "restock_sk",
    "status_after_timeout",
    "stock_at_or_below_threshold",
]

__version__ = "0.2.0"


def package_name() -> str:
    """配布名を返す。"""
    return "household-restock"
