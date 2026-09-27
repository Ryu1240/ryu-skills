---
name: tdd-coverage-review
description: Test coverage review for retail-hub monorepo - analyze (target × test-category) matrix per ecosystem and add missing test cases
argument-hint: <workflow_id>
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(bundle:*)
  - Bash(docker:*)
  - Bash(yarn:*)
  - Bash(npx:*)
  - Bash(npm:*)
  - Bash(git:*)
  - Grep
  - Glob
  - TaskGet
  - TaskUpdate
examples:
  - input: /tdd-coverage-review tdd-20260613-101500
    description: Review test coverage for the completed workflow
---

TDD 完了後、retail-hub のテスト網羅性を「対象 × テストカテゴリ」のマトリクスで分析し、不足を追加する。**`ecosystem` でマトリクスを分岐する。**

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/project-settings.md`（テストコマンド）/ `workflow-schema.md` / `commit-convention.md`

## 入口ゲート
`current-cycle.json` が**存在しないこと**（サイクル進行中でない）と `completed_cycles` 非空を確認。進行中なら `/tdd-commit {id}` を案内し中断。

## 1. コンテキスト
`workflow-{id}.json`（`ecosystem`, `task_title`, `completed_cycles`, `todo_task_id`）を Read。対象テスト・実装ファイルを Read。
- backend: `cd api && bundle exec rails routes | grep -i {resource}` でエンドポイント把握。
- frontend: 実装から props/emits/公開返り値を把握。

## 2. マトリクス

### backend
| カテゴリ | 優先度 |
|---|---|
| 正常系: ステータスコード | 必須 |
| 正常系: OpenAPI スキーマ（`assert_response_schema_confirm`） | 必須 |
| 正常系: **テナント分離**（現テナントのデータのみ） | 必須 |
| 異常系: 404 / 422 / 重複 | 必須/条件付き |
| 権限: 拒否 / 未認証 401 | 該当時必須 |
| モデル: validation / 論理削除 | 推奨/条件付き |

### frontend
| カテゴリ | 優先度 |
|---|---|
| 正常系: レンダリング（role で主要要素が見える） | 必須 |
| 正常系: props バリエーション / ユーザー操作 → emits・状態変化 | 必須 |
| 非同期: ローディング → 解決後表示 | 該当時必須 |
| 異常系: **API エラー**（MSW 注入）の表示 / 空状態 | 該当時必須/条件付き |
| アクセシビリティ: ラベル紐付け・role・キーボード | 推奨 |
| composable/store: 正常系 / 異常系 / 境界値 | 該当時必須 |

各テストファイルの `it` を Grep して各セルにマッピング。

## 3. ギャップ提案
空セルを優先度で絞り、番号付きで提案（対象・カテゴリ・ファイル）。「該当時必須/条件付き」は該当実装が無ければ提案しない。
```
[a] すべて追加 / [1,3] 番号指定 / [n] 追加しない
```

## 4. 追加・実行
選択分を対応テストファイルの適切な context/describe（正常系/異常系）に追加（既存は変更しない。factory/MSW handler も必要に応じ追加。独立性＝tenant 文脈 / MSW・Pinia リセット を維持）。
- backend: `cd api && bundle exec rspec {paths}` / frontend: `cd web && yarn test {paths}`
全件 pass を確認（既存を壊していないこと）。

## 5. コミット + 記録
commit-convention に従い `test: 網羅性レビューで不足テストを追加`（**署名はバージョン無し**）でコミット（hook 準拠）。
`workflow-{id}.json` に `coverage_review`（before/after/added/commit/completed_at）を記録、`updated_at` 更新。

## 6. サマリ（簡潔）
ecosystem / Before/After テスト数 / カテゴリ別追加 / コミット SHA。→ 自動遷移（tdd が Optimize へ）。

## 注意
既存テストは絶対に変更しない（追加のみ）。各テストは独立（順序非依存・個別実行可）。
