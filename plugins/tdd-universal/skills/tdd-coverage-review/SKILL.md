---
name: tdd-coverage-review
description: TDD 完了後に、公開インターフェイス × テストカテゴリのマトリクスでテストの抜けを洗い出し、承認されたケースを追加する（あらゆる言語向け。テストコマンドは project-settings.md から読む）。/tdd から呼ばれるほか、「テストの網羅性を見て」と頼まれたときにも使う。
argument-hint: <workflow_id>
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
  - TaskGet
  - TaskUpdate
examples:
  - input: /tdd-coverage-review tdd-20260613-101500
    description: Review test coverage for the completed workflow
---

TDD 完了後、テスト網羅性を「対象 × テストカテゴリ」のマトリクスで分析し、不足を追加する。言語に依存しないカテゴリで評価する。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/project-settings.md`（テスト実行コマンド・言語固有の慣習）/ `workflow-schema.md` / `commit-convention.md`

## 入口ゲート
`current-cycle.json` が存在しないこと（サイクル進行中でない）と `completed_cycles` 非空を確認。進行中なら `/tdd-commit {id}` を案内し中断。

## 1. コンテキスト
`workflow-{id}.json`（`task_title`, `completed_cycles`, `patterns`, `todo_task_id`）を Read。対象テスト・実装ファイルを Read。
実装から公開インターフェイス（関数/メソッド/エンドポイント/コマンド/イベント）を列挙し、マトリクスの行にする。
project-settings に `{{TEST_COVERAGE}}` があれば実行し、未到達箇所の手がかりにする（未導入ならスキップ）。

## 2. マトリクス

| カテゴリ | 優先度 |
|---|---|
| 正常系: 基本の入出力 | 必須 |
| 正常系: 主要なバリエーション（分岐ごと） | 必須 |
| 境界値: 最小/最大/0件/1件/上限超過 | 必須 |
| 空・未定義: null/空文字/空コレクション | 必須 |
| 異常系: 不正な入力・型・形式 | 必須 |
| 異常系: 失敗する前提条件・想定外の状態 | 推奨 |
| 外部依存の失敗: エラー応答・タイムアウト | 該当時必須 |
| 権限・認可: 未認証 / 権限不足 / 他者データ | 該当時必須 |
| 契約・スキーマ検証 | 該当時必須（project-settings の `{{CONTRACT_CHECK}}`） |
| 冪等性・並行性 | 該当時推奨 |

各テストファイルのケースを Grep（`patterns.test_case_style` の記述形で検索）して各セルにマッピングする。

## 3. ギャップ提案
空セルを優先度で絞り、番号付きで提案（対象・カテゴリ・追加先ファイル・理由）。「該当時必須」は該当する実装（外部依存・認可・契約）が無ければ提案しない。
```
[a] すべて追加 / [1,3] 番号指定 / [n] 追加しない
```

## 4. 追加・実行
選択分を対応テストファイルの適切な位置に追加する。
- 既存テストは変更しない（追加のみ）。
- 既存の慣習を踏襲（不変条件#4）。テストデータ・モックも必要に応じ追加。
- 独立性の担保方法を実装形に落とす（セットアップ/ティアダウンとして書く）。
- project-settings の `{{TEST_ONE_FILE}}`（複数ファイルなら `{{TEST_ALL}}`）で全件 pass を確認（既存を壊していないこと）。

## 5. コミット + 記録
commit-convention に従い `test: 網羅性レビューで不足テストを追加`（署名はバージョン無し）でコミット（hook 準拠）。
`workflow-{id}.json` に `coverage_review`（before/after/added/commit/completed_at）を記録、`updated_at` 更新。

## 6. サマリ（簡潔）
Before/After テスト数 / カテゴリ別追加内容 / コミット SHA。→ 自動遷移（tdd が Optimize へ）。

## 注意
既存テストは変更しない（追加のみ。既存の意味を変えると網羅性の比較が成り立たない）。各テストは独立（順序非依存・単一実行可）。
カバレッジ数値の追求が目的ではない — 意味のあるケースを足す（数値を上げるためだけのテストは追加しない）。
