# v1.0.0 AWS 検証手順（ユーザー実施）

**次の一手:** [recreate.md](recreate.md) で削除→再デプロイしたうえで、下の A〜H を確認する。I は文書のみ。

エージェントは AWS に接続しない。未実施項目は「実装済み・AWS 検証待ち」のまま完成扱いにしない。

詳細な版別手順は v0.1〜v0.5 の `aws-verify-*.md` を参照してよい。ここは全体の照合用。

## 前提

1. `./scripts/check.sh` OK
2. `sam validate --lint` / `sam build` OK
3. [recreate.md](recreate.md) の deploy と画面中継

## 受け入れ A〜I（AWS 側）

| # | 確認すること | メモ |
| --- | --- | --- |
| A | しきい値以下でちょうど 1 本。さらに減らしても 2 本目なし | LOCK と実行数 |
| B | 承認放置 → timeout 却下相当。在庫不変 | Timeout 短縮可 |
| C | 一時失敗は Retry 回復。継続失敗は CancelOrder→CancelRestockRequest | 実行履歴 |
| D | 到着相当を 2 回扱っても在庫加算は 1 回 | stockApplied |
| E | Wait が arriveAt 以降に再開 | DeliveryWaitSeconds 短縮可 |
| F | 削除→再デプロイで同じ操作ができる | [recreate.md](recreate.md) |
| G | 最小画面から一覧・在庫・状態・承認/却下 | localhost aws 中継 |
| H | 秘密・task token がブラウザ経路に出ない | ソースと Network |
| I | 選定理由の文書がある | [why-step-functions.md](plan/why-step-functions.md)（AWS 不要） |

## 片付け

中継を止め、不要なら `sam delete`。
