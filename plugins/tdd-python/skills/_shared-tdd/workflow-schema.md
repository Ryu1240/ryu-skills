# ワークフロー状態スキーマ（正準・単一情報源）

> `.claude/tdd-workflow/workflow-{id}.json` と `current-cycle.json` の**唯一の正しい形**。
> 全スキルはこのスキーマで読み書きする。**キー名の別名・揺れは禁止**（別名が混在すると別インスタンスが状態を読めなくなる）。

## キー名の固定（別名禁止）

| 概念 | **正準キー（これだけ使う）** | 使ってはいけない別名 |
|---|---|---|
| サイクル計画 | `cycle_plan` | ~~`cycles_plan`~~ |
| TODOタスクID | `todo_task_id` | ~~`todo_task_ids`~~ |
| 対象モジュール | `target_module` | ~~`target_modules`~~ |
| タスク本文 | `task_content` | ~~`task_summary`~~ |
| 進捗位置 | `current_cycle` | （省略禁止・必須） |

## workflow-{id}.json スキーマ

```jsonc
{
  "schema_version": 1,                       // 必須。将来の移行用
  "workflow_id": "tdd-YYYYMMDD-HHMMSS",       // 必須
  "status": "planning_done | in_progress | done",  // 必須
  "task_title": "string",                     // 必須
  "task_content": "string",                   // 必須。要件の本文
  "task_content_history": [],                 // 任意。tdd-workflow-update が task_content を上書きした際の旧値
  "task_source": "notion | free-text | conversation-context",  // 必須
  "notion_url": "string | null",              // task_source=notion のときのみ
  "target_module": "schemas | commands | storage | cli",  // 必須
  "target_files": {                           // 必須
    "implementation": ["taskcli/taskcli/..."],
    "test": ["taskcli/tests/test_task_schemas.py", "taskcli/tests/test_add_command.py"],   // サイクルごとに異なりうるので配列
    "fixtures_dir": "taskcli/tests/fixtures/"
  },
  "patterns": {                               // 必須。既存コードから抽出した踏襲ルール
    "model_base_class": "StrictModel",
    "extra_field_policy": "forbid",
    "fixture_helper": "tests/_helpers.py load_json",
    "naming_constants_location": "schemas/_common.py",
    "test_structure": "string"                // 例: '1 cycle = 1 independent test function'
  },
  "user_instructions": "string",              // 必須（無ければ空文字）。--auto 等の都度方針も含めてよい
  "run_mode": "phase-stop | auto",            // 必須。既定 "phase-stop"。--auto 指定時 "auto"
  "cycle_plan": [                             // 必須。1要素=1サイクル=1テスト
    {"cycle": 1, "title": "string", "kind": "schema_roundtrip | logic | validation"}
  ],
  "total_cycles": 0,                          // 必須。len(cycle_plan)
  "current_cycle": 1,                         // 必須。次に着手する（or 進行中の）サイクル番号
  "todo_task_id": "string",                   // 必須。TaskCreate の返却 ID
  "completed_cycles": [                       // 必須（初期 []）
    {
      "cycle_number": 1,
      "title": "string",
      "commit": "sha",
      "test_file_path": "string",
      "implementation_files": ["..."],
      "fixture_files_added": ["..."],
      "test_details": {"total_tests": 0, "passed_tests": 0, "failed_tests": 0}
    }
  ],
  "coverage_review": null,                    // Coverage Review 実行後に {"before": 0, "after": 0, "added": ["..."], "commit": "sha", "completed_at": "ISO8601"} を格納
  "created_at": "ISO8601",                    // 必須
  "updated_at": "ISO8601"                     // 必須。毎更新で書き換える
}
```

### 必須キー（計画フェーズ完了＝これらが揃っていること）

`schema_version, workflow_id, status, task_title, task_content, task_source, target_module,
target_files, patterns, user_instructions, run_mode, cycle_plan, total_cycles, current_cycle,
todo_task_id, completed_cycles, created_at, updated_at`

計画フェーズは、上記必須キーを満たす JSON を Write し、**Read で自己検証してから**完了とする。
1つでも欠ければ計画フェーズは未完了（完了メッセージを出さない）。

## current-cycle.json スキーマ（進行中サイクルのみ）

```jsonc
{
  "workflow_id": "tdd-YYYYMMDD-HHMMSS",
  "cycle_number": 3,
  "phase": "red | green | refactor",          // "commit" は付けない（commit 完了時にこのファイルは削除）
  "test_file_path": "string",
  "target_module": "string",
  "test_case_count": 0,                       // Red 完了時点の test_file_path 内の `def test_` 定義数（parametrize はケース数でなく定義数で数える）。Evac(review) が増加を検出する基準値
  "test_details": {"total_tests": 0, "passed_tests": 0, "failed_tests": 0, "error_type": "...", "error_message": "..."},
  "fixture_files_added": ["..."],
  "implementation_files": ["..."],            // green 以降
  "refactor_details": { },                    // refactor 以降（空オブジェクト不可）
  "retry_count": 0,
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

- **commit 完了時に `current-cycle.json` を削除**し、`workflow-{id}.json` の `completed_cycles` に移す。
  削除後に「ファイルが存在しないこと」を Read で確認する。
- 次サイクルの Red 入口は「`current-cycle.json` が存在しない」を前提条件に検証する。

## 実例（Task スキーマ追加・抜粋）

```jsonc
{
  "schema_version": 1,
  "workflow_id": "tdd-20260612-170046",
  "status": "in_progress",
  "task_title": "Task モデルに priority フィールドを追加 (schemas/task.py)",
  "task_source": "free-text",
  "target_module": "schemas",
  "target_files": {
    "implementation": ["taskcli/taskcli/schemas/task.py",
                       "taskcli/taskcli/schemas/__init__.py"],
    "test": "taskcli/tests/test_task_schemas.py",
    "fixtures_dir": "taskcli/tests/fixtures/"
  },
  "patterns": {"model_base_class": "StrictModel", "extra_field_policy": "forbid",
               "fixture_helper": "tests/_helpers.py load_json",
               "naming_constants_location": "schemas/_common.py"},
  "run_mode": "phase-stop",
  "cycle_plan": [
    {"cycle": 1, "title": "Task basic roundtrip", "kind": "schema_roundtrip"},
    {"cycle": 2, "title": "TaskCreate basic roundtrip", "kind": "schema_roundtrip"}
  ],
  "total_cycles": 2,
  "current_cycle": 3,
  "todo_task_id": "2",
  "completed_cycles": [ /* ... cycle 1,2 ... */ ],
  "updated_at": "2026-06-13T09:00:00+09:00"
}
```
