---
name: tdd-refactor
description: TDD の Refactor フェーズ（あらゆる言語向け）。テストを緑に保ったまま、重複・命名・責務分解・データアクセス効率・エラー処理の一貫性・lint を改善する。言語固有の観点は project-settings.md から読む。通常は /tdd から呼ばれる。
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
  - input: /tdd-refactor tdd-20260613-101500
    description: Execute Refactor phase for the current cycle
---

TDD の Refactor フェーズ。動作を変えずにコード品質を改善し、テストが引き続き pass することを確認する。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/project-settings.md`（lint・言語固有の慣習・テスト実行コマンド）/ `workflow-schema.md` / `state-machine.md`

> 原則: ✅内部改善 ❌新機能 ❌動作変更 ❌新規テスト追加（次サイクルの Red で）。

## 入口ゲート
`current-cycle.json` を Read。`phase=="green"`、`implementation_files` 非空、`updated_at` 非空。違反なら `/tdd-green {id}` 案内し中断。

## 1. 対象読み込み
`implementation_files` と `test_file_path` を Read。

## 2. 改善（該当するものだけ・言語非依存の観点）

以下を上から順に検討する。該当しないものは無理に適用しない（変更しないことも正しい判断）。

1. 重複の除去: 同一ロジックの重複（今サイクルで生まれたもの、既存との重複）を抽出・共通化する。ただし2回目の重複までは待つ（早すぎる抽象化はしない）。
2. 命名: 1文字変数・`data`/`info`/`tmp`/`util` のような無意味名を、役割を表す名前に。
3. 関数/モジュールの分解: 責務過多（1つの関数が取得・変換・判定・副作用を兼ねる）を分割。深いネスト・長い条件式を early return / 述語関数へ。
4. データアクセスの効率: ループ内での I/O・クエリ・API 呼び出し（N+1 型の非効率）をまとめる。計算の重複をキャッシュ/事前計算に。
5. エラー処理の一貫性: 既存のエラー処理方針（例外 / 戻り値 / Result 型）に揃える。握り潰しを解消する。
6. 言語固有の観点: project-settings の「言語固有の慣習」に書かれた項目を適用する（そのリポで重視されている作法が唯一の正解）。
7. lint / 静的解析: project-settings の `{{LINT_FIX}}` / `{{STATIC_CHECK}}` を実行。未導入なら実行しない（存在しないコマンドを叩かない）。

> テストコードのリファクタは可（可読性・重複の除去）。ただしテストケースの追加・削除・アサーションの意味の変更は不可。

## 3. テスト維持確認
project-settings の `{{TEST_ONE_FILE}}` を実行し、全 pass を維持していることを確認する。`{{STATIC_CHECK}}` があれば型崩れも確認。

失敗したら参照ミス（抽出したシグネチャ・import・命名）を修正、または `[r]修正 / [u]ロールバック / [s]停止`。

## 4. 状態更新
`current-cycle.json` を Edit: `phase:"refactor"`, `refactor_details`（適用した観点をキーに: `duplication` / `naming` / `decomposition` / `data_access` / `error_handling` / `language_specific` / `linter`。空オブジェクト不可。何もなければ `{"note":"no refactor needed"}`）, `updated_at`。

## 5. サマリ（簡潔）
適用した改善観点と対象 / 全 pass 維持 / lint・静的解析の結果 / 次は Evac(review)→Commit。→ 自動遷移（承認ゲート②は tdd 側）。

## 注意
- 振る舞いを変える改善は Refactor ではない。仕様変更に踏み込む必要が見えたら、実施せず停止条件#2（設計判断）として報告する。
- 大規模な構造変更（レイヤー追加・依存の向きの変更）はこのフェーズのスコープ外。提案として報告し、別タスクに分ける。
