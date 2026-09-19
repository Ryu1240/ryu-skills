---
name: tdd-refactor
description: Refactor phase - Improve storefront code quality (composable extraction / component split / re-render hygiene for Vue) while keeping tests green
argument-hint: <workflow_id>
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
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
- `.claude/skills/_shared-tdd/project-settings.md`（lint）/ `workflow-schema.md` / `state-machine.md`

> 原則: ✅内部改善 ❌新機能 ❌動作変更 ❌**新規テスト追加**（次サイクルの Red で）。

## 入口ゲート
`current-cycle.json` を Read。`phase=="green"`、`implementation_files` 非空、`updated_at` 非空。違反なら `/tdd-green {id}` 案内し中断。

## 1. 対象読み込み
`implementation_files` と `test_file_path` を Read。

## 2. 改善（該当時のみ）

### Vue / TS
- **composable 抽出**: component 内に肥大化したロジック（複数の `ref`/`computed`/`watch` が絡む状態遷移、複数コンポーネントで重複する処理）を `use*` composable に抽出。単純な表示ロジックは抽出しない。
- **コンポーネント分割**: 責務過多（表示 + データ取得 + 変換が同居）な component を presentational / container に分割。テンプレートの巨大な条件分岐を子コンポーネントへ。
- **再レンダリング衛生**: 不要な `watch` を `computed` に、重い算出はメモ化、大きなリストは `key` の適正化。`reactive` の過剰使用を `ref`/`shallowRef` に見直し。
- **prop drilling 解消**: 深い props バケツリレーを provide/inject または Pinia store に置換（範囲を広げすぎない）。
- **命名改善**（1文字変数・`data`/`item`/`tmp` 等の曖昧名を用途名に）。
- **ESLint**: `yarn lint --fix {files}`（自動修正。手動対応が要るルールは必要に応じて）。

## 3. テスト維持確認
- `yarn test {spec_path}`（対象 spec が引き続き全 pass）
- 必要なら `yarn typecheck` で型崩れがないことも確認。

全件 pass を確認。失敗したら抽出したシグネチャ/import パス/命名の参照ミスを修正、または `[r]修正/[u]ロールバック/[s]停止`。

## 4. 状態更新
`current-cycle.json` を Edit: `phase:"refactor"`, `refactor_details`（composable_extractions / component_splits / rerender / naming / linter。空オブジェクト不可。何もなければ `{"note":"no refactor needed"}`）, `updated_at`。
**自己検証**: `phase=="refactor"` かつ `refactor_details` 非空を Read で確認。

## 5. サマリ（簡潔）
実施した改善（composable/分割/再レンダリング/命名/lint 件数）/ 全件 pass / 次は Evac(review)→Commit。→ 自動遷移（承認ゲート②は tdd 側）。
