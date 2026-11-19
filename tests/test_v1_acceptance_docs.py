"""v1.0.0 受け入れ文書と選定理由がリポジトリにあること。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_acceptance_and_why_sfn_docs_exist() -> None:
    acceptance = (ROOT / "docs/plan/v1.0.0-acceptance.md").read_text(encoding="utf-8")
    why = (ROOT / "docs/plan/why-step-functions.md").read_text(encoding="utf-8")
    recreate = (ROOT / "docs/recreate.md").read_text(encoding="utf-8")
    for letter in "ABCDEFGHI":
        assert f"| {letter} |" in acceptance or f"| {letter} " in acceptance
    assert "Lambda durable functions" in why or "durable functions" in why
    assert "Step Functions" in why
    assert "sam delete" in recreate
    assert "serve-ui.py" in recreate
