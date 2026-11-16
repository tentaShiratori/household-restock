# なぜ Lambda durable functions ではなく Step Functions か

**次の一手:** 受け入れ表の項目 I は、この文書が残っていることで満たす（AWS 検証は不要）。

このリポジトリでは Standard Step Functions を選ぶ。

1. **長時間の待ちと可視化** — 承認の `waitForTaskToken` と配送の日時 Wait を、実行履歴のステートとして追える。学習目的では「今どこで止まっているか」が見えることが優先になる。
2. **サービス統合** — DynamoDB への直接更新（条件付き加算・補償）を Lambda なしで書ける。オーケストレーションと副作用の境界が ASL 上で分かる。
3. **Retry / Catch / 補償の型** — 一時失敗と永久失敗、取消の順序をステート機械として固定しやすい。durable functions でも似たことはできるが、この練習の主眼は Step Functions の概念習得にある。

durable functions との実装比較や書き心地の評価は発展要件であり、完成条件には入れない。
