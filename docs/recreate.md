# 削除して再デプロイする（再現手順）

**次の一手:** ローカルで `./scripts/check.sh` と `sam validate` / `sam build` が通ってから、自分の AWS で下を実施する。

エージェントは AWS に接続・デプロイ・削除しない。未実施なら受け入れ F は「実装済み・AWS 検証待ち」。

## 1. ローカルで定義を確かめる

```bash
mise install
mise exec -- uv sync --locked
mise exec -- npm ci
./scripts/check.sh
SAM_CLI_TELEMETRY=0 mise exec -- uv run sam validate --lint
SAM_CLI_TELEMETRY=0 mise exec -- uv run sam build
```

## 2. 既存スタックを消す（あれば）

```bash
sam delete --stack-name <あなたのスタック名>
```

テーブル・HTTP API・Lambda・State Machine など、`template.yaml` で定義したリソースが消える想定。  
秘密の値はチャットやリポジトリに残さない。

## 3. 再デプロイする

```bash
SAM_CLI_TELEMETRY=0 mise exec -- uv run sam build
SAM_CLI_TELEMETRY=0 mise exec -- uv run sam deploy --guided
```

渡すもの（例）:

- **ApprovalSharedSecret**（16 文字以上、NoEcho）
- 検証を短くするなら **ApprovalTimeoutSeconds** / **DeliveryWaitSeconds**

Outputs の `ApprovalApiUrl` と Table 名を控える。

## 4. 品目を用意する

```bash
./scripts/update-stock.sh "<TableName>" toilet-paper 5 3
```

## 5. 画面と中継を再現する

静的画面は `web/`。中継は `scripts/serve-ui.py`（SAM 外・localhost）。

```bash
export APPROVAL_API_URL='https://….amazonaws.com/prod'
export APPROVAL_SHARED_SECRET='…'
export UI_BACKEND=aws
mise exec -- uv run python scripts/serve-ui.py --port 8765
```

ブラウザで http://127.0.0.1:8765/ を開く（loopback 以外に bind しない）。

ローカルだけ試すときは秘密なしで:

```bash
mise exec -- uv run python scripts/serve-ui.py --port 8765
```

（既定 `UI_BACKEND=memory`）

## 6. 同じ動きか見る

しきい値以下で補充が 1 本始まる、承認/却下、注文/Wait、加算または補償、占有解放後の再起動、秘密がブラウザに出ない、を [aws-verify-v1.0.0.md](aws-verify-v1.0.0.md) の表に沿って確認する。

## 片付け

中継を止め、不要なら再度 `sam delete`。
