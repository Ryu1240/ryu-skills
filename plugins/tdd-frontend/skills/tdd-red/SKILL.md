---
name: tdd-red
description: Red phase - Write ONE failing test for storefront (Vue 3 / Vitest frontend), confirm it fails as expected
argument-hint: <workflow_id> [test_file_path]
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
examples:
  - input: /tdd-red tdd-20260613-101500
    description: Execute Red phase for the current cycle
---

TDD の Red フェーズ。**今サイクルのテストを1つだけ**（1つの `it` / 1ケース）追加し、期待通り失敗することを確認する。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/project-settings.md`（パス・**不変条件**・テストコマンド）
- `.claude/skills/_shared-tdd/workflow-schema.md` / `state-machine.md`

> 🔴 **一度に1テストケースのみ**。複数追加は不変条件違反。

## 入口ゲート（cycle 2 以降）
`current-cycle.json` が**存在しないこと**を Read で確認（存在＝前サイクル未完了 → `/tdd-commit {id}` 案内し中断）。`completed_cycles` 長 == `current_cycle - 1` を確認。

## 1. コンテキスト
`workflow-{id}.json` を Read（`target_files`, `patterns`, `current_cycle`, `user_instructions`）。`todo_task_id` で TaskGet し `cycle_plan` の該当エントリ（`title`, `kind`）を特定。

## 2. テストファイル決定
`$1` 指定があればそれ。無ければ既存構造から決定（実装と**同ディレクトリの `*.spec.ts`** を優先。既存ファイルへの追記を優先、無ければ新規）。
- `src/{components|composables|stores|utils|...}/` に実装があれば、その隣に `Foo.spec.ts` / `useFoo.spec.ts`。既存の近い spec を Glob で確認し慣習（describe の粒度・import エイリアス `@/`）に揃える。

## 2-b. 既存テストへの影響確認（critical）
変更が既存 spec を壊さないか確認。特に **公開インターフェイスの変更**は要注意：
- component の props/emits、composable の返り値、store の state/getter 名を変える場合、それを参照する既存テストを Grep（`render(`, `emitted(`, 返り値の分割代入名）し、必要なら本サイクルで**合わせて更新**（振る舞いの意味は変えない）。

## 3. テスト追加（spec種別で分岐）
既存の近い spec を Read し慣習に揃える。**storefront の必須パターンを守る**：

### composable spec
```ts
import { describe, it, expect } from 'vitest'
import { useLeadFilter } from './useLeadFilter'

describe('useLeadFilter', () => {
  describe('正常系', () => {
    it('在庫ありのみに絞り込む', () => {
      const { filtered, setStockOnly } = useLeadFilter(items)
      setStockOnly(true)
      expect(filtered.value).toHaveLength(3)
    })
  })
})
```

### component spec（Vue Testing Library）
```ts
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import LeadList from './LeadList.vue'

describe('LeadList', () => {
  it('見出しと件数を表示する', async () => {
    render(LeadList, { props: { leads: createLeads(2) } })
    expect(screen.getByRole('heading', { name: 'リード一覧' })).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
  })
})
```
- **role / アクセシブルネームで取得**（`getByRole` 優先。`data-testid` は最後の手段）。ユーザー操作は `userEvent`。
- **正常系・異常系（API エラー表示）・空状態**は別サイクルに分ける。

### store spec（Pinia）
```ts
import { setActivePinia, createPinia } from 'pinia'
beforeEach(() => setActivePinia(createPinia()))   // 各テストで新規＝独立性
```

### API 連携（MSW）
異常系は各テストで `server.use(handlers.leads.error())` のように上書き。共通の正常系 handler は `src/testUtils/mocks/handlers/` に置く。実通信はしない。

## 4. 失敗確認
- `yarn test {spec_path}`（または `npx vitest run {spec_path}`）

期待される失敗: 未定義（module/export/component）, `Unable to find role/element`, 値の不一致, MSW 未設定による fetch 失敗。
予期しない失敗（構文エラー・import パス誤り・Pinia 未初期化・MSW server 未起動）はテスト側を修正して再実行。

## 5. 状態更新
`current-cycle.json` を workflow-schema 準拠で Write（`phase:"red"`, `test_file_path`, `test_details`(error_type/message), `created_at`/`updated_at`）。
**自己検証**: Read で `phase=="red"`・`updated_at` 更新を確認。

## 6. サマリ（簡潔）
テストファイル / 追加した1テスト / 期待通りの失敗 / 適用パターン（role 取得・user-event・MSW・Pinia 独立性 等）/ 次は Green。承認ゲート①は state-machine に従う（tdd 側が判断）。

## エラー
- テストファイル決定不能: `$1` 明示 or タスクに対象名（component/composable 名）追記を案内。
- factory 未定義: `src/testUtils/factory/` を確認し factory 追加を促す。
- MSW handler 未登録で予期せぬ失敗 → `src/testUtils/mocks/handlers/` と server セットアップ（`setup`/`afterEach(resetHandlers)`）を確認。
