# household-restock

**次にやること:** 下の「1. 導入」→ `./scripts/check.sh` →（任意）自分の AWS で [v0.2.0 検証](docs/aws-verify-v0.2.0.md)。

Lambda・Step Functions・DynamoDB を学ぶ日用品自動補充の練習用リポジトリ。  
**いまあるもの:** [完成までの計画](docs/plan/README.md)、品質ツール、**v0.1.0〜v0.2.0**（判定・占有・承認 API・`template.yaml`）。  
**ないもの:** 画面、注文/配送、AWS デプロイ済み環境（**エージェントは AWS に接続しない**）。v0.2.0 は **実装済み・AWS 検証待ち**。

## ツールの役割（二重管理しない）

| 層 | 固定の場所 | 中身 |
| --- | --- | --- |
| ランタイム / CLI | `mise.toml` + `mise.lock` | Python **3.12.16**、Node **22.23.4**、`npm:skills` **1.7.6**、**uv 0.13.7** |
| Python パッケージ | `pyproject.toml` + `uv.lock` | pytest / pytest-cov / Ruff / **ty** / vulture / **aws-sam-cli**、`src/household_restock` |
| IaC（v0.2.0） | `template.yaml` + `statemachine/` | Streams・占有・承認待ち SFN・承認 HTTP API |
| e2e（npm） | `package.json` + `package-lock.json` | **e2e 0.23.0** のみ（mise の npm ツールには載せない） |
| 文書スキル | `.agents/skills/` + `skills-lock.json` | `i-have-adhd` / `yomiyasu`（手順は [AGENTS.md](AGENTS.md)） |

- **mise**: ツール版の固定と `mise exec`
- **uv**: Python 依存の解決・ロック・仮想環境・`uv run`
- **npm**: e2e だけ。`npm:skills` は mise 側のまま。同じ npm パッケージを二重管理しない
- AWS CLI: 任意。ローカル検証では不要。**deploy / 接続はユーザーが自分で行う**（エージェントはしない）
- Docker: `sam build` のデフォルト（コンテナなし）で可。`--use-container` は任意

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

チェックサムが取れない・一致しない場合はインストールしない。

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

```bash
mise exec -- uv sync --locked
mise exec -- uv lock --check
mise exec -- uv pip check       # 期待: All installed packages are compatible
```

### 1-4. e2e 依存を同期する（npm・mise 固定 Node）

```bash
mise exec -- npm ci
mise exec -- npm run e2e:version   # 期待: 0.23.0
```

`mise exec --` で mise 固定の Node / npm を使う（PATH 上の別 Node に依存しない）。  
テレメトリは標準で切る（`E2E_TELEMETRY_DISABLED=1` / `DO_NOT_TRACK=1`。npm scripts にも付与済み）。  
AI モデルや API キーは**要求しない**（engine/gateway とも none）。秘密情報を記録しない。

### 1-5. 文書スキル（既に repo に同梱）

```bash
mise exec -- skills list
# 期待: i-have-adhd と yomiyasu が ./.agents/skills/ に出る
```

## 2. 検証（単一コマンド）

```bash
./scripts/check.sh
# 期待末尾: OK: 品質チェック完了（AWS 未接続・業務機能未検証・e2e シナリオは未作成）
```

中身の対応:

| チェック | コマンド（check.sh 内） | 期待 |
| --- | --- | --- |
| unit + coverage | `mise exec -- uv run pytest` | 判定・Streams 解釈など **80% 以上**（handler 入口は omit） |
| lint | `ruff check .` | 問題なし |
| format | `ruff format --check .` | 問題なし |
| deadcode | `vulture src tests` | 未使用なし |
| typecheck | `ty check`（Astral **ty 0.0.99**、Beta / 1.0 前） | 問題なし（警告も失敗） |
| e2e tooling | `mise exec -- npm run e2e:version` / `e2e:doctor` | `0.23.0`、doctor 成功 |

環境だけ再確認するときは `./scripts/check-env.sh`（SAM と skills の有無も含む軽い確認）。

### coverage について

測定対象は `src/household_restock` の純ロジック（handler は omit）。  
**coverage≥80 はローカル品質ゲートであり、AWS 上の受け入れ完了を意味しない。**

### typecheck（ty）について

- Astral の [`ty`](https://docs.astral.sh/ty/) **0.0.99**（PyPI Development Status: Beta。1.0 前のプレビュー相当）
- uv の dev 依存で固定（mise では管理しない）
- 対象: `src` と `tests`。Python 3.12。`rules.all = "error"`、`error-on-warning = true`、厳格な narrowing

### e2e について

- パッケージはユーザー指定の npm [`e2e`](https://www.npmjs.com/package/e2e) **0.23.0**（tester-army、Apache-2.0）
- 設定は `e2e.config.ts`（`init --engine none --gateway none` 相当）。画面やテスト用アプリは作っていない
- **意味のあるシナリオは [v0.3.0](docs/plan/v0.3.0.md) の最小画面ができてから書く**
- いま `mise exec -- npm run test:e2e`（`e2e run`）はシナリオ0件のため公式どおり `NO_TESTS` で失敗する。`--pass-with-no-tests` で偽の合格にはしない
- GitHub Actions の CI 追加は今回の範囲外（必要なら別途提案）

### SAM（ローカル）

```bash
SAM_CLI_TELEMETRY=0 mise exec -- uv run sam validate --lint
SAM_CLI_TELEMETRY=0 mise exec -- uv run sam build
```

### 在庫更新と承認（ユーザーの AWS）

```bash
./scripts/update-stock.sh <TableName> toilet-paper 2 3
APPROVAL_SHARED_SECRET='…' \
  ./scripts/decide-restock.sh "<ApprovalApiUrl>" toilet-paper "<streamEventId>" approve
```

- v0.1: [docs/aws-verify-v0.1.0.md](docs/aws-verify-v0.1.0.md) / [キー](docs/plan/v0.1.0-keys.md)
- v0.2: [docs/aws-verify-v0.2.0.md](docs/aws-verify-v0.2.0.md) / [設計](docs/plan/v0.2.0-design.md)
- deploy 時の `ApprovalSharedSecret` は NoEcho。リポジトリに書かない

### やっていないこと / 未検証

- AWS 認証・デプロイ・課金操作（エージェントは実施しない）
- 承認 timeout・占有・callback の **AWS 上の確認は未検証**
- 画面・模擬注文以降は未実装

## 3. 関連リンク

- [docs/plan/README.md](docs/plan/README.md) … 全体ロードマップと要件追跡
- [docs/plan/v0.2.0.md](docs/plan/v0.2.0.md) … 承認と占有（実装済み・AWS 検証待ち）
- [docs/aws-verify-v0.2.0.md](docs/aws-verify-v0.2.0.md) … ユーザー向け AWS 確認手順
- [AGENTS.md](AGENTS.md) … 文書スキルと品質コマンド
- [docs/skills-sources.md](docs/skills-sources.md) … skill のソース commit / ライセンス

秘密情報・`.venv`・`node_modules`・`.aws-sam`・ビルド成果物は `.gitignore` で除外。
