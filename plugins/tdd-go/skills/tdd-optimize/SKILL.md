---
name: tdd-optimize
description: Post-TDD test optimization for shipment-api (Go, standard testing) with independence guarantees (assess → analyze → plan → execute → verify). Edits files after user approval.
argument-hint: <workflow_id_or_test_file_path> [test_file_path]
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(go:*)
  - Bash(gofmt:*)
  - Bash(goimports:*)
  - Bash(make:*)
  - Grep
  - Glob
examples:
  - input: /tdd-optimize tdd-20260613-101500
    description: Optimize all tests for the workflow
  - input: /tdd-optimize internal/handler/shipment_test.go
    description: Standalone mode - optimize a single test file
---

TDD 完了後の shipment-api 向けテスト最適化。**テストの独立性を保ったまま**、重複セットアップ・冗長アサーション・類似ケースを集約し、実行速度と可読性を上げる。

> このスキルは承認後にファイルを編集する（`agent: Explore` を付けない — Explore は Write/Edit を持たず、承認後の適用が空振りする）。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/project-settings.md`（テストコマンド・**不変条件**）/ `state-machine.md`

## モード判定
- `$0` が `tdd-` → ワークフローモード（`completed_cycles` から `test_files` 収集。`$1` でファイル限定）。
- `$0` がファイルパス（`_test.go` で終わる）→ スタンドアロン（`test_files=[$0]`、`workflow_id="standalone-{date}"`）。
- 各テストファイルから**パッケージディレクトリ**を求めておく（`go test` はディレクトリ単位。**必ず `./` 始まり**。`internal/handler` は標準ライブラリ扱いで `is not in std` になる）。
- ワークフローモードの入口ゲート: `current-cycle.json` が不在（サイクル進行中でない）かつ `coverage_review` が記録済みであること。違反なら中断。

## SP1: Assessment（必要性判断）
各テストファイルを Read し計測（Grep）:
- `func Test` 数と `t.Run(` 数、個別 `t.Run` で同じ形の準備（フェイク生成・`httptest.NewRequest`・DB セットアップ）が繰り返されている箇所、`if got != want { t.Errorf }` の連続（構造体フィールドごとの個別比較）、同一ファクトリ呼び出しの反復、`t.Helper()` の無いヘルパ、テーブル駆動にできるのに個別 `t.Run` で並んでいるケース。

推奨基準: ケース数が多い（≥15）かつ最適化機会が2つ以上、または明らかな重複セットアップ。小規模はスキップ（サマリして終了）。

## SP2: Analysis（集約候補）
- **テーブル駆動化**: 入力と期待値だけが違う類似ケース（バリデーションの各違反パターン等）を `tests := []struct{ name string; ... }` + `for _, tt := range tests { t.Run(tt.name, ...) }` に集約。**Go の推奨形**。既存の `-run 'TestX/sub'` が通るようサブテスト名は維持する。
- **セットアップのヘルパ抽出**: 各ケースで重複する準備を `t.Helper()` 付きのヘルパ関数（`newTestHandler(t)` 等）へ。後片付けはヘルパ内で `t.Cleanup` に登録。**ケース間で共有される可変状態を作らない**（パッケージレベル変数に置かず、ヘルパが毎回新規に生成）。
- **`cmp.Diff` による一括比較**: 3つ以上のフィールド個別比較を `if diff := cmp.Diff(want, got); diff != "" { t.Errorf("mismatch (-want +got):\n%s", diff) }` に（testify のリポなら `assert.Equal`）。時刻や ID は `cmpopts.IgnoreFields` で除外。
- **重複リクエストの統合**: 同一リクエスト・同一セットアップに対する複数ケースを1ケースで複数観点検証に統合（**正常系と異常系をまたぐ統合は不可**）。
- **`t.Parallel()` の付与**: 共有可変状態（DB の同一レコード・パッケージ変数・`httptest.NewServer` の共有）が無いと確認できたケースにのみ付ける。**Go 1.22 未満はループ変数のキャプチャ（`tt := tt`）が必須**（`go.mod` の `go` ディレクティブで判定）。

各候補の独立性を確認（DB ロールバック維持、`t.Cleanup` で後片付け、パッケージレベルの状態を共有しない）。順序依存が生まれるものは**集約不可**。

## SP3: Planning（承認・必須）
最適化ステップ（対象・変更・削減見込み）とリスク（失敗時の原因特定が難しくなる、テーブルが巨大化して可読性が落ちる、`t.Parallel()` によるフレーク）を提示。
**ユーザー承認まで SP4 を開始しない・ファイル変更しない**: `[Enter/y] 全実行 / [e] 番号指定 / [n] キャンセル`。

## SP4: Execution（適用＋独立性検証）
1. **ベースライン**: `go test {pkgs} -count=1`（全 pass 必須。失敗なら中断）。実行時間（`-v` の `--- PASS ... (0.12s)` / `ok ... 1.234s`）・ケース数を記録。
2. 各ステップを Edit で適用し、`gofmt -w` を通す。
3. 再実行（全 pass）＋ **独立性検証**:
   - **単一ケース実行**: `go test {pkg} -run '^{TestX}$/^{sub_case}$' -count=1 -v` で代表ケースが**それだけ**走って pass すること（`=== RUN` が 1 サブテスト分だけ出る。前方一致だと他のケースも走る。`test_name` は `completed_cycles` から取る）。
   - **ランダム順序**: `go test {pkg} -count=1 -shuffle=on`（複数回。`-shuffle` の seed が出力されるので失敗時は `-shuffle={seed}` で再現）。**`-shuffle` はトップレベルの `TestXxx` の順序しか変えない**ので、テーブル駆動のサブテスト間の順序依存は上の単一ケース実行で検証する。
   - **レース検出**: `go test {pkg} -count=1 -race`（`t.Parallel()` を付けたケースは特に必須）。
   - **フレーク検出**: `go test {pkg} -count=3`。
   - **並列度の両極**: `go test {pkgs} -count=1 -p 1`（パッケージ間を直列化）と `go test {pkg} -count=1 -parallel 1`（`t.Parallel()` サブテスト間を直列化）の双方、および既定並列で pass（DB を共有するテストが直列でしか通らないならロールバック設計の見直しを提案）。
   - 失敗＝独立性破壊 → そのステップを Edit で**ロールバック**し次のステップへ。

## SP5: Verification（メトリクス・レポート）
Before/After（ケース数・ヘルパ数・実行時間）を比較。
`.claude/tdd-workflow/optimization-report-{workflow_id}-{date}.md` に Write（メトリクス表・実行ステップ・独立性検証結果）。最終サマリを簡潔表示。

## 重要原則
- **独立性は絶対**（単一ケース実行・`-shuffle=on`・`-race`・`-count=3` で pass。共有可変状態を作らない。破壊したらロールバック）。
- **統合は順序非依存を厳守**（正常系/異常系混在は統合しない）。
- **承認必須**（SP3 で承認を得てから SP4）。
- `-count=1` を忘れると、外部状態（DB）だけが変わったケースでテストキャッシュの成功結果が返り「実行されていないのに ok」になる。
