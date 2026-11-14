#!/usr/bin/env python3
"""localhost 専用 UI 中継。秘密は環境変数のみ。ブラウザに出さない。"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from household_restock.local_server import Store, create_server  # noqa: E402
from household_restock.memory_store import MemoryStore  # noqa: E402


def build_store(backend: str) -> Store:
    if backend == "memory":
        store = MemoryStore()
        store.seed_demo()
        return store
    if backend == "aws":
        from household_restock.aws_http_store import store_from_env

        return store_from_env()
    raise SystemExit(f"unknown backend: {backend}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="household-restock local UI (loopback only)"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--backend",
        choices=("memory", "aws"),
        default=os.environ.get("UI_BACKEND", "memory"),
        help="memory=ローカル/e2e（AWSなし） / aws=デプロイ済み API へ秘密付き中継",
    )
    args = parser.parse_args()

    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        print("ERROR: loopback 以外には bind しません", file=sys.stderr)
        return 2

    if args.backend == "aws":
        if not os.environ.get("APPROVAL_API_URL"):
            print(
                "ERROR: UI_BACKEND=aws には APPROVAL_API_URL が必要です",
                file=sys.stderr,
            )
            return 2
        if not os.environ.get("APPROVAL_SHARED_SECRET"):
            print(
                "ERROR: UI_BACKEND=aws には APPROVAL_SHARED_SECRET が必要です",
                file=sys.stderr,
            )
            return 2

    store = build_store(args.backend)
    web_root = ROOT / "web"
    server, _ = create_server(
        host=args.host, port=args.port, web_root=web_root, store=store
    )
    print(f"UI listening on http://{args.host}:{args.port}/ (backend={args.backend})")
    if args.backend == "memory":
        print("AWS is not contacted.")
    else:
        print(
            "Proxying to APPROVAL_API_URL with X-Approval-Secret from env (not logged)."
        )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
