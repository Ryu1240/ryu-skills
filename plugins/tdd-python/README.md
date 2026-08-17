# Python TDD スイート（`/tdd`）

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

これらの前提は [`_shared-tdd/project-settings.md`](_shared-tdd/project-settings.md) に集約されています。**自分のプロジェクトに合わせてこのファイルを書き換えてください。**

スキーマモデル（`schemas/task.py` の `Task` など）の roundtrip / validation テストと、CLI コマンド・storage 関数のロジックテストの両方を、1 サイクル = 1 テストで進める構成です。

## インストール

Claude Code のマーケットプレイス経由で導入します。

```text
/plugin marketplace add SC-Ryu1240/general-skills
/plugin install tdd-python@general-skills
```

導入後、Python プロジェクトの `.claude/settings.json` で本 plugin を有効化してください（他スタックのプロジェクトでは無効化しておくと skill 名の衝突を避けられます）。

plugin 同梱の `_shared-tdd/project-settings.md` は架空リポ `taskcli` を題材にしたテンプレです。**初めて `/tdd` を実行すると Phase 0 で `.claude/skills/_shared-tdd/project-settings.md` の有無を判定し、無ければ `tdd-bootstrap` を提案します**。承認するとプロジェクトを走査してプロジェクト固有の設定を `.claude/skills/_shared-tdd/` に生成するので、事前準備は不要です。手動で走らせたい場合は `/tdd-bootstrap`（既存があれば確認）または `/tdd-bootstrap --force`（上書き再生成）を実行してください。

## スキル一覧

- **[tdd](tdd/SKILL.md)** — オーケストレーター。Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。Phase 0 で project-settings の有無を判定し、未生成なら tdd-bootstrap を呼ぶ。
- **[tdd-bootstrap](tdd-bootstrap/SKILL.md)** — 初回セットアップ。Python プロジェクトを走査し、`.claude/skills/_shared-tdd/` にプロジェクト固有設定（`project-settings.md` + テンプレ 3 ファイル）を生成（承認制）。
- **[tdd-project-settings-update](tdd-project-settings-update/SKILL.md)** — 生成済み `project-settings.md` を自然言語指示で調整・追記・修正（diff 提案→承認→適用。手編集を潰さず、メモリ同期も提案）。
- **[tdd-red](tdd-red/SKILL.md)** — Red。失敗する pytest テストを 1 本だけ書く（schema roundtrip / logic / validation）。
- **[tdd-green](tdd-green/SKILL.md)** — Green。テストを通す最小実装（`schemas/` の pydantic モデルや CLI コマンド等）。
- **[tdd-refactor](tdd-refactor/SKILL.md)** — Refactor。挙動を変えずにコード品質を改善。
- **[tdd-commit](tdd-commit/SKILL.md)** — Commit。1 サイクル分をコミットし、状態をアーカイブ。
- **[tdd-evacuator](tdd-evacuator/SKILL.md)** — リファクタ候補・pytest テスト妥当性に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用・編集しない）。
- **[tdd-coverage-review](tdd-coverage-review/SKILL.md)** — pydantic モデル/関数 × テストカテゴリのマトリクスで不足テストを補完。
- **[tdd-coverage-overlap](tdd-coverage-overlap/SKILL.md)** — pytest-cov の coverage-context で意味的なテスト重複を検出（削除/統合候補を提示）。pytest-cov が必要。
- **[tdd-optimize](tdd-optimize/SKILL.md)** — pytest テストの最適化（独立性を担保。承認後に適用）。
- **[tdd-workflow-update](tdd-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

## 共通契約（`_shared-tdd/`）

全スキルが単一情報源として参照します。

- `project-settings.md` — 対象・パス・実行コマンド・**不変条件**・現行構成
- `workflow-schema.md` — 状態 JSON の正準スキーマ（キー名固定）
- `state-machine.md` — フェーズ遷移・2 モード・承認ゲート・停止条件
- `commit-convention.md` — コミット規約・署名

## 使い方

```
# Notion タスクから計画
/tdd https://www.notion.so/<task-id>

# 自由テキストから計画
/tdd "Task に priority フィールドを追加"

# 既存ワークフローを実行（既定はフェーズ停止）
/tdd tdd-20260613-101500

# 一気通貫モード
/tdd tdd-20260613-101500 --auto

# 進行中ワークフローを動的更新
/tdd tdd-20260613-101500 -- サイクル5を削除
```

計画フェーズは状態 JSON を書き出すため、Plan モードではなく通常モードで実行してください。
