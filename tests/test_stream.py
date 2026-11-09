"""Streams レコード解釈の単体テスト。"""

from __future__ import annotations

from household_restock.keys import item_pk, restock_sk, sfn_execution_name
from household_restock.stream import evaluate_dynamodb_record


def _item_modify(
    *,
    event_id: str,
    old_stock: int,
    new_stock: int,
    threshold: int,
    item_id: str = "toilet-paper",
) -> dict[str, object]:
    pk = item_pk(item_id)
    return {
        "eventID": event_id,
        "eventName": "MODIFY",
        "dynamodb": {
            "Keys": {"pk": {"S": pk}, "sk": {"S": "META"}},
            "OldImage": {
                "pk": {"S": pk},
                "sk": {"S": "META"},
                "entityType": {"S": "ITEM"},
                "stock": {"N": str(old_stock)},
                "threshold": {"N": str(threshold)},
            },
            "NewImage": {
                "pk": {"S": pk},
                "sk": {"S": "META"},
                "entityType": {"S": "ITEM"},
                "stock": {"N": str(new_stock)},
                "threshold": {"N": str(threshold)},
            },
        },
    }


def test_restock_row_does_not_start() -> None:
    record = {
        "eventID": "evt-restock-1",
        "eventName": "INSERT",
        "dynamodb": {
            "Keys": {
                "pk": {"S": item_pk("toilet-paper")},
                "sk": {"S": restock_sk("evt-prev")},
            },
            "NewImage": {
                "pk": {"S": item_pk("toilet-paper")},
                "sk": {"S": restock_sk("evt-prev")},
                "entityType": {"S": "RESTOCK"},
                "itemId": {"S": "toilet-paper"},
            },
        },
    }
    decision, start = evaluate_dynamodb_record(record)
    assert decision.should_start is False
    assert decision.reason == "not_item_record"
    assert start is None


def test_below_threshold_builds_start() -> None:
    record = _item_modify(
        event_id="c496f875-aaaa-bbbb-cccc-000000000001",
        old_stock=5,
        new_stock=2,
        threshold=3,
    )
    decision, start = evaluate_dynamodb_record(record)
    assert decision.should_start is True
    assert start is not None
    assert start.item_id == "toilet-paper"
    assert start.stock == 2
    assert start.threshold == 3
    assert start.stream_event_id == "c496f875-aaaa-bbbb-cccc-000000000001"
    assert start.execution_name == sfn_execution_name(
        item_id="toilet-paper",
        stream_event_id="c496f875-aaaa-bbbb-cccc-000000000001",
    )


def test_above_threshold_skips() -> None:
    record = _item_modify(
        event_id="evt-above",
        old_stock=9,
        new_stock=8,
        threshold=3,
    )
    decision, start = evaluate_dynamodb_record(record)
    assert decision.should_start is False
    assert start is None
