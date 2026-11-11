"""パッケージ骨格のスモーク。"""

from __future__ import annotations

from household_restock import __version__, package_name


def test_package_name() -> None:
    assert package_name() == "household-restock"


def test_version_is_v0_3_0() -> None:
    assert __version__ == "0.3.0"
