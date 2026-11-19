"""ローカル / e2e 用のメモリ backend（AWS なし）。"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from threading import Lock
from typing import Any
from uuid import uuid4

from household_restock.approval import STATUS_AWAITING, apply_decision
from household_restock.compensation import (
    apply_order_cancel,
    apply_restock_cancel,
    status_after_compensation,
)
from household_restock.evaluate import stock_at_or_below_threshold
from household_restock.order import (
    MODE_SUCCEED,
    normalize_failure_mode,
    simulate_order_pipeline,
)
from household_restock.status_labels import (
    STATUS_ARRIVAL_CONFIRMED,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_ORDERING,
    STATUS_SHIPPING_WAIT,
    label_for_status,
)
from household_restock.stock_apply import (
    DEFAULT_RESTOCK_QTY,
    OUTCOME_ARRIVED,
    OUTCOME_NOT_ARRIVED,
    apply_stock,
    can_claim_stock_apply,
    normalize_delivery_outcome,
    normalize_restock_qty,
    status_after_successful_apply,
)
from household_restock.ui_validation import parse_non_negative_int


@dataclass
class MemoryStore:
    """品目・補充・占有をプロセス内に持つ。taskToken は外に出さない。"""

    items: dict[str, dict[str, Any]] = field(default_factory=dict)
    restocks: dict[str, dict[str, Any]] = field(default_factory=dict)
    locks: dict[str, str] = field(default_factory=dict)
    restock_qty: int = DEFAULT_RESTOCK_QTY
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
                "deliveryOutcome": OUTCOME_ARRIVED,
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

    def set_delivery_outcome(self, *, item_id: str, outcome: object) -> dict[str, Any]:
        normalized = normalize_delivery_outcome(outcome)
        with self._lock:
            item = self.items.get(item_id)
            if item is None:
                return {"ok": False, "reason": "not_found", "httpStatus": 404}
            item["deliveryOutcome"] = normalized
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
                    outcome = normalize_delivery_outcome(item.get("deliveryOutcome"))
                    qty = normalize_restock_qty(self.restock_qty)
                    self.locks[item_id] = event_id
                    self.restocks[event_id] = {
                        "itemId": item_id,
                        "streamEventId": event_id,
                        "status": STATUS_AWAITING,
                        "stock": parsed.value,
                        "threshold": int(item["threshold"]),
                        "orderFailureMode": mode,
                        "deliveryOutcome": outcome,
                        "restockQty": qty,
                        "stockApplied": False,
                        "orderCancelled": False,
                        "restockCancelled": False,
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
                self._release_lock(item_id, stream_event_id)
                return self._restock_response(row, item_id, stream_event_id)

            row["status"] = STATUS_ORDERING
            mode = normalize_failure_mode(row.get("orderFailureMode"))
            outcome = simulate_order_pipeline(
                mode=mode,
                item_id=item_id,
                stream_event_id=stream_event_id,
                delivery_wait_seconds=1,
            )
            if not outcome.ok:
                self._run_compensation(row, item_id, stream_event_id)
            else:
                row["status"] = STATUS_SHIPPING_WAIT
                row["arriveAt"] = outcome.arrive_at
                row["orderId"] = outcome.order_id

            return self._restock_response(row, item_id, stream_event_id)

    def advance_delivery(self, *, item_id: str, stream_event_id: str) -> dict[str, Any]:
        """ローカル専用: Wait 相当を進めて到着加算または未着補償。"""
        with self._lock:
            row = self.restocks.get(stream_event_id)
            if row is None or row.get("itemId") != item_id:
                return {"ok": False, "reason": "not_found", "httpStatus": 404}
            if row.get("status") != STATUS_SHIPPING_WAIT:
                return {"ok": False, "reason": "not_shipping_wait", "httpStatus": 409}

            outcome = normalize_delivery_outcome(row.get("deliveryOutcome"))
            if outcome == OUTCOME_NOT_ARRIVED:
                self._run_compensation(row, item_id, stream_event_id)
                return self._restock_response(row, item_id, stream_event_id)

            row["status"] = STATUS_ARRIVAL_CONFIRMED
            self._apply_stock_once(row, item_id, stream_event_id)
            return self._restock_response(row, item_id, stream_event_id)

    def notify_arrival(self, *, item_id: str, stream_event_id: str) -> dict[str, Any]:
        """到着通知の模擬。2 回目は加算しない（冪等）。"""
        with self._lock:
            row = self.restocks.get(stream_event_id)
            if row is None or row.get("itemId") != item_id:
                return {"ok": False, "reason": "not_found", "httpStatus": 404}
            status = str(row.get("status"))
            if status == STATUS_SHIPPING_WAIT:
                row["status"] = STATUS_ARRIVAL_CONFIRMED
            elif status not in (STATUS_ARRIVAL_CONFIRMED, STATUS_COMPLETED):
                return {
                    "ok": False,
                    "reason": "not_arrival_eligible",
                    "httpStatus": 409,
                }
            applied = self._apply_stock_once(row, item_id, stream_event_id)
            body = self._restock_response(row, item_id, stream_event_id)
            body["stockAppliedThisCall"] = applied
            return body

    def retry_compensation(
        self, *, item_id: str, stream_event_id: str
    ) -> dict[str, Any]:
        """補償の再試行。二重取消にならない。"""
        with self._lock:
            row = self.restocks.get(stream_event_id)
            if row is None or row.get("itemId") != item_id:
                return {"ok": False, "reason": "not_found", "httpStatus": 404}
            first_order = apply_order_cancel(row)
            first_restock = apply_restock_cancel(row)
            if row.get("restockCancelled"):
                row["status"] = status_after_compensation()
            self._release_lock(item_id, stream_event_id)
            body = self._restock_response(row, item_id, stream_event_id)
            body["orderCancelApplied"] = first_order
            body["restockCancelApplied"] = first_restock
            return body

    def _apply_stock_once(
        self, row: dict[str, Any], item_id: str, stream_event_id: str
    ) -> bool:
        claimed = can_claim_stock_apply(
            status=str(row.get("status")),
            stock_applied=bool(row.get("stockApplied")),
        )
        if not claimed:
            self._release_lock(item_id, stream_event_id)
            if row.get("stockApplied"):
                row["status"] = status_after_successful_apply()
            return False
        item = self.items.get(item_id)
        if item is None:
            return False
        qty = normalize_restock_qty(row.get("restockQty", self.restock_qty))
        item["stock"] = apply_stock(current_stock=int(item["stock"]), restock_qty=qty)
        row["stockApplied"] = True
        row["status"] = STATUS_COMPLETED
        self._release_lock(item_id, stream_event_id)
        return True

    def _run_compensation(
        self, row: dict[str, Any], item_id: str, stream_event_id: str
    ) -> None:
        apply_order_cancel(row)
        apply_restock_cancel(row)
        row["status"] = STATUS_CANCELLED
        self._release_lock(item_id, stream_event_id)

    def _release_lock(self, item_id: str, stream_event_id: str) -> None:
        if self.locks.get(item_id) == stream_event_id:
            del self.locks[item_id]

    def _restock_response(
        self, row: dict[str, Any], item_id: str, stream_event_id: str
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "httpStatus": 200,
            "status": row["status"],
            "label": label_for_status(str(row["status"])),
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
