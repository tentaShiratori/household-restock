"""waitForTaskToken 用: task token を DynamoDB に保存（応答に出さない）。"""

from __future__ import annotations

import os
from typing import Any

from household_restock.approval import STATUS_AWAITING, TERMINAL, may_store_token
from household_restock.keys import item_pk, restock_sk


class ALREADY_TERMINAL(Exception):
    """補充が既に終端。SFN Catch で占有解放のみ行う。"""


class CANNOT_STORE_TOKEN(Exception):
    """token を保存できない状態。"""


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, str]:
    """SFN から invoke.waitForTaskToken で呼ばれる。token はログに書かない。"""
    import boto3

    del context

    task_token = event["taskToken"]
    item_id = event["itemId"]
    stream_event_id = event["streamEventId"]
    if not isinstance(task_token, str) or not task_token:
        raise ValueError("missing taskToken")
    if not isinstance(item_id, str) or not isinstance(stream_event_id, str):
        raise ValueError("missing itemId or streamEventId")

    table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    key = {"pk": item_pk(item_id), "sk": restock_sk(stream_event_id)}
    existing = table.get_item(Key=key).get("Item") or {}
    current = str(existing.get("status", "RECORDED"))
    if current in TERMINAL:
        raise ALREADY_TERMINAL(current)

    result = may_store_token(current)
    if not result.accepted:
        raise CANNOT_STORE_TOKEN(result.reason)

    table.update_item(
        Key=key,
        UpdateExpression="SET #s = :awaiting, taskToken = :token",
        ConditionExpression="#s = :recorded OR #s = :awaiting",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":awaiting": STATUS_AWAITING,
            ":recorded": "RECORDED",
            ":token": task_token,
        },
    )
    return {"status": STATUS_AWAITING}
