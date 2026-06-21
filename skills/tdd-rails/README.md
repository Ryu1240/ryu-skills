# Rails TDD スイート（`/tdd-rails`）

Ruby on Rails + RSpec バックエンド向けの TDD ワークフロー自動化スキル群です。Plan → Red → Green → Refactor → Commit のサイクルをフェーズ単位で進め、Coverage Review と Test Optimize まで回します。

サンプルとして架空リポジトリ **`sales-hub`**（マルチテナント Rails API）を題材に記述しています。

## 前提スタック

| 項目 | 値 |
|---|---|
| アプリ | リポジトリ直下の Rails アプリ |
| テスト | RSpec（`spec/{models,requests,services,...}/`） |
| データ生成 | FactoryBot |
| モック | WebMock / shared context |
| 契約検証 | Committee（`assert_response_schema_confirm`、OpenAPI） |
| マルチテナント | `ApplicationRecord.client` / `ActsAsTenant` |
| N+1 検出 | Bullet |
| 権限 | Pundit |
| lint / hook | Rubocop + husky/lint-staged |
| CI | CircleCI |

これらの前提は [`_shared-tdd-rails/project-settings.md`](_shared-tdd-rails/project-settings.md) に集約されています。**自分のプロジェクトに合わせてこのファイルを書き換えてください。**

## インストール

```bash
cp -r tdd-rails* _shared-tdd-rails ~/your-project/.claude/skills/
```

（`skills/tdd-rails/` ディレクトリの中で実行する想定。`README.md` 以外を `.claude/skills/` 直下にコピーします。）

## スキル一覧

- **[tdd-rails](tdd-rails/SKILL.md)** — オーケストレーター。Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。
- **[tdd-rails-red](tdd-rails-red/SKILL.md)** — Red。失敗するテストを 1 本だけ書き、意図通り失敗することを確認。
- **[tdd-rails-green](tdd-rails-green/SKILL.md)** — Green。テストを通す最小実装。
- **[tdd-rails-refactor](tdd-rails-refactor/SKILL.md)** — Refactor。N+1/dependent/サービス抽出などをテスト緑のまま改善。
- **[tdd-rails-commit](tdd-rails-commit/SKILL.md)** — Commit。1 サイクル分を husky/lint-staged 準拠でコミットし、状態をアーカイブ。
- **[tdd-rails-evacuator](tdd-rails-evacuator/SKILL.md)** — リファクタ候補・テスト妥当性に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用・編集しない）。
- **[tdd-rails-coverage-review](tdd-rails-coverage-review/SKILL.md)** — endpoint/model × テストカテゴリのマトリクスで不足テストを補完。
- **[tdd-rails-optimize](tdd-rails-optimize/SKILL.md)** — RSpec テストの最適化（独立性を担保。承認後に適用）。
- **[tdd-rails-workflow-update](tdd-rails-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

## 共通契約（`_shared-tdd-rails/`）

全スキルが単一情報源として参照します。

- `project-settings.md` — パス・テストコマンド・**不変条件**・CI/hook
- `workflow-schema.md` — 状態 JSON の正準スキーマ（キー名固定）
- `state-machine.md` — フェーズ遷移・2 モード・承認ゲート・停止条件
- `commit-convention.md` — コミット規約・署名・hook 準拠

## 使い方

```
# Notion タスクから計画
/tdd-rails https://www.notion.so/<task-id>

# 自由テキストから計画
/tdd-rails "Lead に status カラムを追加し API で返す"

# 既存ワークフローを実行（既定はフェーズ停止）
/tdd-rails tdd-20260613-101500

# 一気通貫モード
/tdd-rails tdd-20260613-101500 --auto

# 進行中ワークフローを動的更新
/tdd-rails tdd-20260613-101500 -- サイクル5を削除
```

計画フェーズは状態 JSON を書き出すため、Plan モードではなく通常モードで実行してください。
