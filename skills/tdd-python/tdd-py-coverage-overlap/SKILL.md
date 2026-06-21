---
name: tdd-py-coverage-overlap
description: Detect semantic test-overlap in taskcli via coverage-context analysis (pytest-cov, line+branch) and propose delete/merge candidates with a coverage-preservation guarantee. Complements tdd-py-optimize (which handles syntactic dup). Edits after approval.
argument-hint: <workflow_id_or_file_path> [test_file_path]
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(docker:*)
  - Bash(git:*)
  - Bash(jq:*)
  - Grep
  - Glob
examples:
  - input: /tdd-py-coverage-overlap tdd-20260613-101500
    description: ワークフローの全テストで担保重複を検知
  - input: /tdd-py-coverage-overlap taskcli/tests/test_task_schemas.py
    description: スタンドアロン - 単一ファイルの担保重複を検知
---

taskcli のテスト群の「**担保内容の重複**」を **Coverage 精密モード**で検知し、削除/統合候補をユーザー承認のうえ適用する。
（旧版の AST / Mutation モードは廃止。AST は過剰検出で実用に耐えず、Mutation は数十分〜時間かかり単発運用専用だったため、**日常運用に適した Coverage 一本**に絞った。）

> このスキルは承認後にファイルを編集する（`model: opus` で Edit 可能）。
> **tdd-py-optimize との違い**: optimize=構文重複（同型 test を parametrize 集約）、本スキル=**セマンティック重複**（命名が違っても line+branch カバレッジ集合が同じ＝実質同じ担保）。両方使うなら **coverage-overlap が先**（削除してから集約）。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd-python/project-settings.md`（現行構成・docker 実行・pytest-cov 未導入）
- `.claude/skills/_shared-tdd-python/state-machine.md`

## 前提ツール: pytest-cov（必須）
Coverage モードは pytest-cov に依存する。**未導入のままでは動かない**（「うまく働かない」の主因）。

## モード判定（引数）
- `$0` が `tdd-` → `workflow-{id}.json` の `completed_cycles` から `test_files`（`$1` で限定）。
- `$0` がファイルパス → `test_files=[$0]`、`workflow_id="standalone-{date +%Y%m%d-%H%M%S}"`。
- **スコープ厳守**: 確定した `test_files` 以外を対象にしない（以降の Grep/Read/pytest はこの集合のみ）。

## SP1: Pre-flight（pytest-cov 確認 + ベースライン）
1. `grep -E "pytest-cov" taskcli/pyproject.toml` で確認。未導入なら提示：
   ```
   pytest-cov が未導入です。Coverage モードには必須です。
   [i] 導入する（pyproject に追加 → イメージ再ビルド） / [n] 中断
   ```
   `[i]` の場合は **2段階**（どちらか欠けると docker 実行で反映されない）:
   - `cd taskcli && docker compose run --rm app poetry add --group dev pytest-cov`
   - `cd taskcli && docker compose build`（依存はイメージに焼かれるため再ビルド必須）
2. ベースライン: `cd taskcli && docker compose run --rm app pytest -v {test_files の rel パス}` 全 pass を確認（失敗なら修正後に再実行を案内し中断）。passed数 / 実行時間 / 各ファイル行数を記録。

## SP2: Collection（coverage コンテキスト取得）
> docker-compose は `.:/app`（taskcli/ ↔ /app）を双方向マウントするので、コンテナ内生成物は **ホストの `taskcli/` 直下**に現れる。パスはそれ前提。

```bash
cd taskcli && docker compose run --rm app sh -c "\
  pytest --cov=taskcli --cov-branch --cov-context=test --cov-report= {test_files rel} && \
  coverage json --show-contexts -o .coverage-contexts.json"
```
- `--cov-branch` 必須（line だけでは if/else の片側担保を見落とす）。
- `--cov-context=test` でテストごとのカバー行が記録される。
- `.coverage-contexts.json` をホストで Read/jq し、各 `test_id` の担保集合を構築：
  ```
  coverage_sets[test_id] = { (file_path, line_no, branch_arc), ... }
  ```
  contexts が空なら pytest-cov の `--cov-context=test` が効いていない → バージョン/設定を確認（トラブルシュート参照）。

## SP3: Analysis（重複/包含）
担保集合（line+branch arc）で判定。**確度は「中」**（カバレッジは assertion の中身を見ないため）：
- **完全重複 (A==B)**: 片方を消しても担保不変。
- **完全包含 (A⊊B)**: A を消しても B が同じ担保を継続。
- **高重複 (Jaccard≥0.9)**: 差分が意味的に必要か要レビュー。
- **parametrize 内重複**: 各エントリの担保集合が一致 → 設計見直し warning（削除はしない）。
検出ゼロなら「担保重複なし」で終了。

## SP4: Planning（承認・必須）
候補ごとに「対象 / 残す側 / 担保集合の Before-After」を提示。
**重要な限界を明示**: カバレッジ一致でも assertion の値が違えば担保は異なる → 削除候補は**人間が assertion 内容を確認**してから承認。
**承認まで SP5 を開始しない・変更しない**：`[Enter/y] 全実行 / [e] 番号指定 / [d] 詳細（担保集合表示） / [n] キャンセル`。

## SP5: Execution & Verification
1. 承認ステップを Edit で適用（削除＝関数ブロック削除 / 統合＝parametrize 集約）。
2. 再実行で全 pass。
3. **担保維持の検証**（必須）: 削除後に再度 coverage を取り、**line+branch 和集合が減っていないこと**を確認。減っていたら該当ステップを Edit でロールバック（その削除は誤判定）。
4. 残テスト3件を個別実行で独立性確認。
5. レポートを **リポジトリルート直下の** `.claude/tdd-workflow/overlap-report-{workflow_id}-{date}.md` に Write（メトリクス表・適用アクション・担保保証検証・残レビュー項目）。CWD が taskcli/ でも配下に書かない（絶対パス推奨）。

## 重要原則
- **スコープ厳守**（`test_files` 外を対象にしない）。
- **担保保証は絶対**（削除後に line+branch 和集合が減ってはならない。減ったらロールバック）。
- **「カバレッジ一致≠担保一致」**（assertion 中身は見えない。削除候補は人間が assertion を確認）。
- **承認必須**。

## トラブルシュート（うまく動かない時）
- `--cov` でエラー / `unrecognized arguments` → pytest-cov 未導入か、`docker compose build` 未実行（イメージに反映されていない）。SP1 の2段階を実施。
- `.coverage-contexts.json` が出ない / contexts が空 → `--cov-context=test` 指定漏れ、または成果物がホストに見えていない（compose の `.:/app` マウントと CWD を確認）。
- 全テストが同一ファイルで担保が粗い → `--cov-branch` で arc を見ているか確認。それでも粗ければ Coverage の限界（assertion 差は見えない）として要レビュー扱い。
