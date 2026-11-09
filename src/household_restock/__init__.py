"""業務機能は未実装。coverage / typecheck の測定対象になる最小パッケージ骨格。"""

from __future__ import annotations

__all__ = ["__version__", "package_name"]

__version__ = "0.0.0"


def package_name() -> str:
    """配布名を返す。測定対象を空にしないための最小関数。"""
    return "household-restock"
