---
name: tdd-green
description: Green phase - Minimal implementation in storefront (Vue 3 / TypeScript) to pass the failing test
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
  - input: /tdd-green tdd-20260613-101500
    description: Execute Green phase for the current cycle
---

TDD の Green フェーズ。今サイクルの失敗テストを通す**最小限の実装**を行う。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/project-settings.md`（**不変条件**）/ `workflow-schema.md` / `state-machine.md`

> 原則: ✅テストを通す最小実装 ❌先回り実装 ❌リファクタ（次フェーズ）❌新規テスト追加。

## 入口ゲート
`current-cycle.json` を Read。`phase=="red"`、`test_details.error_type` 非空。違反なら `/tdd-red {id}` 案内し中断。

## 1. 失敗の特定
`current-cycle.json` の `error_type` と `test_file_path`（Read）から、不足実装（component/composable/store/util/型/export）を特定。

## 2. 実装（最小）

### Vue / TS — 必須パターン
- **Composition API + `<script setup>`** を既存慣習に合わせて使用。型は明示（`defineProps<...>()` / `defineEmits<...>()`）。
- **composable** は `use*` 命名・純粋なロジック（reactive な返り値）。副作用は最小限。
- **store（Pinia）** は `defineStore`。state/getter/action を最小限で。
- **API 連携**: 実装は API クライアント経由。テストを通すための正常系 **MSW handler**（`src/testUtils/mocks/handlers/...`）を用意（テスト側は異常系を `server.use(...)` で上書き）。
- 実装していない分岐・props・状態は**先行定義しない**（最小実装）。

## 3. テスト pass 確認
- `yarn test {spec_path}`（または `npx vitest run {spec_path}`）

全件 pass を確認。典型的失敗と対処: role/要素が見つからない（アクセシブルな markup になっているか）, 値の不一致（reactive の更新漏れ）, MSW handler 未登録（fetch 失敗）, Pinia 未初期化。
最大3回までリトライ。超えたら state-machine 停止条件#6 として報告。

## 4. 状態更新
`current-cycle.json` を Edit: `phase:"green"`, `test_details`(passed/total/failed:0), `implementation_files`(非空), `retry_count`。
**自己検証**: `phase=="green"` かつ `implementation_files` 非空を Read で確認。

## 5. サマリ（簡潔）
実装した component/composable/store/util / MSW handler の有無 / 全 pass（リトライ回数）/ 次は Refactor。→ 自動遷移。

## 注意
- **型を握りつぶさない**: `any` や `@ts-ignore` で通さない。型エラーは実装で解消（必要なら `yarn typecheck` で確認）。
- i18n キーやルーティング定義など、テストが要求する最小分だけ追加する。
