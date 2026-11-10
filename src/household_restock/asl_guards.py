"""restock.asl.json の安全ガード（ローカルで壊れていないか検査する）。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Catch で ResultPath を省略すると入力全体がエラーに置換され、
# 後続が $.itemId を解決できず States.Runtime（Catch 不可）→ LOCK 残留になり得る。
CATCH_RESULT_PATH = "$.error"

# timeout / failed の更新は承認待ち（または未承認の RECORDED）のときだけ。
TIMEOUT_STATUS_CONDITION = "#s = :awaiting OR #s = :recorded"


def load_restock_asl(path: Path) -> dict[str, Any]:
    """SAM の ${Subst} を仮値に置換して JSON として読む。"""
    raw = path.read_text(encoding="utf-8")
    # TimeoutSeconds: ${ApprovalTimeoutSeconds} → 数値（クォート無し）
    fixed = re.sub(
        r'"TimeoutSeconds":\s*\$\{ApprovalTimeoutSeconds\}',
        '"TimeoutSeconds": 60',
        raw,
    )
    # 既に "..." 内なら中身だけ置換（""SUBST"" にしない）
    fixed = re.sub(r"\$\{[A-Za-z0-9]+\}", "SUBST", fixed)
    data = json.loads(fixed)
    if not isinstance(data, dict):
        raise ValueError("ASL root must be an object")
    return data


def catchers(state: dict[str, Any]) -> list[dict[str, Any]]:
    raw = state.get("Catch") or []
    if not isinstance(raw, list):
        return []
    return [c for c in raw if isinstance(c, dict)]


def assert_catch_preserves_input(state_name: str, state: dict[str, Any]) -> None:
    for catcher in catchers(state):
        path = catcher.get("ResultPath")
        if path != CATCH_RESULT_PATH:
            raise AssertionError(
                f"{state_name} Catch must set ResultPath={CATCH_RESULT_PATH!r} "
                f"to keep itemId/streamEventId; got {path!r}"
            )


def assert_release_lock_policy(state: dict[str, Any]) -> None:
    """想定外の解放失敗を Done に握りつぶさない。"""
    allowed = {"DynamoDB.ConditionalCheckFailedException"}
    for catcher in catchers(state):
        errors = catcher.get("ErrorEquals") or []
        if not isinstance(errors, list):
            raise AssertionError("ReleaseLock Catch ErrorEquals must be a list")
        for err in errors:
            if err not in allowed:
                raise AssertionError(
                    "ReleaseLock must not Catch unexpected errors to Done; "
                    f"found {err!r}"
                )
        if catcher.get("Next") != "Done":
            raise AssertionError("ReleaseLock ConditionalCheckFailed must go to Done")


def assert_timeout_is_conditional(state: dict[str, Any]) -> None:
    params = state.get("Parameters") or {}
    if not isinstance(params, dict):
        raise AssertionError("MarkTimedOut Parameters missing")
    cond = params.get("ConditionExpression")
    if cond != TIMEOUT_STATUS_CONDITION:
        raise AssertionError(
            "MarkTimedOut must only update AWAITING/RECORDED; "
            f"expected {TIMEOUT_STATUS_CONDITION!r}, got {cond!r}"
        )
