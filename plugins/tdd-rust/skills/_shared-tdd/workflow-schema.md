# ワークフロー状態スキーマ（正準・単一情報源）— ledger-core

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
    "test": "src/services/inventory.rs (#[cfg(test)] mod tests) | tests/*.rs",
    "domain": ["src/domain/*.rs"],                                        // 型・エラー enum を触る場合
    "fakes": ["src/testutil/... (#[cfg(test)]) | tests/common/mod.rs"],   // 手書きフェイク・ビルダーを足す場合
    "migrations": ["migrations/..."]                                      // DB スキーマを触る場合（.sqlx/ の再生成も伴う）
  },
  "patterns": {                               // 既存コードから抽出した踏襲ルール
    "test_kind": "route | service | repository | domain | cli",
    "layer": "routes | services | repositories | domain",
    "uses_db": true,                           // #[sqlx::test] / トランザクションが要るか
    "uses_external_api": false,                // wiremock の MockServer が要るか
    "test_location": "inline (#[cfg(test)]) | tests/ dir",
    "is_async": true,                          // #[tokio::test] が要るか
    "assert_lib": "std | pretty_assertions | insta",
    "test_helpers": "oneshot / hand-written fakes / rstest"
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
  "test_name": "string",                      // cargo test に渡すモジュールパス込みの完全名
  "test_details": {"total": 0, "passed": 0, "failed": 0, "error_type": "...", "error_message": "..."},
  "implementation_files": ["..."],            // green 以降
  "refactor_details": { },                    // refactor 以降（空オブジェクト不可）
  "retry_count": 0,
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

- `test_name` は `cargo test -p {crate} {test_name} -- --exact` で単一ケースを流すための**モジュールパス込みの完全名**（例 `services::inventory::tests::returns_out_of_stock_when_stock_is_insufficient`）。統合テスト（`tests/foo.rs`）は `cargo test -p {crate} --test foo {case} -- --exact` で流すため、`test_file_path` が `tests/` 配下なら関数名のみを保存する。
- `test_details.error_type` は Rust 特有の区別を残す: `compile_error_undefined`（テストが要求する型/関数が未定義＝期待される Red）/ `assertion_failed` / `panicked` / `status_mismatch` など。
- **commit 完了時に `current-cycle.json` を削除**し、`completed_cycles` に移す。削除後に不在を Read で確認。
- 次サイクルの Red 入口は「`current-cycle.json` 不在」を前提条件に検証する。
