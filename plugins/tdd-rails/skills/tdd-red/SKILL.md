---
name: tdd-red
description: TDD の Red フェーズ。失敗する RSpec のテスト（`it` 1つ）を1つだけ追加し、期待どおりに失敗することを確認する。通常は /tdd から呼ばれる。単独では「失敗するテストを1つ書いて」と頼まれたときに使う。
argument-hint: <workflow_id> [test_file_path]
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(bundle:*)
  - Bash(docker:*)
  - Bash(git:*)
  - Grep
  - Glob
  - TaskGet
  - Bash(date:*)
examples:
  - input: /tdd-red tdd-20260613-101500
    description: Execute Red phase for the current cycle
---

TDD の Red フェーズ。今サイクルのテストを1つだけ（1つの `it` / 1ケース）追加し、期待通り失敗することを確認する。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/project-settings.md`（パス・不変条件・テストコマンド）
- `.claude/skills/_shared-tdd/workflow-schema.md` / `state-machine.md`

> 🔴 一度に1テストケースのみ。複数追加は不変条件違反。

## 入口ゲート（cycle 2 以降）
`current-cycle.json` が存在しないことを Read で確認（存在＝前サイクル未完了 → `/tdd-commit {id}` 案内し中断）。`completed_cycles` 長 == `current_cycle - 1` を確認。

## 1. コンテキスト
`workflow-{id}.json` を Read（`target_files`, `patterns`, `current_cycle`, `user_instructions`）。`todo_task_id` で TaskGet し `cycle_plan` の該当エントリ（`title`, `kind`）を特定。

## 2. テストファイル決定
`$1` 指定があればそれ。無ければ既存構造から決定（既存ファイルへの追記を優先、無ければ新規）。
- `spec/{models|requests|services|resources|workers|policies|...}/`。request spec は既存の命名構造（Flat `api_user_leads_index_spec.rb` か Nested `api/user/leads/index_spec.rb`）の多数派に合わせる（Glob で確認）。

## 2-b. 既存テストへの影響確認
変更が既存 spec を壊さないか確認。特に enum 追加は要注意：
```ruby
# define_enum_for は値の完全一致チェック。enum に値を足すと、
# 値を列挙している既存テストが「増えた」ことで失敗する。
it { is_expected.to define_enum_for(:action_type).with_values(...) }
```
→ enum / association / validation を変える場合は `define_enum_for` / `have_many` / `validate_` の既存テストを Grep し、必要なら本サイクルで合わせて更新（振る舞いの意味は変えない）。

## 3. テスト追加（spec種別で分岐）
既存の近い spec を Read し慣習に揃える。sales-hub の必須パターンを守る：

### model spec
```ruby
RSpec.describe Lead do
  before { ApplicationRecord.client = create(:client) }   # multi-tenant 文脈
  it { is_expected.to validate_presence_of(:name) }       # implicit subject + shoulda
end
```

### request spec
```ruby
RSpec.describe 'GET /api/user/leads' do
  include_context 'with current user'        # 認証 + tenant（spec/support）
  it 'returns 200 with schema' do
    get '/api/user/leads', headers: headers
    assert_response_schema_confirm(200)      # OpenAPI 契約検証（Committee）
  end
end
```
- 必要なら `openapi/openapi.yaml` から対象エンドポイントの schema を確認。
- 正常系・権限拒否（Pundit）・他テナントデータ除外は別サイクルに分ける。factory は `create(:lead, client: current_client)`。

### service spec
WebMock で外部（外部 CRM API/メール送信 API 等）をモック、tenant 文脈を設定、pure logic を1ケース。

## 4. 失敗確認
- `bundle exec rspec {spec_path}:{line}`（または `docker compose exec app bundle exec rspec ...`）

期待される失敗: 未定義（route/const/method）, `expected 200 got 404/500`, schema 不一致, assertion 失敗。
予期しない失敗（構文エラー・factory 未定義・tenant 設定漏れ・collection error）はテスト側を修正して再実行。

## 5. 状態更新
`current-cycle.json` を workflow-schema 準拠で Write（`phase:"red"`, `test_file_path`, `test_case_count`（`test_file_path` 内の `it ` / `it(` / `specify` / `example` / `scenario` の定義数。`it_behaves_like` / `include_examples` は 1 と数える。Evac(review) の基準値）, `test_details`(error_type/message), `created_at`/`updated_at`）。

## 6. サマリ（簡潔）
テストファイル / 追加した1テスト / 期待通りの失敗 / 適用パターン（implicit subject・tenant scope・OpenAPI契約 等）/ 次は Green。承認ゲート①は state-machine に従う（tdd 側が判断）。

## エラー
- テストファイル決定不能: `$1` 明示 or タスクに対象名（model/endpoint）追記を案内。
- factory 未定義: `spec/factories/` を確認し factory 追加を促す。
- multi-tenant 設定漏れで予期せぬ失敗 → `before` の `ApplicationRecord.client` / `include_context 'with current user'` を確認。
