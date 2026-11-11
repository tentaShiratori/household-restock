"""メモリ backend の在庫更新・承認・秘密非露出。"""

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


def test_reject_non_awaiting_and_approve() -> None:
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
    assert ok["status"] == "APPROVED"
    again = store.decide(
        item_id="toilet-paper", stream_event_id=event_id, decision="approve"
    )
    assert again["httpStatus"] == 409
    assert store.list_items()[0]["stock"] == 0


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
