# ワークフロー状態スキーマ（正準・単一情報源）— 汎用

> `.claude/tdd-workflow/workflow-{id}.json` と `current-cycle.json` の**唯一の正しい形**。
> 全スキルはこのスキーマで読み書きする。**キー名の別名・揺れは禁止**。言語に依存しない。

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
  "task_content_history": [],                // 任意。tdd-workflow-update が task_content を上書きした際の旧値
  "task_source": "notion | free-text | conversation-context",
  "notion_url": "string | null",
  "target_files": {
    "implementation": ["実装ファイルのパス"],
    "test": ["テストファイルのパス"],           // サイクルごとに異なりうるので配列
    "fixtures": ["テストデータ定義のパス"],   // 該当する場合のみ
    "mocks": ["モック/スタブ定義のパス"]       // 該当する場合のみ
  },
  "patterns": {                               // 既存コードから抽出した踏襲ルール
    "test_kind": "project-settings の「テスト種別の区分」から選ぶ",
    "test_case_style": "既存テストのケース記述スタイル（実物から抽出）",
    "isolation": "このサイクルで守る独立性の担保手段",
    "external_deps": "モックが必要な外部依存と手段（無ければ null）",
    "contract_check": "契約/スキーマ検証の要否と手段（無ければ null）"
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
    {"cycle_number": 1, "title": "string", "commit": "sha", "test_file_path": "...", "test_case_id": "...", "implementation_files": ["..."]}
  ],
  "coverage_review": null,                    // 完了後は {"before": 0, "after": 0, "added": ["..."], "commit": "sha", "completed_at": "ISO8601"}
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
  "test_case_id": "string",                   // 単一ケース実行に使う識別子（ケース名 or 行番号）
  "test_case_count": 0,                       // Red 完了時点の test_file_path 内のケース数（project-settings の「ケース記述スタイル」に従って数える）。Evac(review) が増加を検出する基準値
  "test_details": {"total": 0, "passed": 0, "failed": 0, "error_type": "...", "error_message": "..."},
  "implementation_files": ["..."],            // green 以降
  "refactor_details": { },                    // refactor 以降（空オブジェクト不可）
  "retry_count": 0,
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

- `test_case_id` は `project-settings.md` の `{{TEST_ONE_CASE}}` に埋めるための値（ケース名指定の言語ならケース名、行番号指定なら行番号）。
- **commit 完了時に `current-cycle.json` を削除**し、`completed_cycles` に移す。削除後に不在を Read で確認。
- 次サイクルの Red 入口は「`current-cycle.json` 不在」を前提条件に検証する。
