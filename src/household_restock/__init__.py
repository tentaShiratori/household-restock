"""日用品自動補充の共有ロジック（v0.3.0: 最小画面・保護付き API）。"""

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
from household_restock.ui_validation import (
    decision_allowed_for_status,
    parse_non_negative_int,
)

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
    "decision_allowed_for_status",
    "evaluate_item_update",
    "item_pk",
    "package_name",
    "parse_non_negative_int",
    "release_condition",
    "restock_sk",
    "status_after_timeout",
    "stock_at_or_below_threshold",
]

__version__ = "0.3.0"


def package_name() -> str:
    """配布名を返す。"""
    return "household-restock"
