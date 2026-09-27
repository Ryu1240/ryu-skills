---
name: tdd-optimize
description: Post-TDD test optimization for order-api (Vitest) with independence guarantees (assess → analyze → plan → execute → verify). Edits files after user approval.
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
  - input: /tdd-optimize src/routes/orders.test.ts
    description: Standalone mode - optimize a single test file
---

TDD 完了後の order-api 向けテスト最適化。**テストの独立性を保ったまま**、重複セットアップ・冗長アサーション・類似ケースを集約し、実行速度と可読性を上げる。

> このスキルは承認後にファイルを編集する（`model: opus` で Edit 可能）。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/project-settings.md`（テストコマンド・**不変条件**）/ `state-machine.md`

## モード判定
- `$0` が `tdd-` → ワークフローモード（`completed_cycles` から `test_files` 収集。`$1` でファイル限定）。
- `$0` がファイルパス（`.test.ts`）→ スタンドアロン（`test_files=[$0]`、`workflow_id="standalone-{date}"`）。
- ワークフローモードの入口ゲート: `current-cycle.json` が不在（サイクル進行中でない）かつ `coverage_review` が記録済みであること。違反なら中断。

## SP1: Assessment（必要性判断）
各テストファイルを Read し計測（Grep）:
- `it(` 数、`request(app)` 等の HTTP 呼び出し数、`beforeEach` 外での重複セットアップ、個別 `expect(...).toBe/toEqual` の連続、同一ファクトリ呼び出しの反復、`vi.mock` の重複定義。

推奨基準: ケース数が多い（≥15）かつ最適化機会が2つ以上、または明らかな重複セットアップ。小規模はスキップ（サマリして終了）。

## SP2: Analysis（集約候補）
- **セットアップの巻き上げ**: 各ケースで重複する準備（app 構築・ファクトリ・モック定義）を `beforeEach` やヘルパ関数へ。**ケース間で共有される可変状態を作らない**（作るなら `beforeEach` 内で毎回新規化）。
- **`it.each` パラメータ化**: 入力と期待値だけが違う類似ケース（バリデーションの各違反パターン等）を `it.each([...])` に集約。**Vitest の推奨形**。
- **アサーションの集約**: 3つ以上の個別フィールド検証を `expect(res.body).toMatchObject({...})` に。ただし失敗時の可読性が落ちすぎない範囲で。
- **重複 HTTP 呼び出しの統合**: 同一リクエスト・同一セットアップに対する複数ケースを1ケースで複数観点検証に統合（**正常系と異常系をまたぐ統合は不可**）。
- **ファクトリ集約**: 同種データの反復生成をまとめて生成するヘルパへ。

各候補の独立性を確認（DB ロールバック維持、モックは毎回 restore、fake timers を戻す、モジュールレベルの状態を共有しない）。順序依存が生まれるものは**集約不可**。

## SP3: Planning（承認・必須）
最適化ステップ（対象・変更・削減見込み）とリスク（失敗時の原因特定が難しくなる、`it.each` の可読性低下）を提示。
**ユーザー承認まで SP4 を開始しない・ファイル変更しない**: `[Enter/y] 全実行 / [e] 番号指定 / [n] キャンセル`。

## SP4: Execution（適用＋独立性検証）
1. **ベースライン**: `yarn vitest run {paths}`（全 pass 必須。失敗なら中断）。実行時間・ケース数を記録。
2. 各ステップを Edit で適用。
3. 再実行（全 pass）＋ **独立性検証**:
   - **単一ケース実行**: `yarn vitest run {path} -t "{ケース名}"` で代表ケースが単独で pass すること。
   - **ランダム順序**: `yarn vitest run {path} --sequence.shuffle`（複数回）。
   - **並列実行の確認**: Vitest は既定でファイル単位並列。DB を共有するテストは `--no-file-parallelism` 無しで壊れないか確認（壊れるならロールバック設計の見直しを提案）。
   - 失敗＝独立性破壊 → そのステップを Edit で**ロールバック**し次のステップへ。

## SP5: Verification（メトリクス・レポート）
Before/After（ケース数・HTTP 呼び出し数・実行時間）を比較。
`.claude/tdd-workflow/optimization-report-{workflow_id}-{date}.md` に Write（メトリクス表・実行ステップ・独立性検証結果）。最終サマリを簡潔表示。

## 重要原則
- **独立性は絶対**（単一ケース実行・`--sequence.shuffle`・並列実行で pass。共有可変状態を作らない。破壊したらロールバック）。
- **統合は順序非依存を厳守**（正常系/異常系混在は統合しない）。
- **承認必須**（SP3 で承認を得てから SP4）。
