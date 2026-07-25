---
name: tdd-red
description: Red phase - Write ONE failing test in any language, following the repo's existing test conventions and project-settings.md, then confirm it fails as expected
argument-hint: <workflow_id> [test_file_path]
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
examples:
  - input: /tdd-red tdd-20260613-101500
    description: Execute Red phase for the current cycle
---

TDD の Red フェーズ。**今サイクルのテストを1つだけ**追加し、期待通り失敗することを確認する。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/project-settings.md`（**テスト実行コマンド**・配置/命名・**独立性の担保方法**・**言語固有の慣習**・不変条件）
- `.claude/skills/_shared-tdd/workflow-schema.md` / `state-machine.md`

> 🔴 **一度に1テストケースのみ**。複数追加は不変条件違反。
> ⚙️ **コマンドは project-settings のものだけを使う**。書かれていなければ推測せず停止（停止条件#8）。

## 入口ゲート（cycle 2 以降）
`current-cycle.json` が**存在しないこと**を Read で確認（存在＝前サイクル未完了 → `/tdd-commit {id}` 案内し中断）。`completed_cycles` 長 == `current_cycle - 1` を確認。

## 1. コンテキスト
`workflow-{id}.json` を Read（`target_files`, `patterns`, `current_cycle`, `user_instructions`）。`todo_task_id` で TaskGet し `cycle_plan` の該当エントリ（`title`, `kind`）を特定。

## 2. テストファイル決定
`$1` 指定があればそれ。無ければ project-settings の「テスト配置と命名規則」に従って決定（**既存ファイルへの追記を優先**、無ければ新規）。
- 配置（co-located / 別ツリー / 種別サブディレクトリ）とファイル名パターンは project-settings のとおり。
- 既存の命名に**揺れがある場合は Glob で数え、多数派に合わせる**。

## 3. 既存テストの慣習を抽出（**汎用版の最重要ステップ**）
テストを書く前に、**対象に最も近い既存テストを 1〜2 件 Read** する（`patterns.test_case_style` があってもここで実物を再確認する）。抽出する observable:
- ケース記述の構文と命名（何を主語に、どういう文体で書くか）
- セットアップ/ティアダウンの書き方（＝独立性の担保手段の実装形）
- アサーションのスタイルと粒度
- テストデータの作り方（factory / fixture / リテラル）
- 外部依存のモックの張り方

**一般論の「ベストプラクティス」を持ち込まず、このリポの流儀に揃える**（不変条件#4）。既存と異なる書き方をする必要がある場合は、理由を明示して停止し確認する。

## 4. 影響確認（critical）
変更が既存テストを壊さないか確認する。特に**公開インターフェイスの変更**（関数シグネチャ・型・エクスポート名・スキーマ・列挙値）は要注意：参照している既存テストを Grep し、必要なら本サイクルで**合わせて更新**する（振る舞いの意味は変えない）。

## 5. テスト追加
今サイクルの `cycle_plan` エントリに対応する**1ケースだけ**を追加。
- project-settings の「言語固有の慣習」を守る。
- 独立性の担保方法（トランザクションロールバック / 状態リセット / モックリセット等）を必ず実装形に落とす。
- 正常系・異常系・境界は**別サイクル**に分ける（1ケース1サイクル）。

## 6. 失敗確認
project-settings の `{{TEST_ONE_CASE}}`（単一ケース実行）を使う。`{path}`/`{case}`/`{line}` を実値に置換して実行。

期待される失敗: 未定義（関数/型/モジュール/エンドポイント）、値の不一致、期待した例外が出ない、スキーマ/契約の不一致。
**予期しない失敗**（構文エラー・import/パス誤り・セットアップ漏れ・テスト自体のバグ）は**テスト側を修正して再実行**。実装を書き始めてはいけない。

## 7. 状態更新
`current-cycle.json` を workflow-schema 準拠で Write（`phase:"red"`, `test_file_path`, **`test_case_id`**（単一ケース実行に使う識別子）, `test_details`(error_type/message), `created_at`/`updated_at`）。
**自己検証**: Read で `phase=="red"`・`updated_at` 更新を確認。

## 8. サマリ（簡潔）
テストファイル / 追加した1ケース / 期待通りの失敗（エラー種別）/ **踏襲した既存慣習**（どのファイルを参考にしたか）/ 次は Green。承認ゲート①は state-machine に従う（tdd 側が判断）。

## エラー
- **テスト実行コマンドが project-settings に無い**: 推測で組み立てず、`/tdd-project-settings-update` を案内して停止。
- テストファイル決定不能: `$1` 明示 or タスクに対象名の追記を案内。
- 参考にできる既存テストが無い: その旨を提示し、project-settings の「テスト配置と命名規則」「言語固有の慣習」のみを基準にする旨を確認（**停止**）。このケースでは**最初のテストがリポの流儀を決める**ため慎重に。
- 独立性の担保が実装できない（手段が不明）: 停止条件#2（設計判断）として報告。
