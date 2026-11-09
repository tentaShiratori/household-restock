"""占有キーと条件の単体テスト。"""

from __future__ import annotations

from household_restock.keys import LOCK_SK, item_pk
from household_restock.occupancy import (
    build_occupancy_put,
    occupancy_item_attrs,
    release_condition,
)


def test_occupancy_put_allows_same_event_retry() -> None:
    put = build_occupancy_put(item_id="toilet-paper", stream_event_id="evt-1")
    assert put.pk == item_pk("toilet-paper")
    assert put.sk == LOCK_SK
    assert "streamEventId = :eid" in put.condition_expression
    assert put.expression_attribute_values[":eid"] == "evt-1"
    attrs = occupancy_item_attrs(item_id="toilet-paper", stream_event_id="evt-1")
    assert attrs["status"] == "HELD"
    assert attrs["entityType"] == "LOCK"


def test_release_condition_is_scoped() -> None:
    expr, values = release_condition(stream_event_id="evt-9")
    assert expr == "streamEventId = :eid"
    assert values[":eid"] == "evt-9"
