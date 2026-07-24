---
name: tdd-optimize
description: Post-TDD test optimization for taskcli pytest tests with independence guarantees (assess → analyze → plan → execute → verify). Edits files after user approval.
argument-hint: <workflow_id_or_test_file_path> [test_file_path]
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(docker:*)
  - Bash(git:*)
  - Grep
  - Glob
examples:
  - input: /tdd-optimize tdd-20260613-101500
    description: Optimize all tests for the workflow
  - input: /tdd-optimize taskcli/tests/test_task_schemas.py
    description: Standalone mode - optimize a single test file
---

TDD 完了後の pytest テスト最適化。**テストの独立性を保ったまま**、重複 fixture 読み込み・冗長 assert・類似テスト関数を集約し可読性/保守性を上げる。

> このスキルは承認後にファイルを編集する（`model: opus` で Edit 可能。旧版は `agent: Explore` 指定で Edit が空振りしていた）。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/project-settings.md`（現行構成・`load_json`・docker 実行・未導入ツール）
- `.claude/skills/_shared-tdd/state-machine.md`

## モード判定
- `$0` が `tdd-` で始まる → ワークフローモード（`workflow-{id}.json` の `completed_cycles` から `test_files` を収集。`$1` 指定でファイル限定）。
- `$0` がファイルパス → スタンドアロンモード（`test_files=[$0]`、`workflow_id="standalone-{date +%Y%m%d-%H%M%S}"`）。

## SP1: Assessment（必要性判断）
各テストファイルを Read し計測（Grep）: `^def test_` 数、`@pytest.mark.parametrize`/`{GROUP}_BASIC_CASES` 数、`load_json\(` 数。
最適化機会パターン：
1. **同一 fixture を3回以上 `load_json`** → parametrize 候補。
2. **3つ以上連続の `assert instance.X == raw["X"]`** → `assert instance.model_dump() == raw` 化。
3. **ハードコード期待値**（fixture から取れる値の直書き）→ 動的取得化。
4. **共通プレフィックスの類似 test 関数3つ以上**（値だけ違う）→ parametrize 集約。
5. **複数箇所の同一ローカル `class _X(StrictModel)`** → ファイル冒頭 or `tests/_helpers.py` へ抽出。

推奨/スキップ基準: 関数数 ≥15 かつ機会2つ以上、または ≥25 で無条件推奨。<10 or 機会なし or 50行未満はスキップ（サマリ表示して終了）。

## SP2: Analysis（集約候補の特定）
parametrize 集約は **(同 fixture) かつ (同モデル/関数) かつ (同じ期待動作) かつ (変更操作だけが異なる)** をすべて満たす場合のみ。
正常系/異常系混在・異なるモデル・部分フィールド比較は集約不可（個別保持）。
各候補の**独立性**を確認（`load_json` は毎回新 dict を返すので参照共有なし。グローバル状態変更・fixture 共有変更があるものは集約不可）。

## SP3: Planning（承認・必須）
最適化ステップ（対象・変更・削減見込み）とリスク（失敗時の ids= 識別、model_dump の差分肥大）を提示。
**ユーザー承認まで SP4 を開始しない・ファイル変更しない**：`[Enter/y] 全実行 / [e] 番号指定 / [n] キャンセル`。

## SP4: Execution（適用＋独立性検証）
1. ベースライン: `cd taskcli && docker compose run --rm app pytest -v {rel_path}`（全 pass 必須。失敗なら中断）。
2. 各ステップを Edit で適用：
   - parametrize 集約（`ids=` で各ケース識別。各エントリは `load_json` で独立 dict）。
   - `model_dump()` 一括比較化。
   - ローカルモデル抽出。
3. 再実行（全 pass）＋ **個別実行で独立性検証**：`pytest -v "{rel_path}::{test}"`、parametrize は `"...::{test}[case_id]"`。
   失敗＝独立性破壊 → そのステップを Edit でロールバック。
4. pytest-random-order は未導入（project-settings）。導入時のみ `-p random_order --random-order` を追加実行、未導入なら個別実行で代替。

## SP5: Verification（メトリクス・レポート）
Before/After（関数数・行数・実行時間）を比較。
`.claude/tdd-workflow/optimization-report-{workflow_id}-{date}.md` に Write（メトリクス表・実行ステップ・独立性検証結果・適用パターン）。
最終サマリを簡潔表示。

## 重要原則
- **独立性は絶対**（個別実行・ランダム順序で可。グローバル状態変更/ fixture 共有変更は禁止。破壊したらロールバック）。
- **parametrize 集約は SP2 の4条件すべて充足時のみ**。
- **承認必須**（SP3 で承認を得てから SP4）。
