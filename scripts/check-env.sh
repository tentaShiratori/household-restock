#!/usr/bin/env bash
# 開発環境の再確認用。AWS への接続や認証は行わない。
# どのカレントディレクトリから呼んでもリポジトリ根へ移動する。activate は不要。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v mise >/dev/null 2>&1; then
  echo "ERROR: mise が PATH にありません。README の bootstrap を先に実行してください。" >&2
  exit 1
fi

echo "== mise tools =="
mise --version
mise ls --current
mise exec -- python --version
mise exec -- node --version
mise exec -- skills --version
mise exec -- uv --version

echo "== uv project =="
mise exec -- uv lock --check
mise exec -- uv sync --locked --check
mise exec -- uv run python --version
mise exec -- uv pip check

echo "== pytest (+ coverage fail-under=80) =="
mise exec -- uv run pytest

echo "== ruff =="
mise exec -- uv run ruff check .
mise exec -- uv run ruff format --check .

echo "== SAM CLI =="
mise exec -- uv run sam --version
mise exec -- uv run sam --help >/dev/null

echo "== project skills =="
mise exec -- skills list

echo "== AWS CLI（任意・接続はしない） =="
if command -v aws >/dev/null 2>&1; then
  aws --version
else
  echo "aws は未インストール（今回は必須ではない）"
fi

echo "OK: 環境チェック完了（AWS 未接続・補充機能は未検証）"
echo "品質ゲート一式は ./scripts/check.sh（vulture / mypy / e2e doctor を含む）"
