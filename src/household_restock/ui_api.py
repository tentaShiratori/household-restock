"""中継 API の応答整形（秘密を落とす）。"""

from __future__ import annotations

import json
from typing import Any

SECRET_KEYS = frozenset(
    {
        "tasktoken",
        "task_token",
        "approvalsharedsecret",
        "approval_shared_secret",
        "x-approval-secret",
        "aws_secret_access_key",
        "secretaccesskey",
    }
)


def _normalized_key(key: object) -> str:
    return str(key).lower().replace("-", "").replace("_", "")


def strip_secrets(value: Any) -> Any:
    """ネストした dict/list から秘密キーを除く。"""
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, raw in value.items():
            norm = _normalized_key(key)
            if norm in {_normalized_key(k) for k in SECRET_KEYS}:
                continue
            if "token" in norm and "stream" not in norm:
                continue
            cleaned[str(key)] = strip_secrets(raw)
        return cleaned
    if isinstance(value, list):
        return [strip_secrets(v) for v in value]
    return value


def json_body(payload: dict[str, Any]) -> str:
    return json.dumps(strip_secrets(payload), ensure_ascii=False)


def contains_forbidden_secret_text(text: str) -> bool:
    lowered = text.lower()
    markers = (
        "tasktoken",
        "approval_shared_secret",
        "x-approval-secret",
        "aws_secret_access_key",
        "secret-token-",
    )
    return any(m in lowered for m in markers)
