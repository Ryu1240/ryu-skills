---
name: tdd-rails-coverage-review
description: Test coverage review for sales-hub - analyze (endpoint/model × test-category) matrix and add missing test cases
argument-hint: <workflow_id>
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(bundle:*)
  - Bash(docker:*)
  - Bash(git:*)
  - Grep
  - Glob
  - TaskGet
  - TaskUpdate
examples:
  - input: /tdd-rails-coverage-review tdd-20260613-101500
    description: Review test coverage for the completed workflow
---

TDD 完了後、sales-hub のテスト網羅性を「対象 × テストカテゴリ」のマトリクスで分析し、不足を追加する。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd-rails/project-settings.md`（テストコマンド）/ `workflow-schema.md` / `commit-convention.md`

## 1. コンテキスト
`workflow-{id}.json`（`task_title`, `completed_cycles`, `todo_task_id`）を Read。対象テスト・実装ファイルを Read。
`bundle exec rails routes | grep -i {resource}` でエンドポイント一覧を取得。

## 2. マトリクス

| カテゴリ | 優先度 |
|---|---|
| 正常系: ステータスコード | 必須 |
| 正常系: OpenAPI スキーマ（`assert_response_schema_confirm`） | 必須 |
| 正常系: **テナント分離**（現テナントのデータのみ） | 必須 |
| 正常系: レスポンスボディ / 空結果 / 関連データ | 推奨/条件付き |
| 異常系: 404（存在しない） / 422（バリデーション） / 重複 | 必須/条件付き |
| 権限: Pundit 拒否 / 未認証 401 | 該当時必須 |
| モデル: validation（presence/uniqueness） / 論理削除（acts_as_paranoid） | 推奨/条件付き |

各テストファイルの `it` を Grep して各セルにマッピング。

## 3. ギャップ提案
空セルを優先度で絞り、番号付きで提案（対象・カテゴリ・ファイル）。「該当時必須/条件付き」は該当実装が無ければ提案しない。
```
[a] すべて追加 / [1,3] 番号指定 / [n] 追加しない
```

## 4. 追加・実行
選択分を対応テストファイルの適切な context（正常系/異常系）に追加（既存は変更しない。factory/let も必要に応じ追加。multi-tenant 文脈を維持）。
- `bundle exec rspec {paths}`
全件 pass を確認（既存を壊していないこと）。

## 5. コミット + 記録
commit-convention に従い `test: 網羅性レビューで不足テストを追加`（**署名はバージョン無し**）でコミット（hook 準拠）。
`workflow-{id}.json` に `coverage_review`（before/after/added/commit/completed_at）を記録、`updated_at` 更新。

## 6. サマリ（簡潔）
Before/After テスト数 / カテゴリ別追加 / コミット SHA。→ 自動遷移（tdd-rails が Optimize へ）。

## 注意
既存テストは絶対に変更しない（追加のみ）。各テストは独立（順序非依存・個別実行可）。
