---
name: tdd-commit
description: TDD の Commit フェーズ。完了したサイクルを cargo fmt / clippy の pre-commit hook に従ってコミットし（マイグレーション・.sqlx のオフラインデータも含める）、サイクル状態をアーカイブする。通常は /tdd から呼ばれる。
argument-hint: <workflow_id>
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(git:*)
  - Bash(cargo:*)
  - Bash(make:*)
  - Bash(just:*)
  - Bash(rm .claude/tdd-workflow/:*)
  - Bash(date:*)
examples:
  - input: /tdd-commit tdd-20260613-101500
    description: Execute Commit phase for the current cycle
---

TDD の Commit フェーズ。完了サイクルを Git コミットし、サイクル状態をアーカイブする。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/commit-convention.md`（署名・メッセージ・hook 準拠・機密チェック規約）
- `.claude/skills/_shared-tdd/workflow-schema.md` / `project-settings.md`

## 入口ゲート
`current-cycle.json` を Read。`phase=="refactor"`、`refactor_details` 非空、`implementation_files` 非空。違反なら `/tdd-refactor {id}` 案内し中断。
`workflow-{id}.json` を Read（`task_title`, `current_cycle`, `total_cycles`, `cycle_plan`, `completed_cycles`）。

## 0. 中断からの再開判定
前回の tdd-commit がコミットの後で中断していると、`current-cycle.json` は `phase:"refactor"` のまま残る。このままコミットからやり直すとコミットするものが無く、アーカイブをやり直すと `completed_cycles` に同じサイクルが二重に入る。そこで、先にどこまで済んでいるかを判定する。
- `completed_cycles` 末尾の `cycle_number` が `current-cycle.json` の `cycle_number` と同じ → アーカイブまで済んでいる。コミットとアーカイブは飛ばし、「current-cycle.json の削除」から続ける。
- 上に当てはまらず、次の3つがすべて成り立つ → コミットまで済んでいる。HEAD の SHA を今サイクルのコミットとして使い、「アーカイブ」から続ける。
  - `git status --short` に、今サイクルのファイル（`test_file_path` / `implementation_files`）の未コミット変更が無い
  - `git log -1 --name-only` の HEAD コミットに、それらのファイルが含まれている
  - HEAD のコミット時刻が `current-cycle.json` の `created_at` より後
- どちらでもなければ、中断はコミット前なので通常どおり 1 から進める。一部のファイルだけコミット済みなど判定がつかないときは、状況を提示して停止する。

## 1. 変更確認
`git branch --show-current`（命名規約違反は warning のみ）。`git status --short` / `git diff`。
今サイクルの関連ファイルを特定（テスト（inline なら実装ファイルと同一）/ route / service / repository / domain / `migrations/` / `.sqlx/` / `Cargo.lock` / `Cargo.toml`（依存追加時）/ フェイク・ビルダー / `insta` の `*.snap`）。
`.snap.new` が残っていれば `cargo insta accept`（承認済みの変更のみ）か削除して、未確定スナップショットをコミットに含めない。

## 2. コミットメッセージ作成
commit-convention に従う（日本語・型プレフィックス・署名はバージョン無し `Co-Authored-By: Claude <noreply@anthropic.com>`）。サイクル内容を1行サマリ、必要なら詳細箇条書き（`cycle_plan` の `title` 参照）。

## 3. 事前検査（hook が無いリポでは必須）
project-settings の CI / hook 節を確認する。pre-commit hook が無いリポでは、コミット前に静的解析を手動で通す（hook があるリポでも通しておくと hook で弾かれない）:
```bash
cargo fmt --all && cargo clippy --all-targets -- -D warnings   # justfile / Makefile に lint レシピがあればそれを使う
```
警告は実装で解消する（`#[allow(clippy::...)]` で黙らせない。解消できなければ停止条件#8）。

## 4. 機密チェック → 個別ステージング
commit-convention の機密チェック（`.env`/認証情報/APIキー/`DATABASE_URL` などの接続文字列/PII。検出時は停止）。
個別 `git add <path>`（`git add .`/`-A` 禁止）。`migrations/` と `.sqlx/`・`Cargo.lock`・フェイク・スナップショットも忘れず含める（実装だけコミットすると CI の `SQLX_OFFLINE` ビルドや他メンバーの環境が壊れる）。

## 5. コミット（heredoc・hook 準拠）
```bash
git commit -m "$(cat <<'EOF'
{サマリー行}

{詳細（任意）}

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```
`--no-verify` は使わない（→ commit-convention）。`git log -1 --format="%H %s"` で SHA 取得。

### pre-commit hook で失敗した場合（必須リカバリ）
pre-commit / lefthook（または cargo-husky の precommit-hook feature）で `cargo fmt --check` / `cargo clippy -- -D warnings` が走る。ブロックされたら：
1. エラーを特定（rustfmt の差分 / clippy の warning / コンパイルエラー）。
2. 修正: `cargo fmt --all` / clippy 警告は実装で解消（`#[allow(clippy::...)]` で黙らせない）。
3. 修正ファイルを `git add` し直して再コミット（`--no-verify` で回避しない）。
4. 解決不能なら state-machine 停止条件#7 として状態保存し報告。


## 6. アーカイブ（workflow JSON 更新・スキーマ準拠）
`workflow-{id}.json` を Edit（workflow-schema 準拠）: `completed_cycles` に今サイクル追記（`cycle_number`, `title`, `commit`(SHA), `test_file_path`, `test_module_path`, `test_name`, `implementation_files`。Optimize が単一ケース実行に使う）、`current_cycle` +1、`updated_at` 更新、`status` は `in_progress`（全完了時は tdd 側 Phase6 で `done`）。

## 7. current-cycle.json の削除
```bash
rm .claude/tdd-workflow/current-cycle.json
```
次サイクルの Red はこのファイルが無いことを入口条件にしている。不在の確認は 8 の検証でまとめて行う。

## 8. 検証（state-machine の Commit 検証ゲートと対応）
`git log -1 --format="%H"` 非空 / `completed_cycles` 末尾 `commit` == SHA・`current_cycle` == 旧+1 / `current-cycle.json` 不在。いずれか失敗なら状態保存し中断、再実行を案内。

## 9. サマリ（簡潔）
SHA / コミットメッセージ / コミットしたファイル / 進捗 `{current_cycle-1}/{total_cycles}`。
最終サイクルなら「push すれば CI が `cargo test` / `cargo clippy` / `cargo fmt --check` を実行」と案内。→ サイクル境界の挙動は tdd（run_mode）に従う。
