---
name: tdd-coverage-review
description: TDD 完了後に、対象（lib の関数 / hook / Client Component / Server Action / Route Handler）× テストカテゴリのマトリクスで Vitest テストの抜けを洗い出し、承認されたケースを追加する。/tdd から呼ばれるほか、「テストの網羅性を見て」と頼まれたときにも使う。
argument-hint: <workflow_id>
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(yarn:*)
  - Bash(npx:*)
  - Bash(npm:*)
  - Bash(pnpm:*)
  - Bash(git:*)
  - Grep
  - Glob
  - TaskGet
  - TaskUpdate
examples:
  - input: /tdd-coverage-review tdd-20260613-101500
    description: Review test coverage for the completed workflow
---

TDD 完了後、booking-web のテスト網羅性を「対象 × テストカテゴリ」のマトリクスで分析し、不足を追加する。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/project-settings.md`（テストコマンド・置き場の方針）/ `workflow-schema.md` / `commit-convention.md`

## 入口ゲート
`current-cycle.json` が存在しないこと（サイクル進行中でない）と `completed_cycles` 非空を確認。進行中なら `/tdd-commit {id}` を案内し中断。

## 1. コンテキスト
`workflow-{id}.json`（`task_title`, `completed_cycles`, `patterns`, `todo_task_id`）を Read。対象テスト・実装ファイルを Read。
実装から公開インターフェイスを列挙してマトリクスの行にする（component なら props と操作、hook なら返り値と引数、lib なら関数、server action なら入力パターン、route handler ならメソッド）。
`pnpm vitest run --coverage {paths}` を実行し、未到達の分岐を手がかりにする（数値目標ではなく抜けの発見に使う）。

## 2. マトリクス

| カテゴリ | 対象 | 優先度 |
|---|---|---|
| 正常系: 主要な表示（見出し・主要要素が role で見える） | component | 必須 |
| 正常系: props / 検索パラメータによる表示の分岐 | component | 必須 |
| 正常系: ユーザー操作 → コールバック・表示の変化・`router.push` | component | 必須 |
| 非同期: ローディング表示 → 解決後の表示 | component / hook | 該当時必須 |
| 異常系: API エラー（4xx/5xx・ネットワークエラーを MSW で注入）の表示・hook の `isError` | component / hook | 該当時必須 |
| 空状態（0件）・未入力 | component | 必須 |
| 入力バリデーション・二重送信の防止 | component / server-action | 該当時必須 |
| 認証状態: 未認証・読み込み中・トークン取得失敗 | component / hook | 該当時必須 |
| mutation 後の再取得（関連 query の無効化） | hook | 該当時必須 |
| 正常系・境界値（0・上限・端数・日付の端）・不正入力 | lib | 必須 |
| 成功時の `revalidatePath` / `redirect`・検証エラー | server-action | 該当時必須 |
| ステータスコードとレスポンス・不正なリクエスト（400） | route-handler | 該当時必須 |
| アクセシビリティ: ラベル紐付け・キーボード操作・エラーの読み上げ | component | 推奨 |

各テストファイルの `it(` を Grep して各セルにマッピング。

## 3. ギャップ提案
空セルを優先度で絞り、番号付きで提案（対象・カテゴリ・追加先ファイル・理由）。「該当時必須」は該当実装（API 連携・認証・入力フォーム・Server Action）が無ければ提案しない。
単体テストで検証できないもの（ページ遷移・middleware・async Server Component の結合・実際のログイン）は追加候補に入れず、「E2E 側の候補」として別枠で列挙するだけにする。
```
[a] すべて追加 / [1,3] 番号指定 / [n] 追加しない
```

## 4. 追加・実行
選択分を対応テストファイルの適切な `describe` に追加（既存は変更しない。ファクトリ / MSW handler も必要に応じ追加）。
独立性を維持: QueryClient は各テストで新規、`server.resetHandlers()`、モックの戻し、fake timers を戻す。role 取得・user-event の作法も守る。
```bash
pnpm vitest run {paths}
```
全件 pass を確認（既存を壊していないこと）。

## 5. コミット + 記録
commit-convention に従い `test: 網羅性レビューで不足テストを追加`（署名はバージョン無し）でコミット（hook 準拠）。
`workflow-{id}.json` に `coverage_review`（before/after/added/commit/completed_at）を記録、`updated_at` 更新。

## 6. サマリ（簡潔）
Before/After テスト数 / カテゴリ別追加 / E2E 側の候補（あれば）/ コミット SHA。→ 自動遷移（tdd が Optimize へ）。

## 注意
既存テストは変更しない（追加のみ。既存の意味を変えると網羅性の比較が成り立たない）。各テストは独立（順序非依存・単一実行可）。
カバレッジ数値の追求が目的ではない — 意味のあるケースを足す（数値のためだけのテストは追加しない）。`page.tsx` / `layout.tsx` のカバレッジが低いのは方針どおりなので、それ自体を抜けとして扱わない。
