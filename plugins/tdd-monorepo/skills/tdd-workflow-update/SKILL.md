---
name: tdd-workflow-update
description: Update an in-progress retail-hub monorepo TDD workflow JSON via natural-language instructions. Rewrites future cycle_plan entries, user_instructions, run_mode, task_content while protecting completed_cycles, ecosystem, and current-cycle.json.
argument-hint: <workflow_id> <update-instructions>
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - AskUserQuestion
  - Bash(date:*)
  - Bash(jq:*)
  - Glob
examples:
  - input: /tdd-workflow-update tdd-20260613-101500 サイクル5を削除
    description: 未消化の cycle_plan エントリを削除（承認後）
  - input: /tdd-workflow-update tdd-20260613-101500 他テナント除外のサイクルを追加
    description: cycle_plan に新サイクルを追加
  - input: /tdd-workflow-update tdd-20260613-101500 ここから一気通貫で
    description: run_mode を auto に切替
---

進行中の retail-hub TDD ワークフロー JSON を自然言語の指示で動的に更新する。**未消化部分のみ**書き換え、進行中サイクル・完了済みサイクル・**ecosystem** は保護する。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/workflow-schema.md`（**正準スキーマ・キー名固定・保護対象/編集対象の定義**）
- `.claude/skills/_shared-tdd/project-settings.md`

## 編集対象 / 保護対象（workflow-schema 準拠）

| 編集可能 | 保護（絶対に書き換えない） |
|---|---|
| `cycle_plan[]` の未消化エントリ（`cycle > current_cycle`、または `== current_cycle` かつ current_phase≠commit） | `completed_cycles[]` 全件 |
| `user_instructions`（追記マージ） | `current_cycle` / `current_phase` |
| `run_mode`（`phase-stop`↔`auto`） | **`ecosystem`**（計画時に確定。変更＝別ワークフロー） |
| `task_content`（明示指示時のみ。旧値を `task_content_history[]` に append） | `created_at` / `total_cycles`（cycle 追加時のみ +1 可） |
| `updated_at`（必ず更新） | 完了済み `cycle_plan` エントリ / `commit` / **別ファイル** `current-cycle.json` / `schema_version` / `workflow_id` |

> `ecosystem` を変えたい場合はワークフローの作り直し（別 workflow_id）を案内する。1ワークフロー=1エコシステム。

## Step 1: 検証
`$0` が `tdd-\d{8}-\d{6}` 形式。`$1` 以降（指示）が非空。`.claude/tdd-workflow/workflow-{$0}.json` 存在（無ければ Glob で候補提示し中断）。

## Step 2: 読込（read-only）
`workflow-{$0}.json` と（あれば）`current-cycle.json` を Read。`completed_cycles`/`current_cycle`/`current_phase`/`cycle_plan`/`user_instructions`/`run_mode`/`task_content`/`ecosystem` を把握。未消化サイクルを判定。

## Step 3: 提案 diff の構築
指示を解釈して操作を提案（cycle_plan の未消化エントリ 追加/削除/修正、user_instructions 追記、run_mode 切替、task_content 上書き）。
- 削除: 該当エントリ除外（`cycle` 番号は再採番しない＝衝突防止）。
- 追加: 末尾に追加（`cycle` = 既存最大+1）、`total_cycles` +1。
- 修正: 該当の `title`/`kind` を書換。
- **ecosystem 変更の指示が来たら拒否**（別ワークフロー案内）。
diff を提示（編集内容 + 保護対象を明示）。

## Step 4: 承認ゲート（必須）
AskUserQuestion で `[適用] / [キャンセル] / [部分適用]`。**[適用] のときのみ Step 5**。[部分適用] は変更ごとに再質問。[キャンセル] は何も書かず終了。

## Step 5: 書込（承認後のみ）
1. Read で現状の workflow JSON 全文取得 → メモリ展開。
2. 編集対象キーのみ書換、**保護対象（ecosystem 含む）は元の値をそのままコピー**。`updated_at` を `date -u +%Y-%m-%dT%H:%M:%SZ` で更新。Write で上書き。
3. **保護チェック**: 書込後に Read し直し、保護対象が更新前と完全一致を確認。不一致なら `git checkout HEAD -- ...`（追跡されている場合）か手動復元を案内。

## Step 6: 完了サマリ
変更フィールド / 保護フィールド / `次: /tdd {$0}` を表示。

## 起動可能タイミング
`planning_done` / `red` / `green` / `refactor` / `commit`（当該サイクルは完了扱いで保護）/ `coverage-review` / `optimize` のいずれでも可。
進行中 `current-cycle.json` と `completed_cycles[]` は常に read-only。
