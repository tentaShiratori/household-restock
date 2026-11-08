#!/usr/bin/env bash
# 開発環境の再確認用。AWS への接続や認証は行わない。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -x .venv/bin/python ]]; then
  echo "ERROR: .venv がありません。README の手順で作成してください。" >&2
  exit 1
fi

# venv を優先（sam もここに入る）
# shellcheck disable=SC1091
source .venv/bin/activate
export PATH="$ROOT/.venv/bin:$PATH"

echo "== Python =="
python --version

echo "== pytest =="
pytest

echo "== ruff =="
ruff check .
ruff format --check .

echo "== SAM CLI =="
if ! command -v sam >/dev/null 2>&1; then
  echo "ERROR: sam が見つかりません（.venv への aws-sam-cli 導入を確認）。" >&2
  exit 1
fi
sam --version
sam --help >/dev/null

echo "== AWS CLI（任意・接続はしない） =="
if command -v aws >/dev/null 2>&1; then
  aws --version
else
  echo "aws は未インストール（今回は必須ではない。導入する場合は公式インストーラを参照）"
fi

echo "OK: 環境チェック完了（AWS 未接続・補充機能は未検証）"
