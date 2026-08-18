# ワークフロー状態スキーマ（正準・単一情報源）— order-api

> `.claude/tdd-workflow/workflow-{id}.json` と `current-cycle.json` の**唯一の正しい形**。
> 全スキルはこのスキーマで読み書きする。**キー名の別名・揺れは禁止**。

## キー名の固定（別名禁止）

| 概念 | 正準キー | 禁止する別名 |
|---|---|---|
| サイクル計画 | `cycle_plan` | ~~`cycles_plan`~~ |
| TODOタスクID | `todo_task_id` | ~~`todo_task_ids`~~ |
| 進捗位置 | `current_cycle` | （省略禁止・必須） |

## workflow-{id}.json スキーマ

```jsonc
{
  "schema_version": 1,
  "workflow_id": "tdd-YYYYMMDD-HHMMSS",
  "status": "planning_done | in_progress | done",
  "task_title": "string",
  "task_content": "string",
  "task_source": "notion | free-text | conversation-context",
  "notion_url": "string | null",
  "target_files": {
    "implementation": ["src/routes/... | src/services/... | src/repositories/..."],
    "test": "src/.../*.test.ts",
    "schemas": ["src/schemas/*.ts"],              // Zod スキーマを触る場合
    "factories": ["src/testUtils/factory/*.ts"],  // テストデータを足す場合
    "mocks": ["src/testUtils/mocks/handlers/..."] // 外部 API を叩く場合（MSW）
  },
  "patterns": {                               // 既存コードから抽出した踏襲ルール
    "test_kind": "route | service | repository | schema | util",
    "layer": "routes | services | repositories | schemas",
    "uses_db": true,                           // トランザクションロールバックが要るか
    "uses_external_api": false,                // MSW handler が要るか
    "test_helpers": "supertest / vi.mock / factory"
  },
  "user_instructions": "string",
  "run_mode": "phase-stop | auto",            // 既定 "phase-stop"
  "cycle_plan": [
    {"cycle": 1, "title": "string", "kind": "テスト種別 + 正常系/異常系/境界"}
  ],
  "total_cycles": 0,
  "current_cycle": 1,
  "todo_task_id": "string",
  "completed_cycles": [
    {"cycle_number": 1, "commit": "sha", "test_file_path": "...", "implementation_files": ["..."]}
  ],
  "coverage_review": null,
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

### 必須キー（計画フェーズ完了＝これらが揃うこと）

`schema_version, workflow_id, status, task_title, task_content, task_source,
target_files, patterns, user_instructions, run_mode, cycle_plan, total_cycles, current_cycle,
todo_task_id, completed_cycles, created_at, updated_at`

計画フェーズは上記を満たす JSON を Write し、**Read で自己検証してから**完了とする（1つでも欠ければ未完了）。

## current-cycle.json スキーマ（進行中サイクルのみ）

```jsonc
{
  "workflow_id": "tdd-YYYYMMDD-HHMMSS",
  "cycle_number": 3,
  "phase": "red | green | refactor",          // "commit" は付けない（commit 完了でこのファイル削除）
  "test_file_path": "string",
  "test_name": "string",                      // vitest の -t に渡すケース名
  "test_details": {"total": 0, "passed": 0, "failed": 0, "error_type": "...", "error_message": "..."},
  "implementation_files": ["..."],            // green 以降
  "refactor_details": { },                    // refactor 以降（空オブジェクト不可）
  "retry_count": 0,
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

- `test_name` は `yarn vitest run {path} -t "{test_name}"` で単一ケースを流すために使う。
- **commit 完了時に `current-cycle.json` を削除**し、`completed_cycles` に移す。削除後に不在を Read で確認。
- 次サイクルの Red 入口は「`current-cycle.json` 不在」を前提条件に検証する。
