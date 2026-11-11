"""判定 Lambda。Streams → 占有 → SFN 起動。ReportBatchItemFailures 対応。"""

from __future__ import annotations

import json
import os
from typing import Any

from household_restock.keys import LOCK_SK, META_SK, item_pk
from household_restock.occupancy import (
    build_occupancy_put,
    occupancy_item_attrs,
    release_condition,
)
from household_restock.order import normalize_failure_mode
from household_restock.stream import evaluate_dynamodb_record


def _release_lock(table: Any, *, item_id: str, stream_event_id: str) -> None:
    from botocore.exceptions import ClientError

    cond, values = release_condition(stream_event_id=stream_event_id)
    try:
        table.delete_item(
            Key={"pk": item_pk(item_id), "sk": LOCK_SK},
            ConditionExpression=cond,
            ExpressionAttributeValues=values,
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code == "ConditionalCheckFailedException":
            return
        raise


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    """DynamoDB Streams バッチを処理する。失敗レコードだけ報告する。"""
    import boto3
    from botocore.exceptions import ClientError

    del context

    state_machine_arn = os.environ["STATE_MACHINE_ARN"]
    table_name = os.environ["TABLE_NAME"]
    sfn = boto3.client("stepfunctions")
    table = boto3.resource("dynamodb").Table(table_name)

    started = 0
    skipped = 0
    batch_failures: list[dict[str, str]] = []
    records = event.get("Records", [])
    if not isinstance(records, list):
        records = []

    for record in records:
        if not isinstance(record, dict):
            continue
        event_id = record.get("eventID")
        identifier = event_id if isinstance(event_id, str) else None
        try:
            _decision, start = evaluate_dynamodb_record(record)
            if start is None:
                skipped += 1
                continue

            put = build_occupancy_put(
                item_id=start.item_id, stream_event_id=start.stream_event_id
            )
            try:
                table.put_item(
                    Item=occupancy_item_attrs(
                        item_id=start.item_id,
                        stream_event_id=start.stream_event_id,
                    ),
                    ConditionExpression=put.condition_expression,
                    ExpressionAttributeValues=put.expression_attribute_values,
                )
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                if code == "ConditionalCheckFailedException":
                    skipped += 1
                    continue
                raise

            failure_mode = normalize_failure_mode(
                os.environ.get("DEMO_ORDER_FAILURE_MODE", "succeed")
            )
            try:
                meta = table.get_item(
                    Key={"pk": item_pk(start.item_id), "sk": META_SK}
                ).get("Item")
            except ClientError:
                meta = None
            if isinstance(meta, dict) and isinstance(meta.get("orderFailureMode"), str):
                failure_mode = normalize_failure_mode(meta.get("orderFailureMode"))

            payload = {
                "itemId": start.item_id,
                "stock": start.stock,
                "threshold": start.threshold,
                "streamEventId": start.stream_event_id,
                "orderFailureMode": failure_mode,
            }
            try:
                sfn.start_execution(
                    stateMachineArn=state_machine_arn,
                    name=start.execution_name,
                    input=json.dumps(payload),
                )
                started += 1
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                if code == "ExecutionAlreadyExists":
                    skipped += 1
                    continue
                _release_lock(
                    table,
                    item_id=start.item_id,
                    stream_event_id=start.stream_event_id,
                )
                raise
        except Exception:
            if identifier is not None:
                batch_failures.append({"itemIdentifier": identifier})
            else:
                raise

    return {
        "started": started,
        "skipped": skipped,
        "batchItemFailures": batch_failures,
    }
