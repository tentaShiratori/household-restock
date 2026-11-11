"""localhost 中継の AWS モード: HTTP API へ共有秘密付きで中継（boto3 不要）。"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from household_restock.ui_api import strip_secrets


class AwsHttpStore:
    """ブラウザには秘密を渡さず、中継プロセスだけがヘッダを付ける。"""

    def __init__(self, *, api_base: str, shared_secret: str) -> None:
        base = api_base.rstrip("/")
        if not base.startswith("https://"):
            raise ValueError("Approval API base must be https")
        if len(shared_secret) < 16:
            raise ValueError("shared secret too short")
        self.api_base = base
        self._secret = shared_secret

    def list_items(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/items")
        items = data.get("items")
        return items if isinstance(items, list) else []

    def list_restocks(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/restock-requests")
        rows = data.get("restockRequests")
        return rows if isinstance(rows, list) else []

    def update_stock(self, *, item_id: str, stock_raw: object) -> dict[str, Any]:
        return self._request(
            "PUT",
            f"/items/{item_id}/stock",
            body={"stock": stock_raw},
            include_status=True,
        )

    def decide(
        self, *, item_id: str, stream_event_id: str, decision: str
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/items/{item_id}/restock-requests/{stream_event_id}/decision",
            body={"decision": decision},
            include_status=True,
        )

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        include_status: bool = False,
    ) -> dict[str, Any]:
        url = f"{self.api_base}{path}"
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "content-type": "application/json",
                "X-Approval-Secret": self._secret,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                status = getattr(resp, "status", 200)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            status = exc.code
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"ok": False, "reason": "upstream_error"}
            if not isinstance(payload, dict):
                payload = {"ok": False, "reason": "upstream_error"}
            cleaned = strip_secrets(payload)
            if include_status:
                cleaned["httpStatus"] = status
            return cleaned
        except urllib.error.URLError:
            out: dict[str, Any] = {"ok": False, "reason": "upstream_unreachable"}
            if include_status:
                out["httpStatus"] = 502
            return out

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"ok": False, "reason": "bad_upstream_json"}
        if not isinstance(payload, dict):
            payload = {"ok": False, "reason": "bad_upstream_json"}
        cleaned = strip_secrets(payload)
        if include_status:
            cleaned["httpStatus"] = status
        return cleaned


def store_from_env() -> AwsHttpStore:
    api = os.environ.get("APPROVAL_API_URL", "").strip()
    secret = os.environ.get("APPROVAL_SHARED_SECRET", "")
    return AwsHttpStore(api_base=api, shared_secret=secret)
