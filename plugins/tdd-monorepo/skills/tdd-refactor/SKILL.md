---
name: tdd-refactor
description: Refactor phase - Improve retail-hub monorepo code quality (Rails N+1/dependent/service OR Vue composable/component split, per ecosystem) while keeping tests green
argument-hint: <workflow_id>
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(bundle:*)
  - Bash(docker:*)
  - Bash(yarn:*)
  - Bash(npx:*)
  - Bash(npm:*)
  - Grep
  - Glob
  - Bash(date:*)
examples:
  - input: /tdd-refactor tdd-20260613-101500
    description: Execute Refactor phase for the current cycle
---

TDD の Refactor フェーズ。**動作を変えずに**コード品質を改善し、テストが引き続き pass することを確認する。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/project-settings.md`（lint・2エコシステム）/ `workflow-schema.md` / `state-machine.md`

> 原則: ✅内部改善 ❌新機能 ❌動作変更 ❌**新規テスト追加**（次サイクルの Red で）。

## 入口ゲート
`current-cycle.json` を Read。`phase=="green"`、`ecosystem` 取得、`implementation_files` 非空、`updated_at` 非空。違反なら `/tdd-green {id}` 案内し中断。

## 1. 対象読み込み
`implementation_files` と `test_file_path` を Read。

## 2. 改善（ecosystem × 該当時のみ）

### backend（Rails）
- **N+1 対策（必須）**: テスト実行時の **Bullet 警告**を確認 → `.includes(:assoc, ...)` を追加。不要な eager loading は削除。最終的に Bullet 警告ゼロ。
- **Association の `dependent` オプション**: `has_many`/`has_one` に未設定があれば、ビジネスロジックに応じて設定（`:destroy` / `:restrict_with_error` / `:nullify`）。不明なら設定せず停止条件#2（設計判断）として報告。
- **サービス抽出**: action が20行超 / 複数モデル操作 / トランザクション / 外部API なら `api/app/services/{resource}/{action}_service.rb`（stateless・`call`）へ抽出。単純CRUDは抽出しない。
- **命名改善**。**Rubocop**: `cd api && bundle exec rubocop -a {files}`。

### frontend（Vue/TS）
- **composable 抽出**: component 内の肥大化した状態ロジック / 重複ロジックを `use*` composable に抽出。
- **コンポーネント分割**: 責務過多（表示 + 取得 + 変換の同居）を presentational / container に分割。
- **再レンダリング衛生**: 不要な `watch` を `computed` に、重い算出はメモ化、`reactive` の過剰使用を見直し。
- **prop drilling 解消**: 深いバケツリレーを provide/inject または Pinia store に。
- **命名改善**。**ESLint**: `cd web && yarn lint --fix {files}`。

## 3. テスト維持確認
- **backend**: `cd api && bundle exec rspec {spec_path}`（Bullet 警告なしも確認）
- **frontend**: `cd web && yarn test {spec_path}`（必要なら `yarn typecheck`）

全件 pass を確認。失敗したら includes/dependent/抽出シグネチャ/import/命名の参照ミスを修正、または `[r]修正/[u]ロールバック/[s]停止`。

## 4. 状態更新
`current-cycle.json` を Edit: `phase:"refactor"`, `refactor_details`（backend: n1_fixes/dependent_options/service_extractions/naming/linter。frontend: composable_extractions/component_splits/rerender/naming/linter。空オブジェクト不可。何もなければ `{"note":"no refactor needed"}`）, `updated_at`。
**自己検証**: `phase=="refactor"` かつ `refactor_details` 非空を Read で確認。

## 5. サマリ（簡潔）
ecosystem / 実施した改善 / 全件 pass / 次は Evac(review)→Commit。→ 自動遷移（承認ゲート②は tdd 側）。
