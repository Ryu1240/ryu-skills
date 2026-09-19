---
name: tdd-coverage-review
description: Test coverage review for shipment-api (Go) - analyze (handler/service × test-category) matrix and add missing test cases
argument-hint: <workflow_id>
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(go:*)
  - Bash(gofmt:*)
  - Bash(goimports:*)
  - Bash(make:*)
  - Bash(git:*)
  - Grep
  - Glob
  - TaskGet
  - TaskUpdate
examples:
  - input: /tdd-coverage-review tdd-20260613-101500
    description: Review test coverage for the completed workflow
---

TDD 完了後、shipment-api のテスト網羅性を「対象 × テストカテゴリ」のマトリクスで分析し、不足を追加する。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/project-settings.md`（テストコマンド・レイヤー構成）/ `workflow-schema.md` / `commit-convention.md`

## 1. コンテキスト
`workflow-{id}.json`（`task_title`, `completed_cycles`, `patterns`, `todo_task_id`）を Read。対象テスト・実装ファイルを Read。
実装から**公開インターフェイス**を列挙してマトリクスの行にする（handler ならエンドポイント×メソッド、service なら公開メソッド、repository なら公開クエリ、domain なら各型・検証関数）。
```bash
go test {pkgs} -count=1 -coverprofile=coverage.out && go tool cover -func=coverage.out
```
を実行し、カバレッジが低い関数を未到達分岐の手がかりにする（数値目標ではなく**抜けの発見**に使う。`-tags=integration` が要るリポでは付ける）。

## 2. マトリクス

| カテゴリ | 優先度 |
|---|---|
| 正常系: ステータスコードとレスポンス body | 必須 |
| 正常系: 主要な分岐バリエーション | 必須 |
| バリデーション: JSON デコード失敗 / 必須・型・範囲違反 → 400 | 必須 |
| 異常系: 不存在 404 / 競合・重複 409 | 該当時必須 |
| 認証・認可: 未認証 401 / 権限不足 403 | 該当時必須 |
| service: sentinel error の返却（`errors.Is` で判定できること） | 該当時必須 |
| 外部依存の失敗: API エラー・タイムアウト（`httptest.NewServer` 注入） | 該当時必須 |
| DB: ユニーク制約違反・トランザクションのロールバック | 該当時必須 |
| context: キャンセル / タイムアウトでの早期 return | 該当時必須 |
| 境界値: 0件 / 1件 / ページネーション上限 / 最大長 / nil と空スライス | 必須 |
| 並行性: `-race` での同時アクセス（共有状態を持つ型のみ） | 該当時推奨 |
| 冪等性: 再実行・同時更新 | 該当時推奨 |

各テストファイルの `func Test` / `t.Run(` / テーブルの `name:` を Grep して各セルにマッピング。

## 3. ギャップ提案
空セルを優先度で絞り、番号付きで提案（対象・カテゴリ・追加先ファイル・理由）。「該当時必須」は該当実装（認可・外部 API・DB 制約・goroutine）が無ければ提案しない。
```
[a] すべて追加 / [1,3] 番号指定 / [n] 追加しない
```

## 4. 追加・実行
選択分を対応テストファイルの適切な `TestXxx` / テーブルに追加（既存は変更しない。フェイク / ファクトリも必要に応じ追加。既存の `package` 宣言・アサーションライブラリに合わせる）。
**独立性を維持**: DB はトランザクション + `t.Cleanup(tx.Rollback)`、`httptest.NewServer` は `t.Cleanup(srv.Close)`、パッケージレベル変数を書き換えない。
```bash
go test {pkgs} -count=1 -race
```
全件 pass を確認（既存を壊していないこと）。`gofmt -l {files}` で未フォーマットが無いことも確認。

## 5. コミット + 記録
commit-convention に従い `test: 網羅性レビューで不足テストを追加`（**署名はバージョン無し**）でコミット（hook 準拠。`coverage.out` はコミットしない）。
`workflow-{id}.json` に `coverage_review`（before/after/added/commit/completed_at）を記録、`updated_at` 更新。

## 6. サマリ（簡潔）
Before/After テスト数 / カテゴリ別追加 / コミット SHA。→ 自動遷移（tdd が Optimize へ）。

## 注意
既存テストは絶対に変更しない（追加のみ）。各テストは独立（順序非依存・単一実行可）。
**カバレッジ数値の追求が目的ではない** — 意味のあるケースを足す（数値のためだけのテストは追加しない）。
