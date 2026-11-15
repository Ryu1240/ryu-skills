---
name: tdd-optimize
description: TDD 完了後の Vitest + React Testing Library のテストを、独立性を保ったまま最適化する（`it.each` 化・render ヘルパへの集約・セットアップの巻き上げ・MSW handler の重複解消・DOM 不要なテストの node 環境化など）。編集は承認後のみ。/tdd から呼ばれるほか、テストファイルを指定して単独でも使える。
argument-hint: <workflow_id_or_test_file_path> [test_file_path]
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(yarn:*)
  - Bash(npx:*)
  - Bash(npm:*)
  - Bash(pnpm:*)
  - Grep
  - Glob
examples:
  - input: /tdd-optimize tdd-20260613-101500
    description: Optimize all tests for the workflow
  - input: /tdd-optimize features/reservations/components/ReservationForm.test.tsx
    description: Standalone mode - optimize a single test file
---

TDD 完了後の booking-web 向けテスト最適化。テストの独立性を保ったまま、重複セットアップ・冗長アサーション・類似ケースを集約し、実行速度と可読性を上げる。

> このスキルは承認後にファイルを編集する（`agent: Explore` を付けない — Explore は Write/Edit を持たず、承認後の適用が空振りする）。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/project-settings.md`（テストコマンド・不変条件）/ `state-machine.md`

## モード判定
- `$0` が `tdd-` → ワークフローモード（`completed_cycles` から `test_files` 収集。`$1` でファイル限定）。
- `$0` がファイルパス（`.test.ts` / `.test.tsx`）→ スタンドアロン（`test_files=[$0]`、`workflow_id="standalone-{date}"`）。
- ワークフローモードの入口ゲート: `current-cycle.json` が不在（サイクル進行中でない）かつ `coverage_review` が記録済みであること。違反なら中断。

## SP1: Assessment（必要性判断）
各テストファイルを Read し計測（Grep）:
- `it(` 数、`render(` / `renderWithProviders(` / `renderHook(` の呼び出し数、各ケースで重複する QueryClient・認証モック・`next/navigation` モックの配線、`server.use(` の重複、個別 `expect(...)` の連続、同一ファクトリ呼び出しの反復、DOM を使っていないのに jsdom で動いているファイル。

推奨基準: ケース数が多い（≥15）かつ最適化機会が2つ以上、または明らかな重複セットアップ。小規模はスキップ（サマリして終了）。

## SP2: Analysis（集約候補）
- render ヘルパへの集約: 各ケースで手書きしている `QueryClientProvider` や認証モックの配線を `renderWithProviders` / `createWrapper` に寄せる（QueryClient はヘルパの中で毎回新規に作る）。
- `it.each` パラメータ化: 入力と期待値だけが違う類似ケース（lib の境界値、バリデーションの各違反パターン、props の表示分岐）を `it.each([...])` に集約。
- セットアップの巻き上げ: 各ケースで重複するファクトリ・モック定義を `beforeEach` やヘルパ関数へ。ケース間で共有される可変状態を作らない（作るなら `beforeEach` 内で毎回新規化）。
- MSW handler の重複解消: 同じ正常系の `server.use(...)` の反復を共通 handler に寄せる（異常系の上書きは各テストに残す）。
- node 環境への切り替え: DOM を使わない `lib` / `server-action` / `route-handler` / `api-client` のテストに `// @vitest-environment node` を付ける（jsdom の起動が無くなり速くなる）。
- アサーションの集約: 同じ表示状態に対する観点の確認を1ケースにまとめる（正常系と異常系をまたぐ統合は不可）。

各候補の独立性を確認（QueryClient は毎回新規、`server.resetHandlers()`、モックは毎回戻す、fake timers を戻す、DOM は `cleanup`、モジュールレベルの状態を共有しない）。順序依存が生まれるものは集約不可。

## SP3: Planning（承認・必須）
最適化ステップ（対象・変更・削減見込み）とリスク（失敗時の原因特定が難しくなる、`it.each` の可読性低下、ヘルパに隠れて何が配線されているか見えにくくなる）を提示。
ユーザー承認まで SP4 を開始しない・ファイル変更しない: `[Enter/y] 全実行 / [e] 番号指定 / [n] キャンセル`。

## SP4: Execution（適用＋独立性検証）
1. ベースライン: `pnpm vitest run {paths}`（全 pass 必須。失敗なら中断）。実行時間・ケース数を記録。
2. 各ステップを Edit で適用。
3. 再実行（全 pass）＋ 独立性検証:
   - 単一ケース実行: `pnpm vitest run {path} -t "{ケース名}"` で代表ケースが単独で pass すること。
   - ランダム順序: `pnpm vitest run {path} --sequence.shuffle`（複数回）。
   - 失敗＝独立性破壊 → そのステップを Edit でロールバックし次のステップへ。

## SP5: Verification（メトリクス・レポート）
Before/After（ケース数・render 数・実行時間）を比較。
`.claude/tdd-workflow/optimization-report-{workflow_id}-{date}.md` に Write（メトリクス表・実行ステップ・独立性検証結果）。最終サマリを簡潔表示。

## 原則
- 独立性を最優先する（単一ケース実行・`--sequence.shuffle` で pass。共有可変状態を作らない。破壊したらロールバック）。
- 統合は順序に依存しないものに限る（正常系/異常系混在は統合しない）。
- role 取得・user-event の作法は崩さない（最適化のために `data-testid` や `fireEvent` に置き換えない）。
- 承認必須（SP3 で承認を得てから SP4）。
