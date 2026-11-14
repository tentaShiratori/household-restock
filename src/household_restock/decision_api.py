"""承認/却下 API。task token はサーバー側で引き、応答に出さない。"""

from __future__ import annotations

import json
import os
from typing import Any

from household_restock.approval import (
    DECISION_APPROVE,
    apply_decision,
    normalize_decision,
)
from household_restock.keys import item_pk, restock_sk


def _response(status: int, body: dict[str, object]) -> dict[str, object]:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def _unauthorized() -> dict[str, object]:
    return _response(401, {"ok": False, "reason": "unauthorized"})


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, object]:
    import boto3
    from botocore.exceptions import ClientError

    del context

    expected = os.environ.get("APPROVAL_SHARED_SECRET", "")
    headers = event.get("headers") or {}
    if not isinstance(headers, dict):
        headers = {}
    # API Gateway はヘッダ名を小文字化することがある
    provided = headers.get("x-approval-secret") or headers.get("X-Approval-Secret")
    if not expected or not isinstance(provided, str) or provided != expected:
        return _unauthorized()

    params = event.get("pathParameters") or {}
    if not isinstance(params, dict):
        return _response(400, {"ok": False, "reason": "bad_path"})
    item_id = params.get("itemId")
    stream_event_id = params.get("streamEventId")
    if not isinstance(item_id, str) or not isinstance(stream_event_id, str):
        return _response(400, {"ok": False, "reason": "bad_path"})

    raw_body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        return _response(400, {"ok": False, "reason": "unsupported_encoding"})
    if not isinstance(raw_body, str):
        return _response(400, {"ok": False, "reason": "bad_body"})
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return _response(400, {"ok": False, "reason": "bad_json"})
    if not isinstance(payload, dict):
        return _response(400, {"ok": False, "reason": "bad_json"})
    decision_raw = payload.get("decision")
    if not isinstance(decision_raw, str):
        return _response(400, {"ok": False, "reason": "invalid_decision"})
    decision = normalize_decision(decision_raw)
    if decision is None:
        return _response(400, {"ok": False, "reason": "invalid_decision"})

    table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    sfn = boto3.client("stepfunctions")
    key = {"pk": item_pk(item_id), "sk": restock_sk(stream_event_id)}
    item = table.get_item(Key=key).get("Item")
    if not item:
        return _response(404, {"ok": False, "reason": "not_found"})

    current = str(item.get("status", ""))
    result = apply_decision(current_status=current, decision=decision)
    if not result.accepted or result.new_status is None:
        return _response(409, {"ok": False, "reason": result.reason})

    token = item.get("taskToken")
    if not isinstance(token, str) or not token:
        return _response(409, {"ok": False, "reason": "missing_token"})

    # 状態を先に条件付き更新（競合・再送を拒否）
    try:
        table.update_item(
            Key=key,
            UpdateExpression="SET #s = :new REMOVE taskToken",
            ConditionExpression="#s = :awaiting",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":new": result.new_status,
                ":awaiting": "AWAITING_APPROVAL",
            },
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code == "ConditionalCheckFailedException":
            return _response(409, {"ok": False, "reason": "conflict"})
        raise

    try:
        if decision == DECISION_APPROVE:
            output = json.dumps({"decision": decision})
            sfn.send_task_success(taskToken=token, output=output)
        else:
            sfn.send_task_failure(
                taskToken=token,
                error="ApprovalRejected",
                cause="rejected_via_api",
            )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        # 期限切れ後の token 無効など
        if code in {"TaskTimedOut", "InvalidToken", "TaskDoesNotExist"}:
            return _response(409, {"ok": False, "reason": "token_inactive"})
        raise

    return _response(
        200,
        {
            "ok": True,
            "status": result.new_status,
            "itemId": item_id,
            "streamEventId": stream_event_id,
        },
    )
