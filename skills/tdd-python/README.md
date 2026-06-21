# Python TDD スイート（`/tdd-py`）

Python + pytest + pydantic 向けの TDD ワークフロー自動化スキル群です。Plan → Red → Green → Refactor → Commit のサイクルをフェーズ単位で進め、Coverage Review と Test Optimize まで回します。

サンプルとして架空リポジトリ **`taskcli`**（pydantic + pytest で作るローカル CLI ツール。コマンドラインのタスク管理。パッケージ `taskcli`）を題材に記述しています。

## 前提スタック

| 項目 | 値 |
|---|---|
| パッケージ | `taskcli/taskcli/`（`schemas/` + `commands/` + `storage.py` + `cli.py`） |
| Python | 3.10 |
| 依存管理 | Poetry |
| テスト | pytest（`taskcli/tests/`） |
| テスト実行 | docker compose 経由（`docker compose run --rm app pytest`） |
| モデル基底 | `StrictModel`（`extra="forbid"`、`schemas/_common.py`） |
| 共通型/定数 | `TaskStatus` / `TASK_ID_PATTERN` / `TAG_PATTERN`（`schemas/_common.py`） |
| Fixture | `tests/fixtures/*.json` + `load_json`（`tests/_helpers.py`） |
| CI | CircleCI（デプロイのみ。PR 前に手動 pytest 必須） |

これらの前提は [`_shared-tdd-python/project-settings.md`](_shared-tdd-python/project-settings.md) に集約されています。**自分のプロジェクトに合わせてこのファイルを書き換えてください。**

スキーマモデル（`schemas/task.py` の `Task` など）の roundtrip / validation テストと、CLI コマンド・storage 関数のロジックテストの両方を、1 サイクル = 1 テストで進める構成です。

## インストール

```bash
cp -r tdd-py* _shared-tdd-python ~/your-project/.claude/skills/
```

（`skills/tdd-python/` ディレクトリの中で実行する想定。`README.md` 以外を `.claude/skills/` 直下にコピーします。）

## スキル一覧

- **[tdd-py](tdd-py/SKILL.md)** — オーケストレーター。Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。
- **[tdd-py-red](tdd-py-red/SKILL.md)** — Red。失敗する pytest テストを 1 本だけ書く（schema roundtrip / logic / validation）。
- **[tdd-py-green](tdd-py-green/SKILL.md)** — Green。テストを通す最小実装（`schemas/` の pydantic モデルや CLI コマンド等）。
- **[tdd-py-refactor](tdd-py-refactor/SKILL.md)** — Refactor。挙動を変えずにコード品質を改善。
- **[tdd-py-commit](tdd-py-commit/SKILL.md)** — Commit。1 サイクル分をコミットし、状態をアーカイブ。
- **[tdd-py-evacuator](tdd-py-evacuator/SKILL.md)** — リファクタ候補・pytest テスト妥当性に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用・編集しない）。
- **[tdd-py-coverage-review](tdd-py-coverage-review/SKILL.md)** — pydantic モデル/関数 × テストカテゴリのマトリクスで不足テストを補完。
- **[tdd-py-coverage-overlap](tdd-py-coverage-overlap/SKILL.md)** — pytest-cov の coverage-context で意味的なテスト重複を検出（削除/統合候補を提示）。pytest-cov が必要。
- **[tdd-py-optimize](tdd-py-optimize/SKILL.md)** — pytest テストの最適化（独立性を担保。承認後に適用）。
- **[tdd-py-workflow-update](tdd-py-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

## 共通契約（`_shared-tdd-python/`）

全スキルが単一情報源として参照します。

- `project-settings.md` — 対象・パス・実行コマンド・**不変条件**・現行構成
- `workflow-schema.md` — 状態 JSON の正準スキーマ（キー名固定）
- `state-machine.md` — フェーズ遷移・2 モード・承認ゲート・停止条件
- `commit-convention.md` — コミット規約・署名

## 使い方

```
# Notion タスクから計画
/tdd-py https://www.notion.so/<task-id>

# 自由テキストから計画
/tdd-py "Task に priority フィールドを追加"

# 既存ワークフローを実行（既定はフェーズ停止）
/tdd-py tdd-20260613-101500

# 一気通貫モード
/tdd-py tdd-20260613-101500 --auto

# 進行中ワークフローを動的更新
/tdd-py tdd-20260613-101500 -- サイクル5を削除
```

計画フェーズは状態 JSON を書き出すため、Plan モードではなく通常モードで実行してください。
