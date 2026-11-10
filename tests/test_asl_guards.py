"""restock.asl.json の Catch / timeout / 解放ガード。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from household_restock.asl_guards import (
    CATCH_RESULT_PATH,
    TIMEOUT_STATUS_CONDITION,
    assert_catch_preserves_input,
    assert_release_lock_policy,
    assert_timeout_is_conditional,
    catchers,
    load_restock_asl,
)

ASL_PATH = Path(__file__).resolve().parents[1] / "statemachine" / "restock.asl.json"


@pytest.fixture(scope="module")
def asl() -> dict[str, Any]:
    return load_restock_asl(ASL_PATH)


def test_asl_file_exists() -> None:
    assert ASL_PATH.is_file()


def test_wait_for_approval_catch_keeps_item_ids(asl: dict[str, Any]) -> None:
    states = asl["States"]
    assert isinstance(states, dict)
    state = states["WaitForApproval"]
    assert isinstance(state, dict)
    assert_catch_preserves_input("WaitForApproval", state)
    errors = {
        e
        for c in catchers(state)
        for e in (c.get("ErrorEquals") or [])
        if isinstance(e, str)
    }
    assert "States.Timeout" in errors
    assert "ApprovalRejected" in errors
    for catcher in catchers(state):
        assert catcher["ResultPath"] == CATCH_RESULT_PATH


def test_put_and_mark_states_preserve_input_on_catch(asl: dict[str, Any]) -> None:
    states = asl["States"]
    assert isinstance(states, dict)
    for name in ("PutRestockRequest", "MarkTimedOut", "MarkFailed", "ReleaseLock"):
        state = states[name]
        assert isinstance(state, dict)
        assert_catch_preserves_input(name, state)


def test_mark_timed_out_does_not_overwrite_terminal(asl: dict[str, Any]) -> None:
    states = asl["States"]
    assert isinstance(states, dict)
    state = states["MarkTimedOut"]
    assert isinstance(state, dict)
    assert_timeout_is_conditional(state)
    params = state["Parameters"]
    assert isinstance(params, dict)
    assert params["ConditionExpression"] == TIMEOUT_STATUS_CONDITION
    values = params["ExpressionAttributeValues"]
    assert isinstance(values, dict)
    awaiting = values[":awaiting"]
    recorded = values[":recorded"]
    timed = values[":timed"]
    assert isinstance(awaiting, dict)
    assert isinstance(recorded, dict)
    assert isinstance(timed, dict)
    assert awaiting["S"] == "AWAITING_APPROVAL"
    assert recorded["S"] == "RECORDED"
    assert timed["S"] == "TIMED_OUT"
    # 条件不一致でも占有解放へ進む（承認と timeout の競合）
    nexts = {c.get("Next") for c in catchers(state)}
    assert "ReleaseLock" in nexts


def test_release_lock_does_not_swallow_unexpected_errors(asl: dict[str, Any]) -> None:
    states = asl["States"]
    assert isinstance(states, dict)
    state = states["ReleaseLock"]
    assert isinstance(state, dict)
    assert_release_lock_policy(state)
    # States.ALL を Done に送ると解放失敗が成功終了に見える
    for catcher in catchers(state):
        assert "States.ALL" not in (catcher.get("ErrorEquals") or [])


def test_broken_catch_without_result_path_is_detected() -> None:
    broken = {
        "Catch": [
            {
                "ErrorEquals": ["States.Timeout"],
                "Next": "MarkTimedOut",
            }
        ]
    }
    with pytest.raises(AssertionError, match="ResultPath"):
        assert_catch_preserves_input("WaitForApproval", broken)


def test_broken_release_lock_states_all_is_detected() -> None:
    broken = {
        "Catch": [
            {
                "ErrorEquals": ["States.ALL"],
                "ResultPath": "$.error",
                "Next": "Done",
            }
        ]
    }
    with pytest.raises(AssertionError, match="unexpected"):
        assert_release_lock_policy(broken)


def test_broken_unconditional_timeout_is_detected() -> None:
    broken = {
        "Parameters": {
            "UpdateExpression": "SET #s = :timed",
            # ConditionExpression なし
        }
    }
    with pytest.raises(AssertionError, match="AWAITING"):
        assert_timeout_is_conditional(broken)
