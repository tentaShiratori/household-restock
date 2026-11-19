"""パッケージ骨格のスモーク。"""

from __future__ import annotations

from household_restock import __version__, package_name


def test_package_name() -> None:
    assert package_name() == "household-restock"


def test_version_is_v1_0_0() -> None:
    assert __version__ == "1.0.0"
