# household-restock

**次にやること:** 下の「1. 導入」を上から実行し、末尾が `OK: 環境チェック完了…` になることを確認する。

Lambda・Step Functions・DynamoDB を学ぶ日用品自動補充の練習用リポジトリ。  
**いまあるもの:** [v0.1.0 計画](docs/plan/v0.1.0.md)と開発環境だけ。  
**ないもの:** 補充機能本体、AWS デプロイ、`template.yaml`。

計画と環境を分ける理由: 先にツールを動かし、あとから業務テスト失敗とセットアップ失敗を切り分けるため。

## ツールの役割（二重管理しない）

| 層 | 固定の場所 | 中身 |
| --- | --- | --- |
| ランタイム / CLI | `mise.toml` + `mise.lock` | Python **3.12.16**、Node **22.23.4**、`npm:skills` **1.7.6**、**uv 0.13.7** |
| Python パッケージ | `pyproject.toml` + `uv.lock`（`.venv` は uv が作成） | pytest / Ruff / **aws-sam-cli** |
| 文書スキル | `.agents/skills/` + `skills-lock.json` | `i-have-adhd` / `yomiyasu`（手順は [AGENTS.md](AGENTS.md)） |

- **mise**: ツール版の固定と `mise exec`
- **uv**: Python 依存の解決・ロック・仮想環境・`uv run`（Python 本体は mise の 3.12.16。`python-preference = only-system` で別系統の取得をしない）
- AWS CLI: 任意。バージョン確認まで。**認証・接続は不要・禁止（この段階）**
- Docker: 今回は必須にしない（pytest / lint に不要）。将来の `sam local` / `sam build --use-container` で必要になる境界

検証済みの mise 本体: **2026.10.11**（linux-x64）。導入手順は次節。

## 1. 導入

```bash
git clone https://github.com/tentaShiratori/household-restock.git
cd household-restock
```

### 1-1. mise を入れる（本体も 2026.10.11 固定）

```bash
curl -fsSL https://mise.run | MISE_VERSION=v2026.10.11 sh
export PATH="$HOME/.local/bin:$PATH"
mise --version   # 期待: 2026.10.11 …
```

チェックサムが取れない・一致しない場合はインストールしない。手動導入は README 以前の手順どおり `SHASUMS256.txt`（と可能なら minisig）を検証してから展開する。

### 1-2. プロジェクトのツールを入れる

```bash
mise trust          # 初回のみ
mise install        # Python / Node / skills / uv
mise ls --current
mise exec -- python --version   # 期待: Python 3.12.16
mise exec -- node --version     # 期待: v22.23.4
mise exec -- skills --version   # 期待: 1.7.6
mise exec -- uv --version       # 期待: uv 0.13.7 …
```

### 1-3. Python 依存を同期する（uv）

通常利用はロックを更新しない:

```bash
mise exec -- uv sync --locked
mise exec -- uv lock --check
mise exec -- uv pip check       # 期待: All installed packages are compatible
mise exec -- uv run python --version   # 期待: Python 3.12.16
```

`source .venv/bin/activate` や `pip install` は不要。実行は `mise exec -- uv run …`。

依存を足す・上げるときだけ（この学習手順の日常では使わない）:

```bash
mise exec -- uv add --group dev <package>   # 追加して lock 更新
mise exec -- uv lock                        # 明示的に lock 再生成
mise exec -- uv sync --locked
```

### 1-4. 文書スキル（既に repo に同梱）

```bash
mise exec -- skills list
# 期待: i-have-adhd と yomiyasu が ./.agents/skills/ に出る
```

消えたときだけ [AGENTS.md](AGENTS.md) の入れ直し手順を使う。

## 2. 検証

activate は不要。どのディレクトリからでも `./scripts/check-env.sh` はリポジトリ根へ移動する。

| コマンド | 期待 |
| --- | --- |
| `mise exec -- uv run pytest` | **2 passed**（環境スモーク。補充機能の保証ではない） |
| `mise exec -- uv run ruff check .` と `… ruff format --check .` | 問題なし |
| `mise exec -- uv run sam --version` と `… sam --help` | 表示され、help は終了コード 0 |
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
