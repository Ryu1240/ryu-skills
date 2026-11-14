---
name: tdd-optimize
description: TDD 完了後のテストを、独立性を保ったまま最適化する（セットアップの巻き上げ・パラメータ化・アサーション集約など。あらゆる言語向け）。編集は承認後のみ。/tdd から呼ばれるほか、テストファイルを指定して単独でも使える。
argument-hint: <workflow_id_or_test_file_path> [test_file_path]
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
examples:
  - input: /tdd-optimize tdd-20260613-101500
    description: Optimize all tests for the workflow
  - input: /tdd-optimize tests/orders/test_checkout.py
    description: Standalone mode - optimize a single test file
---

TDD 完了後のテスト最適化。テストの独立性を保ったまま、重複セットアップ・冗長アサーション・類似ケースを集約し、実行速度と可読性を上げる。

> このスキルは承認後にファイルを編集する（`agent: Explore` を付けない — Explore は Write/Edit を持たず、承認後の適用が空振りする）。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/project-settings.md`（テスト実行コマンド・独立性の担保方法・言語固有の慣習）/ `state-machine.md`

## モード判定
- `$0` が `tdd-` → ワークフローモード（`completed_cycles` から `test_files` 収集。`$1` でファイル限定）。
- `$0` がファイルパス → スタンドアロン（`test_files=[$0]`、`workflow_id="standalone-{date}"`）。
- ワークフローモードの入口ゲート: `current-cycle.json` が不在（サイクル進行中でない）かつ `coverage_review` が記録済みであること。違反なら中断。

## SP1: Assessment（必要性判断）
各テストファイルを Read し計測（Grep）。`patterns.test_case_style` の記述形でケースを数える:
- ケース数、重複するセットアップ（同一の準備コードの反復）、重複する外部呼び出し/リクエスト、個別アサーションの連続、同一データを作る反復。

推奨基準: ケース数が多い（≥15）かつ最適化機会が2つ以上、または明らかな重複セットアップ。小規模はスキップ（サマリして終了）。

## SP2: Analysis（集約候補・言語非依存）
- セットアップの巻き上げ: 各ケースで重複する準備を、独立性を壊さない範囲で共通のセットアップ（各ケース実行前に毎回走る仕組み）やヘルパ関数へ。ケース間で共有される可変状態を作らない。
- パラメータ化: 入力と期待値だけが違う類似ケースを、テーブル駆動/パラメータ化テストに集約（言語の標準的な仕組みを project-settings の慣習から選ぶ）。
- アサーションの集約: 3つ以上の個別フィールド検証を、期待値オブジェクト/構造体との一括比較に。ただし失敗時の可読性が落ちすぎない範囲で。
- 重複する外部呼び出しの統合: 同一の準備に対する同一の呼び出しが複数ケースに散っている場合、1ケースで複数観点を検証する形に統合（正常系と異常系をまたぐ統合は不可）。
- データ生成の集約: 同種データの反復生成を、まとめて生成する仕組みへ。

各候補について独立性を確認する（project-settings の「独立性の担保方法」に照らす）。順序依存・状態共有が生まれるものは集約不可と判定する。

## SP3: Planning（承認・必須）
最適化ステップ（対象・変更内容・削減見込み）とリスク（失敗時の原因特定が難しくなる、パラメータ化による可読性低下）を提示。
ユーザー承認まで SP4 を開始しない・ファイルを変更しない: `[Enter/y] 全実行 / [e] 番号指定 / [n] キャンセル`。

## SP4: Execution（適用＋独立性検証）
1. ベースライン: project-settings の `{{TEST_ONE_FILE}}`（複数なら `{{TEST_ALL}}`）を実行。全 pass 必須（失敗なら中断）。実行時間・ケース数を記録。
2. 各ステップを Edit で適用。
3. 再実行（全 pass）＋ 独立性検証:
   - 単一ケース実行: `{{TEST_ONE_CASE}}` で代表ケースを個別に実行して pass することを確認（`{case}` / `{line}` は `completed_cycles` の `test_case_id` から取る）。
   - ランダム順序実行: `{{TEST_RANDOM}}` を実行。「未対応」と記録されている場合はスキップし、その旨をレポートに明記する（検証できていないことを隠さない）。
   - 失敗＝独立性破壊 → そのステップを Edit でロールバックし、次のステップへ。

## SP5: Verification（メトリクス・レポート）
Before/After（ケース数・重複呼び出し数・実行時間）を比較。
`.claude/tdd-workflow/optimization-report-{workflow_id}-{date}.md` に Write（メトリクス表・実行ステップ・独立性検証結果・未実施の検証）。最終サマリを簡潔表示。

## 原則
- 独立性を最優先する（単一ケース実行とランダム順序で pass。共有可変状態を作らない。破壊したらロールバック）。
- 統合は順序に依存しないものに限る（正常系/異常系混在は統合しない）。
- 承認必須（SP3 で承認を得てから SP4）。
- 検証できなかったことは報告する（ランダム順序が未対応の言語では独立性の担保が弱い旨を明記）。
