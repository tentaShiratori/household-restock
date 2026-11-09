"""キーヘルパーの単体テスト。"""

from __future__ import annotations

from household_restock.keys import (
    is_item_meta_record,
    item_pk,
    parse_item_id_from_pk,
    restock_sk,
    sfn_execution_name,
)


def test_item_and_restock_keys() -> None:
    assert item_pk("toilet-paper") == "ITEM#toilet-paper"
    assert restock_sk("evt-1") == "RESTOCK#evt-1"
    assert parse_item_id_from_pk("ITEM#toilet-paper") == "toilet-paper"
    assert parse_item_id_from_pk("OTHER#x") is None


def test_item_meta_detection() -> None:
    assert is_item_meta_record(pk="ITEM#a", sk="META", entity_type="ITEM") is True
    assert (
        is_item_meta_record(pk="ITEM#a", sk="RESTOCK#e", entity_type="RESTOCK") is False
    )


def test_execution_name_sanitized_and_stable() -> None:
    name = sfn_execution_name(item_id="toilet-paper", stream_event_id="ab/cd")
    assert " " not in name
    assert "/" not in name
    assert name.startswith("restock-toilet-paper-")
    assert len(name) <= 80


def test_empty_item_id_and_entity_none() -> None:
    assert parse_item_id_from_pk("ITEM#") is None
    assert is_item_meta_record(pk="ITEM#a", sk="META", entity_type=None) is True
    assert is_item_meta_record(pk="ITEM#a", sk="META", entity_type="NOPE") is False
