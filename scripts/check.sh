#!/usr/bin/env bash
# 品質ゲート一式。AWS 接続・認証はしない。業務機能の正しさは保証しない。
# どのカレントディレクトリから呼んでもリポジトリ根へ移動する。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v mise >/dev/null 2>&1; then
  echo "ERROR: mise が PATH にありません。README の bootstrap を先に実行してください。" >&2
  exit 1
fi

export E2E_TELEMETRY_DISABLED=1
export DO_NOT_TRACK=1

echo "== mise / uv 同期確認 =="
mise --version
mise ls --current
mise exec -- uv lock --check
mise exec -- uv sync --locked --check
mise exec -- uv pip check

echo "== unit + coverage (fail-under=80) =="
mise exec -- uv run pytest
# 期待: 測定対象 household_restock が 80% 以上。業務品質の指標ではない。

echo "== ruff lint =="
mise exec -- uv run ruff check .

echo "== ruff format --check =="
mise exec -- uv run ruff format --check .

echo "== deadcode (vulture) =="
# min_confidence=60（pyproject）: 未使用関数(60%)も検出。見つかると exit != 0
mise exec -- uv run vulture src tests

echo "== typecheck (ty; Beta / 0.0.x) =="
mise exec -- uv run ty check
# 期待: src/tests に型エラーなし。警告も error-on-warning で失敗扱い。

echo "== e2e tooling (npm e2e@0.23.0, telemetry off, mise Node) =="
if [[ ! -d node_modules/e2e ]]; then
  echo "ERROR: node_modules/e2e がありません。先に mise exec -- npm ci を実行してください。" >&2
  exit 1
fi
# mise 固定の Node / npm を使う（PATH 上の別 Node に依存しない）
mise exec -- npm run e2e:version
# 期待: 0.23.0
mise exec -- npm run e2e:doctor
# 期待: exit 0（シナリオ0件でも doctor は通る）
#
# 注意: mise exec -- npm run test:e2e (= e2e run) はシナリオ0件だと公式どおり NO_TESTS で失敗する。
# --pass-with-no-tests で偽の合格にしない。意味のあるシナリオは v0.3.0 の画面以降。

echo "OK: 品質チェック完了（AWS 未接続・業務機能未検証・e2e シナリオは未作成）"
