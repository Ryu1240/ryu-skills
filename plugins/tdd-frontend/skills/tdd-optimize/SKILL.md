---
name: tdd-optimize
description: TDD 完了後の Vitest テストを、独立性を保ったまま最適化する（render 統合・it.each 化・共通 setup の巻き上げ・MSW handler の重複解消など）。編集は承認後のみ。/tdd から呼ばれるほか、spec ファイルを指定して単独でも使える。
argument-hint: <workflow_id_or_test_file_path> [test_file_path]
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
  - input: /tdd-optimize tdd-20260613-101500
    description: Optimize all tests for the workflow
  - input: /tdd-optimize src/components/LeadList.spec.ts
    description: Standalone mode - optimize a single spec file
---

TDD 完了後の storefront 向けテスト最適化。テストの独立性を保ったまま、重複 render・冗長 assert・類似テストを集約し、実行速度と可読性を上げる。

> このスキルは承認後にファイルを編集する（`agent: Explore` を付けない — Explore は Write/Edit を持たず、承認後の適用が空振りする）。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/project-settings.md`（テストコマンド）/ `state-machine.md`

## モード判定
- `$0` が `tdd-` → ワークフローモード（`completed_cycles` から `test_files` 収集。`$1` でファイル限定）。
- `$0` がファイルパス（`.spec.ts`）→ スタンドアロン（`test_files=[$0]`、`workflow_id="standalone-{date}"`）。
- ワークフローモードの入口ゲート: `current-cycle.json` が不在（サイクル進行中でない）かつ `coverage_review` が記録済みであること。違反なら中断。

## SP1: Assessment（必要性判断）
各テストファイルを Read し計測（Grep）:
- `it(` 数、`render(` 呼び出し数、`server.use(` の重複、個別 `expect(...).toBe/toEqual` の連続、同一 setup の重複。
推奨基準: テスト数が多い（≥15）かつ最適化機会が2つ以上、または明らかな重複 render / setup。小規模はスキップ（サマリして終了）。

## SP2: Analysis（集約候補）
- render 統合: 同一コンポーネント・同一 props/setup への重複 render を1回にまとめ、複数の観点を1つの `it` で検証（ただし独立性を壊さない範囲で。正常系/異常系をまたぐ統合は不可）。
- `it.each` パラメータ化: 入力だけが違う類似 `it` を `it.each([...])` に集約。
- 共通 setup の巻き上げ: 各 `it` で重複する factory/mount を `beforeEach` や共通ヘルパへ（グローバル可変状態は持たせない）。
- MSW handler の重複解消: 同じ `server.use(...)` の反復を共通 handler に寄せる（異常系の上書きは各テストに残す）。
各候補の独立性を確認（factory は毎回新規、Pinia は各テスト新規、handler は `afterEach(resetHandlers)`、グローバル状態を共有しない）。順序依存があるものは集約不可。

## SP3: Planning（承認・必須）
最適化ステップ（対象・変更・削減見込み）とリスク（render 統合による観点の埋没、`it.each` の可読性低下）を提示。
ユーザー承認まで SP4 を開始しない・ファイル変更しない: `[Enter/y] 全実行 / [e] 番号指定 / [n] キャンセル`。

## SP4: Execution（適用＋独立性検証）
1. ベースライン: `yarn test {paths}`（`vitest run`。全 pass 必須。失敗なら中断）。実行時間・件数を記録。
2. 各ステップを Edit で適用。
3. 再実行（全 pass）＋ 独立性検証:
   - 単一ファイル実行: `yarn test {path}`。
   - ランダム順序: `npx vitest run {path} --sequence.shuffle`（Vitest の順序シャッフル）。
   - 失敗＝独立性破壊 → そのステップを Edit でロールバック。

## SP5: Verification（メトリクス・レポート）
Before/After（件数・render 数・実行時間）を比較。
`.claude/tdd-workflow/optimization-report-{workflow_id}-{date}.md` に Write（メトリクス表・実行ステップ・独立性検証結果）。最終サマリを簡潔表示。

## 原則
- 独立性を最優先する（単一実行・`--sequence.shuffle` で pass。Pinia/MSW/グローバル状態の共有変更禁止。破壊したらロールバック）。
- render 統合は順序に依存しないものに限る（正常系/異常系混在は統合しない）。
- 承認必須（SP3 で承認を得てから SP4）。
