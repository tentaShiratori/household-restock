"""DynamoDB Streams レコードの解釈（boto3 なし）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from household_restock.evaluate import EvaluationDecision, evaluate_item_update
from household_restock.keys import (
    META_SK,
    is_item_meta_record,
    parse_item_id_from_pk,
    sfn_execution_name,
)


@dataclass(frozen=True)
class RestockStart:
    item_id: str
    stock: int
    threshold: int
    stream_event_id: str
    execution_name: str


def _s_value(image: dict[str, Any] | None, attr: str) -> str | None:
    if image is None or attr not in image:
        return None
    node = image[attr]
    if not isinstance(node, dict):
        return None
    raw = node.get("S")
    return raw if isinstance(raw, str) else None


def _n_value(image: dict[str, Any] | None, attr: str) -> int | None:
    if image is None or attr not in image:
        return None
    node = image[attr]
    if not isinstance(node, dict):
        return None
    raw = node.get("N")
    if not isinstance(raw, str):
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def evaluate_dynamodb_record(
    record: dict[str, Any],
) -> tuple[EvaluationDecision, RestockStart | None]:
    """1件の Streams レコードを判定する。起動不要なら RestockStart は None。"""
    event_id = record.get("eventID")
    if not isinstance(event_id, str) or not event_id:
        decision = EvaluationDecision(False, "missing_event_id")
        return decision, None

    dynamodb = record.get("dynamodb")
    if not isinstance(dynamodb, dict):
        decision = EvaluationDecision(False, "not_item_record")
        return decision, None

    keys = dynamodb.get("Keys")
    if not isinstance(keys, dict):
        decision = EvaluationDecision(False, "not_item_record")
        return decision, None

    pk = _s_value(keys, "pk")
    sk = _s_value(keys, "sk")
    if pk is None or sk is None:
        decision = EvaluationDecision(False, "not_item_record")
        return decision, None

    new_image = dynamodb.get("NewImage")
    old_image = dynamodb.get("OldImage")
    new_image_dict = new_image if isinstance(new_image, dict) else None
    old_image_dict = old_image if isinstance(old_image, dict) else None

    entity_type = _s_value(new_image_dict, "entityType")
    item_record = is_item_meta_record(pk=pk, sk=sk, entity_type=entity_type)
    # INSERT で NewImage のみ、MODIFY で Old/New。REMOVE は起動しない。
    event_name = record.get("eventName")
    if event_name == "REMOVE":
        decision = EvaluationDecision(False, "not_item_record")
        return decision, None

    new_stock = _n_value(new_image_dict, "stock")
    threshold = _n_value(new_image_dict, "threshold")
    old_stock = _n_value(old_image_dict, "stock")

    decision = evaluate_item_update(
        is_item_record=item_record,
        old_stock=old_stock,
        new_stock=new_stock,
        threshold=threshold,
    )
    if not decision.should_start:
        return decision, None

    item_id = parse_item_id_from_pk(pk)
    # is_item_meta_record が True なら item_id / stock / threshold は揃っている。
    assert item_id is not None
    assert new_stock is not None
    assert threshold is not None
    assert sk == META_SK

    start = RestockStart(
        item_id=item_id,
        stock=new_stock,
        threshold=threshold,
        stream_event_id=event_id,
        execution_name=sfn_execution_name(item_id=item_id, stream_event_id=event_id),
    )
    return decision, start
