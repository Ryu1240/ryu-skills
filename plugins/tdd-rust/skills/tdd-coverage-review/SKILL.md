---
name: tdd-coverage-review
description: Test coverage review for ledger-core (Rust) - analyze (endpoint/service/error-variant × test-category) matrix and add missing cargo tests
argument-hint: <workflow_id>
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(cargo:*)
  - Bash(make:*)
  - Bash(just:*)
  - Bash(git:*)
  - Grep
  - Glob
  - TaskGet
  - TaskUpdate
examples:
  - input: /tdd-coverage-review tdd-20260613-101500
    description: Review test coverage for the completed workflow
---

TDD 完了後、ledger-core のテスト網羅性を「対象 × テストカテゴリ」のマトリクスで分析し、不足を追加する。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/project-settings.md`（テストコマンド・レイヤー構成）/ `workflow-schema.md` / `commit-convention.md`

## 1. コンテキスト
`workflow-{id}.json`（`task_title`, `completed_cycles`, `patterns`, `todo_task_id`）を Read。対象テスト・実装ファイルを Read。
実装から**公開インターフェイス**を列挙してマトリクスの行にする（route ならエンドポイント×メソッド、service なら `pub fn`、domain なら値オブジェクトのコンストラクタと**エラー enum の各 variant**）。
`cargo llvm-cov`（導入時。無ければスキップ）を実行し、未到達行の手がかりにする（数値目標ではなく**抜けの発見**に使う）。

## 2. マトリクス

| カテゴリ | 優先度 |
|---|---|
| 正常系: ステータスコードとレスポンス body | 必須 |
| 正常系: 主要な分岐バリエーション | 必須 |
| デシリアライズ / 検証: serde の必須フィールド欠落・型不一致・ドメイン検証違反 → 400/422 | 必須 |
| 異常系: 不存在 404 / 競合・重複 409 | 該当時必須 |
| 認証・認可: 未認証 401 / 権限不足 403 | 該当時必須 |
| 外部依存の失敗: 5xx・タイムアウト（wiremock 注入） | 該当時必須 |
| DB: ユニーク制約違反・トランザクションのロールバック | 該当時必須 |
| 境界値: 0件 / 1件 / ページネーション上限 / 最大長 | 必須 |
| 整数境界: オーバーフロー（`checked_*`）・`u64`↔`i64` 変換・負数 | 該当時必須 |
| `None` / 空コレクション経路 | 必須 |
| エラー variant ごとの返却（各 variant を `matches!` で 1 回以上） | 必須 |
| 性質（`proptest` 導入時）: 往復・単調性・不変量 | 該当時推奨 |
| 冪等性・並行性: 再実行・同時更新 | 該当時推奨 |

各テストファイルの `#[test]` / `#[tokio::test]` / `#[sqlx::test]` / `#[rstest]` を Grep して各セルにマッピング。

## 3. ギャップ提案
空セルを優先度で絞り、番号付きで提案（対象・カテゴリ・追加先モジュール/ファイル・理由）。「該当時必須」は該当実装（認可・外部 API・DB 制約・整数演算）が無ければ提案しない。
```
[a] すべて追加 / [1,3] 番号指定 / [n] 追加しない
```

## 4. 追加・実行
選択分を対応する `#[cfg(test)] mod tests` または `tests/*.rs` に追加（既存は変更しない。フェイク / ビルダーも必要に応じ `testutil` に追加）。
**独立性を維持**: DB は `#[sqlx::test]`、`MockServer` はテストごと、共有可変状態を作らない。
```bash
cargo test -p {crate} {module_path}::
cargo test -p {crate} --test {file}
```
全件 pass を確認（既存を壊していないこと）。`cargo clippy --all-targets -- -D warnings` も通す（hook 対策）。

## 5. コミット + 記録
commit-convention に従い `test: 網羅性レビューで不足テストを追加`（**署名はバージョン無し**）でコミット（hook 準拠）。
`workflow-{id}.json` に `coverage_review`（before/after/added/commit/completed_at）を記録、`updated_at` 更新。

## 6. サマリ（簡潔）
Before/After テスト数 / カテゴリ別追加 / コミット SHA。→ 自動遷移（tdd が Optimize へ）。

## 注意
既存テストは絶対に変更しない（追加のみ）。各テストは独立（順序非依存・単一実行可・並列で壊れない）。
**カバレッジ数値の追求が目的ではない** — 意味のあるケースを足す（数値のためだけのテストは追加しない）。
