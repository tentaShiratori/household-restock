"""中継 API ハンドラ（loopback サーバ本体は起動しない）。"""

from __future__ import annotations

from pathlib import Path

from household_restock.local_server import UiApp
from household_restock.memory_store import MemoryStore
from household_restock.ui_api import (
    contains_forbidden_secret_text,
    json_body,
    strip_secrets,
)


def test_api_flow_and_secret_strip(tmp_path: Path) -> None:
    store = MemoryStore()
    store.seed_demo(stock=5, threshold=3)
    app = UiApp(web_root=tmp_path, store=store)

    status, items = app.handle_api("GET", "/api/items", b"")
    assert status == 200
    assert items["items"][0]["itemId"] == "toilet-paper"

    status, updated = app.handle_api(
        "PUT", "/api/items/toilet-paper/stock", b'{"stock": 2}'
    )
    assert status == 200
    assert updated["ok"] is True
    event_id = updated["restockStarted"]["streamEventId"]

    status, approved = app.handle_api(
        "POST",
        f"/api/items/toilet-paper/restock-requests/{event_id}/decision",
        b'{"decision":"approve"}',
    )
    assert status == 200
    assert approved["ok"] is True
    assert approved["status"] == "SHIPPING_WAIT"

    status, conflict = app.handle_api(
        "POST",
        f"/api/items/toilet-paper/restock-requests/{event_id}/decision",
        b'{"decision":"reject"}',
    )
    assert status == 409
    assert conflict["ok"] is False

    status, arrived = app.handle_api(
        "POST",
        f"/api/items/toilet-paper/restock-requests/{event_id}/advance-delivery",
        b"{}",
    )
    assert status == 200
    assert arrived["status"] == "ARRIVAL_CONFIRMED"

    leaked = strip_secrets({"taskToken": "abc", "itemId": "x", "ok": True})
    assert "taskToken" not in leaked
    assert contains_forbidden_secret_text(json_body(leaked)) is False


def test_invalid_stock_rejected(tmp_path: Path) -> None:
    store = MemoryStore()
    store.seed_demo()
    app = UiApp(web_root=tmp_path, store=store)
    status, body = app.handle_api(
        "PUT", "/api/items/toilet-paper/stock", b'{"stock": -1}'
    )
    assert status == 400
    assert body["reason"] == "negative"
