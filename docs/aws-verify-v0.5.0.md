# v0.5.0 AWS 検証手順（ユーザー実施）

**次の一手:** v0.4 まで deploy 済みなら、この版の template を再 deploy し、下を順に確認する。

エージェントは AWS に接続・デプロイしない。未実施なら v0.5.0 は「実装済み・AWS 検証待ち」。

## 前提

1. `./scripts/check.sh` が通っている
2. `SAM_CLI_TELEMETRY=0 mise exec -- uv run sam validate --lint`
3. `SAM_CLI_TELEMETRY=0 mise exec -- uv run sam build`
4. deploy 時に **ApprovalSharedSecret** を渡す。**DeliveryWaitSeconds** は短くしてよい（例: `30`）。**RestockQuantity** は既定 `10` でよい

## 確認手順

### 1. 到着で在庫が 1 回だけ増える（通知 2 回）

1. `DemoDeliveryOutcome=arrived`（既定）で deploy
2. 在庫をしきい値以下にして承認する。Wait 後に `ConfirmArrival` → `ApplyStock` へ進む
3. META の `stock` が `RestockQuantity` 分増えている。RESTOCK は `COMPLETED` かつ `stockApplied=true`
4. 同じ実行で `ApplyStock` 相当を再実行する（または条件を満たした Update/Transact を手元で再送する）と、TransactionCanceled / 条件失敗になり、**在庫はそれ以上増えない**
5. `LOCK` が消えている

### 2. 未着で補償が順に走る

1. 品目 META に `deliveryOutcome=not_arrived` を付ける（または `DemoDeliveryOutcome=not_arrived` で再 deploy）
2. 承認 → Wait 後、`ChooseDeliveryOutcome` → `CancelOrder` → `CancelRestockRequest` → `ReleaseLock`
3. 実行履歴でこの順が並んでいる
4. RESTOCK は `CANCELLED`。`orderCancelled` / `restockCancelled` が true。在庫は増えていない

### 3. 注文失敗でも同じ補償順

1. `orderFailureMode=permanent`
2. 承認後、`PlaceOrder` Catch → `CancelOrder` → `CancelRestockRequest` → `ReleaseLock`
3. 履歴で順序を確認。状態は `CANCELLED`

### 4. 補償の再試行が冪等

1. 補償済みの RESTOCK に対し、同じ Cancel 条件の Update を再送する
2. ConditionalCheckFailed になり、フラグや状態が二重に変わらない
3. `LOCK` は既に無い（または ReleaseLock の条件不一致で Done）

### 5. 終端後に次の補充を始められる

1. 成功または取消で `LOCK` が消えたあと、同じ品目の在庫を再びしきい値以下にする
2. 新しい RESTOCK / SFN 実行が 1 本だけ始まる

## 片付け

中継を止め、不要なら `sam delete`。
