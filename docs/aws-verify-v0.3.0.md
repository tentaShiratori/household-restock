# v0.3.0 AWS 検証手順（ユーザー実施）

**次の一手:** v0.2 まで deploy 済みなら、この版の template を再 deploy し、下の番号を順に確認する。

エージェントは AWS に接続・デプロイしない。未実施なら v0.3.0 は「実装済み・AWS 検証待ち」。

## 前提

1. `./scripts/check.sh` が通っている
2. `mise exec -- npm run test:e2e` がローカル（memory）で通っている
3. `SAM_CLI_TELEMETRY=0 mise exec -- uv run sam validate --lint`
4. `SAM_CLI_TELEMETRY=0 mise exec -- uv run sam build`
5. deploy 時に **ApprovalSharedSecret**（16文字以上）を渡す。値はリポジトリ・チャット・画面に書かない
6. Outputs の `ApprovalApiUrl` と Table 名を控える

## 確認手順

### 1. 品目を用意する

```bash
./scripts/update-stock.sh "<Table>" toilet-paper 5 3
```

### 2. localhost 中継を AWS モードで起動する

```bash
export APPROVAL_API_URL='https://….amazonaws.com/prod'
# 秘密はシェルに一時的に置く。履歴に残したくなければ都度入力する
export APPROVAL_SHARED_SECRET='…'
export UI_BACKEND=aws
mise exec -- uv run python scripts/serve-ui.py --port 8765
```

ブラウザで http://127.0.0.1:8765/ を開く（loopback 以外に bind しない）。

### 3. 画面から操作する

1. 在庫一覧に `toilet-paper` が出る
2. 在庫をしきい値以下（例: 2）に更新する → 補充リクエストが `AWAITING_APPROVAL` になる（Streams → SFN）
3. 画面の承認または却下で状態が変わり、在庫数は承認では変わらない
4. 承認済み行の承認ボタンは押せない。再送するとエラー表示（競合）になる

### 4. 秘密がブラウザに出ていない

1. ページソースと Network の応答に `taskToken` / `X-Approval-Secret` / 共有秘密の値が無い
2. ブラウザの JS に秘密を埋め込んでいない（中継の環境変数だけ）

### 5. 保護なし書込が公開到達しないことの確認方針

- 書込 API は共有秘密なしで 401 になる（curl でヘッダ無しを試してよい。秘密の値は出力に残さない）
- 画面は loopback 中継経由だけを使う。CORS 開放でブラウザから直接書込させない

## 片付け

中継プロセスを止め、不要なら `sam delete`。
