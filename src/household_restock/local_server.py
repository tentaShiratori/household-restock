"""127.0.0.1 専用の最小 UI + API 中継（stdlib のみ）。"""

from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Protocol, override
from urllib.parse import urlparse

from household_restock.memory_store import MemoryStore
from household_restock.ui_api import contains_forbidden_secret_text, json_body
from household_restock.ui_validation import parse_non_negative_int

STOCK_PATH = re.compile(r"^/api/items/([^/]+)/stock$")
DECISION_PATH = re.compile(r"^/api/items/([^/]+)/restock-requests/([^/]+)/decision$")


class Store(Protocol):
    def list_items(self) -> list[dict[str, Any]]: ...

    def list_restocks(self) -> list[dict[str, Any]]: ...

    def update_stock(self, *, item_id: str, stock_raw: object) -> dict[str, Any]: ...

    def decide(
        self, *, item_id: str, stream_event_id: str, decision: str
    ) -> dict[str, Any]: ...


class UiApp:
    def __init__(self, *, web_root: Path, store: Store) -> None:
        self.web_root = web_root.resolve()
        self.store = store

    def handle_api(
        self, method: str, path: str, raw_body: bytes
    ) -> tuple[int, dict[str, Any]]:
        if method == "GET" and path == "/api/items":
            return 200, {"ok": True, "items": self.store.list_items()}
        if method == "GET" and path == "/api/restock-requests":
            return 200, {"ok": True, "restockRequests": self.store.list_restocks()}

        stock_match = STOCK_PATH.match(path)
        if stock_match and method == "PUT":
            item_id = stock_match.group(1)
            try:
                payload = json.loads(raw_body.decode("utf-8") or "{}")
            except (UnicodeDecodeError, json.JSONDecodeError):
                return 400, {"ok": False, "reason": "bad_json"}
            if not isinstance(payload, dict):
                return 400, {"ok": False, "reason": "bad_json"}
            result = self.store.update_stock(
                item_id=item_id, stock_raw=payload.get("stock")
            )
            status = int(result.pop("httpStatus", 500))
            return status, result

        decision_match = DECISION_PATH.match(path)
        if decision_match and method == "POST":
            item_id, event_id = decision_match.group(1), decision_match.group(2)
            try:
                payload = json.loads(raw_body.decode("utf-8") or "{}")
            except (UnicodeDecodeError, json.JSONDecodeError):
                return 400, {"ok": False, "reason": "bad_json"}
            if not isinstance(payload, dict):
                return 400, {"ok": False, "reason": "bad_json"}
            decision = payload.get("decision")
            if not isinstance(decision, str):
                return 400, {"ok": False, "reason": "invalid_decision"}
            result = self.store.decide(
                item_id=item_id, stream_event_id=event_id, decision=decision
            )
            status = int(result.pop("httpStatus", 500))
            return status, result

        return 404, {"ok": False, "reason": "not_found"}


def make_handler(app: UiApp) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        @override
        def log_message(self, format: str, *args: object) -> None:
            del format, args

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _read_body(self) -> bytes:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return b""
            return self.rfile.read(length)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            if path.startswith("/api/"):
                status, payload = app.handle_api("GET", path, b"")
                raw = json_body(payload).encode("utf-8")
                if contains_forbidden_secret_text(raw.decode("utf-8")):
                    raw = json_body({"ok": False, "reason": "internal_error"}).encode(
                        "utf-8"
                    )
                    status = 500
                self._send(status, raw, "application/json; charset=utf-8")
                return
            self._serve_static(path)

        def do_PUT(self) -> None:  # noqa: N802
            self._api("PUT")

        def do_POST(self) -> None:  # noqa: N802
            self._api("POST")

        def _api(self, method: str) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            if not path.startswith("/api/"):
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
            body = self._read_body()
            status, payload = app.handle_api(method, path, body)
            raw = json_body(payload).encode("utf-8")
            if contains_forbidden_secret_text(raw.decode("utf-8")):
                raw = json_body({"ok": False, "reason": "internal_error"}).encode(
                    "utf-8"
                )
                status = 500
            self._send(status, raw, "application/json; charset=utf-8")

        def _serve_static(self, path: str) -> None:
            rel = "index.html" if path in {"", "/"} else path.lstrip("/")
            target = (app.web_root / rel).resolve()
            if not str(target).startswith(str(app.web_root)) or not target.is_file():
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
            data = target.read_bytes()
            # 静的 JS は「秘密検知用の禁止文字列」自体を含むためスキャンしない。
            # 秘密非露出は API 応答側で担保する。
            ctype = "text/plain; charset=utf-8"
            if target.suffix == ".html":
                ctype = "text/html; charset=utf-8"
            elif target.suffix == ".js":
                ctype = "text/javascript; charset=utf-8"
            elif target.suffix == ".css":
                ctype = "text/css; charset=utf-8"
            self._send(200, data, ctype)

    return Handler


def create_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    web_root: Path,
    store: Store | None = None,
) -> tuple[ThreadingHTTPServer, Store]:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("UI server must bind to loopback only")
    backend: Store
    if store is None:
        mem = MemoryStore()
        mem.seed_demo()
        backend = mem
    else:
        backend = store
    app = UiApp(web_root=web_root, store=backend)
    handler = make_handler(app)
    server = ThreadingHTTPServer((host, port), handler)
    return server, backend


def validate_stock_field(raw: object) -> tuple[bool, str | None]:
    parsed = parse_non_negative_int(raw)
    return parsed.ok, parsed.reason
