"""Streams 解釈の境界ケース。"""

from __future__ import annotations

from household_restock.stream import evaluate_dynamodb_record


def test_missing_event_id() -> None:
    decision, start = evaluate_dynamodb_record({"eventName": "MODIFY"})
    assert decision.reason == "missing_event_id"
    assert start is None


def test_remove_event_skipped() -> None:
    record = {
        "eventID": "evt-rm",
        "eventName": "REMOVE",
        "dynamodb": {
            "Keys": {"pk": {"S": "ITEM#a"}, "sk": {"S": "META"}},
            "OldImage": {
                "entityType": {"S": "ITEM"},
                "stock": {"N": "1"},
                "threshold": {"N": "2"},
            },
        },
    }
    decision, start = evaluate_dynamodb_record(record)
    assert decision.should_start is False
    assert start is None


def test_bad_number_and_missing_keys() -> None:
    decision, start = evaluate_dynamodb_record(
        {"eventID": "e1", "dynamodb": {"Keys": {"pk": {"S": "ITEM#a"}}}}
    )
    assert decision.reason == "not_item_record"
    assert start is None

    decision2, start2 = evaluate_dynamodb_record(
        {
            "eventID": "e2",
            "eventName": "MODIFY",
            "dynamodb": {
                "Keys": {"pk": {"S": "ITEM#a"}, "sk": {"S": "META"}},
                "NewImage": {
                    "entityType": {"S": "ITEM"},
                    "stock": {"N": "not-int"},
                    "threshold": {"N": "3"},
                },
            },
        }
    )
    assert decision2.reason == "missing_stock_or_threshold"
    assert start2 is None


def test_entity_type_mismatch() -> None:
    decision, start = evaluate_dynamodb_record(
        {
            "eventID": "e3",
            "eventName": "MODIFY",
            "dynamodb": {
                "Keys": {"pk": {"S": "ITEM#a"}, "sk": {"S": "META"}},
                "NewImage": {
                    "entityType": {"S": "OTHER"},
                    "stock": {"N": "1"},
                    "threshold": {"N": "3"},
                },
            },
        }
    )
    assert decision.reason == "not_item_record"
    assert start is None
