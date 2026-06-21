---
name: tdd-py-coverage-review
description: Test coverage review for taskcli - analyze (pydantic model / function) × test-category matrix and add missing test cases
argument-hint: <workflow_id>
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(docker:*)
  - Bash(git:*)
  - Grep
  - Glob
  - TaskGet
  - TaskUpdate
examples:
  - input: /tdd-py-coverage-review tdd-20260613-101500
    description: Review coverage for the completed workflow
---

TDD 完了後、taskcli のテスト網羅性を「対象 × テストカテゴリ」のマトリクスで分析し、不足テストを追加する。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd-python/project-settings.md`（現行構成・テストファイル選択表・pytest-cov 未導入）
- `.claude/skills/_shared-tdd-python/workflow-schema.md`
- `.claude/skills/_shared-tdd-python/commit-convention.md`

> pytest-cov は未導入のため coverage% は使わない。「対象 × カテゴリ」のマトリクスで漏れを検出する。

## 1. コンテキスト
`workflow-{id}.json`（`target_module`, `task_title`, `completed_cycles`, `todo_task_id`）を Read。
`completed_cycles` から対象テストファイル・実装ファイルを収集して Read。
schema 系なら `Grep "^class .+\(StrictModel\)"` を `schemas/` に対して実行しモデル一覧を取得。

## 2. マトリクス
各対象（モデル/関数）について、該当するカテゴリのテスト有無を確認：

| カテゴリ | 対象 | 優先度 |
|---|---|---|
| basic roundtrip / json_string | pydantic モデル | 必須 |
| validation_error: missing / extra / type | pydantic モデル | 必須 |
| invariant: naming / value range / model_validator | 該当制約があるモデル | 該当時必須 |
| collection invariant | `validate_*_collection` がある場合 | 条件付き |
| roundtrip after model_copy / extra slip-through | pydantic モデル | 推奨 |
| logic: 正常系 / 異常系 / 境界 | CLI コマンド/storage/IO 関数 | 必須（該当時） |

`{GROUP}_BASIC_CASES` のエントリは basic/json_string をカバー済みとみなす。`def test_*` を Grep して各セルにマッピング。

## 3. ギャップ提案
空セルを優先度で絞り、番号付きで提案コード（`load_json` + 既存 fixture 改変）とともに提示。
```
[a] すべて追加 / [1,3] 番号指定 / [n] 追加しない
```
※「該当時必須/条件付き/推奨」は該当する実装が無ければ提案しない。

## 4. 追加・実行
選択分を対応テストファイルの適切なセクションに追加（既存テストは変更しない。`load_json` 再利用、新規 fixture は基本作らず既存を改変）。
```bash
cd taskcli && docker compose run --rm app pytest -v
```
全件 pass を確認（既存テストを壊していないこと）。失敗ならテスト側を修正（実装は変えない）。

## 5. コミット + 記録
commit-convention に従い `test: 網羅性レビューで不足テストを追加`（署名はバージョン無し）でコミット。
`workflow-{id}.json` に `coverage_review`（`total_test_cases_before/after`, `added_test_cases`, `commit`, `completed_at`）を記録、`updated_at` 更新。

## 6. サマリ（簡潔）
Before/After テスト数 / カテゴリ別追加内訳 / コミット SHA。→ 自動遷移（tdd-py が Optimize へ）。
