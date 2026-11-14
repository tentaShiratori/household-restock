"""模擬注文の決定的失敗モード。"""

from __future__ import annotations

from household_restock.order import (
    ERROR_PERMANENT,
    ERROR_TRANSIENT,
    MODE_PERMANENT,
    MODE_TRANSIENT_ONCE,
    evaluate_order_attempt,
    simulate_order_pipeline,
)


def test_succeed_and_permanent() -> None:
    ok = evaluate_order_attempt(
        mode="succeed",
        attempt_number=1,
        item_id="toilet-paper",
        stream_event_id="e1",
        delivery_wait_seconds=5,
    )
    assert ok.ok is True
    assert ok.arrive_at is not None
    bad = evaluate_order_attempt(
        mode=MODE_PERMANENT,
        attempt_number=1,
        item_id="toilet-paper",
        stream_event_id="e1",
        delivery_wait_seconds=5,
    )
    assert bad.ok is False
    assert bad.error_name == ERROR_PERMANENT


def test_transient_once_retries_then_succeeds() -> None:
    first = evaluate_order_attempt(
        mode=MODE_TRANSIENT_ONCE,
        attempt_number=1,
        item_id="toilet-paper",
        stream_event_id="e1",
        delivery_wait_seconds=1,
    )
    assert first.error_name == ERROR_TRANSIENT
    second = evaluate_order_attempt(
        mode=MODE_TRANSIENT_ONCE,
        attempt_number=2,
        item_id="toilet-paper",
        stream_event_id="e1",
        delivery_wait_seconds=1,
    )
    assert second.ok is True
    pipeline = simulate_order_pipeline(
        mode=MODE_TRANSIENT_ONCE,
        item_id="toilet-paper",
        stream_event_id="e1",
    )
    assert pipeline.ok is True
    exhausted = simulate_order_pipeline(
        mode=MODE_TRANSIENT_ONCE,
        item_id="toilet-paper",
        stream_event_id="e1",
        max_transient_attempts=1,
    )
    assert exhausted.ok is False
    assert exhausted.error_name == ERROR_TRANSIENT
