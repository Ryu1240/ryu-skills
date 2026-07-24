# Rails TDD スイート（`/tdd`）

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

これらの前提は [`_shared-tdd/project-settings.md`](_shared-tdd/project-settings.md) に集約されています。**自分のプロジェクトに合わせてこのファイルを書き換えてください。**

## インストール

Claude Code のマーケットプレイス経由で導入します。

```text
/plugin marketplace add SC-Ryu1240/general-skills
/plugin install tdd-rails@general-skills
```

導入後、Rails プロジェクトの `.claude/settings.json` で本 plugin を有効化してください（他スタックのプロジェクトでは無効化しておくと skill 名の衝突を避けられます）。

plugin 同梱の `_shared-tdd/project-settings.md` は架空リポ `sales-hub` を題材にしたテンプレです。**初めて `/tdd` を実行すると Phase 0 で `.claude/skills/_shared-tdd/project-settings.md` の有無を判定し、無ければ `tdd-bootstrap` を提案します**。承認するとプロジェクトを走査してプロジェクト固有の設定を `.claude/skills/_shared-tdd/` に生成するので、事前準備は不要です。手動で走らせたい場合は `/tdd-bootstrap`（既存があれば確認）または `/tdd-bootstrap --force`（上書き再生成）を実行してください。

## スキル一覧

- **[tdd](tdd/SKILL.md)** — オーケストレーター。Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。Phase 0 で project-settings の有無を判定し、未生成なら tdd-bootstrap を呼ぶ。
- **[tdd-bootstrap](tdd-bootstrap/SKILL.md)** — 初回セットアップ。Rails プロジェクトを走査し、`.claude/skills/_shared-tdd/` にプロジェクト固有設定（`project-settings.md` + テンプレ 3 ファイル）を生成（承認制）。
- **[tdd-project-settings-update](tdd-project-settings-update/SKILL.md)** — 生成済み `project-settings.md` を自然言語指示で調整・追記・修正（diff 提案→承認→適用。手編集を潰さず、メモリ同期も提案）。
- **[tdd-red](tdd-red/SKILL.md)** — Red。失敗するテストを 1 本だけ書き、意図通り失敗することを確認。
- **[tdd-green](tdd-green/SKILL.md)** — Green。テストを通す最小実装。
- **[tdd-refactor](tdd-refactor/SKILL.md)** — Refactor。N+1/dependent/サービス抽出などをテスト緑のまま改善。
- **[tdd-commit](tdd-commit/SKILL.md)** — Commit。1 サイクル分を husky/lint-staged 準拠でコミットし、状態をアーカイブ。
- **[tdd-evacuator](tdd-evacuator/SKILL.md)** — リファクタ候補・テスト妥当性に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用・編集しない）。
- **[tdd-coverage-review](tdd-coverage-review/SKILL.md)** — endpoint/model × テストカテゴリのマトリクスで不足テストを補完。
- **[tdd-optimize](tdd-optimize/SKILL.md)** — RSpec テストの最適化（独立性を担保。承認後に適用）。
- **[tdd-workflow-update](tdd-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

## 共通契約（`_shared-tdd/`）

全スキルが単一情報源として参照します。

- `project-settings.md` — パス・テストコマンド・**不変条件**・CI/hook
- `workflow-schema.md` — 状態 JSON の正準スキーマ（キー名固定）
- `state-machine.md` — フェーズ遷移・2 モード・承認ゲート・停止条件
- `commit-convention.md` — コミット規約・署名・hook 準拠

## 使い方

```
# Notion タスクから計画
/tdd https://www.notion.so/<task-id>

# 自由テキストから計画
/tdd "Lead に status カラムを追加し API で返す"

# 既存ワークフローを実行（既定はフェーズ停止）
/tdd tdd-20260613-101500

# 一気通貫モード
/tdd tdd-20260613-101500 --auto

# 進行中ワークフローを動的更新
/tdd tdd-20260613-101500 -- サイクル5を削除
```

計画フェーズは状態 JSON を書き出すため、Plan モードではなく通常モードで実行してください。
