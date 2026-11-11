"""画面入力と decision 可否。"""

from __future__ import annotations

from household_restock.ui_validation import (
    decision_allowed_for_status,
    parse_non_negative_int,
)


def test_parse_non_negative_int() -> None:
    assert parse_non_negative_int(0).ok is True
    assert parse_non_negative_int("12").value == 12
    assert parse_non_negative_int(" 3 ").value == 3
    assert parse_non_negative_int(-1).reason == "negative"
    assert parse_non_negative_int("1.5").reason == "not_integer"
    assert parse_non_negative_int(True).reason == "not_integer"
    assert parse_non_negative_int("").reason == "not_integer"


def test_decision_only_when_awaiting() -> None:
    assert decision_allowed_for_status("AWAITING_APPROVAL") is True
    assert decision_allowed_for_status("APPROVED") is False
    assert decision_allowed_for_status("RECORDED") is False
