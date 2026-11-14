---
name: tdd-optimize
description: TDD 完了後の RSpec テストを、独立性を保ったまま最適化する（リクエスト統合・expected_body による一括比較・create_list 集約など）。編集は承認後のみ。/tdd から呼ばれるほか、spec ファイルを指定して単独でも使える。
argument-hint: <workflow_id_or_test_file_path> [test_file_path]
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
examples:
  - input: /tdd-optimize tdd-20260613-101500
    description: Optimize all tests for the workflow
  - input: /tdd-optimize spec/requests/api_user_leads_index_spec.rb
    description: Standalone mode - optimize a single spec file
---

TDD 完了後の sales-hub 向けテスト最適化。テストの独立性を保ったまま、重複リクエスト・冗長 assert・類似テストを集約し、実行速度と可読性を上げる。

> このスキルは承認後にファイルを編集する。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/project-settings.md`（テストコマンド）/ `state-machine.md`

## モード判定
- `$0` が `tdd-` → ワークフローモード（`completed_cycles` から `test_files` 収集。`$1` でファイル限定）。
- `$0` がファイルパス（`_spec.rb`）→ スタンドアロン（`test_files=[$0]`、`workflow_id="standalone-{date}"`）。
- ワークフローモードの入口ゲート: `current-cycle.json` が不在（サイクル進行中でない）かつ `coverage_review` が記録済みであること。違反なら中断。

## SP1: Assessment（必要性判断）
各テストファイルを Read し計測（Grep）:
- リクエスト数（`get|post|put|patch|delete '/`）、`it` 数、`create(` / `create_list` の使用、個別 `expect(...).to eq` の連続。
推奨基準: テスト数が多い（≥15）かつ最適化機会が2つ以上、または明らかな重複リクエスト。小規模はスキップ（サマリして終了）。

## SP2: Analysis（集約候補）
- リクエスト統合: 同一エンドポイント・同一セットアップへの重複リクエストを1回にまとめ、複数の観点を1つの `it` で検証（ただし独立性を壊さない範囲で。正常系/異常系をまたぐ統合は不可）。
- expected_body 化: 3つ以上の個別 `expect(json[...]).to eq` → `expect(response.parsed_body).to match(expected_body)` の一括比較。
- create_list 集約: 同種レコードの複数 `create(:x)` → `create_list(:x, n)`。
各候補の独立性を確認（factory は毎回新規、グローバル状態を変更しない、tenant 文脈を共有しない）。混在・順序依存があるものは集約不可。

## SP3: Planning（承認・必須）
最適化ステップ（対象・変更・削減見込み）とリスク（リクエスト統合による順序依存、expected_body の差分肥大）を提示。
ユーザー承認まで SP4 を開始しない・ファイル変更しない: `[Enter/y] 全実行 / [e] 番号指定 / [n] キャンセル`。

## SP4: Execution（適用＋独立性検証）
1. ベースライン: `bundle exec rspec {paths}`（全 pass 必須。失敗なら中断）。実行時間・件数を記録。
2. 各ステップを Edit で適用。
3. 再実行（全 pass）＋ 独立性検証:
   - 個別実行: `bundle exec rspec {path}:{line}`。
   - ランダム順序: `bundle exec rspec {path} --order random`（RSpec 標準）。
   - 失敗＝独立性破壊 → そのステップを Edit でロールバック。

## SP5: Verification（メトリクス・レポート）
Before/After（件数・リクエスト数・実行時間）を比較。
`.claude/tdd-workflow/optimization-report-{workflow_id}-{date}.md` に Write（メトリクス表・実行ステップ・独立性検証結果）。最終サマリを簡潔表示。

## 原則
- 独立性を最優先する（個別実行・`--order random` で pass。グローバル状態/tenant 文脈の共有変更禁止。破壊したらロールバック）。
- リクエスト統合は順序に依存しないものに限る（正常系/異常系混在は統合しない）。
- 承認必須（SP3 で承認を得てから SP4）。
