---
name: tdd-commit
description: Commit phase - Create git commit for the completed TDD cycle in any language (pre-commit hook compliant) and archive cycle state
argument-hint: <workflow_id>
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
examples:
  - input: /tdd-commit tdd-20260613-101500
    description: Execute Commit phase for the current cycle
---

TDD の Commit フェーズ。完了サイクルを Git コミットし、サイクル状態をアーカイブする。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/commit-convention.md`（**署名・メッセージ・hook 準拠・機密チェック規約**）
- `.claude/skills/_shared-tdd/workflow-schema.md` / `project-settings.md`

## 入口ゲート
`current-cycle.json` を Read。`phase=="refactor"`、`refactor_details` 非空、`implementation_files` 非空。違反なら `/tdd-refactor {id}` 案内し中断。
`workflow-{id}.json` を Read（`task_title`, `current_cycle`, `total_cycles`, `cycle_plan`, `completed_cycles`）。

## 1. 変更確認
`git branch --show-current`（project-settings のブランチ規約に照らし、違反は warning のみ）。`git status --short` / `git diff`。
今サイクルの関連ファイルを特定（テスト / 実装 / テストデータ / モック定義 / 生成物 / 設定・依存ファイル）。

## 2. コミットメッセージ作成
commit-convention に従う（型プレフィックス・**署名はバージョン無し** `Co-Authored-By: Claude <noreply@anthropic.com>`）。
**既存の履歴に規約がある場合はそれを優先**する: `git log --oneline -20` で書式（言語・Conventional Commits・チケット番号）を確認し揃える。
サイクル内容を1行サマリ、必要なら詳細箇条書き（`cycle_plan` の `title` 参照）。

## 3. 機密チェック → 個別ステージング
commit-convention の機密チェック（`.env`/認証情報/APIキー/PII。検出時は停止）。
個別 `git add <path>`（`git add .`/`-A` 禁止）。生成物・テストデータ・モック定義も忘れず含める。

## 4. コミット（heredoc・hook 準拠）
```bash
git commit -m "$(cat <<'EOF'
{サマリー行}

{詳細（任意）}

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```
**`--no-verify` 絶対禁止**。`git log -1 --format="%H %s"` で SHA 取得。

### pre-commit hook で失敗した場合（必須リカバリ）
project-settings の `{{PRECOMMIT}}` に hook がある場合、lint エラー等でブロックされることがある：
1. エラー内容を特定する。
2. project-settings の `{{LINT_FIX}}` で修正（hook が自動修正したファイルも確認）。未導入なら手で修正。
3. 修正ファイルを `git add` し直して**再コミット**（`--no-verify` で回避しない）。
4. 解決不能なら state-machine 停止条件#7 として状態保存し報告。

## 5. アーカイブ（workflow JSON 更新・スキーマ準拠）
`workflow-{id}.json` を Edit（workflow-schema 準拠）: `completed_cycles` に今サイクル追記（`cycle_number`, `title`, `commit`(SHA), `test_file_path`, `test_case_id`, `implementation_files`。`test_case_id` は Optimize が単一ケース実行に使う）、`current_cycle` +1、`updated_at` 更新、`status` は `in_progress`（全完了時は tdd 側 Phase6 で `done`）。

## 6. current-cycle.json 削除 + 不在確認（必須）
```bash
rm .claude/tdd-workflow/current-cycle.json
```
削除後、Read を試みて**不在（エラー）を確認**。残っていたら再削除。（次サイクル Red 入口が不在を前提とするため。）

## 7. 検証（必須・state-machine と対応）
`git log -1 --format="%H"` 非空 / `completed_cycles` 末尾 `commit` == SHA・`current_cycle` == 旧+1 / `current-cycle.json` 不在。いずれか失敗なら状態保存し中断、再実行を案内。

## 8. サマリ（簡潔）
SHA / コミットメッセージ / コミットしたファイル / 進捗 `{current_cycle-1}/{total_cycles}`。
最終サイクルなら「push すれば CI がテストを実行」と案内（project-settings の `{{CI}}`。CI 未設定なら全件テストの実行を推奨）。→ サイクル境界の挙動は tdd（run_mode）に従う。
