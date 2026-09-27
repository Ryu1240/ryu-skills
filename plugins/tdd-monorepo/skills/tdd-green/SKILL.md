---
name: tdd-green
description: Green phase - Minimal implementation in retail-hub monorepo (Rails or Vue/TS, per workflow ecosystem) to pass the failing test
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
  - input: /tdd-green tdd-20260613-101500
    description: Execute Green phase for the current cycle
---

TDD の Green フェーズ。今サイクルの失敗テストを通す**最小限の実装**を行う。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/project-settings.md`（**不変条件**・2エコシステム）/ `workflow-schema.md` / `state-machine.md`

> 原則: ✅テストを通す最小実装 ❌先回り実装 ❌リファクタ（次フェーズ）❌新規テスト追加。

## 入口ゲート
`current-cycle.json` を Read。`phase=="red"`、`ecosystem` 取得、`test_details.error_type` 非空。違反なら `/tdd-red {id}` 案内し中断。

## 1. 失敗の特定
`current-cycle.json` の `ecosystem` / `error_type` / `test_file_path`（Read）から、不足実装を特定（backend: route/controller/model/column/service。frontend: component/composable/store/util/型/export）。

## 2. 実装（ecosystem × 最小）

### backend（Rails）— 必須パターン
- **action_args** でパラメータ受け（`def index(page: 1, per_page: 20)`）。**tenant スコープ**（`current_client.leads`）。
- 個別 `rescue` を書かず親コントローラのエラーハンドリングに委譲。Resource/Serializer パターンに沿う。
- **API を変更したら OpenAPI を更新**: 実装に合わせて OpenAPI 定義を編集する。実装していないものは先行定義しない（最小実装）。

### frontend（Vue/TS）
- **Composition API + `<script setup>`**。型は明示（`defineProps<...>()`/`defineEmits<...>()`）。composable は `use*`・reactive な返り値。store は `defineStore`。
- API 連携なら対応する **MSW handler**（`web/src/testUtils/mocks/handlers/...`）の正常系を用意。テスト側は異常系を `server.use(...)` で上書き。
- 実装していない分岐・props・状態は先行定義しない（最小実装）。

## 3. テスト pass 確認
- **backend**: `cd api && bundle exec rspec {spec_path}`（または `docker compose exec api bundle exec rspec ...`）
- **frontend**: `cd web && yarn test {spec_path}`（または `npx vitest run {spec_path}`）

全件 pass を確認。典型的失敗と対処: backend=tenant scope 漏れ（件数不一致）/ OpenAPI schema 不一致 / action_args の不足 / factory 未登録。frontend=role/要素が見つからない / 値の不一致 / MSW handler 未登録 / Pinia 未初期化。
最大3回までリトライ。超えたら state-machine 停止条件#6 として報告。

## 4. 状態更新
`current-cycle.json` を Edit: `phase:"green"`, `test_details`(passed/total/failed:0), `implementation_files`(非空。backend は OpenAPI 生成物があれば含める), `retry_count`。
**自己検証**: `phase=="green"` かつ `implementation_files` 非空を Read で確認。

## 5. サマリ（簡潔）
ecosystem / 実装した対象（backend: route/controller/service。frontend: component/composable/store）/ OpenAPI・MSW handler の有無 / 全 pass（リトライ回数）/ 次は Refactor。→ 自動遷移。

## 注意
- **型/契約を握りつぶさない**（frontend: `any`/`@ts-ignore` で通さない。backend: schema に嘘をつかない）。
- テストが要求する最小分だけ追加する（i18n キー・ルーティング・handler 等）。
