---
name: tdd-red
description: Red phase - Write ONE failing test for retail-hub monorepo (RSpec backend or Vitest frontend, per workflow ecosystem), confirm it fails as expected
argument-hint: <workflow_id> [test_file_path]
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
  - TaskGet
  - Bash(date:*)
examples:
  - input: /tdd-red tdd-20260613-101500
    description: Execute Red phase for the current cycle
---

TDD の Red フェーズ。**今サイクルのテストを1つだけ**（1つの `it` / 1ケース）追加し、期待通り失敗することを確認する。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/project-settings.md`（2エコシステム・パス・**不変条件**・テストコマンド）
- `.claude/skills/_shared-tdd/workflow-schema.md` / `state-machine.md`

> 🔴 **一度に1テストケースのみ**。複数追加は不変条件違反。

## 入口ゲート（cycle 2 以降）
`current-cycle.json` が**存在しないこと**を Read で確認（存在＝前サイクル未完了 → `/tdd-commit {id}` 案内し中断）。`completed_cycles` 長 == `current_cycle - 1` を確認。

## 1. コンテキスト
`workflow-{id}.json` を Read（`ecosystem`, `target_files`, `patterns`, `current_cycle`, `user_instructions`）。`todo_task_id` で TaskGet し `cycle_plan` の該当エントリ（`title`, `kind`）を特定。**`ecosystem` で以降を分岐する。**

## 2. テストファイル決定
`$1` 指定があればそれ。無ければ `ecosystem` と既存構造から決定（既存ファイルへの追記を優先、無ければ新規）。
- **backend**: `api/spec/{models|requests|services|resources|workers|policies|...}/`。request spec は既存の命名構造（**Flat** `api_user_leads_index_spec.rb` か **Nested** `api/user/leads/index_spec.rb`）の**多数派に合わせる**（Glob で確認）。
- **frontend**: 実装と同ディレクトリの `web/src/**/*.spec.ts`（`Foo.spec.ts` / `useFoo.spec.ts`）。

## 2-b. 既存テストへの影響確認（critical）
変更が既存 spec を壊さないか確認。
- **backend**: 特に **enum 追加**は要注意（`define_enum_for` は値の完全一致チェック）。enum / association / validation を変える場合は該当既存テストを Grep し、必要なら本サイクルで合わせて更新（意味は変えない）。
- **frontend**: component の props/emits、composable の返り値、store の state/getter 名を変える場合、参照する既存テストを Grep（`render(`, `emitted(`, 返り値の分割代入名）し、必要なら合わせて更新。

## 3. テスト追加（ecosystem × spec種別で分岐）
既存の近い spec を Read し慣習に揃える。

### backend / model spec
```ruby
RSpec.describe Lead do
  before { ApplicationRecord.client = create(:client) }   # multi-tenant 文脈
  it { is_expected.to validate_presence_of(:name) }       # implicit subject + shoulda
end
```

### backend / request spec
```ruby
RSpec.describe 'GET /api/user/leads' do
  include_context 'with current user'        # 認証 + tenant（spec/support）
  it 'returns 200 with schema' do
    get '/api/user/leads', headers: headers
    assert_response_schema_confirm(200)      # OpenAPI 契約検証（Committee）
  end
end
```
- **正常系・権限拒否・他テナントデータ除外**は別サイクルに分ける。factory は `create(:lead, client: current_client)`。

### backend / service spec
WebMock で外部（外部 API/メール送信等）をモック、tenant 文脈を設定、pure logic を1ケース。

### frontend / composable・component・store spec
```ts
import { render, screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'

describe('LeadList', () => {
  it('見出しと件数を表示する', () => {
    render(LeadList, { props: { leads: createLeads(2) } })
    expect(screen.getByRole('heading', { name: 'リード一覧' })).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
  })
})
```
- **role/アクセシブルネームで取得**（`getByRole` 優先）。操作は `userEvent`。API は MSW（`server.use(...)` で異常系上書き）。store は各テストで `setActivePinia(createPinia())`。

## 4. 失敗確認
- **backend**: `cd api && bundle exec rspec {spec_path}:{line}`（または `docker compose exec api bundle exec rspec ...`）
- **frontend**: `cd web && yarn test {spec_path}`（または `npx vitest run {spec_path}`）

期待される失敗: 未定義（route/const/method/module/export/component）, `expected 200 got 404/500` / `Unable to find role`, schema/値の不一致。
予期しない失敗（構文エラー・factory/import 誤り・tenant/Pinia/MSW 設定漏れ）はテスト側を修正して再実行。

## 5. 状態更新
`current-cycle.json` を workflow-schema 準拠で Write（`phase:"red"`, `ecosystem`, `test_file_path`, **`test_case_count`**（`test_file_path` 内のケース定義数。backend=RSpec の `it` / `specify` / `example`、frontend=Vitest の `it(` / `test(` / `it.each` / `test.each`。Evac(review) の基準値）, `test_details`(error_type/message), `created_at`/`updated_at`）。
**自己検証**: Read で `phase=="red"`・`updated_at` 更新を確認。

## 6. サマリ（簡潔）
ecosystem / テストファイル / 追加した1テスト / 期待通りの失敗 / 適用パターン / 次は Green。承認ゲート①は state-machine に従う（tdd 側が判断）。

## エラー
- テストファイル決定不能: `$1` 明示 or タスクに対象名（model/endpoint/component）追記を案内。
- factory 未定義: backend=`api/spec/factories/` / frontend=`web/src/testUtils/factory/` を確認し追加を促す。
- 独立性設定漏れで予期せぬ失敗 → backend=`ApplicationRecord.client`/`include_context`、frontend=MSW server / Pinia 初期化を確認。
