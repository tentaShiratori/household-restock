# v0.1.0 AWS 検証手順（ユーザー実施）

**次の一手:** ローカルで `sam build` 済みなら、自分のアカウントで deploy し、下の番号どおり確認する。

エージェントは AWS に接続・デプロイしない。ここは**ユーザー作業**。未実施なら v0.1.0 は「実装済み・AWS 検証待ち」。

## 前提

1. `mise exec -- uv sync --locked`
2. `mise exec -- uv run sam validate --lint`
3. `mise exec -- uv run sam build`
4. 自分の資格情報で deploy（例: `sam deploy --guided`）。秘密はリポジトリに書かない
5. Outputs の `HouseholdRestockTableName` を控える

## 確認手順

### 1. しきい値超 → SFN 非起動

```bash
./scripts/update-stock.sh <TableName> toilet-paper 9 3
```

1. Lambda ログで `started` が増えていない（または skip）ことを見る
2. Step Functions に新しい実行が無いことを見る
3. テーブルに `sk` が `RESTOCK#…` の行がこの操作では増えていないことを見る

### 2. しきい値以下 → 1本起動 + 記録1件

```bash
./scripts/update-stock.sh <TableName> toilet-paper 2 3
```

1. Standard ワークフローが **1本** 起動する
2. 同じ品目の `RESTOCK#<eventID>` が **1件** ある
3. 実行入力に `itemId=toilet-paper` が入っている

### 3. 補充リクエスト記録だけでは追加起動なし

1. 手順2のあと、補充行が増えたこと自体で Lambda が再起動しないことを確認する
2. フィルタ（`sk=META` かつ `entityType=ITEM`）と判定ロジックの両方で弾いている

### 4. 同一イベント再処理で記録が増えない

1. 手順2の Streams レコード相当を（学習用に）同じ `eventID` で再投入するか、同じ実行名で `StartExecution` を再実行する
2. `ExecutionAlreadyExists` または PutItem の条件失敗で、`RESTOCK#…` は **増えない**

## 片付け

```bash
sam delete
```

スタックを消して作り直せることを確認する（要件9）。
