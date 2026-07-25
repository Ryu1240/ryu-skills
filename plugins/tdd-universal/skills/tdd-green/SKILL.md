---
name: tdd-green
description: Green phase - Minimal implementation in any language to pass the failing test, following project-settings.md conventions
argument-hint: <workflow_id>
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
examples:
  - input: /tdd-green tdd-20260613-101500
    description: Execute Green phase for the current cycle
---

TDD の Green フェーズ。今サイクルの失敗テストを通す**最小限の実装**を行う。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/project-settings.md`（**不変条件**・**言語固有の慣習**・テスト実行コマンド）/ `workflow-schema.md` / `state-machine.md`

> 原則: ✅テストを通す最小実装 ❌先回り実装 ❌リファクタ（次フェーズ）❌新規テスト追加。

## 入口ゲート
`current-cycle.json` を Read。`phase=="red"`、`test_details.error_type` 非空。違反なら `/tdd-red {id}` 案内し中断。

## 1. 失敗の特定
`current-cycle.json` の `error_type` / `error_message` / `test_file_path` から、不足している実装（関数/型/モジュール/エンドポイント/設定/依存）を特定する。

## 2. 実装（最小）
- **既存実装の慣習を踏襲する**: 対象に最も近い既存実装を Read し、レイヤー構成・命名・エラー処理・戻り値の型/形を揃える（不変条件#4 は実装側にも効く）。
- project-settings の「言語固有の慣習」を守る。
- **最小実装のみ**: テストが要求していない分岐・引数・設定・抽象化を先回りで作らない。共通化や抽出は Refactor フェーズで行う。
- 生成物（コード生成・スキーマ生成）を伴う場合は、project-settings の慣習に従って生成コマンドを実行し、追跡対象なら成果物も記録する。

## 3. テスト pass 確認
project-settings の `{{TEST_ONE_FILE}}`（単一ファイル実行）を使う。

全件 pass を確認。失敗したら原因を特定して修正（最大3回までリトライ）。3回を超えたら state-machine 停止条件#6 として状態保存し報告する。
- 典型的な原因: セットアップ/独立性の担保漏れ、モックの未登録、型/スキーマの不一致、依存の未追加、パス解決の誤り。
- **テストを都合よく書き換えて通してはいけない**（Red で承認済みのテストは変えない）。テストの誤りが原因と判断した場合は停止して報告する。

## 4. 状態更新
`current-cycle.json` を Edit: `phase:"green"`, `test_details`(passed/total/failed:0), `implementation_files`(非空。生成物も含める), `retry_count`。
**自己検証**: `phase=="green"` かつ `implementation_files` 非空を Read で確認。

## 5. サマリ（簡潔）
実装したファイルと内容 / 生成物・依存追加の有無 / 全 pass（リトライ回数）/ 次は Refactor。→ 自動遷移。

## 注意
- **型・契約を握りつぶさない**（型チェックの抑制コメント・例外の握り潰し・スキーマへの嘘を書かない）。必要なら `{{STATIC_CHECK}}` で確認する。
- **依存の追加は設計判断**: 新規ライブラリを入れる必要が生じたら、停止条件#2 として提示し承認を得る。
