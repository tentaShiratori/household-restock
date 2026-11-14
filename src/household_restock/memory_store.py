"""ローカル / e2e 用のメモリ backend（AWS なし）。"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from threading import Lock
from typing import Any
from uuid import uuid4

from household_restock.approval import STATUS_AWAITING, apply_decision
from household_restock.evaluate import stock_at_or_below_threshold
from household_restock.order import (
    MODE_SUCCEED,
    normalize_failure_mode,
    simulate_order_pipeline,
)
from household_restock.status_labels import (
    STATUS_ARRIVAL_CONFIRMED,
    STATUS_ORDER_FAILED,
    STATUS_ORDERING,
    STATUS_SHIPPING_WAIT,
    label_for_status,
)
from household_restock.ui_validation import parse_non_negative_int


@dataclass
class MemoryStore:
    """品目・補充・占有をプロセス内に持つ。taskToken は外に出さない。"""

    items: dict[str, dict[str, Any]] = field(default_factory=dict)
    restocks: dict[str, dict[str, Any]] = field(default_factory=dict)
    locks: dict[str, str] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def seed_demo(
        self, *, item_id: str = "toilet-paper", stock: int = 5, threshold: int = 3
    ) -> None:
        with self._lock:
            self.items[item_id] = {
                "itemId": item_id,
                "stock": stock,
                "threshold": threshold,
                "orderFailureMode": MODE_SUCCEED,
            }

    def list_items(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                deepcopy(v)
                for v in sorted(self.items.values(), key=lambda x: str(x["itemId"]))
            ]

    def list_restocks(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = []
            for row in self.restocks.values():
                status = str(row["status"])
                public = {
                    "itemId": row["itemId"],
                    "streamEventId": row["streamEventId"],
                    "status": status,
                    "label": label_for_status(status),
                    "stock": row["stock"],
                    "threshold": row["threshold"],
                }
                rows.append(public)
            return sorted(
                rows, key=lambda r: (str(r["itemId"]), str(r["streamEventId"]))
            )

    def set_order_failure_mode(self, *, item_id: str, mode: object) -> dict[str, Any]:
        normalized = normalize_failure_mode(mode)
        with self._lock:
            item = self.items.get(item_id)
            if item is None:
                return {"ok": False, "reason": "not_found", "httpStatus": 404}
            item["orderFailureMode"] = normalized
            return {
                "ok": True,
                "httpStatus": 200,
                "item": deepcopy(item),
            }

    def update_stock(self, *, item_id: str, stock_raw: object) -> dict[str, Any]:
        parsed = parse_non_negative_int(stock_raw)
        if not parsed.ok or parsed.value is None:
            return {
                "ok": False,
                "reason": parsed.reason or "not_integer",
                "httpStatus": 400,
            }

        with self._lock:
            item = self.items.get(item_id)
            if item is None:
                return {"ok": False, "reason": "not_found", "httpStatus": 404}
            item["stock"] = parsed.value
            started: dict[str, Any] | None = None
            if stock_at_or_below_threshold(
                stock=parsed.value, threshold=int(item["threshold"])
            ):
                if item_id not in self.locks:
                    event_id = f"local-{uuid4().hex[:12]}"
                    mode = normalize_failure_mode(item.get("orderFailureMode"))
                    self.locks[item_id] = event_id
                    self.restocks[event_id] = {
                        "itemId": item_id,
                        "streamEventId": event_id,
                        "status": STATUS_AWAITING,
                        "stock": parsed.value,
                        "threshold": int(item["threshold"]),
                        "orderFailureMode": mode,
                        "taskToken": f"secret-token-{event_id}",
                    }
                    started = {
                        "streamEventId": event_id,
                        "status": STATUS_AWAITING,
                    }
            return {
                "ok": True,
                "httpStatus": 200,
                "item": deepcopy(item),
                "restockStarted": started,
            }

    def decide(
        self, *, item_id: str, stream_event_id: str, decision: str
    ) -> dict[str, Any]:
        with self._lock:
            row = self.restocks.get(stream_event_id)
            if row is None or row.get("itemId") != item_id:
                return {"ok": False, "reason": "not_found", "httpStatus": 404}
            result = apply_decision(
                current_status=str(row["status"]), decision=decision
            )
            if not result.accepted or result.new_status is None:
                return {"ok": False, "reason": result.reason, "httpStatus": 409}
            row["status"] = result.new_status
            row.pop("taskToken", None)

            if result.new_status == "REJECTED":
                if self.locks.get(item_id) == stream_event_id:
                    del self.locks[item_id]
                return {
                    "ok": True,
                    "httpStatus": 200,
                    "status": result.new_status,
                    "label": label_for_status(result.new_status),
                    "itemId": item_id,
                    "streamEventId": stream_event_id,
                }

            # 承認後は占有を維持したまま注文シミュレート（SFN 相当）
            row["status"] = STATUS_ORDERING
            mode = normalize_failure_mode(row.get("orderFailureMode"))
            outcome = simulate_order_pipeline(
                mode=mode,
                item_id=item_id,
                stream_event_id=stream_event_id,
                delivery_wait_seconds=1,
            )
            if not outcome.ok:
                row["status"] = STATUS_ORDER_FAILED
                if self.locks.get(item_id) == stream_event_id:
                    del self.locks[item_id]
            else:
                row["status"] = STATUS_SHIPPING_WAIT
                row["arriveAt"] = outcome.arrive_at
                row["orderId"] = outcome.order_id

            return {
                "ok": True,
                "httpStatus": 200,
                "status": row["status"],
                "label": label_for_status(str(row["status"])),
                "itemId": item_id,
                "streamEventId": stream_event_id,
            }

    def advance_delivery(self, *, item_id: str, stream_event_id: str) -> dict[str, Any]:
        """ローカル専用: Wait 相当を手動で進めて到着確認にする。"""
        with self._lock:
            row = self.restocks.get(stream_event_id)
            if row is None or row.get("itemId") != item_id:
                return {"ok": False, "reason": "not_found", "httpStatus": 404}
            if row.get("status") != STATUS_SHIPPING_WAIT:
                return {"ok": False, "reason": "not_shipping_wait", "httpStatus": 409}
            row["status"] = STATUS_ARRIVAL_CONFIRMED
            if self.locks.get(item_id) == stream_event_id:
                del self.locks[item_id]
            return {
                "ok": True,
                "httpStatus": 200,
                "status": STATUS_ARRIVAL_CONFIRMED,
                "label": label_for_status(STATUS_ARRIVAL_CONFIRMED),
                "itemId": item_id,
                "streamEventId": stream_event_id,
            }

    def has_secret_leak(self, payload: object) -> bool:
        """応答 JSON に秘密っぽいキーが出ていないか（検査用）。"""
        text = str(payload).lower()
        banned = (
            "tasktoken",
            "approval_shared_secret",
            "x-approval-secret",
            "secret-token-",
        )
        return any(b in text for b in banned)
