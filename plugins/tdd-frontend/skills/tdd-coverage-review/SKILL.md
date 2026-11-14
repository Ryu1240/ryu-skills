---
name: tdd-coverage-review
description: TDD 完了後に、対象（component / composable / store）× テストカテゴリのマトリクスで Vitest テストの抜けを洗い出し、承認されたケースを追加する。/tdd から呼ばれるほか、「テストの網羅性を見て」と頼まれたときにも使う。
argument-hint: <workflow_id>
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(yarn:*)
  - Bash(npx:*)
  - Bash(npm:*)
  - Grep
  - Glob
  - TaskGet
  - TaskUpdate
examples:
  - input: /tdd-coverage-review tdd-20260613-101500
    description: Review test coverage for the completed workflow
---

TDD 完了後、storefront のテスト網羅性を「対象 × テストカテゴリ」のマトリクスで分析し、不足を追加する。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/project-settings.md`（テストコマンド）/ `workflow-schema.md` / `commit-convention.md`

## 入口ゲート
`current-cycle.json` が存在しないこと（サイクル進行中でない）と `completed_cycles` 非空を確認。進行中なら `/tdd-commit {id}` を案内し中断。

## 1. コンテキスト
`workflow-{id}.json`（`task_title`, `completed_cycles`, `todo_task_id`）を Read。対象テスト・実装ファイル（component/composable/store）を Read。
props/emits/公開返り値の一覧を実装から把握する。

## 2. マトリクス

| カテゴリ | 優先度 |
|---|---|
| 正常系: レンダリング（見出し・主要要素が role で見える） | 必須 |
| 正常系: props バリエーション（表示分岐） | 必須 |
| 正常系: ユーザー操作 → emits / 状態変化 | 必須 |
| 非同期: ローディング表示 → 解決後の表示 | 該当時必須 |
| 異常系: API エラー（MSW でエラー注入）の表示 | 該当時必須 |
| 異常系: 空状態（0件） / 入力バリデーション | 推奨/条件付き |
| アクセシビリティ: ラベル紐付け・role・キーボード操作 | 推奨 |
| composable/store: 正常系ロジック / 異常系 / 境界値 | 該当時必須 |

各テストファイルの `it` を Grep して各セルにマッピング。

## 3. ギャップ提案
空セルを優先度で絞り、番号付きで提案（対象・カテゴリ・ファイル）。「該当時必須/条件付き」は該当実装（API 連携・非同期・入力）が無ければ提案しない。
```
[a] すべて追加 / [1,3] 番号指定 / [n] 追加しない
```

## 4. 追加・実行
選択分を対応テストファイルの適切な describe（正常系/異常系）に追加（既存は変更しない。factory/MSW handler も必要に応じ追加。role 取得・user-event・独立性を維持）。
- `yarn test {paths}`
全件 pass を確認（既存を壊していないこと）。

## 5. コミット + 記録
commit-convention に従い `test: 網羅性レビューで不足テストを追加`（署名はバージョン無し）でコミット（hook 準拠）。
`workflow-{id}.json` に `coverage_review`（before/after/added/commit/completed_at）を記録、`updated_at` 更新。

## 6. サマリ（簡潔）
Before/After テスト数 / カテゴリ別追加 / コミット SHA。→ 自動遷移（tdd が Optimize へ）。

## 注意
既存テストは変更しない（追加のみ。既存の意味を変えると網羅性の比較が成り立たない）。各テストは独立（順序非依存・個別実行可・MSW/Pinia リセット）。
