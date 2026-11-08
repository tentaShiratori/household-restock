"""開発環境のスモークテスト。

補充機能や AWS 結合の正しさは検証しない。
Python バージョンと、テストランナーが少なくとも1件収集できることだけを見る。
"""

from __future__ import annotations

import sys


def test_python_major_minor_is_3_12() -> None:
    assert sys.version_info[:2] == (3, 12), f"expected Python 3.12.x, got {sys.version}"


def test_smoke_always_passes() -> None:
    """収集件数0を成功扱いにしないための、常に通る小さなケース。"""
    assert 1 + 1 == 2
