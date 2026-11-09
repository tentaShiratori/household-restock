"""判定純関数の単体テスト。"""

from __future__ import annotations

from household_restock.evaluate import evaluate_item_update, stock_at_or_below_threshold


def test_threshold_is_inclusive() -> None:
    assert stock_at_or_below_threshold(stock=3, threshold=3) is True
    assert stock_at_or_below_threshold(stock=2, threshold=3) is True
    assert stock_at_or_below_threshold(stock=4, threshold=3) is False


def test_skips_non_item_record() -> None:
    decision = evaluate_item_update(
        is_item_record=False,
        old_stock=5,
        new_stock=1,
        threshold=3,
    )
    assert decision.should_start is False
    assert decision.reason == "not_item_record"


def test_skips_unchanged_stock() -> None:
    decision = evaluate_item_update(
        is_item_record=True,
        old_stock=2,
        new_stock=2,
        threshold=3,
    )
    assert decision.should_start is False
    assert decision.reason == "stock_unchanged"


def test_skips_above_threshold() -> None:
    decision = evaluate_item_update(
        is_item_record=True,
        old_stock=5,
        new_stock=4,
        threshold=3,
    )
    assert decision.should_start is False
    assert decision.reason == "above_threshold"


def test_starts_when_at_or_below() -> None:
    decision = evaluate_item_update(
        is_item_record=True,
        old_stock=5,
        new_stock=3,
        threshold=3,
    )
    assert decision.should_start is True
    assert decision.reason == "at_or_below_threshold"


def test_insert_without_old_stock_can_start() -> None:
    decision = evaluate_item_update(
        is_item_record=True,
        old_stock=None,
        new_stock=0,
        threshold=2,
    )
    assert decision.should_start is True


def test_missing_values() -> None:
    decision = evaluate_item_update(
        is_item_record=True,
        old_stock=1,
        new_stock=None,
        threshold=3,
    )
    assert decision.reason == "missing_stock_or_threshold"
