---
name: tdd-commit
description: Commit phase - Create git commit for the completed TDD cycle in retail-hub monorepo (husky/lint-staged hook compliant) and archive cycle state
argument-hint: <workflow_id>
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(git:*)
  - Bash(bundle:*)
  - Bash(docker:*)
  - Bash(yarn:*)
  - Bash(npx:*)
  - Bash(npm:*)
examples:
  - input: /tdd-commit tdd-20260613-101500
    description: Execute Commit phase for the current cycle
---

TDD の Commit フェーズ。完了サイクルを Git コミットし、サイクル状態をアーカイブする。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/commit-convention.md`（**署名・メッセージ・hook 準拠・機密チェック規約**）
- `.claude/skills/_shared-tdd/workflow-schema.md` / `project-settings.md`

## 入口ゲート
`current-cycle.json` を Read。`phase=="refactor"`、`refactor_details` 非空、`implementation_files` 非空、`ecosystem` 取得。違反なら `/tdd-refactor {id}` 案内し中断。
`workflow-{id}.json` を Read（`task_title`, `current_cycle`, `total_cycles`, `cycle_plan`, `completed_cycles`）。

## 1. 変更確認
`git branch --show-current`（命名規約違反は warning のみ）。`git status --short` / `git diff`。
今サイクルの関連ファイルを特定（backend: test/implementation/OpenAPI 生成物/route/model/service。frontend: test/component/composable/store/MSW handler/factory。共通: i18n 等）。

## 2. コミットメッセージ作成
commit-convention に従う（日本語・型プレフィックス・**署名はバージョン無し** `Co-Authored-By: Claude <noreply@anthropic.com>`）。サイクル内容を1行サマリ、必要なら詳細箇条書き（`cycle_plan` の `title` 参照）。

## 3. 機密チェック → 個別ステージング
commit-convention の機密チェック（`.env`/認証情報/外部サービスの認証情報・APIキー/PII。検出時は停止）。
個別 `git add <path>`（`git add .`/`-A` 禁止）。backend の OpenAPI 生成物・frontend の MSW handler / factory も忘れず含める。

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
husky + lint-staged が走る。lint エラー等でブロックされたら：
1. エラーを特定（backend=Rubocop / frontend=ESLint/Prettier / type-check）。
2. 修正: `cd api && bundle exec rubocop -a {files}` または `cd web && yarn lint --fix {files}`（lint-staged が自動修正したファイルも確認）。
3. 修正ファイルを `git add` し直して**再コミット**（`--no-verify` で回避しない）。
4. 解決不能なら state-machine 停止条件#7 として状態保存し報告。

## 5. アーカイブ（workflow JSON 更新・スキーマ準拠）
`workflow-{id}.json` を Edit（workflow-schema 準拠）: `completed_cycles` に今サイクル追記（`cycle_number`, `title`, `commit`(SHA), `test_file_path`, `implementation_files`）、`current_cycle` +1、`updated_at` 更新、`status` は `in_progress`（全完了時は tdd 側 Phase6 で `done`）。

## 6. current-cycle.json 削除 + 不在確認（必須）
```bash
rm .claude/tdd-workflow/current-cycle.json
```
削除後、Read を試みて**不在（エラー）を確認**。残っていたら再削除。（次サイクル Red 入口が不在を前提とするため。）

## 7. 検証（必須・state-machine と対応）
`git log -1 --format="%H"` 非空 / `completed_cycles` 末尾 `commit` == SHA・`current_cycle` == 旧+1 / `current-cycle.json` 不在。いずれか失敗なら状態保存し中断、再実行を案内。

## 8. サマリ（簡潔）
SHA / コミットメッセージ / コミットしたファイル / 進捗 `{current_cycle-1}/{total_cycles}`。
最終サイクルなら「push すれば CI が該当パスのテスト・lint を実行」と案内。→ サイクル境界の挙動は tdd（run_mode）に従う。
