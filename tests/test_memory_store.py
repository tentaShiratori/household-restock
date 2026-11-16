"""メモリ backend の在庫更新・承認・冪等加算・補償・秘密非露出。"""

from __future__ import annotations

from household_restock.memory_store import MemoryStore
from household_restock.ui_api import contains_forbidden_secret_text, json_body


def test_update_below_threshold_starts_one_restock() -> None:
    store = MemoryStore()
    store.seed_demo(stock=5, threshold=3)
    first = store.update_stock(item_id="toilet-paper", stock_raw=2)
    assert first["ok"] is True
    assert first["restockStarted"]["status"] == "AWAITING_APPROVAL"
    second = store.update_stock(item_id="toilet-paper", stock_raw=1)
    assert second["ok"] is True
    assert second["restockStarted"] is None
    assert len(store.list_restocks()) == 1


def test_reject_non_awaiting_and_approve_to_shipping() -> None:
    store = MemoryStore()
    store.seed_demo(stock=5, threshold=3)
    started = store.update_stock(item_id="toilet-paper", stock_raw=0)
    event_id = started["restockStarted"]["streamEventId"]
    bad = store.decide(
        item_id="toilet-paper", stream_event_id=event_id, decision="maybe"
    )
    assert bad["ok"] is False
    ok = store.decide(
        item_id="toilet-paper", stream_event_id=event_id, decision="approve"
    )
    assert ok["ok"] is True
    assert ok["status"] == "SHIPPING_WAIT"
    assert ok["label"] == "配送待ち"
    assert "toilet-paper" in store.locks
    again = store.decide(
        item_id="toilet-paper", stream_event_id=event_id, decision="approve"
    )
    assert again["httpStatus"] == 409
    assert store.list_items()[0]["stock"] == 0
    advanced = store.advance_delivery(item_id="toilet-paper", stream_event_id=event_id)
    assert advanced["status"] == "COMPLETED"
    assert "toilet-paper" not in store.locks
    assert store.list_items()[0]["stock"] == 10


def test_arrival_twice_adds_stock_once() -> None:
    store = MemoryStore(restock_qty=10)
    store.seed_demo(stock=5, threshold=3)
    started = store.update_stock(item_id="toilet-paper", stock_raw=0)
    event_id = started["restockStarted"]["streamEventId"]
    store.decide(item_id="toilet-paper", stream_event_id=event_id, decision="approve")
    first = store.notify_arrival(item_id="toilet-paper", stream_event_id=event_id)
    assert first["stockAppliedThisCall"] is True
    assert first["status"] == "COMPLETED"
    assert store.list_items()[0]["stock"] == 10
    second = store.notify_arrival(item_id="toilet-paper", stream_event_id=event_id)
    assert second["stockAppliedThisCall"] is False
    assert store.list_items()[0]["stock"] == 10
    assert "toilet-paper" not in store.locks


def test_permanent_order_failure_runs_compensation() -> None:
    store = MemoryStore()
    store.seed_demo(stock=5, threshold=3)
    store.set_order_failure_mode(item_id="toilet-paper", mode="permanent")
    started = store.update_stock(item_id="toilet-paper", stock_raw=0)
    event_id = started["restockStarted"]["streamEventId"]
    ok = store.decide(
        item_id="toilet-paper", stream_event_id=event_id, decision="approve"
    )
    assert ok["status"] == "CANCELLED"
    assert ok["label"] == "取消済み"
    assert "toilet-paper" not in store.locks
    retry = store.retry_compensation(item_id="toilet-paper", stream_event_id=event_id)
    assert retry["orderCancelApplied"] is False
    assert retry["restockCancelApplied"] is False
    assert retry["status"] == "CANCELLED"


def test_not_arrived_compensates_and_allows_next_restock() -> None:
    store = MemoryStore()
    store.seed_demo(stock=5, threshold=3)
    store.set_delivery_outcome(item_id="toilet-paper", outcome="not_arrived")
    started = store.update_stock(item_id="toilet-paper", stock_raw=0)
    event_id = started["restockStarted"]["streamEventId"]
    store.decide(item_id="toilet-paper", stream_event_id=event_id, decision="approve")
    done = store.advance_delivery(item_id="toilet-paper", stream_event_id=event_id)
    assert done["status"] == "CANCELLED"
    assert store.list_items()[0]["stock"] == 0
    assert "toilet-paper" not in store.locks
    again = store.update_stock(item_id="toilet-paper", stock_raw=0)
    assert again["restockStarted"] is not None


def test_responses_never_include_task_token() -> None:
    store = MemoryStore()
    store.seed_demo(stock=1, threshold=3)
    store.update_stock(item_id="toilet-paper", stock_raw=0)
    payload = {
        "items": store.list_items(),
        "restockRequests": store.list_restocks(),
    }
    text = json_body(payload)
    assert contains_forbidden_secret_text(text) is False
    assert store.has_secret_leak(payload) is False
