---
name: tdd-red
description: TDD の Red フェーズ。失敗する pytest テスト（テスト関数1つ、または parametrize の1エントリ）を1つだけ追加し、期待どおりに失敗することを確認する（schema roundtrip / validation / logic）。通常は /tdd から呼ばれる。単独では「失敗するテストを1つ書いて」と頼まれたときに使う。
argument-hint: <workflow_id> [test_file_path]
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
  - Bash(date:*)
examples:
  - input: /tdd-red tdd-20260613-101500
    description: Execute Red phase for the current cycle
---

TDD の Red フェーズ。今サイクルのテストを1つだけ追加し、期待通り失敗することを確認する。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/project-settings.md`（対象・パス・不変条件・現行構成・テストファイル選択表）
- `.claude/skills/_shared-tdd/workflow-schema.md`（状態スキーマ）
- `.claude/skills/_shared-tdd/state-machine.md`（このフェーズの事前/事後条件）

> 🔴 一度に1テストケースのみ（テスト関数 or 1 parametrize エントリ）。複数追加は不変条件違反。

## 入口ゲート（cycle 2 以降）
`current-cycle.json` が存在しないことを Read で確認（存在＝前サイクル未完了 → 中断し `/tdd-commit {id}` を案内）。
`workflow-{id}.json` の `completed_cycles` 長 == `current_cycle - 1` を確認。不一致なら中断。

## 1. コンテキスト
`workflow-{id}.json` を Read（`target_module`, `target_files`, `patterns`, `current_cycle`, `user_instructions`）。
`todo_task_id` で TaskGet し、`cycle_plan` の `current_cycle` 該当エントリ（`title`, `kind`）を特定。

## 2. テストファイル決定
`$1` 指定があればそれ。無ければ project-settings の「テスト構成」表で `target_module`／対象モデル群から決定（既存ファイルへの追記が原則）。
対応ファイルが無い新機能のみ新規作成。

## 3. テスト追加（`kind` で分岐）

対象ソースを Read し既存パターン（`StrictModel`@`schemas/_common.py`、命名規則定数、`load_json`@`_helpers`、既存テスト構造）に揃える。
import は実態に合わせる：
```python
from taskcli.schemas import Task      # schemas パッケージから
from ._helpers import load_json
```

### kind = schema_roundtrip
グループ別の `{GROUP}_BASIC_CASES` リストに1行追加（既存 `test_task_schemas.py` の `TASK_BASIC_CASES` 構造に倣う）。fixture JSON も新規作成（最小正常系1件）。
```python
TASK_BASIC_CASES: list[tuple[type[BaseModel], str]] = [
    (Task, "task.json"),
    (NewModel, "new_model.json"),    # ← 今回追加（1行）
]
```
→ `test_task_roundtrip`（parametrize）が新モデルを自動カバー。

### kind = validation
fixture を `load_json` で読み、改変して `pytest.raises(ValidationError)` を期待する関数を1つ追加（`match=` を付け、どの検証が発火したか担保）。
```python
def test_task_create_extra_field_forbidden() -> None:
    raw = load_json("task_create.json")
    raw["unexpected_field"] = "x"
    with pytest.raises(ValidationError):
        TaskCreate.model_validate(raw)
```

### kind = logic（CLI コマンド / storage / IO 関数）
対象関数の1挙動を検証する関数を1つ追加。外部依存（ファイル/IO）は `conftest.py` の共有 fixture・モックを利用（project-settings 参照）。正常系/異常系/境界のうち今サイクルの1つだけ。
```python
def test_<func>_<behavior>() -> None:
    result = <call under test>
    assert result == expected
```

## 4. 失敗確認
```bash
cd taskcli && docker compose run --rm app pytest -v {rel_path} -k {keyword}
```
期待される失敗: `ImportError`/`AttributeError`（未定義）, `FileNotFoundError`（fixture 未作成）, `ValidationError`（正常系で・モデル未完成）, `AssertionError`（挙動未実装）。
予期しない失敗（`SyntaxError`/`NameError`/collection error）はテストコードの誤り → 修正して再実行。

## 5. 状態更新
`current-cycle.json` を `workflow-schema.md` の current-cycle スキーマで Write（`phase:"red"`, `test_file_path`, `target_module`, `test_case_count`（`test_file_path` 内の `def test_` の定義数。`@pytest.mark.parametrize` はケース数でなく定義数で数え、パラメータ追加は parametrize の要素数の増加として別途比較する。Evac(review) の基準値）, `test_details`(error_type/message), `fixture_files_added`, `created_at`/`updated_at`）。
`workflow-{id}.json` の `updated_at` を更新。

## 6. サマリ（簡潔）
テストファイル / 追加した1テスト / 期待通りの失敗（種類）/ 次は Green。
→ 制御は呼び出し元（tdd）に返す。承認ゲート①の扱いは state-machine に従う（tdd 側が判断）。

## エラー
- テストファイル決定不能: `$1` で明示 or タスクにモジュール名追記を案内して中断。
- fixture 不在の `FileNotFoundError`: Red の正常な失敗パターン。Green で fixture とモデルを作る旨を記録して続行。
