"""補充リクエスト状態の画面表示ラベル。"""

from __future__ import annotations

STATUS_ORDERING = "ORDERING"
STATUS_SHIPPING_WAIT = "SHIPPING_WAIT"
STATUS_ARRIVAL_CONFIRMED = "ARRIVAL_CONFIRMED"
STATUS_ORDER_FAILED = "ORDER_FAILED"

LABELS: dict[str, str] = {
    "RECORDED": "記録済み",
    "AWAITING_APPROVAL": "承認待ち",
    "APPROVED": "承認済み",
    "REJECTED": "却下",
    "TIMED_OUT": "タイムアウト",
    "FAILED": "失敗",
    STATUS_ORDERING: "注文中",
    STATUS_SHIPPING_WAIT: "配送待ち",
    STATUS_ARRIVAL_CONFIRMED: "到着確認",
    STATUS_ORDER_FAILED: "失敗",
}


def label_for_status(status: str) -> str:
    return LABELS.get(status, status)
