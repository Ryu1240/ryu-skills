---
name: tdd-py-refactor
description: Refactor phase - Improve code quality in taskcli while keeping tests green (no behavior change, no new tests)
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
examples:
  - input: /tdd-py-refactor tdd-20260613-101500
    description: Execute Refactor phase for the current cycle
---

TDD の Refactor フェーズ。**動作を変えずに**コード品質を改善し、テストが引き続き全件 pass することを確認する。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd-python/project-settings.md`（現行構成・未導入ツール）
- `.claude/skills/_shared-tdd-python/workflow-schema.md`
- `.claude/skills/_shared-tdd-python/state-machine.md`

> Refactor の原則: ✅内部改善（重複集約・命名・ヘルパ抽出） ❌新機能 ❌動作変更 ❌**新規テスト追加**（次サイクルの Red で）。

## 入口ゲート
`current-cycle.json` を Read。`phase=="green"`、`implementation_files` 非空、`updated_at` 非空。違反なら中断し `/tdd-py-green {id}` を案内。

## 1. 対象読み込み
`implementation_files` と `test_file_path` を Read。重複正規表現リテラル・重複 `field_validator`・命名・`Literal[...]`・マジックナンバーを確認。

## 2. 改善（該当時のみ・2箇所以上の重複が抽出基準）
- **正規表現の集約** → `schemas/_common.py` の命名規則定数に統合し各所から参照（`from .._common import ...` / モデル側は `field_validator("x")(_validate_x)`）。
- **共通バリデータ抽出** → `schemas/_common.py` に `_validate_positive_int(v, *, field_name)` 等。2モデル以上で使う場合のみ。
- **共通不変条件** → `_validate_distinct(a, b, ...)` 等のヘルパ化。
- **Literal 型エイリアス** → 重複する `Literal[...]` を `schemas/_common.py` で型エイリアス化（`TaskStatus` 等は既存を再利用）。
- **マジックナンバー** → `Final` 定数化。
- **命名改善** → 曖昧名（`data`/`tmp`/1文字、ただし validator 引数 `v` は慣習可）を用途名に。
判断が難しい/1箇所のみは抽出せずスキップ（TODO コメントは残さない＝不変条件）。

## 3. Linter（conditional）
ruff は未導入（project-settings）。`docker compose run --rm app ruff --version` で確認し、未導入なら `linter_status:"skipped: ruff not installed"` を記録してスキップ。導入済みなら `ruff check --fix taskcli/` を実行。

## 4. テスト維持確認
```bash
cd taskcli && docker compose run --rm app pytest -v {rel_path}
```
全件 pass を確認。失敗したら参照ミス（集約先・シグネチャ・命名）を修正、または `[r]修正/[u]ロールバック/[s]停止`。

## 5. 状態更新
`current-cycle.json` を Edit: `phase:"refactor"`, `refactor_details`（実施内容。空オブジェクト不可。何もしなければ `{"note":"no refactor needed"}`）, `updated_at`。
`workflow-{id}.json` の `updated_at` 更新。
**自己検証**: `phase=="refactor"` かつ `refactor_details` 非空を Read で確認。

## 6. サマリ（簡潔）
実施した改善（集約/抽出/命名 件数）/ linter_status / 全件 pass / 次は Evac(review)→Commit。→ 自動遷移（承認ゲート②は tdd-py 側）。
