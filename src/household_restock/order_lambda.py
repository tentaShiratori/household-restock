"""模擬注文 Lambda。失敗モードは決定的（乱数なし）。"""

from __future__ import annotations

import os
from typing import Any

from household_restock.keys import item_pk, restock_sk
from household_restock.order import (
    ERROR_PERMANENT,
    ERROR_TRANSIENT,
    evaluate_order_attempt,
    normalize_failure_mode,
)


class OrderTransientError(Exception):
    """SFN Retry 対象。"""


class OrderPermanentError(Exception):
    """即 Catch（取消骨格）対象。"""


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, object]:
    import boto3

    del context

    item_id = event.get("itemId")
    stream_event_id = event.get("streamEventId")
    if not isinstance(item_id, str) or not isinstance(stream_event_id, str):
        raise OrderPermanentError("bad_input")

    mode = normalize_failure_mode(event.get("orderFailureMode"))
    wait_seconds = int(os.environ.get("DELIVERY_WAIT_SECONDS", "60"))
    table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    key = {"pk": item_pk(item_id), "sk": restock_sk(stream_event_id)}

    # 試行回数を加算してから判定（Retry でも attempt が進む）
    updated = table.update_item(
        Key=key,
        UpdateExpression="ADD orderAttempts :one",
        ExpressionAttributeValues={":one": 1},
        ReturnValues="UPDATED_NEW",
    )
    attempts_raw = updated.get("Attributes", {}).get("orderAttempts", 1)
    attempt_number = int(attempts_raw)

    result = evaluate_order_attempt(
        mode=mode,
        attempt_number=attempt_number,
        item_id=item_id,
        stream_event_id=stream_event_id,
        delivery_wait_seconds=wait_seconds,
    )
    if not result.ok:
        if result.error_name == ERROR_TRANSIENT:
            raise OrderTransientError(result.reason)
        raise OrderPermanentError(result.reason or ERROR_PERMANENT)

    return {
        "orderId": result.order_id,
        "arriveAt": result.arrive_at,
        "itemId": item_id,
        "streamEventId": stream_event_id,
    }
