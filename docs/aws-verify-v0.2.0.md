# v0.2.0 AWS 検証手順（ユーザー実施）

**次の一手:** `sam build` 済みなら、自分の資格情報で deploy し、下の番号を順に確認する。

エージェントは AWS に接続・デプロイしない。未実施なら v0.2.0 は「実装済み・AWS 検証待ち」。

## 前提

1. `./scripts/check.sh` が通っている
2. `SAM_CLI_TELEMETRY=0 mise exec -- uv run sam validate --lint`
3. `SAM_CLI_TELEMETRY=0 mise exec -- uv run sam build`
4. deploy 時に **ApprovalSharedSecret**（16文字以上）を渡し、**ApprovalTimeoutSeconds** を短縮してよい（例: `60`）
5. Outputs の Table 名・ApprovalApiUrl・StateMachine ARN を控える
6. 秘密はリポジトリに書かない。シェル履歴に残したくない場合は都度入力する

## 確認手順

### 1. 承認 API で再開（在庫は承認では変えない）

1. `./scripts/update-stock.sh <Table> toilet-paper 2 3` でしきい値以下にする
2. SFN が `WaitForApproval` で止まる
3. テーブルの `RESTOCK#<eventId>` が `AWAITING_APPROVAL`（`taskToken` 属性はコンソールで見えても **API 応答やスクリプト出力に出さない**）
4. 承認:

```bash
APPROVAL_SHARED_SECRET='…' \
  ./scripts/decide-restock.sh "<ApprovalApiUrl>" toilet-paper "<streamEventId>" approve
```

5. 実行が成功終了し、`LOCK` 行が消えている
6. 品目の `stock` が承認前後で変わっていない

却下する場合は最後の引数を `reject` にする。

### 2. timeout で却下扱い・在庫不変

1. Timeout を短く deploy したうえで、在庫を以下にして承認しない
2. タイムアウト後、補充の status が `TIMED_OUT`
3. `LOCK` が解放されている
4. 品目 `stock` は変わらない

### 3. 占有中は2本目なし

1. 承認待ちのまま、もう一度 `./scripts/update-stock.sh` で在庫をさらに減らす
2. 新しい SFN 実行が **増えない**（EvaluateStock は占有 ConditionalCheckFailed で skip）
3. 承認または timeout で解放後は、再度しきい値以下更新で新しい実行を開始できる

### 4. decision の競合・再送

1. 同じ approve を2回送る → 2回目は 409（`conflict` / `already_terminal`）
2. timeout 後に approve → 409
3. 誤った `X-Approval-Secret` → 401

### 5. 起動失敗時の占有回復（任意）

学習用に StateMachine ARN を一時的に壊す等は本番では避ける。  
コード上は StartExecution 失敗時に `_release_lock` する。ログで confirm できれば十分。

## 片付け

```bash
sam delete
```
