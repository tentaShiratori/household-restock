# household-restock

**次にやること:** 下の「1. 導入」を上から実行し、末尾が `OK: 環境チェック完了…` になることを確認する。

Lambda・Step Functions・DynamoDB を学ぶ日用品自動補充の練習用リポジトリ。  
**いまあるもの:** [v0.1.0 計画](docs/plan/v0.1.0.md)と開発環境だけ。  
**ないもの:** 補充機能本体、AWS デプロイ、`template.yaml`。

計画と環境を分ける理由: 先にツールを動かし、あとから業務テスト失敗とセットアップ失敗を切り分けるため。

## ツールの役割（二重管理しない）

| 層 | 固定の場所 | 中身 |
| --- | --- | --- |
| ランタイム / CLI | `mise.toml` + `mise.lock` | Python **3.12.16**、Node **22.23.4**、`npm:skills` **1.7.6** |
| Python 開発パッケージ | `requirements-dev.txt` + `.venv` | pytest / Ruff / **aws-sam-cli**（SAM はここだけ） |
| 文書スキル | `.agents/skills/` + `skills-lock.json` | `i-have-adhd` / `yomiyasu`（手順は [AGENTS.md](AGENTS.md)） |

- AWS CLI: 任意。バージョン確認まで。**認証・接続は不要・禁止（この段階）**
- Docker: 今回は必須にしない（pytest / lint に不要）。将来の `sam local` / `sam build --use-container` で必要になる境界
- 本番アプリのコンテナ実行（要件でやらない）と、SAM ローカル用 Docker は別

検証済みの mise 本体: **2026.10.11**（linux-x64）。導入手順は次節。

## 1. 導入

```bash
git clone https://github.com/tentaShiratori/household-restock.git
cd household-restock
```

### 1-1. mise を入れる

```bash
curl -fsSL https://mise.run | sh
export PATH="$HOME/.local/bin:$PATH"
mise --version
```

公式インストーラが失敗する場合（チェックサム取得の 504 など）は GitHub Release から同じ版を入れる:

```bash
VER=v2026.10.11
curl -fsSL -o /tmp/mise.tgz "https://github.com/jdx/mise/releases/download/${VER}/mise-${VER}-linux-x64.tar.gz"
mkdir -p /tmp/mise-extract "$HOME/.local/bin"
tar -xzf /tmp/mise.tgz -C /tmp/mise-extract
cp /tmp/mise-extract/mise/bin/mise "$HOME/.local/bin/mise"
chmod +x "$HOME/.local/bin/mise"
export PATH="$HOME/.local/bin:$PATH"
mise --version   # 期待: 2026.10.11 …
```

### 1-2. プロジェクトのツールを入れる

```bash
mise trust          # 初回のみ。mise.toml を読んでから実行
mise install        # ロックに従い Python / Node / skills を入れる
mise ls --current
mise exec -- python --version   # 期待: Python 3.12.16
mise exec -- node --version     # 期待: v22.23.4
mise exec -- skills --version   # 期待: 1.7.6
```

### 1-3. Python 開発依存（venv）

```bash
mise exec -- python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python --version                # 期待: Python 3.12.16
pip install -r requirements-dev.txt
pip check                       # 期待: No broken requirements found.
```

### 1-4. 文書スキル（既に repo に同梱）

通常は追加作業なし。消えたときだけ [AGENTS.md](AGENTS.md) の「スキルを入れ直す」を使う。

```bash
mise exec -- skills list
# 期待: i-have-adhd と yomiyasu が ./.agents/skills/ に出る
```

## 2. 検証

仮想環境を有効化したうえで:

| コマンド | 期待 |
| --- | --- |
| `pytest` | **2 passed**（環境スモーク。補充機能の保証ではない） |
| `ruff check .` と `ruff format --check .` | 問題なし |
| `sam --version` と `sam --help` | 表示され、help は終了コード 0 |
| `./scripts/check-env.sh` | 末尾 `OK: 環境チェック完了（AWS 未接続・補充機能は未検証）` |

### やっていないこと

- `template.yaml` がないため **`sam validate` / `sam build` は未実施**
- AWS 認証・デプロイ・課金操作はしない
- pytest は構成スモークだけ。補充ワークフローは保証しない

## 3. 関連リンク

- [docs/plan/v0.1.0.md](docs/plan/v0.1.0.md) — 将来の縦1本（未実装）
- [AGENTS.md](AGENTS.md) — 文書を読みやすくするときのスキル手順
- [docs/skills-sources.md](docs/skills-sources.md) — skill のソース commit / ライセンス

秘密情報・`.venv`・ビルド成果物は `.gitignore` で除外。手元 PC の設定変更はこの作業では行っていない。
