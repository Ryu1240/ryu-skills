---
name: tdd-py-green
description: Green phase - Minimal implementation in taskcli to pass the failing test (pydantic models in schemas/, or logic functions)
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
  - input: /tdd-py-green tdd-20260613-101500
    description: Execute Green phase for the current cycle
---

TDD の Green フェーズ。**今サイクルのテストを通す最小限の実装のみ**を追加する。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd-python/project-settings.md`（**不変条件**・現行構成）
- `.claude/skills/_shared-tdd-python/workflow-schema.md`
- `.claude/skills/_shared-tdd-python/state-machine.md`

> 最小実装の原則（不変条件 #5）: テストを通す最小限のみ。後続サイクルが駆動する validator を先回り実装しない。共通化・抽出は Refactor で。YAGNI。

## 入口ゲート
`current-cycle.json` を Read。`phase=="red"` かつ `updated_at` 非空であること。違反なら中断し `/tdd-py-red {id}` を案内。

## 1. 要件抽出
`current-cycle.json` の `error_type` から不足を特定：
- `ImportError`/`AttributeError` → モデル/関数が未定義
- `FileNotFoundError` → fixture 未作成
- 正常系の `ValidationError` → モデル定義が不適合
- `AssertionError` → 挙動未実装
`test_file_path` を Read し、検証対象（モデルクラス or 関数）と期待挙動を把握。

## 2. 実装（最小）

### schema 系（pydantic モデル）
対象モデル群ファイル（`schemas/task.py` 等）を Read し、`StrictModel`（`schemas/_common.py`）継承で新規モデルを追加。
- 既存の命名規則定数・共通バリデータ・`TaskStatus` 等を `schemas/_common.py` から**再利用**（再定義しない）。
- 新制約は `@field_validator` / `@model_validator(mode="after")`。
- **公開**: `schemas/__init__.py` の import と `__all__` に追加（テストは `from taskcli.schemas import X` で読む）。
- fixture 未作成なら `tests/fixtures/{snake}.json` に最小正常系を1件 Write（必須フィールドのみ、`extra="forbid"` で弾かれない構成、既存 fixture の値の現実性に合わせる）。

### logic 系（CLI コマンド/storage/IO）
対象モジュールに、テストを通す最小の関数/分岐を実装。既存の型・ヘルパ・schemas モデルを再利用。過剰な汎用化はしない。

## 3. テスト成功確認（最大3回リトライ）
```bash
cd taskcli && docker compose run --rm app pytest -v {rel_path}
```
失敗時の典型と対処: extra_forbidden（fixture/モデルのフィールド不整合）, `int` vs `float` の roundtrip 不一致, 命名規則違反（fixture 値）, Edit 未反映。
3回で通らなければ state-machine の停止条件 #6 に該当 → 状態保存し `[r]再実行 / [d]デバッグ / [s]一時停止` を提示して停止。

## 4. 状態更新
`current-cycle.json` を Edit: `phase:"green"`, `test_details`（passed/total/failed:0）, `implementation_files`（非空）, `retry_count`。
`workflow-{id}.json` の `updated_at`（/`current_phase`）更新。
**自己検証**: `phase=="green"` かつ `implementation_files` 非空を Read で確認。

## 5. サマリ（簡潔）
追加したモデル/関数 / fixture / 全テスト pass（リトライ回数）/ 次は Refactor。→ 自動遷移（tdd-py が Evac(plan)→Refactor を続行）。

## エラー
- `current-cycle.json` 不在: `/tdd-py-red {id}` を案内して中断。
- 新規モジュールに StrictModel が無い: `from taskcli.schemas import StrictModel` を追加して続行（warning）。
