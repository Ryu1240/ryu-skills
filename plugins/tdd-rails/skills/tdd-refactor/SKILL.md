---
name: tdd-refactor
description: TDD の Refactor フェーズ。テストを緑に保ったまま、N+1・association の dependent・サービス抽出・命名・Rubocop を改善する。通常は /tdd から呼ばれる。
argument-hint: <workflow_id>
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
  - Bash(date:*)
examples:
  - input: /tdd-refactor tdd-20260613-101500
    description: Execute Refactor phase for the current cycle
---

TDD の Refactor フェーズ。動作を変えずにコード品質を改善し、テストが引き続き pass することを確認する。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/project-settings.md`（lint）/ `workflow-schema.md` / `state-machine.md`

> 原則: ✅内部改善 ❌新機能 ❌動作変更 ❌新規テスト追加（次サイクルの Red で）。

## 入口ゲート
`current-cycle.json` を Read。`phase=="green"`、`implementation_files` 非空、`updated_at` 非空。違反なら `/tdd-green {id}` 案内し中断。

## 1. 対象読み込み
`implementation_files` と `test_file_path` を Read。

## 2. 改善（該当時のみ）

### Rails
- N+1 対策（必須）: テスト実行時の Bullet 警告を確認（`USE eager loading detected`）→ `.includes(:assoc, ...)` を追加。`AVOID eager loading` なら不要な includes を削除。最終的に Bullet 警告ゼロにする。
- Association の `dependent` オプション: `has_many`/`has_one` に未設定があれば、ビジネスロジックに応じて設定（親削除で子も不要→`:destroy` / 子があれば親削除を防ぐ→`:restrict_with_error` / 子を残す→`:nullify`）。不明なら設定せず停止条件#2（設計判断）として報告。
- サービス抽出: action が20行超 / 複数モデル操作 / トランザクション / 外部API なら `app/services/{resource}/{action}_service.rb`（stateless・`call` メソッド）へ抽出。単純CRUDは抽出しない。
- 命名改善（1文字変数・曖昧名を用途名に）。
- Rubocop: `bundle exec rubocop -a {files}`（自動修正。Metrics系の手動対応は必要に応じて）。

## 3. テスト維持確認
- `bundle exec rspec {spec_path}`（Bullet 警告がないことも確認）

全件 pass を確認。失敗したら includes/dependent/サービスシグネチャ/命名の参照ミスを修正、または `[r]修正/[u]ロールバック/[s]停止`。

## 4. 状態更新
`current-cycle.json` を Edit: `phase:"refactor"`, `refactor_details`（n1_fixes / dependent_options / service_extractions / naming / linter。空オブジェクト不可。何もなければ `{"note":"no refactor needed"}`）, `updated_at`。

## 5. サマリ（簡潔）
実施した改善（N+1/dependent/service/命名/lint 件数）/ 全件 pass / 次は Evac(review)→Commit。→ 自動遷移（承認ゲート②は tdd 側）。
