"""品目・補充一覧と在庫更新 API。共有秘密必須。task token は返さない。"""

from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Any

from household_restock.keys import (
    ENTITY_ITEM,
    ENTITY_RESTOCK,
    LOCK_SK,
    META_SK,
    item_pk,
)
from household_restock.ui_api import strip_secrets
from household_restock.ui_validation import parse_non_negative_int


def _response(status: int, body: dict[str, object]) -> dict[str, object]:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(strip_secrets(body), ensure_ascii=False, default=str),
    }


def _unauthorized() -> dict[str, object]:
    return _response(401, {"ok": False, "reason": "unauthorized"})


def _check_secret(event: dict[str, Any]) -> bool:
    expected = os.environ.get("APPROVAL_SHARED_SECRET", "")
    headers = event.get("headers") or {}
    if not isinstance(headers, dict):
        headers = {}
    provided = headers.get("x-approval-secret") or headers.get("X-Approval-Secret")
    return bool(expected) and isinstance(provided, str) and provided == expected


def _to_int(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("bool")
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    raise ValueError("not_int")


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, object]:
    import boto3

    del context
    if not _check_secret(event):
        return _unauthorized()

    method = str(event.get("requestContext", {}).get("http", {}).get("method") or "")
    # REST/HTTP API 差分の吸収
    if not method:
        method = str(event.get("httpMethod") or "")
    path = str(event.get("rawPath") or event.get("path") or "")
    params = event.get("pathParameters") or {}
    if not isinstance(params, dict):
        params = {}

    table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

    if method == "GET" and path.endswith("/items"):
        return _list_items(table)
    if method == "GET" and path.endswith("/restock-requests"):
        return _list_restocks(table)
    if method == "PUT" and "/stock" in path:
        item_id = params.get("itemId")
        if not isinstance(item_id, str):
            return _response(400, {"ok": False, "reason": "bad_path"})
        return _put_stock(table, item_id=item_id, event=event)

    return _response(404, {"ok": False, "reason": "not_found"})


def _list_items(table: Any) -> dict[str, object]:
    # 学習用の小規模テーブル想定。Scan で META のみ拾う。
    items: list[dict[str, object]] = []
    scan_kwargs: dict[str, Any] = {
        "FilterExpression": "sk = :meta AND entityType = :etype",
        "ExpressionAttributeValues": {":meta": META_SK, ":etype": ENTITY_ITEM},
    }
    while True:
        page = table.scan(**scan_kwargs)
        for raw in page.get("Items", []):
            try:
                items.append(
                    {
                        "itemId": str(raw.get("itemId", "")),
                        "stock": _to_int(raw.get("stock", 0)),
                        "threshold": _to_int(raw.get("threshold", 0)),
                    }
                )
            except ValueError:
                continue
        if not page.get("LastEvaluatedKey"):
            break
        scan_kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    items.sort(key=lambda row: str(row["itemId"]))
    return _response(200, {"ok": True, "items": items})


def _list_restocks(table: Any) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    scan_kwargs: dict[str, Any] = {
        "FilterExpression": "entityType = :etype",
        "ExpressionAttributeValues": {":etype": ENTITY_RESTOCK},
    }
    while True:
        page = table.scan(**scan_kwargs)
        for raw in page.get("Items", []):
            if str(raw.get("sk", "")) == LOCK_SK:
                continue
            try:
                rows.append(
                    {
                        "itemId": str(raw.get("itemId", "")),
                        "streamEventId": str(raw.get("streamEventId", "")),
                        "status": str(raw.get("status", "")),
                        "stock": _to_int(raw.get("stock", 0)),
                        "threshold": _to_int(raw.get("threshold", 0)),
                    }
                )
            except ValueError:
                continue
        if not page.get("LastEvaluatedKey"):
            break
        scan_kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    rows.sort(key=lambda row: (str(row["itemId"]), str(row["streamEventId"])))
    return _response(200, {"ok": True, "restockRequests": rows})


def _put_stock(table: Any, *, item_id: str, event: dict[str, Any]) -> dict[str, object]:
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

    parsed = parse_non_negative_int(payload.get("stock"))
    if not parsed.ok or parsed.value is None:
        return _response(400, {"ok": False, "reason": parsed.reason or "not_integer"})

    key = {"pk": item_pk(item_id), "sk": META_SK}
    existing = table.get_item(Key=key).get("Item")
    if not existing:
        return _response(404, {"ok": False, "reason": "not_found"})
    try:
        threshold = _to_int(existing.get("threshold", 0))
    except ValueError:
        return _response(500, {"ok": False, "reason": "bad_item"})

    table.put_item(
        Item={
            "pk": item_pk(item_id),
            "sk": META_SK,
            "entityType": ENTITY_ITEM,
            "itemId": item_id,
            "stock": parsed.value,
            "threshold": threshold,
        }
    )
    return _response(
        200,
        {
            "ok": True,
            "item": {"itemId": item_id, "stock": parsed.value, "threshold": threshold},
        },
    )
