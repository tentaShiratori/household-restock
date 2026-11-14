#!/usr/bin/env bash
# 承認/却下 API を呼ぶ（ユーザーが自分の秘密ヘッダで実行する）。
# task token はクライアントに出ない。秘密を引数履歴に残したくない場合は環境変数を使う。
set -euo pipefail

usage() {
  cat <<'EOF'
使い方:
  APPROVAL_SHARED_SECRET='…' \
    ./scripts/decide-restock.sh <api-base-url> <item-id> <stream-event-id> approve|reject

例:
  APPROVAL_SHARED_SECRET="$SECRET" \
    ./scripts/decide-restock.sh \
      "https://xxxx.execute-api.region.amazonaws.com/prod" \
      toilet-paper \
      c496f875-aaaa-bbbb-cccc-000000000001 \
      approve
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -ne 4 ]]; then
  usage
  exit 1
fi

BASE="${1%/}"
ITEM_ID="$2"
EVENT_ID="$3"
DECISION="$4"
SECRET="${APPROVAL_SHARED_SECRET:-}"

if [[ -z "$SECRET" ]]; then
  echo "ERROR: APPROVAL_SHARED_SECRET を環境変数で渡してください（リポジトリに書かない）。" >&2
  exit 1
fi

URL="${BASE}/items/${ITEM_ID}/restock-requests/${EVENT_ID}/decision"

curl -sS -X POST "$URL" \
  -H "content-type: application/json" \
  -H "X-Approval-Secret: ${SECRET}" \
  -d "{\"decision\":\"${DECISION}\"}"
echo
