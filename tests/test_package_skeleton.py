"""パッケージ骨格のスモーク。業務ロジックの正しさは見ない。"""

from __future__ import annotations

from household_restock import __version__, package_name


def test_package_name() -> None:
    assert package_name() == "household-restock"


def test_version_is_placeholder() -> None:
    assert __version__ == "0.0.0"
