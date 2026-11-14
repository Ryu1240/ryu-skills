---
name: tdd-optimize
description: TDD 完了後の RSpec（backend）/ Vitest（frontend）テストを、独立性を保ったまま最適化する（リクエスト・render の統合、expected_body 化、it.each パラメータ化など）。編集は承認後のみ。/tdd から呼ばれるほか、テストファイルを指定して単独でも使える。
argument-hint: <workflow_id_or_test_file_path> [test_file_path]
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
  - Bash(git:*)
  - Grep
  - Glob
examples:
  - input: /tdd-optimize tdd-20260613-101500
    description: Optimize all tests for the workflow
  - input: /tdd-optimize api/spec/requests/api_user_leads_index_spec.rb
    description: Standalone mode - optimize a single backend spec file
  - input: /tdd-optimize web/src/components/LeadList.spec.ts
    description: Standalone mode - optimize a single frontend spec file
---

TDD 完了後の retail-hub 向けテスト最適化。テストの独立性を保ったまま、重複・冗長・類似テストを集約し、実行速度と可読性を上げる。

> このスキルは承認後にファイルを編集する（`agent: Explore` を付けない — Explore は Write/Edit を持たず、承認後の適用が空振りする）。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/project-settings.md`（テストコマンド・2エコシステム）/ `state-machine.md`

## モード判定 / ecosystem 判定
- `$0` が `tdd-` → ワークフローモード（`ecosystem` と `completed_cycles` から `test_files` 収集。`$1` でファイル限定）。
- `$0` がファイルパス → スタンドアロン（`test_files=[$0]`、`workflow_id="standalone-{date}"`）。パスから ecosystem を判定（`_spec.rb`=backend / `.spec.ts`=frontend）。
- ワークフローモードの入口ゲート: `current-cycle.json` が不在（サイクル進行中でない）かつ `coverage_review` が記録済みであること。違反なら中断。

## SP1: Assessment（必要性判断）
各テストファイルを Read し計測（Grep）:
- backend: リクエスト数（`get|post|put|patch|delete '/`）、`it` 数、`create(`/`create_list`、個別 `expect(...).to eq` の連続。
- frontend: `it(` 数、`render(` 数、`server.use(` の重複、個別 `expect(...).toBe/toEqual` の連続、同一 setup 重複。
推奨基準: テスト数が多い（≥15）かつ最適化機会が2つ以上、または明らかな重複。小規模はスキップ。

## SP2: Analysis（集約候補・ecosystem 別）

### backend
- リクエスト統合: 同一エンドポイント・同一セットアップの重複リクエストを1回に（独立性を壊さない範囲で。正常系/異常系混在は不可）。
- expected_body 化: 3つ以上の個別 `expect(json[...]).to eq` → `expect(response.parsed_body).to match(expected_body)`。
- create_list 集約: 同種 `create(:x)` の反復 → `create_list(:x, n)`。

### frontend
- render 統合: 同一コンポーネント・同一 props/setup の重複 render を1回に（独立性を壊さない範囲で）。
- `it.each` パラメータ化: 入力だけ違う類似 `it` を集約。
- 共通 setup の巻き上げ: 重複 factory/mount を `beforeEach`/ヘルパへ。MSW handler の重複解消（異常系上書きは各テストに残す）。

各候補の独立性を確認（factory は毎回新規、backend=tenant 文脈を共有しない、frontend=Pinia/MSW リセット、グローバル状態を変更しない）。順序依存があるものは集約不可。

## SP3: Planning（承認・必須）
最適化ステップ（対象・変更・削減見込み）とリスクを提示。
ユーザー承認まで SP4 を開始しない・ファイル変更しない: `[Enter/y] 全実行 / [e] 番号指定 / [n] キャンセル`。

## SP4: Execution（適用＋独立性検証）
1. ベースライン（全 pass 必須。失敗なら中断）:
   - backend: `cd api && bundle exec rspec {paths}` / frontend: `cd web && yarn test {paths}`（`vitest run`）
   実行時間・件数を記録。
2. 各ステップを Edit で適用。
3. 再実行（全 pass）＋ 独立性検証:
   - backend: 個別実行 `bundle exec rspec {path}:{line}` ＋ ランダム順序 `bundle exec rspec {path} --order random`。
   - frontend: 単一実行 `yarn test {path}` ＋ ランダム順序 `npx vitest run {path} --sequence.shuffle`。
   - 失敗＝独立性破壊 → そのステップを Edit でロールバック。

## SP5: Verification（メトリクス・レポート）
Before/After（件数・リクエスト/render 数・実行時間）を比較。
`.claude/tdd-workflow/optimization-report-{workflow_id}-{date}.md` に Write。最終サマリを簡潔表示。

## 原則
- 独立性を最優先する（個別/単一実行・ランダム順序で pass。tenant 文脈 / Pinia / MSW / グローバル状態の共有変更禁止。破壊したらロールバック）。
- 統合は順序に依存しないものに限る（正常系/異常系混在は統合しない）。
- 承認必須（SP3 で承認を得てから SP4）。
