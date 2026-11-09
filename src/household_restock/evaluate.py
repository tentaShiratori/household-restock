"""在庫しきい値判定の純関数（副作用なし）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationDecision:
    """判定結果。should_start が True のときだけ SFN を起動する。"""

    should_start: bool
    reason: str


def stock_at_or_below_threshold(*, stock: int, threshold: int) -> bool:
    """採用条件: 在庫 ≦ しきい値（以下）。"""
    return stock <= threshold


def evaluate_item_update(
    *,
    is_item_record: bool,
    old_stock: int | None,
    new_stock: int | None,
    threshold: int | None,
) -> EvaluationDecision:
    """Streams 由来の1更新を判定する。

    - 品目メタ以外 → 起動しない（再帰防止の最終防衛）
    - 在庫が変わっていない → 起動しない
    - 新在庫またはしきい値が欠ける → 起動しない
    - 在庫 > しきい値 → 起動しない
    - 在庫 ≦ しきい値 → 起動する
    """
    if not is_item_record:
        return EvaluationDecision(False, "not_item_record")
    if new_stock is None or threshold is None:
        return EvaluationDecision(False, "missing_stock_or_threshold")
    if old_stock is not None and old_stock == new_stock:
        return EvaluationDecision(False, "stock_unchanged")
    if not stock_at_or_below_threshold(stock=new_stock, threshold=threshold):
        return EvaluationDecision(False, "above_threshold")
    return EvaluationDecision(True, "at_or_below_threshold")
