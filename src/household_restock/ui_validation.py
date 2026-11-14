"""画面・中継 API 向けの入力検証（純関数）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StockParseResult:
    ok: bool
    value: int | None = None
    reason: str | None = None


def parse_non_negative_int(raw: object) -> StockParseResult:
    """非負整数だけを許す。文字列の前後空白は許容。"""
    if isinstance(raw, bool):
        return StockParseResult(False, reason="not_integer")
    if isinstance(raw, int):
        if raw < 0:
            return StockParseResult(False, reason="negative")
        return StockParseResult(True, value=raw)
    if isinstance(raw, str):
        text = raw.strip()
        if text == "" or not text.isdigit():
            return StockParseResult(False, reason="not_integer")
        return StockParseResult(True, value=int(text))
    return StockParseResult(False, reason="not_integer")


def decision_allowed_for_status(status: str) -> bool:
    """UI・API 共通: 承認待ち以外は decision 不可。"""
    return status == "AWAITING_APPROVAL"
