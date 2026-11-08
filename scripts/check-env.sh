#!/usr/bin/env bash
# 開発環境の再確認用。AWS への接続や認証は行わない。
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

if [[ ! -x .venv/bin/python ]]; then
  echo "ERROR: .venv がありません。README の venv 作成手順を実行してください。" >&2
  exit 1
fi

# 開発依存（pytest / ruff / sam）は venv 側
# shellcheck disable=SC1091
source .venv/bin/activate
export PATH="$ROOT/.venv/bin:$PATH"

echo "== Python packages (venv) =="
python --version
pip check

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

echo "== project skills =="
mise exec -- skills list

echo "== AWS CLI（任意・接続はしない） =="
if command -v aws >/dev/null 2>&1; then
  aws --version
else
  echo "aws は未インストール（今回は必須ではない）"
fi

echo "OK: 環境チェック完了（AWS 未接続・補充機能は未検証）"
