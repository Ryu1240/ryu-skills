---
name: tdd-green
description: TDD の Green フェーズ。Red で追加した失敗テストを通す最小限の Rails 実装を書く。通常は /tdd から呼ばれる。
argument-hint: <workflow_id>
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(bundle:*)
  - Bash(docker:*)
  - Bash(git:*)
  - Grep
  - Glob
  - Bash(date:*)
examples:
  - input: /tdd-green tdd-20260613-101500
    description: Execute Green phase for the current cycle
---

TDD の Green フェーズ。今サイクルのテストを通す最小限の実装のみを追加する。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/project-settings.md`（不変条件）/ `workflow-schema.md` / `state-machine.md`

> 最小実装（不変条件）: テストを通す最小限のみ。N+1対策・共通化・抽出・複雑なロジックは Refactor で。

## 入口ゲート
`current-cycle.json` を Read。`phase=="red"` かつ `updated_at` 非空。違反なら `/tdd-red {id}` 案内し中断。

## 1. 要件抽出
`current-cycle.json` の `error_type` と `test_file_path`（Read）から、不足実装（route/controller/model/column/service）を特定。

## 2. 実装（最小）

### Rails — 必須パターン
- multi-tenant scope: `current_client.leads` のようにテナント経由でアクセス（`Lead.all` 直叩き禁止）。
- action_args: `def index(page: 1, per_page: 20)` でパラメータを引数受け（params 直接参照しない）。
- エラーは親コントローラに委譲: 各 action で個別 `rescue` を書かない。
- Resource/Serializer（Alba 等、既存パターン踏襲）でレスポンス整形。
- route 追加は既存 `config/routes.rb` の namespace 構造に合わせる。
- マイグレーションが要るなら `db/migrate/` 追加 → test DB 反映（`bundle exec rake parallel:prepare` / `db:migrate RAILS_ENV=test`）。
- API を変更したら OpenAPI を更新: `openapi/openapi.yaml` を実装に合わせて編集する。実装していないものは先行定義しない（最小実装）。

## 3. テスト成功確認（最大3回リトライ）
- `bundle exec rspec {spec_path}`（または `docker compose exec app bundle exec rspec ...`）

典型的失敗と対処: tenant scope 漏れ（件数不一致）, OpenAPI schema 不一致（Resource 属性とズレ）, action_args の不足（missing keyword）, factory 未登録。
3回で通らなければ state-machine 停止条件 #6 → 状態保存し `[r]再実行 / [d]デバッグ / [s]一時停止` を提示して停止。

## 4. 状態更新
`current-cycle.json` を Edit: `phase:"green"`, `test_details`(passed/total/failed:0), `implementation_files`(非空), `retry_count`。

## 5. サマリ（簡潔）
実装した route/controller/service / マイグレーション・OpenAPI 更新の有無 / 全 pass（リトライ回数）/ 次は Refactor。→ 自動遷移。

## 注意（sales-hub 固有・落とすと壊す）
- i18n キーは `config/locales/ja.yml` を直接編集して追加する。
- `current-cycle.json` 不在: `/tdd-red {id}` 案内し中断。
