"""判定 Lambda。Streams → 純関数判定 → Step Functions 起動。"""

from __future__ import annotations

import json
import os
from typing import Any

from household_restock.stream import evaluate_dynamodb_record


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    """DynamoDB Streams バッチを処理する。

    boto3 は Lambda ランタイム提供。ローカル型チェックでは unresolved を許容する。
    """
    import boto3
    from botocore.exceptions import ClientError

    state_machine_arn = os.environ["STATE_MACHINE_ARN"]
    sfn = boto3.client("stepfunctions")

    started = 0
    skipped = 0
    records = event.get("Records", [])
    if not isinstance(records, list):
        records = []

    for record in records:
        if not isinstance(record, dict):
            skipped += 1
            continue
        decision, start = evaluate_dynamodb_record(record)
        if start is None:
            skipped += 1
            continue
        payload = {
            "itemId": start.item_id,
            "stock": start.stock,
            "threshold": start.threshold,
            "streamEventId": start.stream_event_id,
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
            # 同一 eventID の再処理: 実行名衝突は成功扱い（冪等）
            if code == "ExecutionAlreadyExists":
                skipped += 1
                continue
            raise

    return {"started": started, "skipped": skipped}
