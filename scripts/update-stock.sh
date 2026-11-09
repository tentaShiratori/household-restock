#!/usr/bin/env bash
# 品目の現在在庫を更新する（ユーザーが自分の AWS 資格情報で実行する）。
# エージェントは AWS に接続しない。秘密情報は引数にも環境にも書かない。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

usage() {
  cat <<'EOF'
使い方:
  ./scripts/update-stock.sh <table-name> <item-id> <stock> [threshold]

例（しきい値以下にして起動を試す）:
  ./scripts/update-stock.sh HouseholdRestock-xxx toilet-paper 2 3

例（しきい値超で非起動を試す）:
  ./scripts/update-stock.sh HouseholdRestock-xxx toilet-paper 9 3

初回は threshold を必ず渡し、品目行を Put する。
2回目以降は stock だけ更新（threshold 省略時は既存値を維持するため Update ではなく、省略時はエラー）。
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -lt 3 ]]; then
  usage
  exit 1
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "ERROR: aws CLI が必要です（認証はユーザー側）。" >&2
  exit 1
fi

TABLE="$1"
ITEM_ID="$2"
STOCK="$3"
THRESHOLD="${4:-}"
PK="ITEM#${ITEM_ID}"
SK="META"

if [[ -z "$THRESHOLD" ]]; then
  echo "ERROR: v0.1.0 のこのスクリプトは Put のため threshold も必須です。" >&2
  echo "       例: ./scripts/update-stock.sh \"$TABLE\" \"$ITEM_ID\" \"$STOCK\" 3" >&2
  exit 1
fi

aws dynamodb put-item \
  --table-name "$TABLE" \
  --item "{
    \"pk\": {\"S\": \"${PK}\"},
    \"sk\": {\"S\": \"${SK}\"},
    \"entityType\": {\"S\": \"ITEM\"},
    \"itemId\": {\"S\": \"${ITEM_ID}\"},
    \"stock\": {\"N\": \"${STOCK}\"},
    \"threshold\": {\"N\": \"${THRESHOLD}\"}
  }"

echo "OK: put ${PK} / ${SK} stock=${STOCK} threshold=${THRESHOLD}"
echo "Streams → EvaluateStock →（条件を満たせば）SFN を確認してください。"
