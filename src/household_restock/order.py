"""模擬注文の決定的な成否判定（乱数なし）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

MODE_SUCCEED = "succeed"
MODE_TRANSIENT_ONCE = "transient_once"
MODE_PERMANENT = "permanent"

ERROR_TRANSIENT = "OrderTransientError"
ERROR_PERMANENT = "OrderPermanentError"

VALID_MODES = frozenset({MODE_SUCCEED, MODE_TRANSIENT_ONCE, MODE_PERMANENT})


@dataclass(frozen=True)
class OrderAttemptResult:
    """1 回の注文試行の結果。"""

    ok: bool
    error_name: str | None = None
    order_id: str | None = None
    arrive_at: str | None = None
    reason: str = ""


def normalize_failure_mode(raw: object) -> str:
    if not isinstance(raw, str):
        return MODE_SUCCEED
    value = raw.strip().lower()
    if value in VALID_MODES:
        return value
    return MODE_SUCCEED


def evaluate_order_attempt(
    *,
    mode: str,
    attempt_number: int,
    item_id: str,
    stream_event_id: str,
    delivery_wait_seconds: int,
) -> OrderAttemptResult:
    """attempt_number は 1 始まり（DynamoDB 加算後の値）。

    - succeed: 常に成功
    - transient_once: 1 回目だけ OrderTransientError（Retry 対象）
    - permanent: 常に OrderPermanentError（Retry せず Catch）
    """
    normalized = normalize_failure_mode(mode)
    if normalized == MODE_PERMANENT:
        return OrderAttemptResult(
            ok=False,
            error_name=ERROR_PERMANENT,
            reason="deterministic_permanent_failure",
        )
    if normalized == MODE_TRANSIENT_ONCE and attempt_number <= 1:
        return OrderAttemptResult(
            ok=False,
            error_name=ERROR_TRANSIENT,
            reason="deterministic_transient_failure",
        )
    wait = max(0, int(delivery_wait_seconds))
    arrive = datetime.now(UTC) + timedelta(seconds=wait)
    order_id = f"ord-{item_id}-{stream_event_id}"[:64]
    return OrderAttemptResult(
        ok=True,
        order_id=order_id,
        arrive_at=arrive.strftime("%Y-%m-%dT%H:%M:%SZ"),
        reason="ordered",
    )


def simulate_order_pipeline(
    *,
    mode: str,
    item_id: str,
    stream_event_id: str,
    delivery_wait_seconds: int = 1,
    max_transient_attempts: int = 2,
) -> OrderAttemptResult:
    """ローカル memory 用: Retry 相当を同期で再現する。"""
    normalized = normalize_failure_mode(mode)
    if normalized == MODE_PERMANENT:
        return evaluate_order_attempt(
            mode=normalized,
            attempt_number=1,
            item_id=item_id,
            stream_event_id=stream_event_id,
            delivery_wait_seconds=delivery_wait_seconds,
        )
    for attempt in range(1, max_transient_attempts + 1):
        result = evaluate_order_attempt(
            mode=normalized,
            attempt_number=attempt,
            item_id=item_id,
            stream_event_id=stream_event_id,
            delivery_wait_seconds=delivery_wait_seconds,
        )
        if result.ok:
            return result
        if result.error_name == ERROR_PERMANENT:
            return result
    return OrderAttemptResult(
        ok=False,
        error_name=ERROR_TRANSIENT,
        reason="transient_retries_exhausted",
    )
