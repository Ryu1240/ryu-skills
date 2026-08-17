---
name: tdd-bootstrap
description: Detect the Python project's stack/paths/tooling and generate a project-specific .claude/skills/_shared-tdd/ for the tdd-python skills
argument-hint: [--force]
model: opus
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash(ls:*)
  - Bash(find:*)
  - Bash(cat:*)
examples:
  - input: /tdd-bootstrap
    description: 初回セットアップ。プロジェクトを走査し、_shared-tdd/ を生成する。
  - input: /tdd-bootstrap --force
    description: 既に _shared-tdd/ がある場合でも再生成（上書き）する。
---

Python プロジェクトを走査し、`.claude/skills/_shared-tdd/` 配下に project-settings.md を含む 4 ファイルを生成する。`/tdd` の Phase 0 から自動呼び出しされるほか、単独でも実行できる。

## 引数

- `--force`: 既存の `.claude/skills/_shared-tdd/` を上書きする。未指定で既存ファイルがある場合は確認のうえ中断（または `[o]` で上書き）。

## Step 1: 上書き判定

`.claude/skills/_shared-tdd/project-settings.md` を Read：

- 存在しない → そのまま Step 2 へ
- 存在し、`--force` なし → 「既に存在します。再生成しますか？ [o]上書き / [n]中断」を確認（**停止**）
- 存在し、`--force` あり → そのまま Step 2 へ（上書き）

## Step 2: プロジェクト走査

以下を Glob / Grep / Bash(ls/find/cat) で確認し、検出結果を表にまとめる。

| 検出項目 | 確認方法 |
|---|---|
| パッケージ名 | `Glob pyproject.toml` → Grep `^name = ['"](.+?)['"]` / 無ければ `setup.cfg` / `setup.py` / 最終的に cwd 名 |
| ソースルート | `Glob */pyproject.toml` から推定（モノレポなら `<pkg>/<pkg>/`、フラットなら `./` 直下の `*.py`） |
| テストルート | `Glob tests/ */tests/` の有無 → 1 つに決定 |
| Fixture | `Glob tests/fixtures/` の有無、`Glob tests/_helpers.py` で `load_json` 等のヘルパ |
| Python バージョン | `pyproject.toml` から `python = "^X.Y"` / `requires-python` を Grep |
| 依存管理 | `pyproject.toml` の `[tool.poetry]` → Poetry / `[project]` → PEP 621（pip/uv 等） / `Pipfile` → Pipenv / `requirements.txt` → pip |
| テストランナー | `pyproject.toml` を Grep（`pytest`） + `Glob tests/conftest.py` |
| docker compose | `Glob docker-compose.yml compose.yml */docker-compose.yml` |
| StrictModel 等の共通基底 | `Grep` ソース配下で `class StrictModel` / `extra = ['"]forbid['"]` / `BaseModel` 出現箇所 |
| 共通定数 / バリデータ | `Grep` で `*_PATTERN = ` / `field_validator` / `@validator` のファイル分布 |
| 命名規則・モジュール分割 | `Glob <src>/schemas/*.py <src>/commands/*.py <src>/<feature>/*.py` で実態を把握 |
| ruff / mypy / black | `pyproject.toml` で `[tool.ruff]` `[tool.mypy]` `[tool.black]` |
| pytest-cov | `pyproject.toml` で `pytest-cov` |
| CI | `Glob .circleci/config.yml .github/workflows/*.yml` |
| Notion 連携 | この plugin の挙動として常に「任意」を表示 |

検出結果を以下の形式で提示：

```
🔍 taskcli のプロジェクト走査結果

| 項目 | 検出値 |
|---|---|
| パッケージ名 | <name> |
| ソースルート | <pkg>/<pkg>/ or ./<pkg>/ |
| テストルート | <pkg>/tests/ |
| Python | 3.X |
| 依存管理 | Poetry / uv / pip |
| pytest | あり (X test files) |
| docker compose | あり / なし → テスト実行コマンド: <推定> |
| StrictModel 基底 | あり (`<file>`) / なし |
| ruff / mypy / black / pytest-cov | 個別に検出値を列挙 |
| CI | CircleCI / GitHub Actions / なし |
```

## Step 3: 承認ゲート

```
↑ の内容で `.claude/skills/_shared-tdd/` を生成しますか？
[y] 生成 / [e] 個別編集 / [n] 中断
```

- `[y]` → Step 4 へ
- `[e]` → 「どの項目を変更しますか？」を聞き、自由入力で上書き。再度 `[y]/[e]/[n]` 確認。
- `[n]` → 中断（何も生成しない）

承認なしに Write してはいけない（**停止**）。

## Step 4: ファイル生成

