"""品目占有の条件式と判定（純関数）。"""

from __future__ import annotations

from dataclasses import dataclass

from household_restock.keys import ENTITY_LOCK, LOCK_SK, item_pk


@dataclass(frozen=True)
class OccupancyPut:
    """条件付き Put に渡す値（boto3 resource 向けの素の値）。"""

    pk: str
    sk: str
    stream_event_id: str
    condition_expression: str
    expression_attribute_values: dict[str, str]


def build_occupancy_put(*, item_id: str, stream_event_id: str) -> OccupancyPut:
    """別イベントは拒否、同一 eventID の再試行は上書き可。"""
    return OccupancyPut(
        pk=item_pk(item_id),
        sk=LOCK_SK,
        stream_event_id=stream_event_id,
        condition_expression="attribute_not_exists(sk) OR streamEventId = :eid",
        expression_attribute_values={":eid": stream_event_id},
    )


def occupancy_item_attrs(*, item_id: str, stream_event_id: str) -> dict[str, str]:
    """PutItem の属性（resource API 用）。"""
    return {
        "pk": item_pk(item_id),
        "sk": LOCK_SK,
        "entityType": ENTITY_LOCK,
        "itemId": item_id,
        "streamEventId": stream_event_id,
        "status": "HELD",
    }


def release_condition(*, stream_event_id: str) -> tuple[str, dict[str, str]]:
    """自分の eventID のロックだけ消す。"""
    return ("streamEventId = :eid", {":eid": stream_event_id})
