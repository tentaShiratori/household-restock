# household-restock

日用品の自動補充ワークフローで、Lambda・Step Functions・DynamoDB を学ぶためのリポジトリです。

**いまの状態**: [v0.1.0 の計画](docs/plan/v0.1.0.md)と、Python + AWS SAM の**開発・テスト環境**だけがあります。  
補充機能本体（DynamoDB / Streams / Lambda / Step Functions）は**未実装**です。AWS へのデプロイもしていません。

## なぜ計画と環境を分けるか

先にツール（pytest / Ruff / SAM CLI）が動くことを確認し、あとから業務テストの失敗とセットアップ失敗を区別するためです。

## 必要ツール

| ツール | このリポジトリでの扱い | 理由 |
| --- | --- | --- |
| **Python 3.12** | 必須（`.python-version` / `requires-python` で指定） | Lambda の安定 GA ランタイム。プレビューの 3.15 は避け、クラウド VM の 3.12.3 と揃える |
| **pip + venv** | 依存管理はこの方式に一本化 | 初心者向けに単純。開発依存は `requirements-dev.txt` にピン留め |
| **pytest / Ruff** | 必須（開発依存） | 小さいテストと lint / format |
| **AWS SAM CLI** | 必須（開発依存に含む） | 将来の IaC。いまは `sam --version` / `sam --help` まで |
| **AWS CLI** | 任意 | バージョン確認まで。**認証情報の設定や AWS 接続は不要・禁止（この段階）** |
| **Docker** | 今回は必須にしない | pytest / lint には不要。将来の `sam local` や `sam build --use-container` で必要になる境界 |

本番アプリをコンテナで動かす話（要件で意図的にやらない VPC / コンテナ）と、SAM のローカル検証用 Docker は別物です。

## クリーン環境からの再現手順

Python 3.12 が入っている前提です（Ubuntu なら `python3.12-venv` も必要になることがあります）。

```bash
git clone <このリポジトリ> && cd household-restock
python3 -m venv .venv
source .venv/bin/activate   # Windows は .venv\Scripts\activate
python --version            # 期待: Python 3.12.x
pip install -r requirements-dev.txt
```

AWS CLI がまだ無い場合（任意）:

```bash
# 公式の AWS CLI v2 インストーラを使う（OS に合わせて公式ドキュメント参照）
aws --version
```

## 検証コマンドと期待結果

仮想環境を有効化したうえで:

```bash
pytest
```

期待: **2 passed**（環境スモーク。補充機能の保証ではない）

```bash
ruff check .
ruff format --check .
```

期待: 問題なし（`All checks passed!` / already formatted）

```bash
sam --version
sam --help
```

期待: バージョンが表示され、help が終了コード 0

まとめて再実行する場合:

```bash
./scripts/check-env.sh
```

期待: 末尾に `OK: 環境チェック完了（AWS 未接続・補充機能は未検証）`

### やっていないこと（誤解防止）

- `template.yaml` はまだ無いため、**`sam validate` / `sam build` は実施済みではありません**
- AWS 認証・デプロイ・課金操作は行いません
- このリポジトリの pytest は**構成・環境のスモーク**です。補充ワークフローの正しさは保証しません

## 計画へのリンク

- [docs/plan/v0.1.0.md](docs/plan/v0.1.0.md) — 将来実装する縦1本の範囲と受け入れ条件（未実装）

## 補足

- 秘密情報・仮想環境・ビルド成果物は `.gitignore` で除外しています
- 手元 PC の設定変更はこの作業では行っていません（クラウド上の検証と、repo から再現できる手順の整備が成果物です）