`.claude/skills/_shared-tdd/` ディレクトリを作成し、以下 4 ファイルを Write：

### 4-1. `project-settings.md`

下記テンプレを、Step 2 の検出結果で埋めて Write。「検出: なし」だった項目は対応行を **削除** するか「未導入」と明記する（推測で「あり」と書かない）。

```markdown
# TDD スキル共通設定（Project Settings）— {package_name}

> 全 TDD スキルの単一情報源。各スキルは `Read .claude/skills/_shared-tdd/project-settings.md` で参照する。

## 対象と環境

| 項目 | 値 |
|---|---|
| 対象パッケージ | `{package_name}` |
| ソースルート | `{src_root}` |
| テストルート | `{tests_root}` |
| Fixture ディレクトリ | `{fixtures_root}`（無ければ削除） |
| Python | {python_version} |
| 依存管理 | {Poetry / uv / pip} |
| テストランナー | pytest {version} |
| テスト実行（全件） | `{cmd_all}` |
| テスト実行（ファイル） | `{cmd_file}` |
| テスト実行（関数/絞り込み） | `{cmd_keyword}` |
| 未導入ツール | {検出されなかった ruff / mypy / black / pytest-cov 等を列挙} |
| CI | {CI 検出結果。テスト実行有無も含めて明記} |

{docker compose 検出時のみ: > ⚠️ テストは必ず docker compose 経由で実行する。ホスト直の pytest は使わない。}

## 現行ソース構成（重要・実態）

{Step 2 で得た実構成を反映。schemas/commands 分割パターンが検出されれば下記の雛形に従う。検出されなければ削除し「モジュール構成は実態に従う」程度に簡略化}

```
{src_root}
  schemas/ ...    # 検出時のみ
  commands/ ...   # 検出時のみ
  ...
```

{StrictModel 検出時のみ: **StrictModel / 共通定数 / 共通バリデータは `{file}`** に集約。新規モデルはこれを継承。}

## 現行テスト構成（重要・実態）

{Step 2 で得たテストファイル分布を表にまとめる。}

| target_module | 主なテストファイル |
|---|---|
| ... | ... |

{Fixture ヘルパ（load_json 等）が検出されれば、その使い方を明記}

## 不変条件（全スキル共通・破ってはいけない線）

1. **1サイクル = 1テスト = 1コミット**。
2. **TDD メタ情報をコード/docstring に残さない**。
3. {docker compose 検出時のみ: **テストは docker compose 経由**で実行する。}
4. {StrictModel 検出時のみ: **新規 pydantic モデルは StrictModel を継承**（`extra="forbid"`）。}
5. **Green は最小実装のみ**（YAGNI）。
6. **承認ゲートは Red 完了後と Commit 直前の2箇所**。
7. **ターン粒度**: 既定は各フェーズで停止。一気通貫は `--auto` でのみ。→ `state-machine.md` 参照。

## 命名・ブランチ

- ブランチ: `feature/<TICKET-KEY>/<package>/<feature>`。
- コミット規約・署名は `commit-convention.md` 参照。
- Notion 統合はオプション。詳細は `tdd/SKILL.md` の Phase 1a 参照。
```

### 4-2. `commit-convention.md` / `workflow-schema.md` / `state-machine.md`

plugin 同梱の **テンプレ**（`${CLAUDE_PLUGIN_ROOT}/skills/_shared-tdd/{filename}`）を Read してそのまま Write する（プロジェクト固有変更なし）。`${CLAUDE_PLUGIN_ROOT}` が解決できない環境では、`plugins/tdd-python/skills/_shared-tdd/{filename}` を相対 Read する。

## Step 5: サマリ提示

```
✅ Bootstrap 完了 — `.claude/skills/_shared-tdd/`
- project-settings.md  (走査結果から生成)
- commit-convention.md (テンプレからコピー)
- workflow-schema.md   (テンプレからコピー)
- state-machine.md     (テンプレからコピー)

次のステップ:
1. project-settings.md を開いて検出に漏れた項目を補完
2. /tdd "<タスク>" で TDD ワークフロー開始
```

## エラーハンドリング

- `pyproject.toml` / `setup.py` / `Pipfile` / `requirements.txt` のいずれも存在しない → 「ここは Python プロジェクトではないようです。中断します」と提示して終了。あわせて**汎用版 `tdd-universal` plugin**（任意の言語向け。対話型 bootstrap でスタックを聞き取って設定を構築）の利用を案内する。
- 検出が極端に乏しい（tests/ 不在、pytest 未導入）→ 警告のみ出し、最小限の project-settings.md を生成（ユーザーが手動で埋める前提）。
- 既存 `.claude/skills/_shared-tdd/` がある状態で `--force` 未指定 → 承認なしに上書きしてはいけない。
