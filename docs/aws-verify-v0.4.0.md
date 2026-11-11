# v0.4.0 AWS 検証手順（ユーザー実施）

**次の一手:** v0.3 まで deploy 済みなら、この版の template を再 deploy し、下を順に確認する。

エージェントは AWS に接続・デプロイしない。未実施なら v0.4.0 は「実装済み・AWS 検証待ち」。

## 前提

1. `./scripts/check.sh` が通っている
2. `SAM_CLI_TELEMETRY=0 mise exec -- uv run sam validate --lint`
3. `SAM_CLI_TELEMETRY=0 mise exec -- uv run sam build`
4. deploy 時に **ApprovalSharedSecret** を渡す。**DeliveryWaitSeconds** は短くしてよい（例: `30`）
5. 失敗モード確認用に、再 deploy または品目の `orderFailureMode` を切り替える

## 確認手順

### 1. 一時失敗が Retry で回復する

1. 品目 META に `orderFailureMode=transient_once` を付ける（または `DemoOrderFailureMode=transient_once` で deploy）
2. 在庫をしきい値以下にして承認する
3. SFN 実行履歴で `PlaceOrder` が `OrderTransientError` のあと Retry し、成功している
4. 状態が `SHIPPING_WAIT` → Wait 後 `ARRIVAL_CONFIRMED` になる
5. `LOCK` が最終的に消えている。在庫は注文では変わらない

### 2. 継続失敗が Catch / 取消骨格へ入る

1. `orderFailureMode=permanent`
2. 承認後、`PlaceOrder` が `OrderPermanentError` で Catch → `CancelSkeleton`
3. 状態が `ORDER_FAILED`。実行履歴に取消骨格側の遷移がある
4. `LOCK` が解放されている

### 3. Wait 後に到着確認へ進む

1. `succeed` モードで承認
2. `WaitForDelivery` で止まり、`arriveAt` 以降に `ConfirmArrival` へ進む（待ちは短縮可）
3. 画面（localhost aws 中継）で「配送待ち」→「到着確認」が分かる

### 4. 画面ラベル

localhost 中継（`UI_BACKEND=aws`）で「注文中」「配送待ち」「失敗」が表示されることを確認する。

## 片付け

中継を止め、不要なら `sam delete`。
