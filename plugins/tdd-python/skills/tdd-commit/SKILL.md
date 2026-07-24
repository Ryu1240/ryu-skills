---
name: tdd-commit
description: Commit phase - Create git commit for the completed TDD cycle in taskcli and archive cycle state
argument-hint: <workflow_id>
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(git:*)
examples:
  - input: /tdd-commit tdd-20260613-101500
    description: Execute Commit phase for the current cycle
---

TDD の Commit フェーズ。完了サイクルを Git コミットし、サイクル状態をアーカイブする。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/commit-convention.md`（**署名・メッセージ・ステージング・機密チェック規約**）
- `.claude/skills/_shared-tdd/workflow-schema.md`（completed_cycles / current-cycle スキーマ）
- `.claude/skills/_shared-tdd/project-settings.md`

## 入口ゲート
`current-cycle.json` を Read。`phase=="refactor"`、`refactor_details` 非空、`implementation_files` 非空。違反なら中断し `/tdd-refactor {id}` を案内。
`workflow-{id}.json` を Read（`task_title`, `target_module`, `current_cycle`, `total_cycles`, `cycle_plan`, `completed_cycles`）。

## 1. 変更確認
`git branch --show-current`（命名規約違反は warning のみ）。`git status --short` / `git diff`。
`current-cycle.json` の `test_file_path`/`implementation_files`/`fixture_files_added` から今サイクルの関連ファイルを特定。

## 2. コミットメッセージ作成
commit-convention に従う（日本語・型プレフィックス・**署名はバージョン無し `Co-Authored-By: Claude <noreply@anthropic.com>`**）。サイクルの内容を1行サマリ、必要なら詳細箇条書き。`cycle_plan` の該当 `title` を参照。

## 3. 機密チェック → 個別ステージング
commit-convention の機密チェック（`.env`/鍵/PII 等。検出時は停止）。
個別 `git add <path>`（`git add .`/`-A` 禁止）。

## 4. コミット（heredoc）
```bash
git commit -m "$(cat <<'EOF'
{サマリー行}

{詳細（任意）}

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```
`--no-verify` 禁止。`git log -1 --format="%H %s"` で SHA とサマリーを取得。

## 5. アーカイブ（workflow JSON 更新・スキーマ準拠）
`workflow-{id}.json` を Edit（workflow-schema 準拠）：
- `completed_cycles` に今サイクルを追記（`cycle_number`, `title`, `commit`(SHA), `test_file_path`, `implementation_files`, `fixture_files_added`, `test_details`）。
- `current_cycle` を +1。`updated_at` 更新。`status` は `in_progress`（全完了時は tdd 側 Phase 6 で `done`）。

## 6. current-cycle.json 削除 + 不在確認（必須）
```bash
rm .claude/tdd-workflow/current-cycle.json
```
削除後、Read を試みて**存在しない（エラーが返る）ことを確認**。残っていたら再削除。（次サイクルの Red 入口ゲートが不在を前提とするため。）

## 7. 検証（必須・state-machine 4-3 と対応）
- `git log -1 --format="%H"` が空でない。
- `workflow-{id}.json`: `completed_cycles` 末尾 `commit` == 上記 SHA、`current_cycle` == 旧+1。
- `current-cycle.json` 不在。
いずれか失敗なら状態を保存し中断、再実行を案内。

## 8. サマリ（簡潔）
SHA / コミットメッセージ / コミットしたファイル / 進捗 `{current_cycle-1}/{total_cycles}`。
最終サイクルなら「PR 前に全件 pytest 必須（CI で走らない）」を明記。→ サイクル境界の挙動は tdd（run_mode）に従う。
